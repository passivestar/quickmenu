import bpy, bmesh, math, bl_math, re, json, os, platform, subprocess
from bpy.props import IntProperty, FloatProperty, StringProperty, BoolProperty, EnumProperty, FloatVectorProperty, BoolVectorProperty, PointerProperty
from mathutils import Vector, Euler, Quaternion, Matrix, Color, noise
from random import random
from functools import reduce

bl_info = {
  'name': 'QuickMenu',
  'version': (2, 4, 6),
  'author': 'passivestar',
  'blender': (3, 3, 0),
  'location': 'Press the bound hotkey in 3D View',
  'description': 'Simplifies access to useful operators and adds new functionality',
  'category': 'Interface'
}

# @Globals

app = {
  "keymaps": [],
  "items": []
}

AXES = [ 'X', 'Y', 'Z' ]
MODAL_SENSITIVITY = 0.01
BOOLEAN_BOUNDARY_EXTEND = 0.0001
RADIUS_TO_VERTICES = 256

# @Util

__location__ = os.path.realpath(
  os.path.join(os.getcwd(), os.path.dirname(__file__)))

def select(obj):
  bpy.ops.object.select_all(action='DESELECT')
  obj.select_set(True)
  bpy.context.view_layer.objects.active = obj

def deselect_object_geometry(obj):
  for v in bmesh.from_edit_mesh(obj.data).verts:
    v.select = False
  bmesh.update_edit_mesh(obj.data)

def get_selected_non_active():
  return [o for o in bpy.context.selected_objects if o != bpy.context.object][0]

def get_selection_and_active_indices():
  selected_indeces = []
  active_indeces = []
  mesh = bpy.context.active_object.data
  bm = bmesh.from_edit_mesh(mesh)
  if not mesh.vertex_colors: mesh.vertex_colors.new()
  for face in [face for face in bm.faces if face.select]:
    for loop in face.loops:
      selected_indeces.append(loop.index)
      if face == bm.faces.active: active_indeces.append(loop.index)
  return (selected_indeces, active_indeces)

def get_paths():
  directory = bpy.path.abspath('//')
  file = bpy.path.basename(bpy.data.filepath).split('.')[0]
  return ( directory, file )

def grid_snap(grid, value):
  return round(value / grid) * grid

def view_vector(left_to_right = False, use_object_transform = True):
  view_matrix = bpy.context.space_data.region_3d.view_matrix
  object_matrix = bpy.context.object.matrix_world if bpy.context.object else Matrix()
  if use_object_transform:
    if bpy.context.mode == 'POSE':
      matrix = view_matrix @ object_matrix @ bpy.context.active_pose_bone.matrix
    else: matrix = view_matrix @ object_matrix
  else:
    matrix = view_matrix
  return (Vector((-1, 0, 0) if left_to_right else (0, 0, 1)) @ matrix).normalized()

def view_snapped_vector(left_to_right = False, use_object_transform = True):
  vec = view_vector(left_to_right, use_object_transform)
  biggest = max(abs(n) for n in vec)
  for i in range(len(vec)): vec[i] = grid_snap(1, vec[i]) if abs(vec[i]) == biggest else 0
  return vec

def axis_by_vector(vector):
  for i in range(3):
    if (vector[i] == 1): return ( AXES[i], False )
    elif (vector[i] == -1): return ( AXES[i], True )

def cursor_to_selected(to_active = False):
  ts = bpy.context.scene.tool_settings
  previous_context = bpy.context.area.type
  bpy.context.area.type = 'VIEW_3D'
  previous_pivot = ts.transform_pivot_point
  ts.transform_pivot_point = 'BOUNDING_BOX_CENTER'
  if to_active:
    bpy.ops.view3d.snap_cursor_to_active()
  else:
    bpy.ops.view3d.snap_cursor_to_selected()
  ts.transform_pivot_point = previous_pivot
  bpy.context.area.type = previous_context

def execute_in_mode(mode, callback):
  previous_mode = 'EDIT' if is_in_editmode() else bpy.context.mode
  bpy.ops.object.mode_set(mode=mode)
  result = callback()
  try: bpy.ops.object.mode_set(mode=previous_mode)
  except: pass
  return result

def make_vertex_group(name):
  bpy.context.object.vertex_groups.new(name=name)
  bpy.ops.object.vertex_group_set_active(group=name)

def calculate_number_of_vertices_by_radius(radius, subsurf=False):
  if subsurf or modifier_exists('SUBSURF') or modifier_exists('MULTIRES'):
    return 6
  radius = max(0, radius)
  return max(6, grid_snap(2, math.log(1 + 0.03 + 0.4 * radius) * RADIUS_TO_VERTICES))

def iterate_islands(operator, callback, restore_selection=False):
  if restore_selection:
    make_vertex_group('qm_iterate_islands_selection')
    bpy.ops.object.vertex_group_assign()
  bpy.ops.mesh.hide(unselected=True)
  bpy.ops.mesh.select_all(action='DESELECT')
  mode = tuple(bpy.context.scene.tool_settings.mesh_select_mode).index(True)
  obj = bpy.context.edit_object
  mesh = obj.data
  bm = bmesh.from_edit_mesh(mesh)
  if mode == 0:
    entities = [e for e in bm.verts if not e.hide]
    bm.verts.ensure_lookup_table()
  elif mode == 1:
    entities = [e for e in bm.edges if not e.hide]
    bm.edges.ensure_lookup_table()
  elif mode == 2:
    entities = [e for e in bm.faces if not e.hide]
    bm.faces.ensure_lookup_table()
  while entities:
    entities[0].select_set(True)
    bpy.ops.mesh.select_linked()
    make_vertex_group('qm_iterate_islands_island_selection')
    bpy.ops.object.vertex_group_assign()
    callback(operator)
    bpy.ops.object.vertex_group_set_active(group='qm_iterate_islands_island_selection')
    bpy.ops.object.vertex_group_select()
    bpy.ops.object.vertex_group_remove()
    bpy.ops.mesh.hide(unselected=False)
    for e in reversed(entities):
      if e.hide: entities.remove(e)
  bpy.ops.mesh.reveal()
  bmesh.update_edit_mesh(mesh)
  bpy.ops.mesh.select_all(action='DESELECT')
  if restore_selection:
    bpy.ops.object.vertex_group_set_active(group='qm_iterate_islands_selection')
    bpy.ops.object.vertex_group_select()
    bpy.ops.object.vertex_group_remove()

def modifier_exists(modifier_type):
  return len([m for m in bpy.context.object.modifiers if m.type == modifier_type]) > 0

def move_modifier_on_top(modifier_name):
  bpy.ops.object.modifier_move_to_index(modifier=modifier_name, index=0)

def add_or_get_modifier(modifier_type, move_on_top=False):
  if modifier_exists(modifier_type):
    for modifier in bpy.context.object.modifiers:
      if modifier.type == modifier_type:
        return modifier
  bpy.ops.object.modifier_add(type=modifier_type)
  modifier = bpy.context.object.modifiers[-1]
  if move_on_top: move_modifier_on_top(modifier.name)
  return modifier

def is_in_editmode():
  return bpy.context.mode == 'EDIT_MESH'

def anything_is_selected_in_editmode(obj = None):
  if obj != None:
    return True in [v.select for v in bmesh.from_edit_mesh(obj.data).verts]
  for o in bpy.context.objects_in_mode:
    if True in [v.select for v in bmesh.from_edit_mesh(o.data).verts]:
      return True
  return False

def anything_is_hidden_in_editmode(obj = None):
  if obj != None:
    return True in [v.hide for v in bmesh.from_edit_mesh(obj.data).verts]
  for o in bpy.context.objects_in_mode:
    if True in [v.hide for v in bmesh.from_edit_mesh(o.data).verts]:
      return True
  return False

def modal_invoke(operator, context, event):
  operator.modal_first_mouse_x = event.mouse_x
  if hasattr(operator, 'on_modal_invoke'):
    operator.on_modal_invoke(context, event)
  context.window.cursor_set('SCROLL_X')
  context.window_manager.modal_handler_add(operator)
  operator.report({'INFO'}, 'modal invoked')
  return {'RUNNING_MODAL'}

