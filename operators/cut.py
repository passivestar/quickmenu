import bpy
from .. common.common import *

class BooleanOperator(bpy.types.Operator):
  """Boolean"""
  bl_idname = 'qm.boolean'
  bl_label = 'Boolean'
  bl_options = {'REGISTER', 'UNDO'}

  operation: bpy.props.EnumProperty(name='Operation', items=(
    ('DIFFERENCE', 'Difference', 'Difference'),
    ('UNION', 'Union', 'Union'),
    ('INTERSECT', 'Intersect', 'Intersect')
  ))

  solver: bpy.props.EnumProperty(name='Solver', default='EXACT', items=(
    ('FLOAT', 'Float', 'Float'),
    ('EXACT', 'Exact', 'Exact'),
  ))

  boundary_extend: bpy.props.FloatProperty(name='Boundary Extend', default=0.0001, min=0)

  use_self: bpy.props.BoolProperty(name='Self', default=False)

  recalculate_normals: bpy.props.BoolProperty(name='Recalculate Normals', default=True)

  move_on_top: bpy.props.BoolProperty(name='Move Modifier On Top', default=True)

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
  bl_idname = 'qm.plane_intersect'
  bl_label = 'Plane Intersect'
  bl_options = {'REGISTER', 'UNDO'}

  mode: bpy.props.EnumProperty(name='Mode', default='ISLAND', items=(
    ('SELECTION', 'Selection', 'Selection'),
    ('ISLAND', 'Island', 'Island'),
    ('MESH', 'Whole Mesh', 'Whole Mesh')
  ))

  snap_view_axis: bpy.props.BoolProperty(name='Snap View Axis', default = True)

  active: bpy.props.BoolProperty(name='Active', default = True)

  clear_outer: bpy.props.BoolProperty(name='Clear Outer', default = False)

  clear_inner: bpy.props.BoolProperty(name='Clear Inner', default = False)

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    vector = view_snapped_vector(False, False) if self.snap_view_axis else view_vector(False, False)
    cursor_to_selected(self.active)
    if self.mode == 'ISLAND':
      bpy.ops.mesh.select_linked(delimit=set())
    elif self.mode == 'MESH':
      bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.bisect(plane_co=context.scene.cursor.location, plane_no=vector, clear_outer=self.clear_outer, clear_inner=self.clear_inner)
    return {'FINISHED'}

def register():
  bpy.utils.register_class(BooleanOperator)
  bpy.utils.register_class(PlaneIntersectOperator)

def unregister():
  bpy.utils.unregister_class(BooleanOperator)
  bpy.utils.unregister_class(PlaneIntersectOperator)