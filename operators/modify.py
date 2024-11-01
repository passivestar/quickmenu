import bpy
from .. common.common import *

class ConvertToMeshOperator(bpy.types.Operator):
  """Convert To Mesh"""
  bl_idname = 'qm.convert_to_mesh'
  bl_label = 'Convert To Mesh'
  bl_options = {'REGISTER', 'UNDO'}

  close_strokes: bpy.props.BoolProperty(name='GPencil Close Strokes', default=True)

  dissolve_angle: bpy.props.FloatProperty(name='GPencil Dissolve Angle', subtype='ANGLE', step=5, default=0.261799, min=0, max=1.5708)

  doubles_threshold: bpy.props.FloatProperty(name='GPencil Doubles Threshold', default=0.02, min=0)

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
    execute_in_object_mode(fn)
    return {'FINISHED'}

class SubsurfOperator(bpy.types.Operator):
  """Subsurf"""
  bl_idname = 'qm.subsurf'
  bl_label = 'Subsurf'
  bl_options = {'REGISTER', 'UNDO'}

  level: bpy.props.IntProperty(name='Level', default=2, min=0, soft_max=5)

  def execute(self, context):
    if context.mode != 'SCULPT':
      m = add_or_get_modifier('QMSubsurf', 'SUBSURF')
      m.levels, m.boundary_smooth = self.level, 'PRESERVE_CORNERS'
    else:
      m = add_or_get_modifier('QMMultires', 'MULTIRES')
      bpy.ops.object.multires_subdivide(modifier=m.name, mode='CATMULL_CLARK')
      m.levels = min(m.sculpt_levels, self.level)
    return {'FINISHED'}

class BevelOperator(bpy.types.Operator):
  """Bevel"""
  bl_idname = 'qm.bevel'
  bl_label = 'Bevel'
  bl_options = {'REGISTER', 'UNDO'}

  amount: bpy.props.FloatProperty(name='Amount', default=0.1, step=0.1, min=0)

  segments: bpy.props.IntProperty(name='Segments', default=4, min=0, soft_max=12)

  angle: bpy.props.FloatProperty(name='Angle', subtype='ANGLE', default=0.785398, min=0, max=3.141593)

  use_weight: bpy.props.BoolProperty(name='Use Weight', default=False)

  harden_normals: bpy.props.BoolProperty(name='Harden Normals', default=True)

  loop_slide: bpy.props.BoolProperty(name='Loop Slide', default=False)

  use_clamp_overlap: bpy.props.BoolProperty(name='Clamp Overlap', default=True)

  def execute(self, context):
    existed = modifier_exists('BEVEL')
    b = add_or_get_modifier('QMBevel', 'BEVEL')
    if not existed: b.miter_outer = 'MITER_ARC'
    b.limit_method = 'WEIGHT' if self.use_weight else 'ANGLE'
    b.width, b.segments, b.angle_limit, b.harden_normals, b.loop_slide, b.use_clamp_overlap = self.amount, self.segments, self.angle, self.harden_normals, self.loop_slide, self.use_clamp_overlap
    return {'FINISHED'}

class TriangulateOperator(bpy.types.Operator):
  """Triangulate"""
  bl_idname = 'qm.triangulate'
  bl_label = 'Triangulate'
  bl_options = {'REGISTER', 'UNDO'}

  keep_normals: bpy.props.BoolProperty(name='Keep Normals', default=True)

  def execute(self, context):
    existed = modifier_exists('TRIANGULATE')
    t = add_or_get_modifier('QMTriangulate', 'TRIANGULATE')
    if not existed:
      t.keep_custom_normals = self.keep_normals
      t.min_vertices = 5
    return {'FINISHED'}

def register():
  bpy.utils.register_class(ConvertToMeshOperator)
  bpy.utils.register_class(SubsurfOperator)
  bpy.utils.register_class(BevelOperator)
  bpy.utils.register_class(TriangulateOperator)

def unregister():
  bpy.utils.unregister_class(ConvertToMeshOperator)
  bpy.utils.unregister_class(SubsurfOperator)
  bpy.utils.unregister_class(BevelOperator)
  bpy.utils.unregister_class(TriangulateOperator)