def modal_run(operator, context, event, delete=True):
  if event.type in {'MOUSEMOVE', 'LEFT_CTRL', 'RIGHT_CTRL', 'LEFT_SHIFT', 'RIGHT_SHIFT', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
    operator.modal_delta = (event.mouse_x - operator.modal_first_mouse_x) * MODAL_SENSITIVITY
    if delete: bpy.ops.mesh.delete(type='VERT')
    if hasattr(operator, 'on_modal_run'): operator.on_modal_run(context, event)
  elif event.type in {'LEFTMOUSE', 'SPACE'}:
    if hasattr(operator, 'on_modal_finished'):
      operator.on_modal_finished(context, event)
    context.window.cursor_set('DEFAULT')
    operator.report({'INFO'}, 'modal finished')
    return {'FINISHED'}
  elif event.type in {'RIGHTMOUSE', 'ESC'}:
    context.window.cursor_set('DEFAULT')
    if delete: bpy.ops.mesh.delete(type='VERT')
    if hasattr(operator, 'on_modal_cancelled'):
      operator.on_modal_cancelled(context, event)
    operator.report({'INFO'}, 'modal finished')
    return {'CANCELLED'}
  return {'RUNNING_MODAL'}

# @MenuOperators

class QuickMenuOperator(bpy.types.Operator):
  """Quick Menu"""
  bl_idname, bl_label = 'qm.quick_menu', 'Quick Menu Operator'

  def execute(self, context):
    bpy.ops.wm.call_menu(name=QuickMenu.bl_idname)
    return {'FINISHED'}

class EditMenuItemsOperator(bpy.types.Operator):
  """Edit Menu Items"""
  bl_idname, bl_label = 'qm.edit_items', 'Edit Menu Items Operator'

  def execute(self, context):
    config_path = get_config_path()
    if platform.system() == 'Darwin': # macOS
      subprocess.call(('open', config_path))
    elif platform.system() == 'Windows': # Windows
      os.startfile(config_path)
    else: # linux variants
      subprocess.call(('xdg-open', config_path))
    return {'FINISHED'}

class ReloadMenuItemsOperator(bpy.types.Operator):
  """Reload Menu Items"""
  bl_idname, bl_label = 'qm.load_items', 'Reload Menu Items Operator'

  def execute(self, context):
    load_items(get_config_path())
    return {'FINISHED'}

# @Operators

class JoinSeparateOperator(bpy.types.Operator):
  """Join or Separate"""
  bl_idname, bl_label, bl_options = 'qm.join_separate', 'Separate / Join', {'REGISTER', 'UNDO'}
  reset_origin: BoolProperty(name='Reset Origin on Separate', default=True)
  reset_drivers: BoolProperty(name='Reset Drivers on Separate', default=True)

  def execute(self, context):
    if is_in_editmode():
      if anything_is_selected_in_editmode():
        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.editmode_toggle()
        select(bpy.context.selected_objects[-1])
        if self.reset_origin: bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
        if self.reset_drivers:
          bpy.ops.qm.clear_drivers()
    elif len(bpy.context.selected_objects) > 0:
      bpy.ops.object.join()
    return {'FINISHED'}

class SetSmoothOperator(bpy.types.Operator):
  """Set Smooth Shading"""
  bl_idname, bl_label, bl_options = 'qm.smooth', 'Set Smooth', {'REGISTER', 'UNDO'}
  smooth: BoolProperty(name='Smooth', default=True)
  auto: BoolProperty(name='Auto', default=True)
  angle: FloatProperty(name='Angle', subtype='ANGLE', default=0.872665, step=2)

  def execute(self, context):
    def fn():
      if self.smooth:
        bpy.ops.object.shade_smooth(use_auto_smooth=self.auto, auto_smooth_angle=self.angle)
      else:
        bpy.ops.object.shade_flat()
    execute_in_mode('OBJECT', fn)
    return {'FINISHED'}

class LocalViewOperator(bpy.types.Operator):
  """Local View"""
  bl_idname, bl_label, bl_options = 'qm.local_view', 'Local View', {'REGISTER', 'UNDO'}

  def execute(self, context):
    if is_in_editmode():
      if anything_is_hidden_in_editmode(): bpy.ops.mesh.reveal(select=False)
      elif anything_is_selected_in_editmode(): bpy.ops.mesh.hide(unselected=True)
    else: bpy.ops.view3d.localview()
    return {'FINISHED'}

class SetOriginOperator(bpy.types.Operator):
  """Set origin to geometry center or selection. Hold shift to set origin to bottom"""
  bl_idname, bl_label, bl_options = 'qm.set_origin', 'Set Origin', {'REGISTER', 'UNDO'}
  type: EnumProperty(name='Type', items=(
    ('GEOMETRY', 'Geometry', 'Origin To Geometry'),
    ('BOTTOM', 'Bottom', 'Origin To Bottom')
  ))

  def invoke(self, context, event):
    if event.shift: self.type = 'BOTTOM'
    return self.execute(context)

  def execute(self, context):
    if self.type == 'GEOMETRY':
      if is_in_editmode() and anything_is_selected_in_editmode():
        cursor_to_selected()
        fn = lambda: bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='BOUNDS')
      else:
        fn = lambda: bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    elif self.type == 'BOTTOM':
      def fn():
        for obj in context.selected_objects:
          select(obj)
          bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
          bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
          new_origin = Vector((0, 0, -obj.dimensions.z / 2))
          obj.data.transform(Matrix.Translation(-new_origin))
          obj.location += new_origin
    execute_in_mode('OBJECT', fn)
    return {'FINISHED'}

class ProportionalEditingOperator(bpy.types.Operator):
  """Proportional Editing"""
  bl_idname, bl_label, bl_options = 'qm.proportional_editing', 'Proportional Editing', {'REGISTER', 'UNDO'}
  falloff: EnumProperty(name='Type', default='SMOOTH', items=(
    ('SMOOTH', 'Smooth', 'Smooth falloff'),
    ('SPHERE', 'Sphere', 'Sphere falloff'),
    ('ROOT', 'Root', 'Root falloff'),
    ('INVERSE_SQUARE', 'Inverse Square', 'Inverse Square falloff'),
    ('SHARP', 'Sharp', 'Sharp falloff'),
    ('LINEAR', 'Linear', 'Linear falloff'),
    ('CONSTANT', 'Constant', 'Constant falloff'),
    ('RANDOM', 'Random', 'Random falloff'),
  ))
  connected: BoolProperty(name='Connected', default = True)

  def execute(self, context):
    ts = context.scene.tool_settings
    if context.mode != 'OBJECT':
      ts.use_proportional_connected = self.connected
      if ts.proportional_edit_falloff == self.falloff and not self.options.is_repeat:
        ts.use_proportional_edit = not ts.use_proportional_edit
      else:
        ts.use_proportional_edit = True
        ts.proportional_edit_falloff = self.falloff
    else:
      ts.use_proportional_connected = self.connected
      if ts.proportional_edit_falloff == self.falloff and not self.options.is_repeat:
        ts.use_proportional_edit_objects = not ts.use_proportional_edit_objects
      else:
        ts.use_proportional_edit_objects = True
        ts.proportional_edit_falloff = self.falloff
    return {'FINISHED'}

class WireframeOperator(bpy.types.Operator):
  """Toggle Wireframe"""
  bl_idname, bl_label, bl_options = 'qm.wireframe', 'Wireframe', {'REGISTER', 'UNDO'}
  opacity: FloatProperty(name='Opacity', default=0.75, min=0, max=1)

  def execute(self, context):
    ol = context.space_data.overlay
    if not self.options.is_repeat:
      ol.show_wireframes = not ol.show_wireframes
    context.space_data.overlay.wireframe_opacity = self.opacity
    return {'FINISHED'}

class RotateOperator(bpy.types.Operator):
  """Rotate. Hold shift to invert angle"""
  bl_idname, bl_label, bl_options = 'qm.rotate', 'Rotate', {'REGISTER', 'UNDO'}
  angle: FloatProperty(name='Angle', subtype='ANGLE', default=1.5708)

  def invoke(self, context, event):
    if event.shift: self.angle = -abs(self.angle)
    return self.execute(context)

  def execute(self, context):
    axis, negative = axis_by_vector(view_snapped_vector(False, False))
    value = -self.angle if negative else self.angle
    bpy.ops.transform.rotate(value=value, orient_axis=axis, orient_type='GLOBAL')
    return {'FINISHED'}

class DrawOperator(bpy.types.Operator):
  """Draw"""
  bl_idname, bl_label = 'qm.draw', 'Draw'

  def execute(self, context):
    axis, negative = axis_by_vector(view_snapped_vector(False, False))
    if context.active_object: bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.gpencil_add(align='WORLD', type='EMPTY')
    bpy.ops.object.mode_set(mode='PAINT_GPENCIL')
    bpy.ops.gpencil.blank_frame_add()
    context.scene.tool_settings.gpencil_stroke_placement_view3d = 'SURFACE'
    context.object.data.zdepth_offset = 0
    context.scene.tool_settings.gpencil_sculpt.lock_axis = 'AXIS_' + axis
    return {'FINISHED'}

class ApplyToMultiuserOperator(bpy.types.Operator):
  """Apply to Multiuser"""
  bl_idname, bl_label, bl_options = 'qm.apply_to_multiuser', 'Apply to Multiuser', {'REGISTER', 'UNDO'}
  location: BoolProperty(name='Location', default = False)
  rotation: BoolProperty(name='Rotation', default = False)
  scale: BoolProperty(name='Scale', default = True)

  def execute(self, context):
    bpy.ops.object.make_single_user(object=True, obdata=True, material=False, animation=False)
    bpy.ops.object.transform_apply(location=self.location, rotation=self.rotation, scale=self.scale)
    bpy.ops.object.make_links_data(type='OBDATA')
    return {'FINISHED'}

class ConvertToInstancesOperator(bpy.types.Operator):
  """Convert Geometry Node Instances To Object Instances"""
  bl_idname, bl_label, bl_options = 'qm.convert_to_instances', 'Convert To Instances', {'REGISTER', 'UNDO'}

  suffix: StringProperty(name='Add Suffix', default='-prefab')

  def execute(self, context):
    if not modifier_exists('NODES'):
      return {'FINISHED'}
    original_object = context.object
    # Convert to instances:
    bpy.ops.object.duplicates_make_real(use_base_parent=True)
    # Clear modifiers on new objects and add suffix
    for obj in context.selected_objects:
      obj.name = obj.name + self.suffix
      obj.modifiers.clear()
    # Hide the original:
    original_object.modifiers["GeometryNodes"].show_viewport = False
    return {'FINISHED'}

class CorrectAttributesOperator(bpy.types.Operator):
  """Toggle Correct Face Attributes"""
  bl_idname, bl_label, bl_options = 'qm.correct_attributes', 'Toggle Correct Face Attributes', {'REGISTER', 'UNDO'}

  def execute(self, context):
    ts = bpy.context.scene.tool_settings
    ts.use_transform_correct_face_attributes = not ts.use_transform_correct_face_attributes
    return {'FINISHED'}

class SelectRingOperator(bpy.types.Operator):
  """Select ring. Hold shift to select loop"""
  bl_idname, bl_label, bl_options = 'qm.select_ring', 'Select Ring', {'REGISTER', 'UNDO'}
  select_loop: BoolProperty(name='Select Loop', default=False)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def invoke(self, context, event):
    self.select_loop = event.shift
    return self.execute(context)

  def execute(self, context):
    bpy.ops.mesh.loop_multi_select(ring=not self.select_loop)
    return {'FINISHED'}

class SelectMoreOperator(bpy.types.Operator):
  """Select more. Hold shift to select less"""
  bl_idname, bl_label, bl_options = 'qm.select_more', 'Select More', {'REGISTER', 'UNDO'}
  select_less: BoolProperty(name='Select Less', default=False)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def invoke(self, context, event):
    self.select_less = event.shift
    return self.execute(context)

  def execute(self, context):
    if self.select_less: bpy.ops.mesh.select_less()
    else: bpy.ops.mesh.select_more()
    return {'FINISHED'}

class RegionToLoopOperator(bpy.types.Operator):
  """Convert Region To Loop Or Loop To Region"""
  bl_idname, bl_label, bl_options = 'qm.region_to_loop', 'Region To Loop', {'REGISTER', 'UNDO'}
  select_bigger: BoolProperty(name='Loop To Region Bigger', default = False)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    mode = tuple(context.scene.tool_settings.mesh_select_mode).index(True)
    if mode == 1:
      bpy.ops.mesh.loop_to_region(select_bigger=self.select_bigger)
      bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')
    elif mode == 2:
      bpy.ops.mesh.region_to_loop()
    return {'FINISHED'}

