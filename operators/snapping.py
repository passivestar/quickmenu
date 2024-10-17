import bpy
from ..common.common import *

class TransformOrientationOperator(bpy.types.Operator):
  """Transform Orientation"""
  bl_idname, bl_label, bl_options = 'qm.transform_orientation', 'Transform Orientation', {'REGISTER', 'UNDO'}
  type: bpy.props.StringProperty(name='Type')

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
  type: bpy.props.StringProperty(name='Type')

  def execute(self, context):
    context.scene.tool_settings.transform_pivot_point = self.type
    return {'FINISHED'}

class SetSnapOperator(bpy.types.Operator):
  """Set Snap"""
  bl_idname, bl_label = 'qm.set_snap', 'Set Snap'
  mode: bpy.props.StringProperty(name='Mode')
  type: bpy.props.StringProperty(name='Type')

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

def register():
    bpy.utils.register_class(TransformOrientationOperator)
    bpy.utils.register_class(TransformPivotOperator)
    bpy.utils.register_class(SetSnapOperator)

def unregister():
    bpy.utils.unregister_class(TransformOrientationOperator)
    bpy.utils.unregister_class(TransformPivotOperator)
    bpy.utils.unregister_class(SetSnapOperator)