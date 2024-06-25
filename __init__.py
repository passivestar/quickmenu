import bpy, bmesh, math, re, json, string, os, platform, subprocess
from bpy.props import IntProperty, FloatProperty, StringProperty, BoolProperty, EnumProperty, FloatVectorProperty, BoolVectorProperty, PointerProperty
from mathutils import Vector, Euler, Quaternion, Matrix, Color
from random import random
from functools import reduce

bl_info = {
  'name': 'QuickMenu',
  'version': (3, 0, 10),
  'author': 'passivestar',
  'blender': (4, 1, 0),
  'location': 'Press the hotkey in 3D View',
  'description': 'Simplifies access to useful operators and adds new functionality',
  'category': '3D View'
}

# @Globals

app = {
  "items": [],
  "first_run": True,
  "vertex_colors": [
    (247, 241, 176),
    (246, 212, 180),
    (252, 202, 206),
    (241, 192, 232),
    (207, 186, 240),
    (163, 196, 243),
    (144, 219, 244),
    (152, 245, 225),
    (185, 251, 192),
    (163, 240, 173),
  ],
}

if __name__ == '__main__':
  # For development purposes when running the script directly in Blender:
  addon_directory = '/Users/passivestar/Files/blender/addons/quickmenu/'
else:
  addon_directory = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

nodes_path = os.path.join(addon_directory, 'nodetools.blend')
config_path = os.path.join(addon_directory, 'config.json')

# @Util

def select(obj):
  bpy.ops.object.select_all(action='DESELECT')
  obj.select_set(True)
  bpy.context.view_layer.objects.active = obj

def get_selected_non_active():
  objects = [o for o in bpy.context.selected_objects if o != bpy.context.object]
  return objects[0] if len(objects) == 1 else None

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
  axes = ['X', 'Y', 'Z']
  for i in range(3):
    if vector[i] == 1:
      return axes[i], False
    elif vector[i] == -1:
      return axes[i], True

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

def execute_in_mode(mode, callback, *args):
  previous_mode = 'EDIT' if is_in_editmode() else bpy.context.mode
  bpy.ops.object.mode_set(mode=mode)
  result = callback(*args)
  try: bpy.ops.object.mode_set(mode=previous_mode)
  except: pass
  return result

def make_vertex_group(name, assign=True):
  bpy.context.object.vertex_groups.new(name=name)
  bpy.ops.object.vertex_group_set_active(group=name)
  if assign: bpy.ops.object.vertex_group_assign()

def modifier_exists(modifier_type, name = None):
  if name is None:
    return len([m for m in bpy.context.object.modifiers if m.type == modifier_type]) > 0
  else:
    return len([m for m in bpy.context.object.modifiers if m.type == modifier_type and m.name == name]) > 0

def get_modifier(modifier_type, name):
  if name is None:
    return [m for m in bpy.context.object.modifiers if m.type == modifier_type][0]
  else:
    return [m for m in bpy.context.object.modifiers if m.type == modifier_type and m.name == name][0]

def move_modifier_on_top(modifier_name):
  bpy.ops.object.modifier_move_to_index(modifier=modifier_name, index=0)

def add_modifier(modifier_type):
  bpy.ops.object.modifier_add(type=modifier_type)
  return bpy.context.object.modifiers[-1]

def add_or_get_modifier(modifier_type, move_on_top=False):
  if modifier_exists(modifier_type):
    for modifier in bpy.context.object.modifiers:
      if modifier.type == modifier_type:
        return modifier
  bpy.ops.object.modifier_add(type=modifier_type)
  modifier = bpy.context.object.modifiers[-1]
  if move_on_top: move_modifier_on_top(modifier.name)
  return modifier

def geonode_modifier_exists(node_group_name):
  return len([m for m in bpy.context.object.modifiers if m.type == 'NODES' and m.node_group is not None and m.node_group.name == node_group_name]) > 0

def add_geonode_modifier(node_group_name):
  bpy.ops.object.modifier_add(type='NODES')
  modifier = bpy.context.object.modifiers[-1]
  modifier.node_group = bpy.data.node_groups[node_group_name]
  return modifier

def add_or_get_geonode_modifier(node_group_name):
  if geonode_modifier_exists(node_group_name):
    for modifier in bpy.context.object.modifiers:
      if modifier.type == 'NODES' and modifier.node_group.name == node_group_name:
        return modifier
  bpy.ops.object.modifier_add(type='NODES')
  modifier = bpy.context.object.modifiers[-1]
  modifier.node_group = bpy.data.node_groups[node_group_name]
  return modifier