class InvertSelectionConnectedOperator(bpy.types.Operator):
  """Invert Selection Connected"""
  bl_idname, bl_label, bl_options = 'qm.invert_selection_connected', 'Invert Selection Connected', {'REGISTER', 'UNDO'}

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    me = context.edit_object.data
    bm = bmesh.from_edit_mesh(me)
    mode = tuple(context.scene.tool_settings.mesh_select_mode).index(True)
    bm.faces.active = None
    if mode == 0: elements = [e for e in bm.verts if e.select]
    elif mode == 1: elements = [e for e in bm.edges if e.select]
    elif mode == 2: elements = [e for e in bm.faces if e.select]
    bpy.ops.mesh.select_linked()
    for e in elements: e.select_set(False)
    bmesh.update_edit_mesh(me)
    return {'FINISHED'}

class SelectSharpEdgesOperator(bpy.types.Operator):
  """Select Sharp Edges"""
  bl_idname, bl_label, bl_options = 'qm.select_sharp_edges', 'Select Sharp Edges', {'REGISTER', 'UNDO'}
  sharpness: FloatProperty(name='Sharpness', subtype='ANGLE', default=1.0472, min=0.000174533, max=3.14159)
  in_selection: BoolProperty(name='In Selection', default = True)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    in_selection = self.in_selection and anything_is_selected_in_editmode()
    if in_selection: bpy.ops.mesh.hide(unselected=True)
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
    bpy.ops.mesh.edges_select_sharp(sharpness=self.sharpness)
    if in_selection: bpy.ops.mesh.reveal(select=False)
    return {'FINISHED'}

class SelectViewGeometryOperator(bpy.types.Operator):
  """Select View Geometry"""
  bl_idname, bl_label, bl_options = 'qm.select_view_geometry', 'Select View Geometry', {'REGISTER', 'UNDO'}
  mode: EnumProperty(name='Mode', default='EDGES', items=(
    ('EDGES', 'Edges', 'Edges'),
    ('FACES', 'Faces', 'Faces')
  ))
  threshold: FloatProperty(name='Threshold', subtype='ANGLE', default=0.5235, min=0.000174533, max=1.5707)
  in_selection: BoolProperty(name='In Selection', default = True)
  snap_view_axis: BoolProperty(name='Snap View Axis', default = True)
  negative: BoolProperty(name='Negative', default = False)
  back_faces: BoolProperty(name='Back Faces', default = False)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def invoke(self, context, event):
    self.negative = event.shift
    return self.execute(context)

  def execute(self, context):
    for obj in bpy.context.objects_in_mode:
      mesh = obj.data
      bm = bmesh.from_edit_mesh(mesh)
      bm.faces.active = None
      vector = view_snapped_vector() if self.snap_view_axis else view_vector()
      if self.mode == 'EDGES':
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
        in_selection = self.in_selection and anything_is_selected_in_editmode(obj)
        print(in_selection)
        if in_selection: bpy.ops.mesh.hide(unselected=True)
        deselect_object_geometry(obj)
        for e in bm.edges:
          edge_vector = e.verts[0].co - e.verts[1].co
          if edge_vector.length != 0:
            parallel = abs(edge_vector.angle(vector) - (math.pi / 2)) > self.threshold
          else:
            parallel = False
          if self.negative: parallel = not parallel
          e.select = parallel
      elif self.mode == 'FACES':
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')
        in_selection = self.in_selection and anything_is_selected_in_editmode(obj)
        if in_selection: bpy.ops.mesh.hide(unselected=True)
        deselect_object_geometry(obj)
        for f in bm.faces:
          angle = (math.pi / 2) - f.normal.angle(vector)
          if self.back_faces: angle = abs(angle)
          facing = angle > self.threshold
          if self.negative: facing = not facing
          f.select = facing
      bmesh.update_edit_mesh(mesh)
      if in_selection: bpy.ops.mesh.reveal(select=False)
    return {'FINISHED'}

class AddSingleVertexOperator(bpy.types.Operator):
  """Add Single Vertex"""
  bl_idname, bl_label, bl_options = 'qm.add_single_vertex', 'Add Single Vertex', {'REGISTER', 'UNDO'}

  def execute(self, context):
    bpy.ops.mesh.primitive_plane_add(align='WORLD')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.merge(type='CENTER')
    bpy.ops.mesh.select_mode(type='VERT')
    return {'FINISHED'}

class SpinOperator(bpy.types.Operator):
  """Spin Operator"""
  bl_idname, bl_label, bl_options = 'qm.spin', 'Spin', {'REGISTER', 'UNDO'}
  negative_angle: BoolProperty(name='Negative Angle', default=False)
  steps: IntProperty(name='Steps', default=6, min=1)
  angle: FloatProperty(name='Angle', subtype='ANGLE', default=1.5708)
  flip_normals: BoolProperty(name='Flip Normals', default=False)
  duplicates: BoolProperty(name='Use Duplicates', default=False)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()
  
  def invoke(self, context, event):
    self.negative_angle = event.shift
    return self.execute(context)

  def execute(self, context):
    vsv = view_snapped_vector(False, False)
    angle = -self.angle if self.negative_angle else self.angle
    bpy.ops.mesh.spin(dupli=self.duplicates, steps=self.steps, angle=angle, use_normal_flip=self.flip_normals, center=context.scene.cursor.location, axis=vsv)
    return {'FINISHED'}

class BboxOperator(bpy.types.Operator):
  """Bbox around Selection"""
  bl_idname, bl_label, bl_options = 'qm.bbox', 'Bbox Around Selection', {'REGISTER', 'UNDO'}

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    original_object = context.object

    # Separate the selected geometry into a temporary copy
    bpy.ops.mesh.duplicate()
    bpy.ops.mesh.separate(type='SELECTED')
    new_object = context.selected_objects[-1]
    new_object.modifiers.clear()
    bpy.ops.object.editmode_toggle()
    select(new_object)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    cursor_to_selected()
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    # Add a bounding box around the new object
    bpy.ops.mesh.primitive_cube_add()
    cube = context.selected_objects[-1]
    cube.dimensions = new_object.dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.object.editmode_toggle()

    # Remove the temporary copy
    select(new_object)
    bpy.ops.object.delete()

    # Join the bounding box with original geometry
    select(original_object)
    cube.select_set(True)
    bpy.ops.object.join()
    bpy.ops.object.editmode_toggle()
    return {'FINISHED'}

class ConnectOperator(bpy.types.Operator):
  """Connect Selected"""
  bl_idname, bl_label, bl_options = 'qm.connect', 'Connect Selected', {'REGISTER', 'UNDO'}

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    bpy.ops.mesh.duplicate()
    bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')
    bpy.ops.mesh.merge(type='COLLAPSE')
    bpy.ops.mesh.edge_face_add()
    bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
    return {'FINISHED'}

class AddGeometryOperator(bpy.types.Operator):
  """Add Geometry"""
  bl_idname, bl_label, bl_options = 'qm.add_geometry', 'Add Geometry', {'REGISTER', 'UNDO'}
  radius: FloatProperty(name='Radius', default=1)
  vertices: IntProperty(name='Vertices', default=8, soft_min=1, soft_max=256)
  square: BoolProperty(name='Square Profile', default=False)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def on_modal_run(self, context, event):
    self.radius = self.size * (1 + self.modal_delta)
    self.square = event.shift
    self.execute(context)

  def on_modal_invoke(self, context, event):
    n = Vector((0, 0, 0))
    p = 0.0
    faces = [f for f in bmesh.from_edit_mesh(context.edit_object.data).faces if f.select]

    for f in faces:
      n += f.normal
      p += f.calc_perimeter()

    self.size = p / 8 if p else 2

    up = Vector((0, 0, 1 if p else 0))
    if context.object.rotation_euler != Euler():
      n = n @ context.object.matrix_world.inverted()
    self.orientation = (up.rotation_difference(n)).to_euler()
    cursor_to_selected()
    bpy.ops.mesh.select_all(action='DESELECT')

  def modal(self, context, event):
    return modal_run(self, context, event, True)

  def invoke(self, context, event):
    return modal_invoke(self, context, event)

  def add_geometry(self):
    cursor_to_selected()
    if self.square:
      bpy.ops.mesh.primitive_plane_add(size=self.radius * 2, enter_editmode=False, rotation=self.orientation)
    else:
      if not self.options.is_repeat:
        self.vertices = calculate_number_of_vertices_by_radius(self.radius)
        self.report({'INFO'}, f'{self.vertices} vertices')
      bpy.ops.mesh.primitive_circle_add(radius=self.radius, vertices=self.vertices, fill_type='NGON', enter_editmode=False, rotation=self.orientation)

  def execute(self, context):
    self.add_geometry()
    return {'FINISHED'}

class ExtrudeBothWaysOperator(bpy.types.Operator):
  """Extrude Both ways"""
  bl_idname, bl_label, bl_options = 'qm.extrude_both_ways', 'Extrude Both Ways', {'REGISTER', 'UNDO'}
  offset: FloatProperty(name='Offset', default=0.3, step=0.05)
  dissolve_original: BoolProperty(name='Dissolve Original Geometry')

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.vertex_group_add()
    bpy.ops.object.vertex_group_assign()
    bpy.ops.mesh.extrude_region_shrink_fatten(TRANSFORM_OT_shrink_fatten={'value':self.offset, 'use_even_offset':True})
    bpy.ops.object.vertex_group_remove_from()
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.vertex_group_select()
    bpy.ops.mesh.extrude_region_shrink_fatten(TRANSFORM_OT_shrink_fatten={'value':self.offset, 'use_even_offset':True})
    bpy.ops.object.vertex_group_remove_from()
    if self.dissolve_original:
      bpy.ops.mesh.select_all(action='DESELECT')
      bpy.ops.object.vertex_group_select()
      bpy.ops.mesh.select_mode(type='EDGE')
      bpy.ops.mesh.dissolve_mode(use_verts=True)
    bpy.ops.object.vertex_group_select()
    bpy.ops.object.vertex_group_remove()
    return {'FINISHED'}

