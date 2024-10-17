import bpy, bmesh
from mathutils import Vector, Matrix

def is_in_editmode():
  return 'EDIT' in bpy.context.mode

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

def execute_in_object_mode(callback, *args):
  return execute_in_mode('OBJECT', callback, *args)

def execute_in_edit_mode(callback, *args):
  return execute_in_mode('EDIT', callback, *args)

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

def add_or_get_modifier(modifier_name, modifier_type, move_on_top=False):
  if modifier_exists(modifier_type):
    for modifier in bpy.context.object.modifiers:
      if modifier.type == modifier_type:
        return modifier
  modifier = bpy.context.object.modifiers.new(name=modifier_name, type=modifier_type)
  if move_on_top: move_modifier_on_top(modifier.name)
  return modifier

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