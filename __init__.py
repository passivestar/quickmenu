# Reload submodules if not the initial load
if "bpy" in locals():
  current_package_prefix = __name__ + "."
  for name, module in sys.modules.copy().items():
      if name.startswith(current_package_prefix):
          print("Reloading: ", name)
          importlib.reload(module)

import bpy, re, json, os, platform, subprocess, sys, importlib
from bpy.props import *
from bpy_extras.io_utils import ImportHelper
from . operators import general, selection, generate, modify, texturing, vertex_colors, cut, animation, snapping, files
from . common.common import *

addon_directory = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
library_directory = os.path.join(addon_directory, 'blend')
nodes_path = os.path.join(addon_directory, 'blend', 'nodetools.blend')
default_config_path = os.path.join(addon_directory, 'configs', 'default.json')

app = {
  "items": [],
  "keymaps": []
}

def get_user_preferences():
  return bpy.context.preferences.addons[__package__].preferences

def draw_menu(self, items):
  layout = self.layout

  if len(items) == 0:
    layout.label(text='No menu items loaded', icon='ERROR')
    layout.label(text='Add a config file in the addon preferences')
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

def check_json_syntax(path):
  if not os.path.exists(path):
    return False

  with open(path, 'r') as file:
    data = file.read()
    try:
      obj = json.loads(data)
    except ValueError as e:
      return False
    
    if not 'items' in obj:
      return False
  
  return True

# Load the items from the config and add them to the menu
def load_items():
  app['items'] = []

  for config in get_user_preferences().configs:
    if not config.enabled:
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

class VoidEditModeOnlyOperator(bpy.types.Operator):
  """Edit Mode Only"""
  bl_idname = 'qm.void_edit_mode_only'
  bl_label = 'Edit Mode Only'

  @classmethod
  def poll(cls, context):
    return is_in_editmode()

  def execute(self, context):
    return {'FINISHED'}

class QuickMenuAddConfigOperator(bpy.types.Operator, ImportHelper):
  """Add Config"""
  bl_idname = 'qm.add_config'
  bl_label = 'Add Config'
  bl_description = 'Add a new config file'

  def execute(self, context):
    path = self.properties.filepath

    if path == '':
      return {'CANCELLED'}
    
    if not os.path.exists(path):
      return {'CANCELLED'}
    
    if not path.endswith('.json') or not check_json_syntax(path):
      self.report({'ERROR'}, 'The file must be a valid JSON file!')
      return {'CANCELLED'}

    for config in get_user_preferences().configs:
      if config.path == path:
        self.report({'ERROR'}, 'The file already exists!')
        return {'CANCELLED'}

    get_user_preferences().configs.add().path = path
    load_items()
    return {'FINISHED'}

class QuickMenuRemoveConfigOperator(bpy.types.Operator):
  """Remove Config"""
  bl_idname = 'qm.remove_config'
  bl_label = 'Remove Config'
  bl_description = 'Remove the active config file'

  def execute(self, context):
    user_preferences = get_user_preferences()
    user_preferences.configs.remove(user_preferences.active_config_index)

    load_items()
    return {'FINISHED'}

class QuickMenuEditConfigOperator(bpy.types.Operator):
  """Edit Config"""
  bl_idname = 'qm.edit_config'
  bl_label = 'Edit Config'
  bl_description = 'Open the active config file in the default text editor'

  def execute(self, context):
    path = get_user_preferences().configs[get_user_preferences().active_config_index].path

    if platform.system() == 'Darwin': # macOS
      subprocess.call(('open', path))
    elif platform.system() == 'Windows': # Windows
      os.startfile(path)
    else: # Linux variants
      subprocess.call(('xdg-open', path))
    return {'FINISHED'}