class FlattenOperator(bpy.types.Operator):
  """Flatten"""
  bl_idname, bl_label, bl_options = 'qm.flatten', 'Flatten', {'REGISTER', 'UNDO'}
  amount: FloatProperty(name='Amount', min=0, max=1, step=0.3, default=1)
  to_active: BoolProperty(name='To Active', default=False)
  merge: BoolProperty(name='Merge', default=True)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    bpy.ops.qm.transform_orientation(type="GLOBAL")
    vsv = view_snapped_vector(False, False)
    for i in range(3): vsv[i] = 1 if vsv[i] == 0 else 1 - self.amount
    if self.to_active:
      previous_pivot = context.scene.tool_settings.transform_pivot_point
      context.scene.tool_settings.transform_pivot_point = 'ACTIVE_ELEMENT'
    bpy.ops.transform.resize(value=vsv)
    if self.to_active:
      context.scene.tool_settings.transform_pivot_point = previous_pivot
    if self.merge:
      bpy.ops.mesh.remove_doubles(threshold=0.0001, use_unselected=False, use_sharp_edge_from_normals=False)
    return {'FINISHED'}

class ClearSharpOperator(bpy.types.Operator):
  """Clear Sharp"""
  bl_idname, bl_label, bl_options = 'qm.clear_sharp', 'Clear Sharp', {'REGISTER', 'UNDO'}

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.mark_sharp(clear=True)
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
    return {'FINISHED'}

class RandomizeOperator(bpy.types.Operator):
  """Randomize"""
  bl_idname, bl_label, bl_options = 'qm.randomize', 'Randomize', {'REGISTER', 'UNDO'}
  location: FloatVectorProperty(name='Location', subtype='TRANSLATION', default=(0, 0, 0))
  rotation: FloatVectorProperty(name='Rotation', subtype='EULER', default=(0, 0, 0))
  scale: FloatVectorProperty(name='Scale', subtype='XYZ', default=(0, 0, 0))
  scale_even: BoolProperty(name='Scale Even (Use X)')
  seed: IntProperty(name='Seed', default=1, min=1)
  offset: FloatProperty(name='Vertex Noise Offset', default=0, step=0.1)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def draw(self, context):
    l = self.layout
    l.prop(self.properties, 'location')
    l.prop(self.properties, 'rotation')
    l.prop(self.properties, 'scale')
    l.prop(self.properties, 'scale_even')
    l.prop(self.properties, 'seed')
    l.prop(self.properties, 'offset')

  def execute(self, context):
    if self.offset:
      bpy.ops.transform.vertex_random(offset=self.offset)
      return {'FINISHED'}

    self.i = 0

    def process_island(operator):
      operator.i += 100
      noise.seed_set(operator.seed + operator.i)
      loc = noise.random_vector()
      rot = noise.random_vector()
      scale = noise.random_vector()
      if operator.location.length:
        bpy.ops.transform.translate(value=(operator.location.x * loc.x, operator.location.y * loc.y, operator.location.z * loc.z))
      if operator.scale.length:
        sx = abs(operator.scale.x * scale.x + 1)
        if operator.scale_even: bpy.ops.transform.resize(value=(sx, sx, sx))
        else: bpy.ops.transform.resize(value=(sx, abs(operator.scale.y * scale.y + 1), abs(operator.scale.z * scale.z + 1)))
      if operator.rotation.x: bpy.ops.transform.rotate(value=operator.rotation.x * rot.x, orient_axis='X')
      if operator.rotation.y: bpy.ops.transform.rotate(value=operator.rotation.y * rot.y, orient_axis='Y')
      if operator.rotation.z: bpy.ops.transform.rotate(value=operator.rotation.z * rot.z, orient_axis='Z')

    iterate_islands(self, process_island, restore_selection=True)
    return {'FINISHED'}

class ConvertOperator(bpy.types.Operator):
  """Convert to curve or skin. Hold shift to use square profile"""
  bl_idname, bl_label, bl_options = 'qm.convert', 'Convert', {'REGISTER', 'UNDO'}
  type: EnumProperty(name='Type', items=(
    ('CURVE', 'Curve', 'Convert to curve'),
    ('SKIN', 'Skin', 'Convert to skin')
  ))
  depth: FloatProperty(name='Depth', default=0.4, step=0.1, min=0, soft_min=0.001)
  auto_resolution: BoolProperty(name='Auto Resolution', default=True)
  resolution: IntProperty(name='Curve Resolution', default=2, soft_min=1, soft_max=20)
  edit_mode: BoolProperty(name='Edit Mode')
  cap: BoolProperty(name='Curve Cap', default=False)
  square_profile: BoolProperty(name='Square Profile')
  delete_source: BoolProperty(name='Delete Source', default=True)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def invoke(self, context, event):
    if event.shift: self.square_profile = True
    return self.execute(context)

  def execute(self, context):
    old_object = context.object

    if is_in_editmode():
      if not self.delete_source: bpy.ops.mesh.duplicate()
      bpy.ops.mesh.separate()
      bpy.ops.object.editmode_toggle()
      new_object = context.selected_objects[-1]
      if not self.options.is_repeat:
        self.depth = max(new_object.dimensions) / 10
      select(new_object)
      bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
      new_object.modifiers.clear()

    if self.type == 'CURVE':
      bpy.ops.object.convert(target='CURVE')
      context.object.data.bevel_depth = self.depth
      if self.auto_resolution:
        subsurf = modifier_exists('SUBSURF') or modifier_exists('MULTIRES')
        self.resolution = int(max(1, (calculate_number_of_vertices_by_radius(self.depth, subsurf) / 2 - 3)))
      context.object.data.bevel_resolution = self.resolution
      if self.square_profile:
        context.object.data.bevel_depth = 0
        context.object.data.extrude = self.depth
        bpy.ops.object.convert(target='MESH')
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.qm.extrude_both_ways(offset=self.depth, dissolve_original=True)
        bpy.ops.object.editmode_toggle()
    elif self.type == 'SKIN':
      bpy.ops.object.modifier_add(type='SKIN')
      bpy.ops.object.editmode_toggle()
      bpy.ops.mesh.select_all(action='SELECT')
      bpy.ops.transform.skin_resize(value=(self.depth, self.depth, self.depth))
      bpy.ops.object.editmode_toggle()

    if self.edit_mode:
      bpy.ops.object.convert(target='MESH')
      bpy.ops.object.editmode_toggle()
      bpy.ops.mesh.select_all(action='SELECT')
      if self.cap:
        try: bpy.ops.mesh.edge_face_add()
        except: pass
      bpy.ops.object.editmode_toggle()
      old_object.select_set(True)
      context.view_layer.objects.active = old_object
      bpy.ops.object.join()
      bpy.ops.object.editmode_toggle()

    return {'FINISHED'}

class ConvertToMeshOperator(bpy.types.Operator):
  """Convert To Mesh"""
  bl_idname, bl_label, bl_options = 'qm.convert_to_mesh', 'Convert To Mesh', {'REGISTER', 'UNDO'}
  close_strokes: BoolProperty(name='GPencil Close Strokes', default=True)
  dissolve_angle: FloatProperty(name='GPencil Dissolve Angle', subtype='ANGLE', step=5, default=0.261799, min=0, max=1.5708)
  doubles_threshold: FloatProperty(name='GPencil Doubles Threshold', default=0.02, min=0)

  @classmethod
  def poll(cls, context):
    return context.object != None

  def execute(self, context):
    if len(context.selected_objects) == 0:
      return {'FINISHED'}
    def fn():
      if context.active_object.type == 'GPENCIL':
        original = context.active_object

        if self.close_strokes:
          bpy.ops.object.mode_set(mode='EDIT_GPENCIL')
          previous_context = context.area.type
          context.area.type = 'VIEW_3D'
          bpy.ops.gpencil.select_all(action='SELECT')
          bpy.ops.gpencil.stroke_cyclical_set(type='CLOSE', geometry=True)
          bpy.ops.gpencil.stroke_flip()
          context.area.type = previous_context
          bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.gpencil.convert(type='POLY', use_timing_data=False)
        new = get_selected_non_active()
        select(original)
        bpy.ops.object.delete()
        select(new)
        bpy.ops.object.convert(target='MESH')
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='VERT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.005)
        bpy.ops.mesh.dissolve_limited(angle_limit=self.dissolve_angle)
        bpy.ops.mesh.remove_doubles(threshold=self.doubles_threshold)
      else:
        bpy.ops.object.convert(target='MESH')
    execute_in_mode('OBJECT', fn)
    return {'FINISHED'}

class MirrorOperator(bpy.types.Operator):
  """Mirror"""
  bl_idname, bl_label, bl_options = 'qm.mirror', 'Mirror', {'REGISTER', 'UNDO'}
  axis: BoolVectorProperty(name='Axis', subtype='XYZ')
  bisect_flip: BoolVectorProperty(name='Bisect Flip', subtype='XYZ')

  def draw(self, context):
    l = self.layout
    l.row().prop(self.properties, 'axis', toggle=1)
    l.row().prop(self.properties, 'bisect_flip', toggle=1)

  def execute(self, context):
    if modifier_exists('MIRROR'):
      m = add_or_get_modifier('MIRROR')
      fn = lambda: bpy.ops.object.modifier_apply(modifier=m.name)
      execute_in_mode('OBJECT', fn)
      return {'FINISHED'}
    m = add_or_get_modifier('MIRROR', move_on_top=True)
    m.use_axis[0], m.show_on_cage = False, True
    vsv = view_snapped_vector(True)
    vsv_notransform = view_snapped_vector(True, False)
    axis, negative = axis_by_vector(vsv)
    if not self.options.is_repeat:
      index = ['x', 'y', 'z'].index(axis.lower())
      self.axis[index] = self.bisect_flip[index] = True
      self.bisect_flip[index] = negative
    for i in range(3):
      m.use_axis[i] = m.use_bisect_axis[i] = self.axis[i]
      m.use_bisect_flip_axis[i] = self.bisect_flip[i]
    return {'FINISHED'}

class SubsurfOperator(bpy.types.Operator):
  """Subsurf"""
  bl_idname, bl_label, bl_options = 'qm.subsurf', 'Subsurf', {'REGISTER', 'UNDO'}
  level: IntProperty(name='Level', default=2, min=0, soft_max=5)

  def execute(self, context):
    if context.mode != 'SCULPT':
      m = add_or_get_modifier('SUBSURF')
      m.levels, m.boundary_smooth = self.level, 'PRESERVE_CORNERS'
    else:
      m = add_or_get_modifier('MULTIRES')
      bpy.ops.object.multires_subdivide(modifier=m.name, mode='CATMULL_CLARK')
      m.levels = min(m.sculpt_levels, self.level)
    return {'FINISHED'}

