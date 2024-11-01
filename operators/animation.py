import bpy
from .. common.common import *

class ParentToNewEmptyOperator(bpy.types.Operator):
  """Parent To New Empty"""
  bl_idname = 'qm.parent_to_new_empty'
  bl_label = 'Parent To New Empty'
  bl_options = {'REGISTER', 'UNDO'}
  reset_transforms: bpy.props.BoolProperty(name='Reset Transforms', default=True)

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
  bl_idname = 'qm.add_bone'
  bl_label = 'Add Bone'
  bl_options = {'REGISTER', 'UNDO'}

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

class AddBodyOperator(bpy.types.Operator):
  """Add Physics Body"""
  bl_idname = 'qm.add_body'
  bl_label = 'Add Body'
  bl_options = {'REGISTER', 'UNDO'}

  type: bpy.props.EnumProperty(
    name = 'Type',
    items = (
      ('ACTIVE', 'Active', 'Active'),
      ('PASSIVE', 'Passive', 'Passive'),
    ),
    default = 'ACTIVE'
  )

  mass: bpy.props.FloatProperty(name='Mass', default=1, min=0)
  friction: bpy.props.FloatProperty(name='Friction', default=0.5, min=0, max=1)
  bounciness: bpy.props.FloatProperty(name='Bounciness', default=0, min=0, max=1)

  @classmethod
  def poll(cls, context):
    return len(context.selected_objects) > 0

  def execute(self, context):
    all_selected_objects = context.selected_objects

    for obj in all_selected_objects:
      if obj.type == 'MESH':
        select(obj)
        bpy.ops.rigidbody.object_add()
        bpy.context.object.rigid_body.type = self.type
        bpy.context.object.rigid_body.friction = self.friction
        bpy.context.object.rigid_body.restitution = self.bounciness

        if self.type == 'ACTIVE':
          bpy.context.object.rigid_body.mass = self.mass
 
    for obj in all_selected_objects:
      obj.select_set(True)
    return {'FINISHED'}

class RemoveBodyOperator(bpy.types.Operator):
  """Remove Physics Body"""
  bl_idname = 'qm.remove_body'
  bl_label = 'Remove Body'
  bl_options = {'REGISTER', 'UNDO'}

  apply_transforms: bpy.props.BoolProperty(name='Apply Transforms', default=True)

  @classmethod
  def poll(cls, context):
    return len(context.selected_objects) > 0

  def execute(self, context):
    all_selected_objects = context.selected_objects

    if self.apply_transforms:
      bpy.ops.object.visual_transform_apply()

    for obj in all_selected_objects:
      if obj.type == 'MESH' and obj.rigid_body:
        select(obj)
        bpy.ops.rigidbody.object_remove()

    for obj in all_selected_objects:
      obj.select_set(True)

    return {'FINISHED'}

class AddCollisionOperator(bpy.types.Operator):
  """Add Collision"""
  bl_idname = 'qm.add_collision'
  bl_label = 'Add Collision'
  bl_options = {'REGISTER', 'UNDO'}

  thickness_outer: bpy.props.FloatProperty(name='Thickness Outer', default=0.01, min=0, max=1)
  cloth_friction: bpy.props.FloatProperty(name='Cloth Friction', default=5, min=0, max=80)

  def execute(self, context):
    all_selected_objects = context.selected_objects

    for obj in all_selected_objects:
      select(obj)
      add_or_get_modifier('QMCollision', 'COLLISION')
      context.object.collision.thickness_outer = self.thickness_outer
      context.object.collision.cloth_friction = self.cloth_friction
    
    for obj in all_selected_objects:
      obj.select_set(True)
    return {'FINISHED'}

class AddClothOperator(bpy.types.Operator):
  """Add Cloth"""
  bl_idname = 'qm.add_cloth'
  bl_label = 'Add Cloth'
  bl_options = {'REGISTER', 'UNDO'}

  pressure: bpy.props.FloatProperty(name='Pressure', default=0, min=-20, max=20)

  tension: bpy.props.FloatProperty(name='Tension', default=5, min=0, max=30)

  compression: bpy.props.FloatProperty(name='Compression', default=5, min=0, max=30)

  shear: bpy.props.FloatProperty(name='Shear', default=5, min=0, max=30)

  bending: bpy.props.FloatProperty(name='Bending', default=0.1, min=0, max=30)

  self_collisions: bpy.props.BoolProperty(name='Self Collisions', default=False)

  def execute(self, context):
    all_selected_objects = context.selected_objects

    for obj in all_selected_objects:
      select(obj)
      c = add_or_get_modifier('QMCloth', 'CLOTH')
      c.settings.use_pressure = self.pressure != 0
      c.settings.uniform_pressure_force = self.pressure
      c.settings.tension_stiffness = self.tension
      c.settings.compression_stiffness = self.compression
      c.settings.shear_stiffness = self.shear
      c.settings.bending_stiffness = self.bending
      c.collision_settings.use_self_collision = self.self_collisions
    
    for obj in all_selected_objects:
      obj.select_set(True)

    context.scene.frame_set(0)
    return {'FINISHED'}