def remove_geonode_modifier(node_group_name):
  if geonode_modifier_exists(node_group_name):
    for modifier in bpy.context.object.modifiers:
      if modifier.type == 'NODES' and modifier.node_group.name == node_group_name:
        bpy.context.object.modifiers.remove(modifier)
        break

def is_in_editmode():
  return bpy.context.mode == 'EDIT_MESH' or bpy.context.mode == 'EDIT_CURVE' or bpy.context.mode == 'EDIT_SURFACE' or bpy.context.mode == 'EDIT_METABALL' or bpy.context.mode == 'EDIT_TEXT' or bpy.context.mode == 'EDIT_ARMATURE'

def anything_is_selected_in_editmode():
  for o in bpy.context.objects_in_mode:
    if o.type == 'MESH':
      if True in [v.select for v in bmesh.from_edit_mesh(o.data).verts]:
        return True
    elif o.type == 'CURVE':
      for spline in o.data.splines:
        for p in spline.bezier_points:
          if p.select_control_point:
            return True
  return False

def anything_is_hidden_in_editmode():
  for o in bpy.context.objects_in_mode:
    if True in [v.hide for v in bmesh.from_edit_mesh(o.data).verts]:
      return True
  return False

def snake_to_title_case(string):
  return ''.join([s.title() for s in string.split('_')])

def nodes_were_loaded():
  # If any node starting with 'QM ' exists, assume nodes were loaded
  for n in bpy.data.node_groups:
    if n.name.startswith('QM '):
      return True
  return False

# @MenuOperators

class QuickMenuOperator(bpy.types.Operator):
  """Quick Menu"""
  bl_idname, bl_label, bl_options = 'qm.quick_menu', 'Quick Menu Operator', {'REGISTER', 'UNDO'}

  def execute(self, context):
    # Inject cursor
    bpy.ops.qm.set_cursor_rotation_to_view()

    # Unload geometry nodes on first run to make sure nodes are updated
    # when you update the addon
    if app['first_run']:
      unload_geometry_nodes()

    # Load geometry nodes if not yet loaded
    if not nodes_were_loaded():
      load_geometry_nodes()
    app['first_run'] = False

    bpy.ops.wm.call_menu(name=QuickMenu.bl_idname)
    return {'FINISHED'}

class EditMenuItemsOperator(bpy.types.Operator):
  """Edit Menu Items"""
  bl_idname, bl_label = 'qm.edit_items', 'Edit Menu Items Operator'

  def execute(self, context):
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
    load_items(config_path)
    return {'FINISHED'}

# @Operators

class JoinSeparateOperator(bpy.types.Operator):
  """Join or Separate"""
  bl_idname, bl_label, bl_options = 'qm.join_separate', 'Separate / Join', {'REGISTER', 'UNDO'}
  reset_origin: BoolProperty(name='Reset Origin on Separate', default=True)
  reset_drivers: BoolProperty(name='Reset Drivers on Separate', default=True)

  @classmethod
  def poll(cls, context):
    if is_in_editmode() and not anything_is_selected_in_editmode():
      return False
    return True

  def execute(self, context):
    if is_in_editmode():
      if anything_is_selected_in_editmode():
        if context.object.type == 'CURVE':
          bpy.ops.curve.separate()
        elif context.object.type == 'MESH':
          bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.editmode_toggle()
        select(context.selected_objects[-1])
        if self.reset_origin: bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
        if self.reset_drivers:
          bpy.ops.qm.clear_drivers()
    elif len(context.selected_objects) > 0:
      bpy.ops.object.join()
    return {'FINISHED'}

