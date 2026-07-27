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

def get_builtin_config_paths():
  return [
    (os.path.join(addon_directory, 'configs', 'default.json'), True),
  ]

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
      operator = layout.operator(item['operator'], text=title)

      if not operator:
        layout.label(text='Operator not found: ' + item['operator'], icon='ERROR')
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
  return path in [path[0] for path in get_builtin_config_paths()]

# Load the items from the config and add them to the menu
def load_items():
  app['items'] = []

  for config in get_user_preferences().configs:
    if not config.enabled:
      continue

    if config_path_is_builtin(config.path):
      continue

    if not os.path.exists(config.path):
      print(f'[QuickMenu] Config file not found: {config.path}')
      continue

    with open(config.path, 'r') as config:
      data = config.read()
    
    try:
      obj = json.loads(data)
    except:
      raise Exception('Decoding JSON has failed')

    if not 'items' in obj:
      raise Exception('No items in config')
  
    app['items'].extend(build_menu_items(obj['items']))

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

def reset_configs():
  configs = get_user_preferences().configs
  configs.clear()

  default_path = get_builtin_config_paths()[0][0]
  user_path = os.path.join(os.path.dirname(default_path), 'user.json')
  if not os.path.exists(user_path):
    shutil.copy2(default_path, user_path)

  config = configs.add()
  config.path = user_path
  config.enabled = True
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
  enabled: BoolProperty(default=True, update=lambda self, context: load_items())
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
  if not any(
    not config_path_is_builtin(config.path) and os.path.exists(config.path)
    for config in configs
  ):
    reset_configs()
  else:
    load_items()

def unregister():
  bpy.utils.unregister_class(QuickMenu)
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
