import bpy
from .. common.common import *

class SelectRingOperator(bpy.types.Operator):
  """Select ring. Hold shift to select loop"""
  bl_idname = 'qm.select_ring'
  bl_label = 'Select Ring Or Loop'
  bl_options = {'REGISTER', 'UNDO'}

  select_loop: bpy.props.BoolProperty(name='Select Loop', default=False)

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
  bl_idname = 'qm.select_more'
  bl_label = 'Select More Or Less'
  bl_options = {'REGISTER', 'UNDO'}

  select_less: bpy.props.BoolProperty(name='Select Less', default=False)

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
  bl_idname = 'qm.region_to_loop'
  bl_label = 'Region To Loop'
  bl_options = {'REGISTER', 'UNDO'}

  select_bigger: bpy.props.BoolProperty(name='Loop To Region Bigger', default = False)

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

def register():
    bpy.utils.register_class(SelectRingOperator)
    bpy.utils.register_class(SelectMoreOperator)
    bpy.utils.register_class(RegionToLoopOperator)

def unregister():
    bpy.utils.unregister_class(SelectRingOperator)
    bpy.utils.unregister_class(SelectMoreOperator)
    bpy.utils.unregister_class(RegionToLoopOperator)