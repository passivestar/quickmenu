import bpy
from mathutils import Color

from .. common.common import *

colors = [
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
]

class SetVertexColorOperator(bpy.types.Operator):
  """Set Vertex Color"""
  bl_idname = 'qm.set_vertex_color'
  bl_label = 'Set Vertex Color'
  bl_options = {'REGISTER', 'UNDO'}

  color: bpy.props.FloatVectorProperty(name='Color', subtype='COLOR', min=0, max=1)

  set_to_active: bpy.props.BoolProperty(name='Set To Active', default = False)

  reset_index: bpy.props.BoolProperty(name='Reset Index', default = False)

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
      if i < len(colors):
        values = tuple([c / 255 for c in colors[i]])
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
      selection_indeces, active_indeces = execute_in_edit_mode(get_selection_and_active_indices)
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
      execute_in_object_mode(assign_colors)
    return {'FINISHED'}

class SelectByVertexColorOperator(bpy.types.Operator):
  """Select By Vertex Color"""
  bl_idname = 'qm.select_by_vertex_color'
  bl_label = 'Select By Vertex Color'
  bl_options = {'REGISTER', 'UNDO'}

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    context.space_data.shading.color_type = 'VERTEX'
    selected_colors = []
    # Gather all of the selected colors across all of the objects first
    for obj in context.objects_in_mode:
      context.view_layer.objects.active = obj
      selection_indeces, _ = execute_in_edit_mode(get_selection_and_active_indices)
      def fn():
        for index in selection_indeces:
          selected_colors.append(obj.data.vertex_colors.active.data[index].color)
      execute_in_object_mode(fn)
    # Set selection
    for obj in context.objects_in_mode:
      mesh = obj.data
      context.view_layer.objects.active = obj
      selection_indeces, _ = execute_in_edit_mode(get_selection_and_active_indices)
      def fn():
        for poly in mesh.polygons:
          poly.select = False
          for index in poly.loop_indices:
            c = mesh.vertex_colors.active.data[index].color
            for sc in selected_colors:
              if c[0] == sc[0] and c[1] == sc[1] and c[2] == sc[2]:
                poly.select = True
                continue
      execute_in_object_mode(fn)
    return {'FINISHED'}

def register():
    bpy.utils.register_class(SetVertexColorOperator)
    bpy.utils.register_class(SelectByVertexColorOperator)

def unregister():
    bpy.utils.unregister_class(SetVertexColorOperator)
    bpy.utils.unregister_class(SelectByVertexColorOperator)