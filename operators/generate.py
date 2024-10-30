import bpy
from .. common.common import *

class MirrorOperator(bpy.types.Operator):
  """Mirror"""
  bl_idname = 'qm.mirror'
  bl_label = 'Mirror'
  bl_options = {'REGISTER', 'UNDO'}

  axis: bpy.props.BoolVectorProperty(name='Axis', subtype='XYZ')

  bisect_flip: bpy.props.BoolVectorProperty(name='Bisect Flip', subtype='XYZ')

  @classmethod
  def poll(cls, context):
    return len(context.selected_objects) > 0

  def draw(self, context):
    l = self.layout
    l.row().prop(self.properties, 'axis', toggle=1)
    l.row().prop(self.properties, 'bisect_flip', toggle=1)

  def execute(self, context):
    if modifier_exists('MIRROR'):
      m = add_or_get_modifier('QMMirror', 'MIRROR')
      fn = lambda: bpy.ops.object.modifier_apply(modifier=m.name)
      execute_in_object_mode(fn)
      return {'FINISHED'}
    m = add_or_get_modifier('QMMirror', 'MIRROR', move_on_top=True)
    m.use_axis[0], m.show_on_cage = False, True
    vsv = view_snapped_vector(True)
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
  bl_idname = 'qm.array'
  bl_label = 'Array'
  bl_options = {'REGISTER', 'UNDO'}

  count: bpy.props.IntProperty(name='Count', default=3, step=1, min=0)

  offset: bpy.props.FloatProperty(name='Offset', default=1.1)

  @classmethod
  def poll(cls, context):
    return len(context.selected_objects) > 0

  def execute(self, context):
    v = view_snapped_vector() * self.offset
    v.negate()
    a = add_or_get_modifier('QMArray', 'ARRAY')
    a.count = self.count
    a.relative_offset_displace = v
    return {'FINISHED'}

def register():
    bpy.utils.register_class(MirrorOperator)
    bpy.utils.register_class(ArrayOperator)

def unregister():
    bpy.utils.unregister_class(MirrorOperator)
    bpy.utils.unregister_class(ArrayOperator)