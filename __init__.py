# Reload submodules if not the initial load
if "bpy" in locals():
  current_package_prefix = __name__ + "."
  for name, module in sys.modules.copy().items():
      if name.startswith(current_package_prefix):
          print("Reloading: ", name)
          importlib.reload(module)

import bpy, re, json, os, shutil, sys, importlib
from bpy.props import *
from . operators import general, selection, generate, modify, materials, vertex_colors, cut, animation, snapping, files
from . common.common import *
from . import editor

addon_directory = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
library_directory = os.path.join(addon_directory, 'blend')

app = {
  "items": [],
  "keymaps": []
}

def get_user_preferences():
  return bpy.context.preferences.addons[__package__].preferences

def get_builtin_config_path():
  return os.path.join(addon_directory, 'configs', 'default.json')

def is_node_tool_operator(operator_id):
  try:
    module_name, operator_name = operator_id.split('.', 1)
    operator = getattr(getattr(bpy.ops, module_name), operator_name)
    properties = operator.get_rna_type().properties
    return properties.get('inputs') is not None and properties.get('panels') is not None
  except (AttributeError, KeyError, RuntimeError, ValueError):
    return False

def draw_menu(self, items):
  layout = self.layout

  if len(items) == 0:
    layout.label(text='No menu items loaded', icon='ERROR')
    return

  i = 0
  for item in items:
    if 'mode' in item and item['mode'] != bpy.context.mode:
      continue
    title = item['title']
    i += 1
    if i < 10 and not title.startswith('('):
      title = f'({i}) {title}'
    if 'children' in item:
      layout.menu(item['idname'], text=title)
    elif item['title'] == '[Separator]':
      layout.separator()
      i -= 1
    elif 'operator' in item:
      operator_id = item['operator']
      if is_node_tool_operator(operator_id):
        operator = layout.operator('qm.execute_node_tool', text=title)
        operator.operator_id = operator_id
        operator.params = json.dumps(item.get('params', {}))
        continue

      operator = layout.operator(operator_id, text=title)

      if not operator:
        layout.label(text='Operator not found: ' + operator_id, icon='ERROR')
        continue

      if 'params' in item:
        for key, val in item['params'].items():
          if isinstance(val, list):
            val = tuple(val)
          setattr(operator, key, val)

    elif 'menu' in item:
      layout.menu(item['menu'], text=title)

def register_menu_type(menu_definition):
  title = menu_definition['title']
  items = menu_definition['children']
  idname = menu_definition['idname']

  def draw(self, context):
    draw_menu(self, items)

  menu_type = type(idname + "Menu", (bpy.types.Menu,), {
    'bl_idname': idname,
    'bl_label': title,
    'draw': draw
  })

  bpy.utils.register_class(menu_type)

def build_menu_items(config_items):
  """Convert hierarchical config items to runtime menu items."""
  result = []
  for item in config_items:
    item_type = item.get('type', 'operator')
    if item_type == 'separator':
      result.append({'title': '[Separator]'})
    elif item_type == 'group':
      name = item.get('name', '')
      children = build_menu_items(item.get('children', []))
      idname = 'OBJECT_MT_Menu' + re.sub('[^A-Za-z0-9]+', '', name)
      menu_def = {
        'title': name,
        'children': children,
        'idname': idname,
      }
      register_menu_type(menu_def)
      result.append(menu_def)
    elif item_type == 'menu':
      entry = {'title': item.get('name', ''), 'menu': item.get('menu', '')}
      if item.get('mode') and item['mode'] != 'ANY':
        entry['mode'] = item['mode']
      result.append(entry)
    else:  # operator
      entry = {'title': item.get('name', ''), 'operator': item.get('operator', '')}
      if 'params' in item:
        entry['params'] = item['params']
      if item.get('mode') and item['mode'] != 'ANY':
        entry['mode'] = item['mode']
      result.append(entry)
  return result

def config_path_is_builtin(path):
  return path == get_builtin_config_path()

# Load the items from the active config and add them to the menu
def load_items():
  app['items'] = []

  prefs = get_user_preferences()
  idx = prefs.active_config_index
  if 0 <= idx < len(prefs.configs):
    config_path = prefs.configs[idx].path
    if not config_path_is_builtin(config_path) and os.path.exists(config_path):
      with open(config_path, 'r') as config:
        data = config.read()

      try:
        obj = json.loads(data)
      except:
        raise Exception('Decoding JSON has failed')

      if not 'items' in obj:
        raise Exception('No items in config')

      app['items'].extend(build_menu_items(obj['items']))
    elif not os.path.exists(config_path):
      print(f'[QuickMenu] Config file not found: {config_path}')

  editor.refresh_cached_items()

def register_asset_library():
  asset_libraries = bpy.context.preferences.filepaths.asset_libraries
  if asset_libraries.find("QuickMenuLibrary") == -1:
    library = asset_libraries.new(name="QuickMenuLibrary", directory=library_directory)
    library.import_method = "LINK"

def register_hotkey():
  keymaps = bpy.context.window_manager.keyconfigs.addon.keymaps
  keymap = keymaps.new(name='3D View', space_type='VIEW_3D')
  keymap_item = keymap.keymap_items.new('wm.call_menu', type='D', value='PRESS')
  keymap_item.properties.name = QuickMenu.bl_idname
  app['keymaps'].append((keymap, keymap_item))

def unregister_hotkey():
  for keymap, keymap_item in app['keymaps']:
    keymap.keymap_items.remove(keymap_item)
  app['keymaps'].clear()

@bpy.app.handlers.persistent
def _on_load_post(dummy):
  editor.refresh_cached_items()

class VoidEditModeOnlyOperator(bpy.types.Operator):
  """Edit Mode Only"""
  bl_idname = 'qm.void_edit_mode_only'
  bl_label = 'Edit Mode Only'

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    return {'FINISHED'}