class SetSmoothOperator(bpy.types.Operator):
  """Set Smooth Shading. Hold shift to use modifier"""
  bl_idname, bl_label, bl_options = 'qm.smooth', 'Set Smooth', {'REGISTER', 'UNDO'}
  smooth: BoolProperty(name='Smooth', default=True)
  by_angle: BoolProperty(name='By Angle', default=True)
  angle: FloatProperty(name='Angle', subtype='ANGLE', default=0.872665, step=2, min=0, max=1.5708)
  use_modifier: BoolProperty(name='Use Modifier', default=True)

  def invoke(self, context, event):
    if event.shift: self.use_modifier = True
    return self.execute(context)

  def execute(self, context):
    if self.use_modifier:
      if self.smooth:
        m = add_or_get_geonode_modifier('Smooth by Angle')
        m['Input_1'] = self.angle
        m['Socket_1'] = True
      else:
        remove_geonode_modifier('Smooth by Angle')
    else:
      remove_geonode_modifier('Smooth by Angle')
      def fn():
        if self.smooth:
          if self.by_angle:
            try:
              bpy.ops.object.shade_smooth_by_angle(angle=self.angle)
              bpy.ops.mesh.customdata_custom_splitnormals_add()
            except : bpy.ops.object.shade_smooth(use_auto_smooth=True, auto_smooth_angle=self.angle)
          else: bpy.ops.object.shade_smooth()
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
        objects = context.selected_objects
        for obj in objects:
          select(obj)
          bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
          bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
          new_origin = Vector((0, 0, -obj.dimensions.z / 2))
          obj.data.transform(Matrix.Translation(-new_origin))
          obj.location += new_origin
        for obj in objects: obj.select_set(True)
    execute_in_mode('OBJECT', fn)
    return {'FINISHED'}

class ProportionalEditingOperator(bpy.types.Operator):
  """Toggle Proportional Editing"""
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
        self.report({'INFO'}, 'Proportional Editing: ' + ('On' if ts.use_proportional_edit else 'Off'))
      else:
        ts.use_proportional_edit = True
        ts.proportional_edit_falloff = self.falloff
    else:
      ts.use_proportional_connected = self.connected
      if ts.proportional_edit_falloff == self.falloff and not self.options.is_repeat:
        ts.use_proportional_edit_objects = not ts.use_proportional_edit_objects
        self.report({'INFO'}, 'Proportional Editing: ' + ('On' if ts.use_proportional_edit_objects else 'Off'))
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
      self.report({'INFO'}, 'Wireframe: ' + ('On' if ol.show_wireframes else 'Off'))
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

class CorrectAttributesOperator(bpy.types.Operator):
  """Toggle Correct Face Attributes"""
  bl_idname, bl_label, bl_options = 'qm.correct_attributes', 'Toggle Correct Face Attributes', {'REGISTER', 'UNDO'}

  def execute(self, context):
    ts = bpy.context.scene.tool_settings
    ts.use_transform_correct_face_attributes = not ts.use_transform_correct_face_attributes
    self.report({'INFO'}, 'Correct Face Attributes: ' + ('On' if ts.use_transform_correct_face_attributes else 'Off'))
    return {'FINISHED'}

class ClearModifiersOperator(bpy.types.Operator):
  """Clear Modifiers"""
  bl_idname, bl_label, bl_options = 'qm.clear_modifiers', 'Clear Modifiers', {'REGISTER', 'UNDO'}

  def execute(self, context):
    for obj in context.selected_objects:
      obj.modifiers.clear()
    return {'FINISHED'}

class SelectRingOperator(bpy.types.Operator):
  """Select ring. Hold shift to select loop"""
  bl_idname, bl_label, bl_options = 'qm.select_ring', 'Select Ring Or Loop', {'REGISTER', 'UNDO'}
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
  bl_idname, bl_label, bl_options = 'qm.select_more', 'Select More Or Less', {'REGISTER', 'UNDO'}
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

class MirrorOperator(bpy.types.Operator):
  """Mirror"""
  bl_idname, bl_label, bl_options = 'qm.mirror', 'Mirror', {'REGISTER', 'UNDO'}
  axis: BoolVectorProperty(name='Axis', subtype='XYZ')
  bisect_flip: BoolVectorProperty(name='Bisect Flip', subtype='XYZ')

  @classmethod
  def poll(cls, context):
    return len(context.selected_objects) > 0

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