class BevelOperator(bpy.types.Operator):
  """Bevel"""
  bl_idname, bl_label, bl_options = 'qm.bevel', 'Bevel', {'REGISTER', 'UNDO'}
  amount: FloatProperty(name='Amount', default=0.1, step=0.1, min=0)
  segments: IntProperty(name='Segments', default=4, min=0, soft_max=12)
  angle: FloatProperty(name='Angle', subtype='ANGLE', default=0.785398, min=0, max=3.141593)
  use_weight: BoolProperty(name='Use Weight', default=False)
  harden_normals: BoolProperty(name='Harden Normals', default=True)
  loop_slide: BoolProperty(name='Loop Slide', default=False)
  use_clamp_overlap: BoolProperty(name='Clamp Overlap', default=True)

  def execute(self, context):
    existed = modifier_exists('BEVEL')
    b = add_or_get_modifier('BEVEL')
    if not existed: b.miter_outer = 'MITER_ARC'
    if self.use_weight: b.limit_method = 'WEIGHT'
    b.width, b.segments, b.angle_limit, b.harden_normals, b.loop_slide, b.use_clamp_overlap = self.amount, self.segments, self.angle, self.harden_normals, self.loop_slide, self.use_clamp_overlap
    return {'FINISHED'}

class SolidifyOperator(bpy.types.Operator):
  """Solidify"""
  bl_idname, bl_label, bl_options = 'qm.solidify', 'Solidify', {'REGISTER', 'UNDO'}
  thickness: FloatProperty(name='Thickness', default=0.01, step=0.1, min=0)
  offset: FloatProperty(name='Offset', default=0, min=-1, max=1)

  def execute(self, context):
    existed = modifier_exists('SOLIDIFY')
    s = add_or_get_modifier('SOLIDIFY')
    if not existed:
      s.solidify_mode, s.use_even_offset, s.show_on_cage = 'NON_MANIFOLD', True, True
    s.thickness, s.offset = self.thickness, self.offset
    return {'FINISHED'}

class TriangulateOperator(bpy.types.Operator):
  """Triangulate"""
  bl_idname, bl_label, bl_options = 'qm.triangulate', 'Triangulate', {'REGISTER', 'UNDO'}
  keep_normals: BoolProperty(name='Keep Normals', default=True)

  def execute(self, context):
    existed = modifier_exists('TRIANGULATE')
    t = add_or_get_modifier('TRIANGULATE')
    if not existed:
      t.keep_custom_normals = self.keep_normals
    return {'FINISHED'}

class ArrayOperator(bpy.types.Operator):
  """Array"""
  bl_idname, bl_label, bl_options = 'qm.array', 'Array', {'REGISTER', 'UNDO'}
  count: IntProperty(name='Count', default=3, step=1, min=0)
  offset: FloatProperty(name='Offset', default=1.1)

  def execute(self, context):
    v = view_snapped_vector() * self.offset
    v.negate()
    a = add_or_get_modifier('ARRAY')
    a.count = self.count
    a.relative_offset_displace = v
    return {'FINISHED'}

class SimpleDeformOperator(bpy.types.Operator):
  """Simple Deform"""
  bl_idname, bl_label, bl_options = 'qm.simple_deform', 'Simple Deform', {'REGISTER', 'UNDO'}
  method: StringProperty(name='Method', default='BEND')
  angle: FloatProperty(name='Angle', subtype='ANGLE', default=6.28319, step=2)

  def execute(self, context):
    vsv = view_snapped_vector()
    axis, negative = axis_by_vector(vsv)
    sd = add_or_get_modifier('SIMPLE_DEFORM')
    sd.deform_method, sd.angle, sd.deform_axis = self.method, self.angle, axis
    return {'FINISHED'}

class ClearModifiersOperator(bpy.types.Operator):
  """Clear Modifiers"""
  bl_idname, bl_label, bl_options = 'qm.clear_modifiers', 'Clear Modifiers', {'REGISTER', 'UNDO'}

  def execute(self, context):
    for obj in context.selected_objects:
      obj.modifiers.clear()
    return {'FINISHED'}

class DeleteBackFacingOperator(bpy.types.Operator):
  """Delete Back Facing Faces. Works on selection"""
  bl_idname, bl_label, bl_options = 'qm.delete_back_facing', 'Delete Back Facing Faces', {'REGISTER', 'UNDO'}
  threshold: FloatProperty(name='Threshold', subtype='ANGLE', default=1.5706, min=0.000174533, max=1.5707)
  snap_view_axis: BoolProperty(name='Snap View Axis', default = True)
  both_ways: BoolProperty(name='Both Ways', default = False)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    obj = context.edit_object
    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    bm.faces.active = None
    vector = view_snapped_vector() if self.snap_view_axis else view_vector()
    faces_to_delete = []
    for f in bm.faces:
      if f.select and f.normal.length > 0:
        angle = f.normal.angle(vector) - (math.pi / 2)
        if self.both_ways: angle = abs(angle)
        if angle > self.threshold: faces_to_delete.append(f)
    bmesh.ops.delete(bm, geom=faces_to_delete, context='FACES')
    bmesh.update_edit_mesh(me)
    return {'FINISHED'}

class SeparateByLoosePartsOperator(bpy.types.Operator):
  """Separate By Loose Parts"""
  bl_idname, bl_label, bl_options = 'qm.separate_by_loose_parts', 'Separate By Loose Parts', {'REGISTER', 'UNDO'}
  calculate_rotation: BoolProperty(name='Calculate Rotation', default=False)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    bpy.ops.mesh.separate()
    bpy.ops.object.editmode_toggle()
    new_object = context.selected_objects[-1]
    select(new_object)
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.separate(type='LOOSE')
    bpy.ops.object.editmode_toggle()
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    bpy.ops.object.make_links_data(type='OBDATA')
    if self.calculate_rotation:
      active = context.object
      objects = [o for o in context.selected_objects if o != active]
      locations = [o.location for o in context.selected_objects]
      center = reduce((lambda x, y: x + y), locations) / len(locations)
      for o in objects:
        active_direction = center - active.location
        current_direction = center - o.location
        angle = active_direction.angle(current_direction)
        cross = active_direction.cross(current_direction)
        o.rotation_euler = Quaternion(cross, angle).to_euler()
    return {'FINISHED'}

class StraightenUVsOperator(bpy.types.Operator):
  """Straighten UVs"""
  bl_idname, bl_label, bl_options = 'qm.straighten_uvs', 'Straighten UVs', {'REGISTER', 'UNDO'}

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    mesh = context.object.data
    selection_indeces, active_indeces = execute_in_mode('EDIT', get_selection_and_active_indices)
    def process_uvs():
      prev_uv_coords = first_axis = None
      for index in [*active_indeces, active_indeces[0]]:
        uv_coords = mesh.uv_layers.active.data[index].uv
        if prev_uv_coords:
          if first_axis == None:
            diff = uv_coords - prev_uv_coords
            diff_abs = [abs(diff.x), abs(diff.y)]
            min_axis = diff_abs.index(min(diff_abs))
            first_axis = min_axis
          else:
            min_axis = (first_axis + index + 1) % 2
          uv_coords[min_axis] = prev_uv_coords[min_axis]
        prev_uv_coords = uv_coords
    execute_in_mode('OBJECT', process_uvs)
    bpy.ops.uv.follow_active_quads()
    return {'FINISHED'}

class UVProjectModifierOperator(bpy.types.Operator):
  """UV Project Modifier"""
  bl_idname, bl_label, bl_options = 'qm.uv_project_modifier', 'UV Project Modifier', {'REGISTER', 'UNDO'}

  @classmethod
  def poll(cls, context):
    return context.object != None

  def execute(self, context):
    obj_name = context.object.name
    bpy.ops.object.modifier_add(type='UV_PROJECT')
    uv_project = context.object.modifiers[-1]
    uv_project.uv_layer = "UVMap"
    uv_project.projector_count = 10

    deg45 = math.pi / 4
    deg90 = math.pi / 2

    rotations = [
      Vector((0, 0, 0)), Vector((math.pi, 0, 0)),
      Vector((deg90, 0, 0)), Vector((deg90, 0, deg45)), Vector((deg90, 0, deg45 * 2)),
      Vector((deg90, 0, deg45 * 3)), Vector((deg90, 0, deg45 * 4)), Vector((deg90, 0, deg45 * 5)),
      Vector((deg90, 0, deg45 * 6)), Vector((deg90, 0, deg45 * 7))
    ]

    bpy.ops.object.empty_add(type='CUBE', location=context.object.location)
    container = context.object
    container.name = f'ProjectorContainer_{obj_name}';

    for i, rot in enumerate(rotations):
      bpy.ops.object.empty_add(type='SINGLE_ARROW', location=(0, 0, 0), rotation=rot)
      context.object.name = "Projector";
      context.object.parent = container
      uv_project.projectors[i].object = context.object

    select(container)

    return {'FINISHED'}

class MarkSeamOperator(bpy.types.Operator):
  """Mark Or Clear Seam. Hold shift to clear seam"""
  bl_idname, bl_label, bl_options = 'qm.mark_seam', 'Mark Seam', {'REGISTER', 'UNDO'}
  clear_inner_region: BoolProperty(name='Clear Inner Region', default=False)
  clear: BoolProperty(name='Clear', default=False)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def invoke(self, context, event):
    if event.shift: self.clear = True
    return self.execute(context)

  def execute(self, context):
    if self.clear:
      bpy.ops.mesh.mark_seam(clear=True)
      return {'FINISHED'}
    mode = tuple(context.scene.tool_settings.mesh_select_mode).index(True)
    if self.clear_inner_region: bpy.ops.mesh.mark_seam(clear=True)
    if mode == 1: bpy.ops.mesh.mark_seam()
    elif mode == 2:
      bpy.ops.mesh.region_to_loop()
      bpy.ops.mesh.mark_seam()
      bpy.ops.mesh.loop_to_region()
      bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')
    return {'FINISHED'}

class MarkSeamsSharpOperator(bpy.types.Operator):
  """Mark Seams Sharp"""
  bl_idname, bl_label, bl_options = 'qm.mark_seams_sharp', 'Mark Seams Sharp', {'REGISTER', 'UNDO'}
  sharpness: FloatProperty(name='Sharpness', subtype='ANGLE', default=1.0472, min=0.000174533, max=3.14159)
  from_islands: BoolProperty(name='Preserve Islands', default=False)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    if self.from_islands: bpy.ops.qm.mark_seams_from_islands()
    bpy.ops.qm.select_sharp_edges(sharpness=self.sharpness)
    bpy.ops.qm.mark_seam()
    bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')
    return {'FINISHED'}