class QuickMenuExecuteNodeToolOperator(bpy.types.Operator):
  """Execute a geometry node tool without triggering Blender's active-attribute crash"""
  bl_idname = 'qm.execute_node_tool'
  bl_label = 'Execute Node Tool'
  bl_options = {'INTERNAL'}

  operator_id: StringProperty(options={'HIDDEN', 'SKIP_SAVE'})
  params: StringProperty(default='{}', options={'HIDDEN', 'SKIP_SAVE'})

  def _run(self, context, call_context):
    active_attributes = []
    objects = getattr(context, 'objects_in_mode_unique_data', ())

    for obj in objects:
      mesh = getattr(obj, 'data', None)
      attributes = getattr(mesh, 'attributes', None)
      active = attributes.active if attributes else None
      if active:
        # Blender 5.2 crashes while rebuilding the edit mesh after a node tool
        # if the source mesh has an active attribute.
        active_attributes.append((mesh, active.name))
        attributes.active_index = -1

    try:
      module_name, operator_name = self.operator_id.split('.', 1)
      operator = getattr(getattr(bpy.ops, module_name), operator_name)
      params = json.loads(self.params) if self.params else {}
      return operator(call_context, **params)
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError) as error:
      self.report({'ERROR'}, f'Could not execute node tool: {error}')
      return {'CANCELLED'}
    finally:
      for mesh, attribute_name in active_attributes:
        if attribute_name in mesh.attributes:
          mesh.attributes.active = mesh.attributes[attribute_name]

  def invoke(self, context, event):
    return self._run(context, 'INVOKE_DEFAULT')

  def execute(self, context):
    return self._run(context, 'EXEC_DEFAULT')

def reset_configs():
  configs = get_user_preferences().configs
  configs.clear()

  default_path = get_builtin_config_path()
  user_path = os.path.join(os.path.dirname(default_path), 'user.json')
  if not os.path.exists(user_path):
    shutil.copy2(default_path, user_path)

  config = configs.add()
  config.path = user_path
  get_user_preferences().active_config_index = 0

  load_items()

class QuickMenu(bpy.types.Menu):
  bl_idname = 'OBJECT_MT_quick_menu'
  bl_label = 'Quick Menu'

  def draw(self, context):
    layout = self.layout

    # Draw a label that shows a warning if the current version is less than Blender 5.2.
    if bpy.app.version < (5, 2, 0):
      layout.label(text='You need Blender 5.2 or newer for the addon to work properly', icon='ERROR')
      layout.label(text=f'Current version: {bpy.app.version_string}')

    draw_menu(self, app['items'])

class QuickMenuConfig(bpy.types.PropertyGroup):
  path: StringProperty(default='')

class QuickMenuPreferences(bpy.types.AddonPreferences):
  bl_idname = __package__

  configs: CollectionProperty(
    name = 'Configs',
    type = QuickMenuConfig
  )

  active_config_index: IntProperty(
    name = 'Active Config Index'
  )

  def draw(self, context):
    layout = self.layout
    layout.label(text='Configs are managed in the Quick Menu N-panel (3D Viewport sidebar)', icon='INFO')
    box = layout.box()
    box.label(text='To change the menu hotkey, go to "Keymap" and search for "Quick Menu"', icon='INFO')

class QuickMenuProperties(bpy.types.PropertyGroup):
  # Used to track the current vertex color index. This is used to generate unique
  # vertex colors for id maps in apps like Substance Painter
  vertex_color_index: bpy.props.IntProperty(name='Vertex Color Index', default=3)
 
def register():
  bpy.utils.register_class(QuickMenuExecuteNodeToolOperator)
  bpy.utils.register_class(QuickMenu)
  bpy.utils.register_class(VoidEditModeOnlyOperator)
  bpy.utils.register_class(QuickMenuConfig)
  bpy.utils.register_class(QuickMenuPreferences)
  bpy.utils.register_class(QuickMenuProperties)

  editor.register()

  general.register()
  selection.register()
  generate.register()
  modify.register()
  materials.register()
  vertex_colors.register()
  cut.register()
  animation.register()
  snapping.register()
  files.register()

  bpy.types.Scene.quick_menu = bpy.props.PointerProperty(type=QuickMenuProperties)
  register_hotkey()
  register_asset_library()
  bpy.app.handlers.load_post.append(_on_load_post)

  editor.build_operator_list()

  # Create a user-editable copy of the default when no custom config exists.
  configs = get_user_preferences().configs
  valid_indices = [
    i
    for i, config in enumerate(configs)
    if not config_path_is_builtin(config.path) and os.path.exists(config.path)
  ]
  if not valid_indices:
    reset_configs()
  else:
    active_index = get_user_preferences().active_config_index
    editor.activate_config(
      active_index if active_index in valid_indices else valid_indices[0]
    )

def unregister():
  bpy.utils.unregister_class(QuickMenu)
  bpy.utils.unregister_class(QuickMenuExecuteNodeToolOperator)
  bpy.utils.unregister_class(VoidEditModeOnlyOperator)
  bpy.utils.unregister_class(QuickMenuConfig)
  bpy.utils.unregister_class(QuickMenuPreferences)
  bpy.utils.unregister_class(QuickMenuProperties)

  editor.unregister()

  general.unregister()
  selection.unregister()
  generate.unregister()
  modify.unregister()
  materials.unregister()
  vertex_colors.unregister()
  cut.unregister()
  animation.unregister()
  snapping.unregister()
  files.unregister()

  del bpy.types.Scene.quick_menu
  unregister_hotkey()
  if _on_load_post in bpy.app.handlers.load_post:
    bpy.app.handlers.load_post.remove(_on_load_post)