class ArrayOperator(bpy.types.Operator):
  """Array"""
  bl_idname, bl_label, bl_options = 'qm.array', 'Array', {'REGISTER', 'UNDO'}
  count: IntProperty(name='Count', default=3, step=1, min=0)
  offset: FloatProperty(name='Offset', default=1.1)

  @classmethod
  def poll(cls, context):
    return len(context.selected_objects) > 0

  def execute(self, context):
    v = view_snapped_vector() * self.offset
    v.negate()
    a = add_or_get_modifier('ARRAY')
    a.count = self.count
    a.relative_offset_displace = v
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
    b.limit_method = 'WEIGHT' if self.use_weight else 'ANGLE'
    b.width, b.segments, b.angle_limit, b.harden_normals, b.loop_slide, b.use_clamp_overlap = self.amount, self.segments, self.angle, self.harden_normals, self.loop_slide, self.use_clamp_overlap
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
      t.min_vertices = 5
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

    # Show an error if nothing is selected
    if len(selection_indeces) == 0:
      self.report({'ERROR'}, 'Nothing is selected')
      return {'FINISHED'}

    # Show an error if nothing is active
    if len(active_indeces) == 0:
      self.report({'ERROR'}, 'Nothing is active. Please make sure you have an active face')
      return {'FINISHED'}

    def process_uvs():
      # Reorder active indices to ensure clockwise order
      active_uv = mesh.uv_layers.active.data
      center_x = sum(active_uv[i].uv.x for i in active_indeces) / len(active_indeces)
      center_y = sum(active_uv[i].uv.y for i in active_indeces) / len(active_indeces)
      active_indeces.sort(key=lambda i: math.atan2(active_uv[i].uv.y - center_y, active_uv[i].uv.x - center_x) % (2 * math.pi))

      # Align UV vertices for the active quad
      prev_uv_coords = first_axis = None
      for iteration_index, index in enumerate([*active_indeces, active_indeces[0]]):
        uv_coords = mesh.uv_layers.active.data[index].uv
        if prev_uv_coords:
          if first_axis == None:
            diff = uv_coords - prev_uv_coords
            diff_abs = [abs(diff.x), abs(diff.y)]
            min_axis = diff_abs.index(min(diff_abs))
            first_axis = min_axis
          else:
            min_axis = (first_axis + iteration_index + 1) % 2
          uv_coords[min_axis] = prev_uv_coords[min_axis]
        prev_uv_coords = uv_coords

    execute_in_mode('OBJECT', process_uvs)
    bpy.ops.uv.follow_active_quads()
    return {'FINISHED'}

class MarkSeamOperator(bpy.types.Operator):
  """Mark Or Clear Seam. Hold shift to clear seam"""
  bl_idname, bl_label, bl_options = 'qm.mark_seam', 'Mark Seam', {'REGISTER', 'UNDO'}
  clear_inner_region: BoolProperty(name='Clear Inner Region', default=False)
  clear: BoolProperty(name='Clear', default=False)
  unwrap: BoolProperty(name='Unwrap', default=True)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def invoke(self, context, event):
    if event.shift: self.clear = True
    return self.execute(context)

  def execute(self, context):
    if self.unwrap:
      unwrap_previous_value = bpy.context.scene.tool_settings.use_edge_path_live_unwrap
      bpy.context.scene.tool_settings.use_edge_path_live_unwrap = True
    if self.clear:
      bpy.ops.mesh.mark_seam(clear=True)
      if self.unwrap:
        bpy.context.scene.tool_settings.use_edge_path_live_unwrap = unwrap_previous_value
      return {'FINISHED'}
    mode = tuple(context.scene.tool_settings.mesh_select_mode).index(True)
    if self.clear_inner_region: bpy.ops.mesh.mark_seam(clear=True)
    if mode == 1: bpy.ops.mesh.mark_seam()
    elif mode == 2:
      bpy.ops.mesh.region_to_loop()
      bpy.ops.mesh.mark_seam()
      bpy.ops.mesh.loop_to_region()
      bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')
    if self.unwrap:
      bpy.context.scene.tool_settings.use_edge_path_live_unwrap = unwrap_previous_value
    return {'FINISHED'}