class MarkSeamsFromIslandsOperator(bpy.types.Operator):
  """Mark Seams From Islands"""
  bl_idname, bl_label, bl_options = 'qm.mark_seams_from_islands', 'Mark Seams From Islands', {'REGISTER', 'UNDO'}

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    previous_area = context.area.ui_type
    context.area.ui_type = 'UV'
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.seams_from_islands()
    context.area.ui_type = previous_area
    return {'FINISHED'}

class TransformUVsOperator(bpy.types.Operator):
  """Transform UV"""
  bl_idname, bl_label, bl_options = 'qm.transform_uvs', 'Transform UVs', {'REGISTER', 'UNDO'}

  offset_x: FloatProperty(name='Offset X', default=0, step=0.1)
  offset_y: FloatProperty(name='Offset Y', default=0, step=0.1)
  rotation: FloatProperty(name='Rotation', subtype='ANGLE', default=0, soft_min=-3.14159, soft_max=3.14159)
  scale_x: FloatProperty(name='Scale X', default=1, step=0.1, soft_min=0)
  scale_y: FloatProperty(name='Scale Y', default=1, step=0.1, soft_min=0)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    me = bpy.context.edit_object.data
    bm = bmesh.from_edit_mesh(me)
    uv_layer = bm.loops.layers.uv.verify()
    uvs = []
    for face in bm.faces:
      if face.select:
        center = face.calc_center_median()
        for loop in face.loops:
          uvs.append(loop[uv_layer])
    center = reduce(lambda a, b: a + b, [uv.uv for uv in uvs]) / len(uvs)

    for uv in uvs:
      if self.offset_x or self.offset_y:
        uv.uv += Vector( (self.offset_x, self.offset_y) )
      if self.rotation:
        rotation_matrix = Matrix.Rotation(self.rotation, 2)
        offset_uv = uv.uv - center
        offset_uv.rotate(rotation_matrix)
        uv.uv = center + offset_uv
      if self.scale_x != 1 or self.scale_y != 1:
        uv.uv = center + Vector(uv.uv - center) * Vector((self.scale_x, self.scale_y))

    bmesh.update_edit_mesh(me)
    return {'FINISHED'}

class SetVertexColorOperator(bpy.types.Operator):
  """Set Vertex Color"""
  bl_idname, bl_label, bl_options = 'qm.set_vertex_color', 'Set Vertex Color', {'REGISTER', 'UNDO'}
  color: FloatVectorProperty(name='Color', subtype='COLOR', min=0, max=1)
  linked: BoolProperty(name='Linked', default = True)
  set_to_active: BoolProperty(name='Set To Active', default = False)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    context.space_data.shading.color_type = 'VERTEX'

    # Generate next unique RGB
    if not self.set_to_active and not self.options.is_repeat:
      i = context.scene.quick_menu.vertex_color_index
      values = (1 - math.floor(i % 10) / 10, 1 - math.floor(i / 100 % 10) / 10, 1 - math.floor(i / 10 % 10) / 10)
      next_color = Color()
      next_color.r = values[0]
      next_color.g = values[1]
      next_color.b = values[2]
      context.scene.quick_menu.vertex_color_index += 3

    # Linked
    if self.linked: bpy.ops.mesh.select_linked()

    # Track if we already set color from active so that we can copy between meshes:
    initial_active = context.active_object
    for obj in context.objects_in_mode:
      mesh = obj.data
      context.view_layer.objects.active = obj
      selection_indeces, active_indeces = execute_in_mode('EDIT', get_selection_and_active_indices)
      def assign_colors():
        # Set color to the next random color:
        if self.set_to_active:
          if obj == initial_active:
            if len(active_indeces) > 0 and mesh.vertex_colors.active:
              self.color = list(mesh.vertex_colors.active.data[active_indeces[0]].color)[:3]
            else: self.color = (1, 1, 1)
        elif not self.options.is_repeat:
          self.color = next_color
        # Set the color of selection
        for index in selection_indeces:
          mesh.vertex_colors.active.data[index].color = (self.color[0], self.color[1], self.color[2], 1)
      execute_in_mode('OBJECT', assign_colors)
    return {'FINISHED'}

class SelectByVertexColorOperator(bpy.types.Operator):
  """Select By Vertex Color"""
  bl_idname, bl_label, bl_options = 'qm.select_by_vertex_color', 'Select By Vertex Color', {'REGISTER', 'UNDO'}

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    context.space_data.shading.color_type = 'VERTEX'
    selected_colors = []
    # Gather all of the selected colors across all of the objects first
    for obj in context.objects_in_mode:
      context.view_layer.objects.active = obj
      selection_indeces, active_indeces = execute_in_mode('EDIT', get_selection_and_active_indices)
      def fn():
        for index in selection_indeces:
          selected_colors.append(obj.data.vertex_colors.active.data[index].color)
      execute_in_mode('OBJECT', fn)
    # Set selection
    for obj in context.objects_in_mode:
      mesh = obj.data
      context.view_layer.objects.active = obj
      selection_indeces, active_indeces = execute_in_mode('EDIT', get_selection_and_active_indices)
      def fn():
        for poly in mesh.polygons:
          poly.select = False
          for index in poly.loop_indices:
            c = mesh.vertex_colors.active.data[index].color
            for sc in selected_colors:
              if c[0] == sc[0] and c[1] == sc[1] and c[2] == sc[2]:
                poly.select = True
                continue
      execute_in_mode('OBJECT', fn)
    return {'FINISHED'}

class BakeIDMapOperator(bpy.types.Operator):
  """Bake ID Map From Vertex Colors"""
  bl_idname, bl_label = 'qm.bake_id_map', 'Bake ID Map'
  map_size: IntProperty(name='Map Size', default=2048)

  def execute(self, context):
    if bpy.data.filepath == '':
      self.report({'ERROR'}, 'File is not saved')
      return {'FINISHED'}
    if len(context.selected_objects) == 0:
      self.report({'ERROR'}, 'Nothing is selected')
      return {'FINISHED'}
    if bpy.context.scene.render.engine != 'CYCLES':
      self.report({'ERROR'}, 'Please set render engine to cycles')
      return {'FINISHED'}
    
    initial_material = None

    for obj in context.selected_objects:
      num_materials = len(obj.data.materials)
      if num_materials != 1:
        self.report({'ERROR'}, f'{obj.name} must have exactly 1 material')
        return {'FINISHED'}
      mat = obj.data.materials[0]
      if initial_material == None: initial_material = mat
      if mat != initial_material:
        self.report({'ERROR'}, 'All of the selected objects should have the same material')
        return {'FINISHED'}
    
    # The name of the id map includes the name of the material (texture set)
    idmap_name = f'{initial_material.name}_idmap'

    # Create an id map image if it doesnt exist
    if not bpy.data.images.get(idmap_name):
      bpy.ops.image.new(name=idmap_name, width=self.map_size, height=self.map_size)

    # Create an ID Map material if it doesnt exist
    mat = bpy.data.materials.get('idmap')
    if not mat:
      mat = bpy.data.materials.new(name='idmap')
      mat.use_nodes = True
      bsdf = mat.node_tree.nodes['Principled BSDF']
      texImage = mat.node_tree.nodes.new('ShaderNodeTexImage')
      texImage.image = bpy.data.images[idmap_name]
      vertex_color_node = mat.node_tree.nodes.new('ShaderNodeVertexColor')
      mat.node_tree.links.new(bsdf.inputs['Emission'], vertex_color_node.outputs['Color'])

    # Change materials to idmap material for baking
    for obj in context.selected_objects:
      obj.data.materials[0] = mat

    # Bake emission
    bpy.ops.object.bake(type='EMIT', margin=1)

    # Change materials back to initial material
    for obj in context.selected_objects:
      obj.data.materials[0] = initial_material

    # Save id map texture to file in the same folder as .blend
    directory, file = get_paths()
    filepath = f'{directory}{file}_{idmap_name}.png'
    img = bpy.data.images.get(idmap_name)
    img.filepath_raw = filepath
    img.file_format = 'PNG'
    img.save()

    return {'FINISHED'}

class EditAlbedoMapOperator(bpy.types.Operator):
  """Edit albedo maps of selected objects externally"""
  bl_idname, bl_label = 'qm.edit_albedo_map', 'Edit Albdeo Map'

  def execute(self, context):
    # Unpack images first to make sure we're not editing the original
    # from material library
    if bpy.data.filepath == '':
      self.report({'ERROR'}, 'File is not saved')
      return {'FINISHED'}
    bpy.ops.qm.unpack_all_data_to_files()

    # Make sure something is selected
    if len(context.selected_objects) == 0:
      self.report({'ERROR'}, 'Nothing is selected')
      return {'FINISHED'}

    for obj in context.selected_objects:
      for material_slot in obj.material_slots:
        material = material_slot.material
        if material.use_nodes:
          for link in material.node_tree.links:
            if link.from_node.type == 'TEX_IMAGE' and link.to_socket.name == 'Base Color':
              path = bpy.path.abspath(link.from_node.image.filepath)
              bpy.ops.image.external_edit(filepath=path)
    return {'FINISHED'}