class QuickMenuReloadMenuItemsOperator(bpy.types.Operator):
  """Reload Menu Items"""
  bl_idname = 'qm.reload_menu_items'
  bl_label = 'Reload Menu Items'
  bl_description = 'Reload the menu items from the config files'

  def execute(self, context):
    load_items()
    return {'FINISHED'}

class QuickMenuResetConfigsOperator(bpy.types.Operator):
  """Reset Configs"""
  bl_idname = 'qm.reset_configs'
  bl_label = 'Reset Configs'
  bl_description = 'Reset the config files to the default'

  def execute(self, context):
    configs = get_user_preferences().configs
    configs.clear()
    configs.add().path = default_config_path

    load_items()
    return {'FINISHED'}

class QuickMenu(bpy.types.Menu):
  bl_idname = 'OBJECT_MT_quick_menu'
  bl_label = 'Quick Menu'

  def draw(self, context):
    layout = self.layout

    # Draw a label that shows a warning if the current version is less than blender 4.3.0
    if bpy.app.version < (4, 3, 0):
      layout.label(text=f'You need Blender 4.3 or newer for the addon to work properly', icon='ERROR')
      layout.label(text=f'Current version: {bpy.app.version_string}')

    draw_menu(self, app['items'])

class QuickMenuConfig(bpy.types.PropertyGroup):
  enabled: BoolProperty(default=True, update=lambda self, context: load_items())
  path: StringProperty(default='')

class UI_UL_QuickMenuConfigList(bpy.types.UIList):
  def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
    row = layout.row()
    row.alignment = 'LEFT'

    if not os.path.exists(item.path):
      row.label(text='', icon='ERROR')
    else:
      row.prop(item, 'enabled', text='')

    basename = os.path.basename(item.path)
    row.label(text=basename)
    row.label(text='(Not found)') if not os.path.exists(item.path) else None
    row.label(text='(Default)') if item.path == default_config_path else None

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

    layout.label(text="Menu Configs:")

    row = layout.row(align=True)
    row.template_list("UI_UL_QuickMenuConfigList", "", self, "configs", self, "active_config_index")

    column = row.column(align=True)
    column.operator('qm.add_config', icon='ADD', text='')
    column.operator('qm.remove_config', icon='REMOVE', text='')
    column.operator('qm.edit_config', icon='GREASEPENCIL', text='')
    column.operator('qm.reload_menu_items', icon='FILE_REFRESH', text='')

    if len(self.configs) != 1 or len(self.configs) == 1 and self.configs[0].path != default_config_path:
        column.operator('qm.reset_configs', icon='LOOP_BACK', text='')

    # Display the path of the current config
    if len(self.configs) > 0:
      layout.label(text=self.configs[self.active_config_index].path)

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
  bpy.utils.register_class(UI_UL_QuickMenuConfigList)
  bpy.utils.register_class(QuickMenuAddConfigOperator)
  bpy.utils.register_class(QuickMenuRemoveConfigOperator)
  bpy.utils.register_class(QuickMenuEditConfigOperator)
  bpy.utils.register_class(QuickMenuReloadMenuItemsOperator)
  bpy.utils.register_class(QuickMenuResetConfigsOperator)
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

  # Add the default config if the list is empty
  configs = get_user_preferences().configs
  if len(configs) == 0:
    configs.add().path = default_config_path

  load_items()

def unregister():
  bpy.utils.unregister_class(QuickMenu)
  bpy.utils.unregister_class(VoidEditModeOnlyOperator)
  bpy.utils.unregister_class(QuickMenuConfig)
  bpy.utils.unregister_class(UI_UL_QuickMenuConfigList)
  bpy.utils.unregister_class(QuickMenuAddConfigOperator)
  bpy.utils.unregister_class(QuickMenuRemoveConfigOperator)
  bpy.utils.unregister_class(QuickMenuEditConfigOperator)
  bpy.utils.unregister_class(QuickMenuReloadMenuItemsOperator)
  bpy.utils.unregister_class(QuickMenuResetConfigsOperator)
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