class SmartUVProject(bpy.types.Operator):
  """Smart UV Project"""
  bl_idname, bl_label, bl_options = 'qm.smart_uv_project', 'Smart UV Project', {'REGISTER', 'UNDO'}
  angle: FloatProperty(name='Angle', subtype='ANGLE', default=1.0472, min=0.0001, max=3.14159)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    bpy.ops.uv.smart_project(angle_limit=self.angle)
    bpy.ops.uv.seams_from_islands()
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
    return is_in_editmode() and anything_is_selected_in_editmode()

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
  set_to_active: BoolProperty(name='Set To Active', default = False)
  reset_index: BoolProperty(name='Reset Index', default = False)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()
  
  def invoke(self, context, event):
    if event.shift: self.reset_index = True
    return self.execute(context)

  def execute(self, context):
    context.space_data.shading.color_type = 'VERTEX'

    # Reset index
    if self.reset_index:
      context.scene.quick_menu.vertex_color_index = 0

    # Generate next unique RGB
    if not self.set_to_active and not self.options.is_repeat:
      i = context.scene.quick_menu.vertex_color_index

      # If index is in colors range, use it
      vertex_colors = app['vertex_colors']
      if i < len(vertex_colors):
        values = tuple([c / 255 for c in vertex_colors[i]])
      # Else pick next unique one
      else:
        values = (
          1 - (i * 3 % 10) / 10,
          1 - ((i * 3 // 10) % 10) / 10,
          1 - ((i * 3 // 10) % 10) / 10
        )
      next_color = Color()
      next_color.r = values[0]
      next_color.g = values[1]
      next_color.b = values[2]

      self.report({'INFO'}, 'Vertex Color Index: ' + str(i))

      context.scene.quick_menu.vertex_color_index += 1

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
  boundary_extend: FloatProperty(name='Boundary Extend', default=0.0001, min=0)
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
      bpy.ops.object.select_all(action='DESELECT')
      for obj in objects: obj.select_set(True)
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

class AddBoneOperator(bpy.types.Operator):
  """Add Bone"""
  bl_idname, bl_label, bl_options = 'qm.add_bone', 'Add Bone', {'REGISTER', 'UNDO'}

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    cursor_to_selected()
    bpy.ops.object.mode_set(mode='OBJECT')

    active = context.object
    active_bone_name = None

    # If armature exists, add bone to it:
    parent = context.object.parent
    if parent and parent.type == 'ARMATURE':
      select(parent)
      bpy.ops.object.mode_set(mode='EDIT')
      bpy.ops.armature.bone_primitive_add()
      bpy.ops.armature.select_linked()
      bpy.ops.view3d.snap_selected_to_cursor(use_offset=False)
      active_bone_name = context.selected_bones[0].name
      bpy.ops.object.mode_set(mode='OBJECT')
      select(active)
      bpy.ops.object.mode_set(mode='EDIT')
      # Remove selected geometry from all existing vertex groups:
      for group in active.vertex_groups:
        bpy.ops.object.vertex_group_set_active(group=group.name)
        bpy.ops.object.vertex_group_remove_from()
      # Add to vertex group:
      make_vertex_group(active_bone_name)
    # Else if armature doesnt exist, create it:
    else:
      bpy.ops.object.armature_add()
      armature = context.object
      active.select_set(True)
      bpy.ops.object.parent_set(type='ARMATURE_AUTO')
      armature.data.display_type = 'STICK'
      context.object.show_in_front = True
      bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
      active_bone_name = armature.data.bones[0].name
      select(active)
      bpy.ops.object.mode_set(mode='EDIT')

    return {'FINISHED'}

class AddCollisionOperator(bpy.types.Operator):
  """Add Collision"""
  bl_idname, bl_label, bl_options = 'qm.add_collision', 'Add Collision', {'REGISTER', 'UNDO'}

  thickness_outer: FloatProperty(name='Thickness Outer', default=0.01, min=0, max=1)
  cloth_friction: FloatProperty(name='Cloth Friction', default=5, min=0, max=80)

  def execute(self, context):
    add_or_get_modifier('COLLISION')
    context.object.collision.thickness_outer = self.thickness_outer
    context.object.collision.cloth_friction = self.cloth_friction
    return {'FINISHED'}

class AddClothOperator(bpy.types.Operator):
  """Add Cloth"""
  bl_idname, bl_label, bl_options = 'qm.add_cloth', 'Add Cloth', {'REGISTER', 'UNDO'}

  pressure: FloatProperty(name='Pressure', default=0, min=-2, max=2)
  tension: FloatProperty(name='Tension', default=5, min=0, max=30)
  compression: FloatProperty(name='Compression', default=5, min=0, max=30)
  shear: FloatProperty(name='Shear', default=5, min=0, max=30)
  bending: FloatProperty(name='Bending', default=0.1, min=0, max=30)
  self_collisions: BoolProperty(name='Self Collisions', default=False)

  def execute(self, context):
    c = add_or_get_modifier('CLOTH')
    c.settings.use_pressure = self.pressure != 0
    c.settings.uniform_pressure_force = self.pressure
    c.settings.tension_stiffness = self.tension
    c.settings.compression_stiffness = self.compression
    c.settings.shear_stiffness = self.shear
    c.settings.bending_stiffness = self.bending
    c.collision_settings.use_self_collision = self.self_collisions
    context.scene.frame_set(0)
    return {'FINISHED'}

class AnimateRotationOperator(bpy.types.Operator):
  """Animate Rotation"""
  bl_idname, bl_label, bl_options = 'qm.animate_rotation', 'Animate Rotation', {'REGISTER', 'UNDO'}

  cycles_x: IntProperty(name='Cycles X', default=0)
  cycles_y: IntProperty(name='Cycles Y', default=0)
  cycles_z: IntProperty(name='Cycles Z', default=1)

  def execute(self, context):
    end_frame = context.scene.frame_end

    for obj in context.selected_objects:
      for i, cycles in enumerate([self.cycles_x, self.cycles_y, self.cycles_z]):
        if cycles > 0:
          curve = obj.driver_add('rotation_euler', i)
          curve.driver.expression = f'frame / {end_frame} * tau * {cycles}'

    return {'FINISHED'}

class ToggleAutoKeyingOperator(bpy.types.Operator):
  """Toggle Auto Keying"""
  bl_idname, bl_label, bl_options = 'qm.toggle_auto_keying', 'Toggle Auto Keying', {'REGISTER', 'UNDO'}

  def execute(self, context):
    context.scene.tool_settings.use_keyframe_insert_auto = not context.scene.tool_settings.use_keyframe_insert_auto
    self.report({'INFO'}, 'Auto Keying: ' + ('On' if context.scene.tool_settings.use_keyframe_insert_auto else 'Off'))
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

class ToolOperator(bpy.types.Operator):
  """Set Tool"""
  bl_idname, bl_label = 'qm.tool', 'Set Tool'
  tool_name: StringProperty(name='Tool')

  def execute(self, context):
    bpy.ops.wm.tool_set_by_id(name=self.tool_name)
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
  unpack_data: BoolProperty(name='Unpack Data', default=True)
  apply_modifiers: BoolProperty(name='Apply Modifiers', default=True)
  apply_transform: BoolProperty(name='Apply Transform', default=True)
  batch_mode: StringProperty(name='Batch Mode', default='OFF')
  selected_object: BoolProperty(name='Selected Object', default=False)

  def execute(self, context):
    if bpy.data.filepath == '':
      self.report({'ERROR'}, 'File is not saved')
      return {'FINISHED'}

    file = bpy.path.basename(bpy.data.filepath).split('.')[0]
    file_directory = os.path.dirname(bpy.data.filepath)
    active_collection_name_clean = re.sub(r'[^a-zA-Z0-9_]', '_', bpy.context.view_layer.active_layer_collection.name)

    if self.batch_mode == "COLLECTION" and (self.mode == "gltf" or self.mode == "glb") and active_collection_name_clean == "Scene_Collection":
      self.report({'ERROR'}, 'Select a collection')
      return {'FINISHED'}

    # Save the blend file
    bpy.ops.wm.save_mainfile()

    # Unpack all data to files if needed
    if self.unpack_data:
      bpy.ops.qm.unpack_all_data_to_files()
    
    # Name of the object if exporting selected object
    filename = context.object.name if self.selected_object else file

    if self.mode == 'glb':
      bpy.ops.export_scene.gltf(
        export_format='GLB',
        export_apply=self.apply_modifiers,
        export_lights=True,
        export_cameras=True,
        export_keep_originals=True,
        export_extras=True,
        export_import_convert_lighting_mode='COMPAT',
        export_gn_mesh=True,
        use_selection=self.selected_object,
        use_active_collection=self.batch_mode == 'COLLECTION',
        filepath = os.path.join(file_directory, active_collection_name_clean if self.batch_mode == 'COLLECTION' else filename + '.glb')
      )
    elif self.mode == 'gltf':
      bpy.ops.export_scene.gltf(
        export_format='GLTF_SEPARATE',
        export_apply=self.apply_modifiers,
        export_lights=True,
        export_cameras=True,
        export_keep_originals=True,
        export_extras=True,
        export_import_convert_lighting_mode='COMPAT',
        export_gn_mesh=True,
        use_selection=self.selected_object,
        use_active_collection=self.batch_mode == 'COLLECTION',
        filepath = os.path.join(file_directory, active_collection_name_clean if self.batch_mode == 'COLLECTION' else filename + '.gltf')
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
        use_selection=self.selected_object,
        filepath=os.path.join(file_directory, filename + '.fbx') if self.batch_mode == 'OFF' else file_directory
      )
    else:
      self.report({'ERROR'}, 'Unknown export extension')
    return {'FINISHED'}

class MakeLodsOperator(bpy.types.Operator):
    """Make LODs from selection in object mode. This supports multiple objects"""
    bl_idname = "qm.make_lods"
    bl_label = "Make LODs"
    bl_options = {'REGISTER', 'UNDO'}

    num_lods: IntProperty(name="Num of LODs",default=4,min=1,max=6)
    lod0: FloatProperty(name="LOD 0",default=100,min=0.01,max=100.0,precision=2,subtype="PERCENTAGE", options={'HIDDEN'})
    lod1: FloatProperty(name="LOD 1",default=50,min=0.01,max=100.0,precision=2,subtype="PERCENTAGE")
    lod2: FloatProperty(name="LOD 2",default=25,min=0.01,max=100.0,precision=2,subtype="PERCENTAGE")
    lod3: FloatProperty(name="LOD 3",default=12.5,min=0.01,max=100.0,precision=2,subtype="PERCENTAGE")
    lod4: FloatProperty(name="LOD 4",default=6.25,min=0.01,max=100.0,precision=2,subtype="PERCENTAGE")
    lod5: FloatProperty(name="LOD 5",default=3.125,min=0.01,max=100.0,precision=2,subtype="PERCENTAGE")
    lod6: FloatProperty(name="LOD 6",default=1.5625,min=0.01,max=100.0,precision=2,subtype="PERCENTAGE")

    is_no_lod0: BoolProperty(name="Do not create LOD0", default=True)
    is_apply_modifier: BoolProperty(name="Apply modifiers", default=True)
    
    lods = []

    @classmethod
    def poll(cls, context):
      return (context.mode == 'OBJECT') and len(context.selected_objects) > 0

    def execute(self, context):
        self.lods += [self.lod0, self.lod1, self.lod2, self.lod3, self.lod4, self.lod5, self.lod6]
        
        objs = context.selected_objects
        outputs = []

        for i in range(len(objs)):
          for k in range(self.num_lods+1):
            outputs.append(self.make_lod(objs[i], k))

        if self.is_no_lod0:
          [obj.select_set(True) for obj in objs+outputs if obj is not None]
        else:
          [obj.select_set(True) for obj in outputs if obj is not None]

        return {'FINISHED'}
    
    def make_lod(self, object, level):
      if level==0 and self.is_no_lod0:
        return

      bpy.context.view_layer.objects.active = object
      bpy.ops.object.select_all(action="DESELECT")
      bpy.context.view_layer.objects.active.select_set(True)
      bpy.ops.object.duplicate()

      obj = bpy.context.view_layer.objects.active

      if level > 0:
        bpy.ops.object.modifier_add(type='DECIMATE')
        obj.modifiers["Decimate"].ratio = self.lods[level]*0.01
        if self.is_apply_modifier:
          for mod in obj.modifiers:
            bpy.ops.object.modifier_apply(modifier=mod.name)

      obj.name = object.name + "_LOD" + str(level)

      return obj

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

class SetCursorRotationToViewOperator(bpy.types.Operator):
  """Set Cursor Rotation To View"""
  bl_idname, bl_label = 'qm.set_cursor_rotation_to_view', 'Set Cursor Rotation To View'

  def execute(self, context):
    euler = view_vector().to_track_quat('Z', 'Y').to_euler()
    context.scene.cursor.rotation_euler = euler
    return {'FINISHED'}

class VoidEditModeOnlyOperator(bpy.types.Operator):
  """Edit Mode Only"""
  bl_idname, bl_label = 'qm.void_edit_mode_only', 'Edit Mode Only'

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    return {'FINISHED'}

# @QuickMenu

class QuickMenu(bpy.types.Menu):
  bl_idname, bl_label = 'OBJECT_MT_quick_menu', 'Quick Menu'

  def draw(self, context):
    layout = self.layout

    # Draw a label that shows a warning if the current version is less than blender 4.1.0
    if bpy.app.version < (4, 1, 0):
      layout.label(text=f'You need Blender 4.1 for the addon to work properly', icon='ERROR')
      layout.label(text=f'Current version: {bpy.app.version_string}')

    draw_menu(self, app['items'])

    layout.separator()
    layout.operator('qm.edit_items', text='Edit Menu')
    layout.operator('qm.load_items', text='Reload Menu')

# @Preferences

class QuickMenuPreferences(bpy.types.AddonPreferences):
  bl_idname = __name__

  def draw(self, context):
    layout = self.layout
    layout.label(text='To change the hotkey, go to Keymap and search for "Quick Menu Operator"')

# @Properties

class QuickMenuProperties(bpy.types.PropertyGroup):
  # Used to track the current vertex color index. This is used to generate unique
  # vertex colors for id maps in apps like Substance Painter
  vertex_color_index: IntProperty(name='Vertex Color Index', default=3)

# @Register

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
      icon = 'NODETREE' if item['operator'] == 'geometry.execute_node_group' else 'NONE'
      if 'icon' in item: icon = item['icon']

      if item['operator'] == 'geometry.execute_node_group' and not is_in_editmode():
        layout.operator('qm.void_edit_mode_only', text=title, icon=icon)
      else:
        operator = layout.operator(item['operator'], text=title, icon=icon)
        if 'params' in item:
          for key, val in item['params'].items():
            operator[key] = tuple(val) if isinstance(val, list) else val

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
      return item if len(path) == 1 else get_or_create_menu_definition_at_path(path[1:], item['children'])

  menu_definition = {
    'title': path[0],
    'children': [],
    'idname': 'OBJECT_MT_Menu' + re.sub('[^A-Za-z0-9]+', '', path[0])
  }

  register_menu_type(menu_definition)
  items.append(menu_definition)

  return menu_definition

# Load the items from the config and add them to the menu
def load_items(config_path):
  app['items'] = []

  with open(config_path, 'r') as config:
    data = config.read()
  
  try:
    obj = json.loads(data)
  except:
    raise Exception('Decoding JSON has failed')

  if not 'items' in obj:
    raise Exception('No items in config')
 
  for item in obj['items']:
    # Split by "/" and remove whitespace
    path = re.split('\s*\/\s*', item['path'])
    item['title'] = path[-1]
    if len(path) == 1:
      app['items'].append(item)
    else:
      menu = get_or_create_menu_definition_at_path(path[:-1], app['items'])
      menu['children'].append(item)

# Remove the node groups from the current file
def unload_geometry_nodes():
  for node_group in bpy.data.node_groups:
    if node_group.name.startswith('QM '):
      bpy.data.node_groups.remove(node_group)

# Add built-in geometry nodes to the current file
def load_geometry_nodes():
  with bpy.data.libraries.load(nodes_path) as (data_from, data_to):
    # Append nodes groups that dont exist in the current file
    for node_group in data_from.node_groups:
      if node_group not in bpy.data.node_groups:
        data_to.node_groups.append(node_group)

def get_classes():
  return [cls for name, cls in globals().items() if isinstance(cls, type) and issubclass(cls, (bpy.types.Operator, bpy.types.PropertyGroup, bpy.types.Menu, bpy.types.AddonPreferences))]

def find_keymap_item(km, idname):
  if '3D View' not in km:
    return None

  for keymap_item in km['3D View'].keymap_items:
    if keymap_item.idname == idname:
      return keymap_item
  return None
 
def register():
  for cls in get_classes():
    if cls.__name__ not in bpy.types.Scene.__annotations__:
      bpy.utils.register_class(cls)

  bpy.types.Scene.quick_menu = PointerProperty(type=QuickMenuProperties)

  key_config = bpy.context.window_manager.keyconfigs.active
  keymap_item = find_keymap_item(key_config.keymaps, QuickMenuOperator.bl_idname)

  if keymap_item is None:
    km = key_config.keymaps.new(name='3D View', space_type='VIEW_3D')
    km.keymap_items.new(QuickMenuOperator.bl_idname, type='D', value='PRESS')
  
  # Load menu items from the config
  load_items(config_path)

def unregister():
  for cls in get_classes(): bpy.utils.unregister_class(cls)
  del bpy.types.Scene.quick_menu

# Call if ran as script
if __name__ == '__main__': register()