class BooleanOperator(bpy.types.Operator):
  """Boolean"""
  bl_idname, bl_label, bl_options = 'qm.boolean', 'Boolean', {'REGISTER', 'UNDO'}
  operation: EnumProperty(name='Operation', items=(
    ('DIFFERENCE', 'Difference', 'Difference'),
    ('UNION', 'Union', 'Union'),
    ('INTERSECT', 'Intersect', 'Intersect')
  ))
  solver: EnumProperty(name='Solver', default='EXACT', items=(
    ('FAST', 'Fast', 'Fast'),
    ('EXACT', 'Exact', 'Exact'),
  ))
  solidify: FloatProperty(name='Solidify', default=0)
  boundary_extend: FloatProperty(name='Boundary Extend', default=BOOLEAN_BOUNDARY_EXTEND, min=0)
  use_self: BoolProperty(name='Self', default=False)
  recalculate_normals: BoolProperty(name='Recalculate Normals', default=True)
  move_on_top: BoolProperty(name='Move Modifier On Top', default=True)

  def execute(self, context):
    if self.recalculate_normals and is_in_editmode(): bpy.ops.mesh.normals_make_consistent(inside=False)
    if not self.use_self and self.boundary_extend > 0:
      transform_pivot = context.scene.tool_settings.transform_pivot_point
      context.scene.tool_settings.transform_pivot_point = 'INDIVIDUAL_ORIGINS'
      val = 1 + self.boundary_extend
      bpy.ops.transform.resize(value=(val, val, val))
      context.scene.tool_settings.transform_pivot_point = transform_pivot
    if is_in_editmode():
      if self.solidify != 0:
        bpy.ops.mesh.solidify(thickness=self.solidify)
        bpy.ops.mesh.select_linked(delimit=set())
      bpy.ops.mesh.intersect_boolean(operation=self.operation, solver=self.solver, use_self=self.use_self)
    else:
      active = context.object
      objects = [o for o in context.selected_objects if o != active]
      for obj in objects:
        select(active)
        bpy.ops.object.modifier_add(type='BOOLEAN')
        boolean = context.object.modifiers[-1]
        boolean.object = obj
        boolean.object, boolean.operation, boolean.solver = obj, self.operation, self.solver
        if self.move_on_top:
          move_modifier_on_top(boolean.name)
        select(obj)
        context.object.display_type = 'BOUNDS'
        context.object.hide_render = True
        if self.solidify != 0:
          bpy.ops.object.modifier_add(type='SOLIDIFY')
          solidify = context.object.modifiers[-1]
          solidify.offset = .5
          solidify.thickness = self.solidify
      bpy.ops.object.select_all(action='DESELECT')
      for obj in objects: obj.select_set(True)
    return {'FINISHED'}

class KnifeIntersectOperator(bpy.types.Operator):
  """Knife Intersect"""
  bl_idname, bl_label, bl_options = 'qm.knife_intersect', 'Knife Intersect', {'REGISTER', 'UNDO'}
  solver: EnumProperty(name='Solver', default='EXACT', items=(
    ('FAST', 'Fast', 'Fast'),
    ('EXACT', 'Exact', 'Exact'),
  ))
  boundary_extend: FloatProperty(name='Boundary Extend', default=0.001, min=0)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    if self.boundary_extend > 0:
      transform_pivot = context.scene.tool_settings.transform_pivot_point
      context.scene.tool_settings.transform_pivot_point = 'INDIVIDUAL_ORIGINS'
      val = 1 + self.boundary_extend
      bpy.ops.transform.resize(value=(val, val, val))
      context.scene.tool_settings.transform_pivot_point = transform_pivot
    make_vertex_group('qm_knife_intersect_original')
    bpy.ops.object.vertex_group_assign()
    bpy.ops.mesh.intersect(mode='SELECT_UNSELECT', separate_mode='CUT', solver=self.solver)
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.vertex_group_select()
    bpy.ops.mesh.select_linked(delimit=set())
    bpy.ops.mesh.delete(type='VERT')
    bpy.ops.object.vertex_group_remove()
    return {'FINISHED'}

class PlaneIntersectOperator(bpy.types.Operator):
  """Plane Intersect"""
  bl_idname, bl_label, bl_options = 'qm.plane_intersect', 'Plane Intersect', {'REGISTER', 'UNDO'}
  mode: EnumProperty(name='Mode', default='ISLAND', items=(
    ('SELECTION', 'Selection', 'Selection'),
    ('ISLAND', 'Island', 'Island'),
    ('MESH', 'Whole Mesh', 'Whole Mesh')
  ))
  snap_view_axis: BoolProperty(name='Snap View Axis', default = True)
  active: BoolProperty(name='Active', default = True)
  clear_outer: BoolProperty(name='Clear Outer', default = False)
  clear_inner: BoolProperty(name='Clear Inner', default = False)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    vector = view_snapped_vector(False, False) if self.snap_view_axis else view_vector(False, False)
    cursor_to_selected(self.active)
    if self.mode == 'ISLAND': bpy.ops.mesh.select_linked(delimit=set())
    elif self.mode == 'MESH': bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.bisect(plane_co=context.scene.cursor.location, plane_no=vector, clear_outer=self.clear_outer, clear_inner=self.clear_inner)
    return {'FINISHED'}

class WeldEdgesIntoFacesOperator(bpy.types.Operator):
  """Weld Edges Into Faces"""
  bl_idname, bl_label, bl_options = 'qm.weld_edges_into_faces', 'Weld Edges Into Faces', {'REGISTER', 'UNDO'}

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.face_split_by_edges()
    bpy.ops.mesh.select_all(action='DESELECT')
    return {'FINISHED'}

class ParentToNewEmptyOperator(bpy.types.Operator):
  """Parent To New Empty"""
  bl_idname, bl_label, bl_options = 'qm.parent_to_new_empty', 'Parent To New Empty', {'REGISTER', 'UNDO'}
  reset_transforms: BoolProperty(name='Reset Transforms', default=True)


  def execute(self, context):
    parent = context.object.parent
    selection = context.selected_objects
    bpy.ops.view3d.snap_cursor_to_selected()
    bpy.ops.object.empty_add()
    empty = context.object
    for obj in selection:
      obj.select_set(True)
    if self.reset_transforms:
      bpy.ops.object.parent_no_inverse_set()
    else:
      bpy.ops.object.parent_set()
    if parent:
      select(empty)
      parent.select_set(True)
      context.view_layer.objects.active = parent
      bpy.ops.object.parent_set()
      select(empty)
    return {'FINISHED'}

class ClearDriversOperator(bpy.types.Operator):
  """Clear Drivers"""
  bl_idname, bl_label, bl_options = 'qm.clear_drivers', 'Clear Drivers', {'REGISTER', 'UNDO'}

  def execute(self, context):
    for obj in context.selected_objects:
      animation_data = obj.animation_data
      if animation_data:
        for dr in obj.animation_data.drivers:
          obj.driver_remove(dr.data_path, -1)
    return {'FINISHED'}

class SetUseSelfDriversOperator(bpy.types.Operator):
  """Set Use Self Drivers"""
  bl_idname, bl_label, bl_options = 'qm.set_use_self_drivers', 'Set Use Self Drivers', {'REGISTER', 'UNDO'}

  def execute(self, context):
    for obj in context.selected_objects:
      animation_data = obj.animation_data
      if animation_data:
        for dr in obj.animation_data.drivers:
          dr.driver.use_self = True
          # Reevaluate expression with use self enabled:
          dr.driver.expression = dr.driver.expression
    return {'FINISHED'}

class IntersectOperator(bpy.types.Operator):
  """Intersect"""
  bl_idname, bl_label, bl_options = 'qm.intersect', 'Intersect', {'REGISTER', 'UNDO'}
  snap_to_axis: BoolProperty(name='Snap To Axis', default=True)
  recalculate_normals: BoolProperty(name='Recalculate Normals', default=True)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    if self.recalculate_normals: bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.qm.flatten()
    v = 1 + BOOLEAN_BOUNDARY_EXTEND
    bpy.ops.transform.resize(value=(v, v, v), orient_type='GLOBAL')
    vector = view_snapped_vector(False, False) if self.snap_to_axis else view_vector(False, False)
    l = max((context.object.dimensions * vector).length, 1)
    bpy.ops.transform.translate(value=vector*l, orient_type='GLOBAL')
    bpy.ops.object.vertex_group_add()
    bpy.ops.object.vertex_group_assign()
    bpy.ops.mesh.delete(type='ONLY_FACE')
    bpy.ops.object.vertex_group_select()
    bpy.ops.mesh.select_mode(type='EDGE')
    bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={'value':vector * -l * 3})
    bpy.ops.mesh.select_linked(delimit=set())
    bpy.ops.mesh.intersect(mode='SELECT_UNSELECT', solver='FAST', separate_mode='CUT', threshold=0.000000000001)
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.vertex_group_select()
    bpy.ops.mesh.select_linked(delimit=set())
    bpy.ops.mesh.delete(type='VERT')
    bpy.ops.object.vertex_group_remove()
    return {'FINISHED'}

class TransformOrientationOperator(bpy.types.Operator):
  """Transform Orientation"""
  bl_idname, bl_label, bl_options = 'qm.transform_orientation', 'Transform Orientation', {'REGISTER', 'UNDO'}
  type: StringProperty(name='Type')

  def execute(self, context):
    if self.type == 'CREATE': bpy.ops.transform.create_orientation(use=True, name = 'Custom', overwrite = True)
    elif self.type == 'NORMAL':
      context.scene.transform_orientation_slots[0].type = 'NORMAL'
      context.scene.tool_settings.transform_pivot_point = 'ACTIVE_ELEMENT'
    else: context.scene.transform_orientation_slots[0].type = self.type
    if self.type != 'NORMAL':
      context.scene.tool_settings.transform_pivot_point = 'BOUNDING_BOX_CENTER'
    return {'FINISHED'}

class TransformPivotOperator(bpy.types.Operator):
  """Transform Pivot"""
  bl_idname, bl_label, bl_options = 'qm.transform_pivot', 'Transform Pivot', {'REGISTER', 'UNDO'}
  type: StringProperty(name='Type')

  def execute(self, context):
    context.scene.tool_settings.transform_pivot_point = self.type
    return {'FINISHED'}

class SetSnapOperator(bpy.types.Operator):
  """Set Snap"""
  bl_idname, bl_label = 'qm.set_snap', 'Set Snap'
  mode: StringProperty(name='Mode')
  type: StringProperty(name='Type')

  def execute(self, context):
    ts = context.scene.tool_settings
    if self.mode == 'GENERAL':
      ts.use_snap_backface_culling = ts.use_snap_self = True
      if self.type == 'VERTEX': ts.snap_elements, ts.use_snap_align_rotation = {'VERTEX', 'EDGE_MIDPOINT'}, False
      elif self.type == 'FACE': ts.snap_elements, ts.use_snap_align_rotation = {'VERTEX', 'EDGE', 'FACE'}, True
      elif self.type == 'INCREMENT': ts.snap_elements, ts.use_snap_align_rotation, use_snap_grid_absolute = {'INCREMENT'}, False, False
    elif self.mode == 'TARGET':
      ts.snap_target = self.type
      if self.type == 'CLOSEST':
        context.scene.tool_settings.transform_pivot_point = 'BOUNDING_BOX_CENTER'
    return {'FINISHED'}

