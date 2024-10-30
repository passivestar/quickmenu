import bpy
from mathutils import Vector, Matrix
from .. common.common import *

class ViewOperator(bpy.types.Operator):
  """View Selected if in edit mode or anything is selected in object mode. View Camera otherwise"""
  bl_idname = 'qm.view'
  bl_label = 'View'

  camera: bpy.props.BoolProperty(name='Camera', default=False)

  def execute(self, context):
    if is_in_editmode() or len(context.selected_objects) > 0:
      bpy.ops.view3d.view_selected()
    else:
      bpy.ops.view3d.view_camera()
    return {'FINISHED'}

class JoinSeparateOperator(bpy.types.Operator):
  """Join or Separate"""
  bl_idname = 'qm.join_separate'
  bl_label = 'Separate / Join'
  bl_options = {'REGISTER', 'UNDO'}

  reset_origin: bpy.props.BoolProperty(name='Reset Origin on Separate', default=True)

  reset_drivers: bpy.props.BoolProperty(name='Reset Drivers on Separate', default=True)

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
        if self.reset_origin:
          bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
        if self.reset_drivers:
          bpy.ops.qm.clear_drivers()
    elif len(context.selected_objects) > 0:
      bpy.ops.object.join()
    return {'FINISHED'}

class LocalViewOperator(bpy.types.Operator):
  """Local View"""
  bl_idname = 'qm.local_view'
  bl_label = 'Local View'
  bl_options = {'REGISTER', 'UNDO'}

  def execute(self, context):
    if is_in_editmode():
      if anything_is_hidden_in_editmode():
        bpy.ops.mesh.reveal(select=False)
      elif anything_is_selected_in_editmode():
        bpy.ops.mesh.hide(unselected=True)
    else: bpy.ops.view3d.localview()
    return {'FINISHED'}

class SetSmoothOperator(bpy.types.Operator):
  """Set Smooth Shading. Hold shift to use modifier"""
  bl_idname = 'qm.smooth'
  bl_label = 'Set Smooth'
  bl_options = {'REGISTER', 'UNDO'}

  smooth: bpy.props.BoolProperty(name='Smooth', default=True)

  auto: bpy.props.BoolProperty(name='Auto', default=True)

  auto_angle: bpy.props.FloatProperty(name='Angle', subtype='ANGLE', default=0.872665, step=2, min=0, max=1.5708)

  def invoke(self, context, event):
    if event.shift: self.auto = True
    return self.execute(context)

  def execute(self, context):
    if self.smooth:
      if self.auto:
        execute_in_object_mode(lambda: bpy.ops.object.shade_auto_smooth(angle=self.auto_angle))
      else:
        execute_in_object_mode(bpy.ops.object.shade_smooth)
    else:
      execute_in_object_mode(bpy.ops.object.shade_flat)
    return {'FINISHED'}

class SetOriginOperator(bpy.types.Operator):
  """Set origin to geometry center or selection. Hold shift to set origin to bottom"""

  bl_idname = 'qm.set_origin'
  bl_label = 'Set Origin'
  bl_options = {'REGISTER', 'UNDO'}

  type: bpy.props.EnumProperty(name='Type', items=(
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
    execute_in_object_mode(fn)
    return {'FINISHED'}

class ProportionalEditingOperator(bpy.types.Operator):
  """Toggle Proportional Editing"""
  bl_idname = 'qm.proportional_editing'
  bl_label = 'Proportional Editing'
  bl_options = {'REGISTER', 'UNDO'}

  falloff: bpy.props.EnumProperty(name='Type', default='SMOOTH', items=(
    ('SMOOTH', 'Smooth', 'Smooth falloff'),
    ('SPHERE', 'Sphere', 'Sphere falloff'),
    ('ROOT', 'Root', 'Root falloff'),
    ('INVERSE_SQUARE', 'Inverse Square', 'Inverse Square falloff'),
    ('SHARP', 'Sharp', 'Sharp falloff'),
    ('LINEAR', 'Linear', 'Linear falloff'),
    ('CONSTANT', 'Constant', 'Constant falloff'),
    ('RANDOM', 'Random', 'Random falloff'),
  ))

  connected: bpy.props.BoolProperty(name='Connected', default = True)

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
  bl_idname = 'qm.wireframe'
  bl_label = 'Wireframe'
  bl_options = {'REGISTER', 'UNDO'}

  opacity: bpy.props.FloatProperty(name='Opacity', default=0.75, min=0, max=1)

  def execute(self, context):
    ol = context.space_data.overlay
    if not self.options.is_repeat:
      ol.show_wireframes = not ol.show_wireframes
      self.report({'INFO'}, 'Wireframe: ' + ('On' if ol.show_wireframes else 'Off'))
    context.space_data.overlay.wireframe_opacity = self.opacity
    return {'FINISHED'}

class CorrectAttributesOperator(bpy.types.Operator):
  """Toggle Correct Face Attributes"""
  bl_idname = 'qm.correct_attributes'
  bl_label = 'Toggle Correct Face Attributes'
  bl_options = {'REGISTER', 'UNDO'}

  def execute(self, context):
    ts = bpy.context.scene.tool_settings
    ts.use_transform_correct_face_attributes = not ts.use_transform_correct_face_attributes
    self.report({'INFO'}, 'Correct Face Attributes: ' + ('On' if ts.use_transform_correct_face_attributes else 'Off'))
    return {'FINISHED'}

def register():
    bpy.utils.register_class(ViewOperator)
    bpy.utils.register_class(JoinSeparateOperator)
    bpy.utils.register_class(LocalViewOperator)
    bpy.utils.register_class(SetSmoothOperator)
    bpy.utils.register_class(SetOriginOperator)
    bpy.utils.register_class(ProportionalEditingOperator)
    bpy.utils.register_class(WireframeOperator)
    bpy.utils.register_class(CorrectAttributesOperator)

def unregister():
    bpy.utils.unregister_class(ViewOperator)
    bpy.utils.unregister_class(JoinSeparateOperator)
    bpy.utils.unregister_class(LocalViewOperator)
    bpy.utils.unregister_class(SetSmoothOperator)
    bpy.utils.unregister_class(SetOriginOperator)
    bpy.utils.unregister_class(ProportionalEditingOperator)
    bpy.utils.unregister_class(WireframeOperator)
    bpy.utils.unregister_class(CorrectAttributesOperator)