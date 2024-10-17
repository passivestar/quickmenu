# Reload submodules if not the initial load
if "bpy" in locals():
  current_package_prefix = __name__ + "."
  for name, module in sys.modules.copy().items():
      if name.startswith(current_package_prefix):
          print("Reloading: ", name)
          importlib.reload(module)

import bpy, re, json, os, platform, subprocess, sys, importlib
from .operators import general, selection, generate, modify, texturing, vertex_colors, cut, animation, snapping, files
from .common.common import *

addon_directory = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
nodes_path = os.path.join(addon_directory, 'nodetools.blend')
config_path = os.path.join(addon_directory, 'config.json')

app = {
  "items": [],
  "keymaps": []
}

class EditMenuItemsOperator(bpy.types.Operator):
  """Edit Menu Items"""
  bl_idname, bl_label = 'qm.edit_items', 'Edit Menu Items Operator'

  def execute(self, context):
    if platform.system() == 'Darwin': # macOS
      subprocess.call(('open', config_path))
    elif platform.system() == 'Windows': # Windows
      os.startfile(config_path)
    else: # linux variants
      subprocess.call(('xdg-open', config_path))
    return {'FINISHED'}

class ReloadMenuItemsOperator(bpy.types.Operator):
  """Reload Menu Items"""
  bl_idname, bl_label = 'qm.load_items', 'Reload Menu Items Operator'

  def execute(self, context):
    load_items(config_path)
    return {'FINISHED'}

class VoidEditModeOnlyOperator(bpy.types.Operator):
  """Edit Mode Only"""
  bl_idname, bl_label = 'qm.void_edit_mode_only', 'Edit Mode Only'

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    return {'FINISHED'}

class QuickMenu(bpy.types.Menu):
  bl_idname, bl_label = 'OBJECT_MT_quick_menu', 'Quick Menu'

  def draw(self, context):
    layout = self.layout

    # Draw a label that shows a warning if the current version is less than blender 4.3.0
    if bpy.app.version < (4, 3, 0):
      layout.label(text=f'You need Blender 4.3 or newer for the addon to work properly', icon='ERROR')
      layout.label(text=f'Current version: {bpy.app.version_string}')

    draw_menu(self, app['items'])

    layout.separator()
    layout.operator('qm.edit_items', text='Edit Menu')
    layout.operator('qm.load_items', text='Reload Menu')

class QuickMenuPreferences(bpy.types.AddonPreferences):
  bl_idname = __name__

  def draw(self, context):
    layout = self.layout
    layout.label(text='To change the hotkey, go to Keymap and search for "Quick Menu Operator"')

class QuickMenuProperties(bpy.types.PropertyGroup):
  # Used to track the current vertex color index. This is used to generate unique
  # vertex colors for id maps in apps like Substance Painter
  vertex_color_index: bpy.props.IntProperty(name='Vertex Color Index', default=3)

def draw_menu(self, items):
  layout = self.layout
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
    elif 'nodetool' in item:
      if is_in_editmode():
        operator = layout.operator('geometry.execute_node_group', text=title, icon='NODETREE')
        operator.name = item['nodetool']
        operator.asset_library_type = 'CUSTOM'
        operator.asset_library_identifier = 'QuickMenuLibrary'
        operator.relative_asset_identifier = 'nodetools.blend/NodeTree/' + item['nodetool']
      else:
        layout.operator('qm.void_edit_mode_only', text=title, icon='NODETREE')
    elif 'operator' in item:
      icon = 'NODETREE' if item['operator'] == 'geometry.execute_node_group' else 'NONE'
      if 'icon' in item: icon = item['icon']
      operator = layout.operator(item['operator'], text=title, icon=icon)
      if 'params' in item:
        for key, val in item['params'].items():
          operator[key] = tuple(val) if isinstance(val, list) else val

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

def get_or_create_menu_definition_at_path(path, items):
  for item in items:
    if item['title'] == path[0]:
      return item if len(path) == 1 else get_or_create_menu_definition_at_path(path[1:], item['children'])

  menu_definition = {
    'title': path[0],
    'children': [],
    'idname': 'OBJECT_MT_Menu' + re.sub('[^A-Za-z0-9]+', '', path[0])
  }

  register_menu_type(menu_definition)
  items.append(menu_definition)

  return menu_definition

# Load the items from the config and add them to the menu
def load_items(config_path):
  app['items'] = []

  with open(config_path, 'r') as config:
    data = config.read()
  
  try:
    obj = json.loads(data)
  except:
    raise Exception('Decoding JSON has failed')

  if not 'items' in obj:
    raise Exception('No items in config')
 
  for item in obj['items']:
    # Split by "/" and remove whitespace
    path = re.split('\s*\/\s*', item['path'])
    item['title'] = path[-1]
    if len(path) == 1:
      app['items'].append(item)
    else:
      menu = get_or_create_menu_definition_at_path(path[:-1], app['items'])
      menu['children'].append(item)

def register_asset_library():
  asset_libraries = bpy.context.preferences.filepaths.asset_libraries
  if asset_libraries.find("QuickMenuLibrary") == -1:
    library = asset_libraries.new(name="QuickMenuLibrary", directory=addon_directory)
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
 
def register():
  bpy.utils.register_class(QuickMenu)
  bpy.utils.register_class(EditMenuItemsOperator)
  bpy.utils.register_class(ReloadMenuItemsOperator)
  bpy.utils.register_class(VoidEditModeOnlyOperator)
  bpy.utils.register_class(QuickMenuPreferences)
  bpy.utils.register_class(QuickMenuProperties)

  general.register()
  selection.register()
  generate.register()
  modify.register()
  texturing.register()
  vertex_colors.register()
  cut.register()
  animation.register()
  snapping.register()
  files.register()

  bpy.types.Scene.quick_menu = bpy.props.PointerProperty(type=QuickMenuProperties)
  register_hotkey()
  register_asset_library() 
  load_items(config_path)


def unregister():
  bpy.utils.unregister_class(QuickMenu)
  bpy.utils.unregister_class(EditMenuItemsOperator)
  bpy.utils.unregister_class(ReloadMenuItemsOperator)
  bpy.utils.unregister_class(VoidEditModeOnlyOperator)
  bpy.utils.unregister_class(QuickMenuPreferences)
  bpy.utils.unregister_class(QuickMenuProperties)

  general.unregister()
  selection.unregister()
  generate.unregister()
  modify.unregister()
  texturing.unregister()
  vertex_colors.unregister()
  cut.unregister()
  animation.unregister()
  snapping.unregister()
  files.unregister()

  del bpy.types.Scene.quick_menu
  unregister_hotkey()