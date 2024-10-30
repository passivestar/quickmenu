import bpy, bmesh, math
from mathutils import Vector, Matrix
from functools import reduce
from .. common.common import *

class StraightenUVsOperator(bpy.types.Operator):
  """Straighten UVs"""
  bl_idname = 'qm.straighten_uvs'
  bl_label = 'Straighten UVs'
  bl_options = {'REGISTER', 'UNDO'}

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    mesh = context.object.data
    selection_indeces, active_indeces = execute_in_edit_mode(get_selection_and_active_indices)

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

    execute_in_object_mode(process_uvs)
    bpy.ops.uv.follow_active_quads()
    return {'FINISHED'}

class MarkSeamOperator(bpy.types.Operator):
  """Mark Or Clear Seam. Hold shift to clear seam"""
  bl_idname = 'qm.mark_seam'
  bl_label = 'Mark Seam'
  bl_options = {'REGISTER', 'UNDO'}

  clear_inner_region: bpy.props.BoolProperty(name='Clear Inner Region', default=False)

  clear: bpy.props.BoolProperty(name='Clear', default=False)

  unwrap: bpy.props.BoolProperty(name='Unwrap', default=True)

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
  bl_idname = 'qm.smart_uv_project'
  bl_label = 'Smart UV Project'
  bl_options = {'REGISTER', 'UNDO'}

  angle: bpy.props.FloatProperty(name='Angle', subtype='ANGLE', default=1.0472, min=0.0001, max=3.14159)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    bpy.ops.uv.smart_project(angle_limit=self.angle)
    bpy.ops.uv.seams_from_islands()
    return {'FINISHED'} 

class TransformUVsOperator(bpy.types.Operator):
  """Transform UV"""
  bl_idname = 'qm.transform_uvs'
  bl_label = 'Transform UVs'
  bl_options = {'REGISTER', 'UNDO'}

  offset_x: bpy.props.FloatProperty(name='Offset X', default=0, step=0.1)

  offset_y: bpy.props.FloatProperty(name='Offset Y', default=0, step=0.1)

  rotation: bpy.props.FloatProperty(name='Rotation', subtype='ANGLE', default=0, soft_min=-3.14159, soft_max=3.14159)

  scale_x: bpy.props.FloatProperty(name='Scale X', default=1, step=0.1, soft_min=0)

  scale_y: bpy.props.FloatProperty(name='Scale Y', default=1, step=0.1, soft_min=0)

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

def register():
    bpy.utils.register_class(StraightenUVsOperator)
    bpy.utils.register_class(MarkSeamOperator)
    bpy.utils.register_class(SmartUVProject)
    bpy.utils.register_class(TransformUVsOperator)

def unregister():
    bpy.utils.unregister_class(StraightenUVsOperator)
    bpy.utils.unregister_class(MarkSeamOperator)
    bpy.utils.unregister_class(SmartUVProject)
    bpy.utils.unregister_class(TransformUVsOperator)