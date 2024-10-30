import bpy
import re
from .. common.common import *

def move_object_to_collection(collection_name):
  obj = bpy.context.object
  collection = bpy.data.collections.get(collection_name)
  if collection is None:
    # Move to a new collection
    bpy.ops.object.move_to_collection(collection_index=0, is_new=True, new_collection_name=collection_name)
  else:
    # Move to an existing collection
    if obj.users_collection:
      obj_collection = obj.users_collection[0]
      obj_collection.objects.unlink(obj)
    collection.objects.link(obj)

class SetHint(bpy.types.Operator):
  """Set Objects hint to enabled or disabled"""
  bl_idname = 'qm.set_hint'
  bl_label = 'Set Objects hint to enabled or disabled'
  bl_options = {'REGISTER', 'UNDO'}

  hint_name: bpy.props.StringProperty(name='Name', default='-hint')

  enabled: bpy.props.BoolProperty(name='Enabled', default=True)

  @classmethod
  def poll(cls, context):
    return len(bpy.context.selected_objects) > 0

  def execute(self, context):
    for o in bpy.context.selected_objects:
      if self.enabled:
        if not self.hint_name in o.name:
          o.name += self.hint_name
      else:
        if self.hint_name in o.name:
          o.name = o.name.replace(self.hint_name, '')
    return {'FINISHED'}

class ToggleHint(bpy.types.Operator):
  """Toggle Objects hint"""
  bl_idname = 'qm.toggle_hint'
  bl_label = 'Toggle Objects hint'
  bl_options = {'REGISTER', 'UNDO'}

  hint_name: bpy.props.StringProperty(name='Name', default='-hint')

  @classmethod
  def poll(cls, context):
    return len(bpy.context.selected_objects) > 0

  def execute(self, context):
    for o in bpy.context.selected_objects:
      if self.hint_name in o.name:
        o.name = o.name.replace(self.hint_name, '')
      else:
        o.name += self.hint_name
    return {'FINISHED'}

class RemoveHints(bpy.types.Operator):
  """Remove hints"""
  bl_idname = 'qm.remove_hints'
  bl_label = 'Remove hints'
  bl_options = {'REGISTER', 'UNDO'}

  hints: bpy.props.StringProperty(name='Hints', default='')

  @classmethod
  def poll(cls, context):
    return len(bpy.context.selected_objects) > 0

  def execute(self, context):
    for o in bpy.context.selected_objects:
      for hint in re.split(r'\s*,\s*', self.hints):
        if hint in o.name:
          o.name = o.name.replace(hint, '')
    return {'FINISHED'}

def register():
  bpy.utils.register_class(SetHint)
  bpy.utils.register_class(ToggleHint)
  bpy.utils.register_class(RemoveHints)

def unregister():
  bpy.utils.unregister_class(SetHint)
  bpy.utils.unregister_class(ToggleHint)
  bpy.utils.unregister_class(RemoveHints)