class ModeOperator(bpy.types.Operator):
  """Set Mode"""
  bl_idname, bl_label = 'qm.mode_set', 'Mode'
  mode: StringProperty(name='Mode')

  def execute(self, context):
    gpencil_modes = {
      'OBJECT': 'OBJECT',
      'EDIT': 'EDIT_GPENCIL',
      'SCULPT': 'SCULPT_GPENCIL',
      'VERTEX_PAINT': 'VERTEX_GPENCIL',
      'WEIGHT_PAINT': 'WEIGHT_GPENCIL',
      'TEXTURE_PAINT': 'PAINT_GPENCIL'
    }
    mode = gpencil_modes[self.mode] if context.active_object and context.active_object.type == 'GPENCIL' else self.mode
    try: bpy.ops.object.mode_set(mode=mode)
    except: pass
    return {'FINISHED'}

class ToolOperator(bpy.types.Operator):
  """Set Tool"""
  bl_idname, bl_label = 'qm.tool', 'Set Tool'
  tool_name: StringProperty(name='Tool')

  def execute(self, context):
    bpy.ops.wm.tool_set_by_id(name=self.tool_name)
    return {'FINISHED'}

class SaveAndReloadOperator(bpy.types.Operator):
  """Save and Reload"""
  bl_idname, bl_label, bl_options = 'qm.save_and_reload', 'Save And Reload', {'REGISTER', 'UNDO'}

  def execute(self, context):
    bpy.ops.wm.save_mainfile()
    bpy.ops.wm.revert_mainfile()
    return {'FINISHED'}

class ReimportTexturesOperator(bpy.types.Operator):
  """Reimport Textures"""
  bl_idname, bl_label, bl_options = 'qm.reimport_textures', 'Reimport Textures', {'REGISTER', 'UNDO'}

  def execute(self, context):
    for item in bpy.data.images: item.reload()
    return {'FINISHED'}

class UnpackAllDataToFilesOperator(bpy.types.Operator):
  """Unpack All Data To Files"""
  bl_idname, bl_label, bl_options = 'qm.unpack_all_data_to_files', 'Unpack All Data To Files', {'REGISTER', 'UNDO'}

  def execute(self, context):
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    bpy.ops.file.pack_all()
    bpy.ops.file.unpack_all(method='WRITE_LOCAL')
    return {'FINISHED'}

class ExportOperator(bpy.types.Operator):
  """Export"""
  bl_idname, bl_label = 'qm.export', 'Export'
  mode: StringProperty(name='Mode', default='fbx')
  unpack_data: BoolProperty(name='Unpack Data', default=False)
  apply_modifiers: BoolProperty(name='Apply Modifiers', default=True)
  apply_transform: BoolProperty(name='Apply Transform', default=True)
  batch_mode: StringProperty(name='Batch Mode', default='OFF')
  remove_suffix: BoolProperty(name='Remove Suffix', default=True)

  def execute(self, context):
    if bpy.data.filepath == '':
      self.report({'ERROR'}, 'File is not saved')
      return {'FINISHED'}

    directory, file = get_paths()

    # Save the blend file
    bpy.ops.wm.save_mainfile()

    # Unpack all data to files if needed
    if self.unpack_data:
      bpy.ops.qm.unpack_all_data_to_files()

    # Remove _a, _b, _c, etc suffix if present
    if self.remove_suffix:
      file = re.sub('_[a-cA-C]$', '', file)

    if self.mode == 'glb':
      bpy.ops.export_scene.gltf(
        export_format='GLB',
        export_apply=self.apply_modifiers,
        filepath=directory + file + '.glb'
      )
    elif self.mode == 'fbx':
      bpy.ops.export_scene.fbx(
        mesh_smooth_type='EDGE',
        use_mesh_modifiers=self.apply_modifiers,
        add_leaf_bones=False,
        apply_scale_options='FBX_SCALE_ALL',
        use_batch_own_dir=False,
        bake_anim_use_nla_strips=False,
        bake_space_transform=self.apply_transform,
        batch_mode=self.batch_mode,
        filepath=directory + file + '.fbx' if self.batch_mode == 'OFF' else directory
      )
    else:
      self.report({'ERROR'}, 'Unknown export extension')
    return {'FINISHED'}

class ViewOperator(bpy.types.Operator):
  """View Selected if in edit mode or anything is selected in object mode. View Camera otherwise"""
  bl_idname, bl_label = 'qm.view', 'View'
  camera: BoolProperty(name='Camera', default=False)

  def execute(self, context):
    if is_in_editmode() or len(context.selected_objects) > 0:
      bpy.ops.view3d.view_selected()
    else:
      bpy.ops.view3d.view_camera()
    return {'FINISHED'}

# @QuickMenu

class QuickMenu(bpy.types.Menu):
  bl_label, bl_idname = 'Quick Menu', 'OBJECT_MT_quick_menu'

  def draw(self, context):
    layout = self.layout
    draw_menu(self, app['items'])
    layout.separator()
    layout.operator('qm.edit_items', text='Edit Quick Menu')
    layout.operator('qm.load_items', text='Reload Quick Menu')

# @Preferences

class QuickMenuPreferences(bpy.types.AddonPreferences):
  bl_idname = __name__

  hotkey: StringProperty(name='Hotkey (Restart required)', default='D')

  def draw(self, context):
    layout = self.layout
    layout.prop(self, 'hotkey')

# @Properties

class QuickMenuProperties(bpy.types.PropertyGroup):
  vertex_color_index: IntProperty(name='Vertex Color Index', default=3)

# @Register

classes = (
  QuickMenuOperator,
  EditMenuItemsOperator,
  ReloadMenuItemsOperator,

  JoinSeparateOperator, SetSmoothOperator, LocalViewOperator, SetOriginOperator, ProportionalEditingOperator,
  WireframeOperator, RotateOperator, DrawOperator, ApplyToMultiuserOperator, ConvertToInstancesOperator, CorrectAttributesOperator,
  SelectRingOperator, SelectMoreOperator, RegionToLoopOperator, InvertSelectionConnectedOperator,
  SelectSharpEdgesOperator, SelectViewGeometryOperator, AddSingleVertexOperator, SpinOperator,
  BboxOperator, ConnectOperator, AddGeometryOperator, ExtrudeBothWaysOperator, ClearSharpOperator, FlattenOperator,
  RandomizeOperator, ConvertOperator, ConvertToMeshOperator, MirrorOperator, SubsurfOperator,
  BevelOperator, SolidifyOperator, TriangulateOperator, ArrayOperator,
  SimpleDeformOperator, ClearModifiersOperator, DeleteBackFacingOperator,
  SeparateByLoosePartsOperator, StraightenUVsOperator, UVProjectModifierOperator, MarkSeamOperator, 
  MarkSeamsSharpOperator, MarkSeamsFromIslandsOperator, TransformUVsOperator, SetVertexColorOperator, SelectByVertexColorOperator, BakeIDMapOperator, EditAlbedoMapOperator,
  BooleanOperator, WeldEdgesIntoFacesOperator, ParentToNewEmptyOperator, ClearDriversOperator, SetUseSelfDriversOperator,
  PlaneIntersectOperator, KnifeIntersectOperator, IntersectOperator, TransformOrientationOperator, TransformPivotOperator,
  SetSnapOperator, ModeOperator, ToolOperator, SaveAndReloadOperator, ReimportTexturesOperator, UnpackAllDataToFilesOperator, ExportOperator, ViewOperator,

  QuickMenu, QuickMenuPreferences, QuickMenuProperties
)

def draw_menu(self, items):
  layout = self.layout
  i = 0
  for item in items:
    if 'mode' in item and item['mode'] != bpy.context.mode:
      continue
    title = item['title']
    i += 1
    if i < 10 and not title.startswith('('):
      title = f'({i}) {title}'
    if 'children' in item:
      layout.menu(item['idname'], text=title)
    elif item['title'] == '[Separator]':
      layout.separator()
      i -= 1
    elif 'operator' in item:
      operator = layout.operator(item['operator'], text=title)
      if 'params' in item:
        for key, val in item['params'].items():
          if isinstance(val, list): val = tuple(val)
          operator[key] = val
    elif 'menu' in item:
      layout.menu(item['menu'], text=title) 

def register_menu_type(menu_definition):
  title = menu_definition['title']
  items = menu_definition['children']
  idname = menu_definition['idname']

  def draw(self, context):
    draw_menu(self, items)

  menu_type = type(idname + "Menu", (bpy.types.Menu,), {
    'bl_idname': idname,
    'bl_label': title,
    'draw': draw
  })

  bpy.utils.register_class(menu_type)

def get_or_create_menu_definition_at_path(path, items):
  for item in items:
    if item['title'] == path[0]:
      if len(path) == 1:
        return item
      else:
        return get_or_create_menu_definition_at_path(path[1:], item['children'])

  menu_definition = {
    'title': path[0],
    'children': [],
    'idname': 'OBJECT_MT_Menu' + re.sub('[^A-Za-z0-9]+', '', path[0])
  }

  register_menu_type(menu_definition)
  items.append(menu_definition)
  return menu_definition

def load_items(config_path):
  app['items'] = []

  # if not os.path.exists(config_path):
  #   raise Exception('Config file not found')

  with open(config_path, 'r') as config:
    data = config.read()
  
  try:
    obj = json.loads(data)
  except:
    raise Exception('Decoding JSON has failed')

  if not 'items' in obj:
    raise Exception('No items in config')
 
  for item in obj['items']:
    # Split by "/"
    path = re.split('\s*\/\s*', item['path'])
    item['title'] = path[-1]
    if len(path) == 1:
      app['items'].append(item)
    else:
      menu = get_or_create_menu_definition_at_path(path[:-1], app['items'])
      menu['children'].append(item)

def get_config_path():
  if __name__ == '__main__':
    # For testing purposes:
    return '/Users/passivestar/Files/blender/addons/quickmenu/config.json'
  else:
    print(__location__)
    return os.path.join(__location__, 'config.json')

def register():
  for c in classes: bpy.utils.register_class(c)
  bpy.types.Scene.quick_menu = PointerProperty(type=QuickMenuProperties)
  wm = bpy.context.window_manager
  kc = wm.keyconfigs.addon
  if __name__ == '__main__':
    hotkey = 'D'
  else:
    hotkey = bpy.context.preferences.addons[__name__].preferences.hotkey
  if kc:
    km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
    kmi = km.keymap_items.new(QuickMenuOperator.bl_idname, type=hotkey.upper(), value='PRESS')
    app['keymaps'].append((km, kmi))
  load_items(get_config_path())

def unregister():
  for c in classes: bpy.utils.unregister_class(c)
  del bpy.types.Scene.quick_menu
  for km, kmi in app['keymaps']:
    km.keymap_items.remove(kmi)
  app['keymaps'].clear()

if __name__ == '__main__': register()