class AnimateRotationOperator(bpy.types.Operator):
  """Animate Rotation"""
  bl_idname = 'qm.animate_rotation'
  bl_label = 'Animate Rotation'
  bl_options = {'REGISTER', 'UNDO'}

  cycles_x: bpy.props.IntProperty(name='Cycles X', default=0)

  cycles_y: bpy.props.IntProperty(name='Cycles Y', default=0)

  cycles_z: bpy.props.IntProperty(name='Cycles Z', default=1)

  def execute(self, context):
    end_frame = context.scene.frame_end

    for obj in context.selected_objects:
      for i, cycles in enumerate([self.cycles_x, self.cycles_y, self.cycles_z]):
        if cycles > 0:
          curve = obj.driver_add('rotation_euler', i)
          curve.driver.expression = f'frame / {end_frame} * tau * {cycles}'

    return {'FINISHED'}

class RewindOperator(bpy.types.Operator):
  """Rewind"""
  bl_idname = 'qm.rewind'
  bl_label = 'Rewind'
  bl_options = {'REGISTER', 'UNDO'}

  def execute(self, context):
    context.scene.frame_set(0)
    return {'FINISHED'}

class ToggleAutoKeyingOperator(bpy.types.Operator):
  """Toggle Auto Keying"""
  bl_idname = 'qm.toggle_auto_keying'
  bl_label = 'Toggle Auto Keying'
  bl_options = {'REGISTER', 'UNDO'}

  def execute(self, context):
    context.scene.tool_settings.use_keyframe_insert_auto = not context.scene.tool_settings.use_keyframe_insert_auto
    self.report({'INFO'}, 'Auto Keying: ' + ('On' if context.scene.tool_settings.use_keyframe_insert_auto else 'Off'))
    return {'FINISHED'}

class ClearDriversOperator(bpy.types.Operator):
  """Clear Drivers"""
  bl_idname = 'qm.clear_drivers'
  bl_label = 'Clear Drivers'
  bl_options = {'REGISTER', 'UNDO'}

  def execute(self, context):
    for obj in context.selected_objects:
      animation_data = obj.animation_data
      if animation_data:
        for dr in obj.animation_data.drivers:
          obj.driver_remove(dr.data_path, -1)
    return {'FINISHED'}

class SetUseSelfDriversOperator(bpy.types.Operator):
  """Set Use Self Drivers"""
  bl_idname = 'qm.set_use_self_drivers'
  bl_label = 'Set Use Self Drivers'
  bl_options = {'REGISTER', 'UNDO'}

  def execute(self, context):
    for obj in context.selected_objects:
      animation_data = obj.animation_data
      if animation_data:
        for dr in obj.animation_data.drivers:
          dr.driver.use_self = True
          # Reevaluate expression with use self enabled:
          dr.driver.expression = dr.driver.expression
    return {'FINISHED'}

def register():
  bpy.utils.register_class(ParentToNewEmptyOperator)
  bpy.utils.register_class(AddBoneOperator)
  bpy.utils.register_class(AddBodyOperator)
  bpy.utils.register_class(RemoveBodyOperator)
  bpy.utils.register_class(AddCollisionOperator)
  bpy.utils.register_class(AddClothOperator)
  bpy.utils.register_class(AnimateRotationOperator)
  bpy.utils.register_class(RewindOperator)
  bpy.utils.register_class(ToggleAutoKeyingOperator)
  bpy.utils.register_class(ClearDriversOperator)
  bpy.utils.register_class(SetUseSelfDriversOperator)

def unregister():
  bpy.utils.unregister_class(ParentToNewEmptyOperator)
  bpy.utils.unregister_class(AddBoneOperator)
  bpy.utils.unregister_class(AddBodyOperator)
  bpy.utils.unregister_class(RemoveBodyOperator)
  bpy.utils.unregister_class(AddCollisionOperator)
  bpy.utils.unregister_class(AddClothOperator)
  bpy.utils.unregister_class(AnimateRotationOperator)
  bpy.utils.unregister_class(RewindOperator)
  bpy.utils.unregister_class(ToggleAutoKeyingOperator)
  bpy.utils.unregister_class(ClearDriversOperator)
  bpy.utils.unregister_class(SetUseSelfDriversOperator)