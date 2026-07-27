import bpy, re, json, os, platform, subprocess, shutil
from bpy.props import *

_expanded_groups = set()
_suppress_edit_save = False
_suppress_param_update = False


def _get_scene_from_context(context=None):
    if context is not None:
        scene = getattr(context, "scene", None)
        if scene is not None:
            return scene

    scene = getattr(bpy.context, "scene", None)
    if scene is not None:
        return scene

    scenes = getattr(bpy.data, "scenes", None)
    if scenes and len(scenes) > 0:
        return scenes[0]

    return None


MODE_ITEMS = [
    ("ANY", "Any", "Show in all modes"),
    ("OBJECT", "Object", "Object mode"),
    ("EDIT_MESH", "Edit Mesh", "Mesh edit mode"),
    ("EDIT_CURVE", "Edit Curve", "Curve edit mode"),
    ("EDIT_SURFACE", "Edit Surface", "Surface edit mode"),
    ("EDIT_METABALL", "Edit Metaball", "Metaball edit mode"),
    ("EDIT_TEXT", "Edit Text", "Text edit mode"),
    ("EDIT_ARMATURE", "Edit Armature", "Armature edit mode"),
    ("EDIT_LATTICE", "Edit Lattice", "Lattice edit mode"),
    ("EDIT_GREASE_PENCIL", "Edit Grease Pencil", "Grease Pencil edit mode"),
    ("SCULPT", "Sculpt", "Sculpt mode"),
    ("PAINT_VERTEX", "Vertex Paint", "Vertex paint mode"),
    ("PAINT_WEIGHT", "Weight Paint", "Weight paint mode"),
    ("PAINT_TEXTURE", "Texture Paint", "Texture paint mode"),
    ("PAINT_GPENCIL", "GP Paint", "Grease Pencil paint mode"),
    ("POSE", "Pose", "Pose mode"),
    ("PARTICLE", "Particle Edit", "Particle edit mode"),
]


class QuickMenuOperatorEntry(bpy.types.PropertyGroup):
    pass


def _param_enum_items_cb(self, context):
    try:
        items = json.loads(self.enum_items_json)
        if items:
            return [(str(i), str(i), "") for i in items]
    except:
        pass
    return [("NONE", "None", "")]


def _on_param_changed(self, context):
    """Auto-save when an inline-edit param entry changes."""
    if _suppress_edit_save:
        return
    scene = _get_scene_from_context(context)
    if scene is None:
        return
    my_ptr = self.as_pointer()
    for p in scene.qm_edit_params:
        if p.as_pointer() == my_ptr:
            _save_current_edit(context)
            return


class QuickMenuParamEntry(bpy.types.PropertyGroup):
    prop_type: StringProperty(default="STRING")
    str_value: StringProperty(name="Value", default="", update=_on_param_changed)
    int_value: IntProperty(name="Value", update=_on_param_changed)
    float_value: FloatProperty(name="Value", update=_on_param_changed)
    bool_value: BoolProperty(name="Value", update=_on_param_changed)
    enum_items_json: StringProperty(default="")
    enum_value: EnumProperty(
        name="Value", items=_param_enum_items_cb, update=_on_param_changed
    )
    is_set: BoolProperty(name="", default=False, update=_on_param_changed)


def _get_op_rna(op_id):
    """Get RNA type for an operator idname, or None."""
    if not op_id or "." not in op_id:
        return None
    mod_name, op_name = op_id.split(".", 1)
    mod = getattr(bpy.ops, mod_name, None)
    op = getattr(mod, op_name, None) if mod else None
    if not op:
        return None
    try:
        return op.get_rna_type()
    except:
        return None


def _set_entry_value(entry, val):
    """Set a param entry's typed value field from a Python value."""
    if entry.prop_type == "BOOLEAN":
        entry.bool_value = bool(val)
    elif entry.prop_type == "INT":
        entry.int_value = int(val)
    elif entry.prop_type == "FLOAT":
        entry.float_value = float(val)
    elif entry.prop_type == "ENUM":
        try:
            entry.enum_value = str(val)
        except:
            entry.str_value = str(val)
            entry.prop_type = "STRING"
    else:
        entry.str_value = (
            json.dumps(val) if isinstance(val, (list, tuple)) else str(val)
        )


def _get_param_value(param):
    """Read a param entry's value based on its type."""
    if param.prop_type == "BOOLEAN":
        return param.bool_value
    if param.prop_type == "INT":
        return param.int_value
    if param.prop_type == "FLOAT":
        return param.float_value
    if param.prop_type == "ENUM":
        return param.enum_value
    try:
        return json.loads(param.str_value)
    except:
        return param.str_value


def _populate_params(collection, op_id, existing_params=None):
    """Populate a params CollectionProperty from operator RNA properties."""
    global _suppress_edit_save
    was_suppressed = _suppress_edit_save
    _suppress_edit_save = True
    try:
        collection.clear()
        rna = _get_op_rna(op_id.strip() if op_id else "")
        if not rna:
            return
        if existing_params is None:
            existing_params = {}
        seen = set()

        for prop in rna.properties:
            if prop.identifier == "rna_type" or prop.is_hidden or prop.is_readonly:
                continue
            entry = collection.add()
            entry.name = prop.identifier
            seen.add(prop.identifier)

            is_array = getattr(prop, "is_array", False)
            if is_array:
                entry.prop_type = "STRING"
                entry.str_value = json.dumps(list(getattr(prop, "default_array", [])))
            elif prop.type == "BOOLEAN":
                entry.prop_type = "BOOLEAN"
                entry.bool_value = prop.default
            elif prop.type == "INT":
                entry.prop_type = "INT"
                entry.int_value = prop.default
            elif prop.type == "FLOAT":
                entry.prop_type = "FLOAT"
                entry.float_value = prop.default
            elif prop.type == "STRING":
                entry.prop_type = "STRING"
                entry.str_value = prop.default or ""
            elif prop.type == "ENUM":
                entry.prop_type = "ENUM"
                entry.enum_items_json = json.dumps(
                    [item.identifier for item in prop.enum_items]
                )
                try:
                    entry.enum_value = prop.default
                except:
                    pass
            else:
                entry.prop_type = "STRING"

            if prop.identifier in existing_params:
                entry.is_set = True
                _set_entry_value(entry, existing_params[prop.identifier])

        # Extra params from config that aren't in RNA
        for key, val in existing_params.items():
            if key in seen:
                continue
            entry = collection.add()
            entry.name = key
            entry.is_set = True
            if isinstance(val, bool):
                entry.prop_type = "BOOLEAN"
            elif isinstance(val, int):
                entry.prop_type = "INT"
            elif isinstance(val, float):
                entry.prop_type = "FLOAT"
            else:
                entry.prop_type = "STRING"
            _set_entry_value(entry, val)
    finally:
        _suppress_edit_save = was_suppressed


def _collect_params(collection):
    """Collect set params into a dict."""
    return {p.name: _get_param_value(p) for p in collection if p.is_set}


_PARAM_FIELD = {
    "BOOLEAN": "bool_value",
    "INT": "int_value",
    "FLOAT": "float_value",
    "ENUM": "enum_value",
}

_FORM_SPACING = 0.5


def _draw_params(collection, layout):
    if not collection:
        return
    box = layout.box()
    column = box.column(align=True)
    column.label(text="Parameters:")
    column.separator(factor=_FORM_SPACING)
    for index, param in enumerate(collection):
        if index:
            column.separator(factor=_FORM_SPACING)
        row = column.row(align=True)
        row.prop(param, "is_set", text="")
        sub = row.row(align=True)
        sub.active = param.is_set
        sub.prop(param, _PARAM_FIELD.get(param.prop_type, "str_value"), text=param.name)


def _on_operator_id_changed(self, context):
    """Update callback for the Add operator's operator_id field."""
    if _suppress_param_update:
        return
    _populate_params(self.params_list, self.operator_id)
    if not self.name.strip():
        rna = _get_op_rna(self.operator_id.strip())
        if rna and rna.name:
            self.name = rna.name


def build_operator_list():
    """Populate WindowManager.qm_operator_list with all registered operators."""
    col = bpy.context.window_manager.qm_operator_list
    col.clear()
    for mod_name in dir(bpy.ops):
        mod = getattr(bpy.ops, mod_name, None)
        if mod is None:
            continue
        for op_name in dir(mod):
            col.add().name = f"{mod_name}.{op_name}"


# --- Address / config helpers ---


def _parse_address(addr_str):
    return [int(x) for x in addr_str.split(",")]


def _get_item_by_address(items, address):
    node = items[address[0]]
    for idx in address[1:]:
        node = node["children"][idx]
    return node


def _get_parent_and_index(items, address):
    if len(address) == 1:
        return items, address[0]
    parent = _get_item_by_address(items, address[:-1])
    return parent["children"], address[-1]


def _load_config(config_path):
    with open(config_path, "r") as f:
        return json.load(f)


def _save_config(config_path, data):
    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)


def get_user_preferences():
    return bpy.context.preferences.addons[__package__].preferences


def get_configs_directory():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs")


def is_builtin_config(path):
    return os.path.normpath(path) == os.path.normpath(
        os.path.join(get_configs_directory(), "default.json")
    )


def get_active_user_config_path():
    prefs = get_user_preferences()
    if not prefs.configs:
        return None
    idx = prefs.active_config_index
    if 0 <= idx < len(prefs.configs):
        path = prefs.configs[idx].path
        if not is_builtin_config(path) and os.path.exists(path):
            return path
    return None


def activate_config(index):
    """Select and load one user config."""
    prefs = get_user_preferences()
    if not 0 <= index < len(prefs.configs):
        return False

    active_config = prefs.configs[index]
    if is_builtin_config(active_config.path) or not os.path.exists(active_config.path):
        return False

    prefs.active_config_index = index
    load_items()
    return True


# --- Inline editing ---


def _load_selection_into_edit(context):
    """Populate inline-edit Scene properties from the currently selected item."""
    global _suppress_edit_save
    was_suppressed = _suppress_edit_save
    _suppress_edit_save = True
    try:
        scene = _get_scene_from_context(context)
        if scene is None:
            return
        idx = scene.qm_item_list_index
        scene.qm_edit_name = ""
        scene.qm_edit_operator = ""
        scene.qm_edit_mode = "ANY"
        scene.qm_edit_menu = ""
        scene.qm_edit_params.clear()

        if idx < 0 or idx >= len(scene.qm_item_list):
            return

        entry = scene.qm_item_list[idx]
        if entry.is_separator:
            return

        scene.qm_edit_name = entry.item_name
        if not entry.is_group:
            valid_modes = {m[0] for m in MODE_ITEMS}
            scene.qm_edit_mode = entry.mode if entry.mode in valid_modes else "ANY"
            if entry.is_menu:
                scene.qm_edit_menu = entry.menu
            else:
                scene.qm_edit_operator = entry.operator
                if entry.operator:
                    existing = json.loads(entry.params) if entry.params else {}
                    _populate_params(scene.qm_edit_params, entry.operator, existing)
    finally:
        _suppress_edit_save = was_suppressed


def _save_current_edit(context):
    """Save inline-edit fields back to the JSON config file."""
    global _suppress_edit_save
    scene = _get_scene_from_context(context)
    if scene is None:
        return
    idx = scene.qm_item_list_index
    if idx < 0 or idx >= len(scene.qm_item_list):
        return
    entry = scene.qm_item_list[idx]
    if (
        not entry.config_path
        or not entry.address
        or is_builtin_config(entry.config_path)
    ):
        return
    if entry.is_separator:
        return

    data = _load_config(entry.config_path)
    address = _parse_address(entry.address)
    item = _get_item_by_address(data["items"], address)

    if entry.is_group:
        new_name = scene.qm_edit_name.strip()
        old_name = item.get("name", "")
        item["name"] = new_name
        _save_config(entry.config_path, data)
        if new_name != old_name:
            # Update _expanded_groups paths for the rename
            old_gp = entry.group_path
            parts = old_gp.rsplit("/", 1)
            new_gp = (parts[0] + "/" + new_name) if len(parts) > 1 else new_name
            to_add = set()
            for gp in list(_expanded_groups):
                if gp == old_gp or gp.startswith(old_gp + "/"):
                    _expanded_groups.discard(gp)
                    to_add.add(new_gp + gp[len(old_gp) :])
            _expanded_groups.update(to_add)
            # Full refresh needed for group rename (group_path changes in tree)
            _suppress_edit_save = True
            refresh_cached_items()
            scene.qm_item_list_index = min(idx, len(scene.qm_item_list) - 1)
            _suppress_edit_save = False
        return

    # Non-group item
    item["name"] = scene.qm_edit_name.strip()
    if entry.is_menu:
        item["menu"] = scene.qm_edit_menu.strip()
    else:
        item["operator"] = scene.qm_edit_operator.strip()
        params = _collect_params(scene.qm_edit_params)
        if params:
            item["params"] = params
        elif "params" in item:
            del item["params"]

    mode = scene.qm_edit_mode
    if mode and mode != "ANY":
        item["mode"] = mode
    elif "mode" in item:
        del item["mode"]

    _save_config(entry.config_path, data)

    # Update display entry in-place
    entry.item_name = scene.qm_edit_name.strip()
    if entry.is_menu:
        entry.menu = scene.qm_edit_menu.strip()
    else:
        entry.operator = scene.qm_edit_operator.strip()
        params = _collect_params(scene.qm_edit_params)
        entry.params = json.dumps(params) if params else ""
    entry.mode = mode if mode and mode != "ANY" else ""


def _on_selection_changed(self, context):
    _load_selection_into_edit(context)


def _on_edit_field(self, context):
    """Generic save trigger for name, mode, menu edits."""
    if not _suppress_edit_save:
        _save_current_edit(context)


def _on_edit_operator_field(self, context):
    """Save + auto-fill name + repopulate params when operator changes."""
    global _suppress_edit_save
    if _suppress_edit_save:
        return
    scene = _get_scene_from_context(context)
    if scene is None:
        return

    # Auto-fill name if empty
    if not scene.qm_edit_name.strip():
        rna = _get_op_rna(scene.qm_edit_operator.strip())
        if rna and rna.name:
            _suppress_edit_save = True
            scene.qm_edit_name = rna.name
            _suppress_edit_save = False

    # Repopulate params from new operator RNA
    _populate_params(scene.qm_edit_params, scene.qm_edit_operator.strip())

    # Save
    _save_current_edit(context)


# --- Display list ---


def refresh_cached_items():
    """Rebuild the scene display list from the active config."""
    global _suppress_edit_save
    was_suppressed = _suppress_edit_save
    _suppress_edit_save = True
    scene = _get_scene_from_context()
    if scene is None:
        _suppress_edit_save = was_suppressed
        return
    scene.qm_item_list.clear()
    config_path = get_active_user_config_path()
    if config_path:
        try:
            data = _load_config(config_path)
        except:
            data = None
        if data is not None:
            _walk_items(scene, config_path, data.get("items", []), 0, "", [])
    _load_selection_into_edit(bpy.context)
    _suppress_edit_save = was_suppressed


def _make_entry(scene, config_path, address, depth, group_path):
    """Create a display entry with common fields."""
    entry = scene.qm_item_list.add()
    entry.depth = depth
    entry.group_path = group_path
    entry.address = ",".join(str(x) for x in address)
    entry.config_path = config_path
    return entry


def _walk_items(scene, config_path, items, depth, group_path, address_prefix):
    for i, item in enumerate(items):
        address = address_prefix + [i]
        item_type = item.get("type", "operator")

        if item_type == "group":
            name = item.get("name", "")
            gp = (group_path + "/" + name) if group_path else name
            entry = _make_entry(scene, config_path, address, depth, gp)
            entry.is_group = True
            entry.item_name = name
            entry.expanded = gp in _expanded_groups
            if entry.expanded:
                _walk_items(
                    scene, config_path, item.get("children", []), depth + 1, gp, address
                )
        elif item_type == "separator":
            _make_entry(
                scene, config_path, address, depth, group_path
            ).is_separator = True
        else:  # operator or menu
            entry = _make_entry(scene, config_path, address, depth, group_path)
            entry.item_name = item.get("name", "")
            entry.mode = item.get("mode", "")
            if item_type == "menu":
                entry.is_menu = True
                entry.menu = item.get("menu", "")
            else:
                entry.operator = item.get("operator", "")
                entry.params = json.dumps(item["params"]) if "params" in item else ""


def get_insert_position(context):
    """Return (config_path, data, parent_list, insert_index) for inserting after selection."""
    scene = context.scene
    idx = scene.qm_item_list_index
    if 0 <= idx < len(scene.qm_item_list):
        entry = scene.qm_item_list[idx]
        config_path = entry.config_path
        if config_path and not is_builtin_config(config_path):
            data = _load_config(config_path)
            address = _parse_address(entry.address)
            items = data["items"]
            if entry.is_group:
                children = _get_item_by_address(items, address).setdefault(
                    "children", []
                )
                return config_path, data, children, len(children)
            else:
                parent_list, local_idx = _get_parent_and_index(items, address)
                return config_path, data, parent_list, local_idx + 1

    user_path = get_active_user_config_path()
    if user_path:
        data = _load_config(user_path)
        return user_path, data, data["items"], len(data["items"])
    return None, None, None, -1


def load_items():
    """Forward to the main module's load_items."""
    import importlib

    importlib.import_module(__package__).load_items()


# --- Add operator helpers ---


def _draw_item_fields(self, layout, context, group_label):
    layout.use_property_split = True
    column = layout.column(align=True)
    column.label(text=f"Group: {group_label or '(root)'}", icon="FILE_FOLDER")
    column.separator(factor=_FORM_SPACING)
    column.prop_search(
        self, "operator_id", context.window_manager, "qm_operator_list", text="Operator"
    )
    column.separator(factor=_FORM_SPACING)
    column.prop(self, "name")
    column.separator(factor=_FORM_SPACING)
    column.prop(self, "mode")
    if self.params_list:
        column.separator(factor=_FORM_SPACING)
        _draw_params(self.params_list, column)


def _build_operator_item(self):
    item = {
        "type": "operator",
        "name": self.name.strip(),
        "operator": self.operator_id.strip(),
    }
    params = _collect_params(self.params_list)
    if params:
        item["params"] = params
    if self.mode and self.mode != "ANY":
        item["mode"] = self.mode
    return item


# --- Operators ---


class QuickMenuReloadMenuItemsOperator(bpy.types.Operator):
    """Reload menu items from the active config"""

    bl_idname = "qm.reload_menu_items"
    bl_label = "Reload Menu Items"

    def execute(self, context):
        load_items()
        return {"FINISHED"}


class QuickMenuCreateConfigOperator(bpy.types.Operator):
    """Create a new config file"""

    bl_idname = "qm.create_config"
    bl_label = "New Config"

    name: StringProperty(name="Config Name", default="")
    from_default: BoolProperty(name="Copy From Default", default=False)

    def invoke(self, context, event):
        self.name = ""
        return context.window_manager.invoke_props_dialog(self, width=350)

    def draw(self, context):
        self.layout.prop(self, "name")
        self.layout.prop(self, "from_default")

    def execute(self, context):
        if not self.name.strip():
            self.report({"ERROR"}, "Config name is required")
            return {"CANCELLED"}
        sanitized = re.sub(r"[^\w\-. ]", "_", self.name.strip())
        configs_dir = get_configs_directory()
        os.makedirs(configs_dir, exist_ok=True)
        new_path = os.path.join(configs_dir, sanitized + ".json")
        if os.path.exists(new_path):
            self.report({"ERROR"}, f'Config "{sanitized}.json" already exists')
            return {"CANCELLED"}
        if self.from_default:
            default_path = os.path.join(configs_dir, "default.json")
            if os.path.exists(default_path):
                shutil.copy2(default_path, new_path)
            else:
                _save_config(new_path, {"items": []})
        else:
            _save_config(new_path, {"items": []})
        prefs = get_user_preferences()
        cfg = prefs.configs.add()
        cfg.path = new_path
        activate_config(len(prefs.configs) - 1)
        return {"FINISHED"}


class QuickMenuDeleteConfigOperator(bpy.types.Operator):
    """Delete the active config file"""

    bl_idname = "qm.delete_config"
    bl_label = "Delete Config"

    @classmethod
    def poll(cls, context):
        prefs = get_user_preferences()
        return 0 <= prefs.active_config_index < len(prefs.configs)

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        prefs = get_user_preferences()
        idx = prefs.active_config_index
        if not 0 <= idx < len(prefs.configs):
            self.report({"ERROR"}, "No config selected")
            return {"CANCELLED"}
        config = prefs.configs[idx]
        if is_builtin_config(config.path):
            self.report({"ERROR"}, "Cannot delete the built-in default config")
            return {"CANCELLED"}
        if os.path.exists(config.path):
            os.remove(config.path)
        prefs.configs.remove(idx)

        valid_indices = [
            i
            for i, config in enumerate(prefs.configs)
            if not is_builtin_config(config.path) and os.path.exists(config.path)
        ]
        if not valid_indices:
            import importlib

            importlib.import_module(__package__).reset_configs()
            return {"FINISHED"}

        next_index = next((i for i in valid_indices if i >= idx), valid_indices[-1])
        activate_config(next_index)
        return {"FINISHED"}


class QuickMenuOpenConfigsFolderOperator(bpy.types.Operator):
    """Open the configs folder in the file browser"""

    bl_idname = "qm.open_configs_folder"
    bl_label = "Open Configs Folder"

    def execute(self, context):
        configs_dir = get_configs_directory()
        os.makedirs(configs_dir, exist_ok=True)
        if platform.system() == "Darwin":
            subprocess.call(("open", configs_dir))
        elif platform.system() == "Windows":
            os.startfile(configs_dir)
        else:
            subprocess.call(("xdg-open", configs_dir))
        return {"FINISHED"}


class QuickMenuSwitchConfigOperator(bpy.types.Operator):
    """Switch active config"""

    bl_idname = "qm.switch_config"
    bl_label = "Switch Config"

    index: IntProperty(options={"HIDDEN", "SKIP_SAVE"})

    def execute(self, context):
        if not activate_config(self.index):
            self.report({"ERROR"}, "Config file not found")
            return {"CANCELLED"}
        return {"FINISHED"}


class QM_MT_ConfigSelector(bpy.types.Menu):
    bl_idname = "QM_MT_config_selector"
    bl_label = "Configs"

    def draw(self, context):
        layout = self.layout
        prefs = get_user_preferences()
        has_configs = False

        for i, config in enumerate(prefs.configs):
            if is_builtin_config(config.path):
                continue
            name = os.path.splitext(os.path.basename(config.path))[0]
            op = layout.operator(
                "qm.switch_config",
                text=name,
                icon="CHECKMARK" if i == prefs.active_config_index else "NONE",
            )
            op.index = i
            has_configs = True

        if not has_configs:
            layout.label(text="No configs available", icon="INFO")


class QuickMenuAddItemOperator(bpy.types.Operator):
    """Add a new operator item"""

    bl_idname = "qm.add_item"
    bl_label = "Add Menu Item"

    group_path: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    name: StringProperty(name="Name", default="")
    operator_id: StringProperty(
        name="Operator", default="", update=_on_operator_id_changed
    )
    params_list: CollectionProperty(type=QuickMenuParamEntry)
    mode: EnumProperty(name="Mode Filter", items=MODE_ITEMS, default="ANY")

    def invoke(self, context, event):
        global _suppress_param_update
        _suppress_param_update = True
        self.name = ""
        self.operator_id = ""
        self.mode = "ANY"
        _suppress_param_update = False
        self.params_list.clear()
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):
        _draw_item_fields(self, self.layout, context, self.group_path)

    def execute(self, context):
        if not self.name.strip() or not self.operator_id.strip():
            self.report({"ERROR"}, "Name and Operator are required")
            return {"CANCELLED"}
        config_path, data, parent_list, insert_idx = get_insert_position(context)
        if data is None:
            self.report({"ERROR"}, "No active config loaded")
            return {"CANCELLED"}
        parent_list.insert(insert_idx, _build_operator_item(self))
        _save_config(config_path, data)
        load_items()
        return {"FINISHED"}


class QuickMenuRemoveItemOperator(bpy.types.Operator):
    """Remove this item, separator, or group"""

    bl_idname = "qm.remove_item"
    bl_label = "Remove Item"

    address: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    config_path_prop: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    group_path: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        data = _load_config(self.config_path_prop)
        parent_list, local_idx = _get_parent_and_index(
            data["items"], _parse_address(self.address)
        )
        parent_list.pop(local_idx)
        if self.group_path:
            _expanded_groups.discard(self.group_path)
            _expanded_groups.difference_update({
                gp for gp in _expanded_groups if gp.startswith(self.group_path + "/")
            })
        _save_config(self.config_path_prop, data)
        load_items()
        return {"FINISHED"}


class QuickMenuMoveItemOperator(bpy.types.Operator):
    """Move this menu item up or down"""

    bl_idname = "qm.move_item"
    bl_label = "Move Item"

    address: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    config_path_prop: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    direction: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    def execute(self, context):
        data = _load_config(self.config_path_prop)
        parent_list, local_idx = _get_parent_and_index(
            data["items"], _parse_address(self.address)
        )
        swap_idx = local_idx + (-1 if self.direction == "UP" else 1)
        if swap_idx < 0 or swap_idx >= len(parent_list):
            return {"CANCELLED"}
        parent_list[local_idx], parent_list[swap_idx] = (
            parent_list[swap_idx],
            parent_list[local_idx],
        )
        _save_config(self.config_path_prop, data)
        load_items()
        return {"FINISHED"}


class QuickMenuAddSeparatorOperator(bpy.types.Operator):
    """Add a separator"""

    bl_idname = "qm.add_separator"
    bl_label = "Add Separator"

    group_path: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    def execute(self, context):
        config_path, data, parent_list, insert_idx = get_insert_position(context)
        if data is None:
            self.report({"ERROR"}, "No active config loaded")
            return {"CANCELLED"}
        parent_list.insert(insert_idx, {"type": "separator"})
        _save_config(config_path, data)
        load_items()
        return {"FINISHED"}


class QuickMenuAddGroupOperator(bpy.types.Operator):
    """Add a new submenu group"""

    bl_idname = "qm.add_group"
    bl_label = "Add Group"

    group_path: StringProperty(options={"HIDDEN", "SKIP_SAVE"})
    name: StringProperty(name="Group Name", default="")

    def invoke(self, context, event):
        self.name = ""
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        self.layout.label(
            text=f"Parent: {self.group_path or '(root)'}", icon="FILE_FOLDER"
        )
        self.layout.prop(self, "name")

    def execute(self, context):
        if not self.name.strip():
            self.report({"ERROR"}, "Group name is required")
            return {"CANCELLED"}
        name = self.name.strip()
        config_path, data, parent_list, insert_idx = get_insert_position(context)
        if data is None:
            self.report({"ERROR"}, "No active config loaded")
            return {"CANCELLED"}
        parent_list.insert(insert_idx, {"type": "group", "name": name, "children": []})
        _save_config(config_path, data)
        _expanded_groups.add(
            (self.group_path + "/" + name) if self.group_path else name
        )
        load_items()
        return {"FINISHED"}


class QuickMenuToggleGroupOperator(bpy.types.Operator):
    """Expand or collapse a menu group"""

    bl_idname = "qm.toggle_group"
    bl_label = "Toggle Group"

    group_path: StringProperty(options={"HIDDEN", "SKIP_SAVE"})

    def execute(self, context):
        _expanded_groups.symmetric_difference_update({self.group_path})
        refresh_cached_items()
        for i, entry in enumerate(context.scene.qm_item_list):
            if entry.is_group and entry.group_path == self.group_path:
                context.scene.qm_item_list_index = i
                break
        return {"FINISHED"}


class UI_UL_QuickMenuItemList(bpy.types.UIList):
    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname
    ):
        row = layout.row(align=True)
        for _ in range(item.depth):
            row.label(text="", icon="BLANK1")
        if item.is_group:
            sub = row.row(align=True)
            sub.alignment = "LEFT"
            op = sub.operator(
                "qm.toggle_group",
                text=item.group_path.split("/")[-1],
                icon="TRIA_DOWN" if item.expanded else "TRIA_RIGHT",
                emboss=False,
            )
            op.group_path = item.group_path
        elif item.is_separator:
            row.label(text="---")
        else:
            row.label(text=item.item_name)


class QuickMenuItemEntry(bpy.types.PropertyGroup):
    item_name: StringProperty()
    operator: StringProperty()
    menu: StringProperty()
    params: StringProperty()
    mode: StringProperty()
    is_group: BoolProperty()
    is_separator: BoolProperty()
    is_menu: BoolProperty()
    expanded: BoolProperty()
    depth: IntProperty()
    group_path: StringProperty()
    address: StringProperty(default="")
    config_path: StringProperty(default="")


class VIEW3D_PT_QuickMenuEditor(bpy.types.Panel):
    bl_label = "Quick Menu"
    bl_idname = "VIEW3D_PT_quick_menu_editor"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Quick Menu"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        prefs = get_user_preferences()

        config_box = layout.box()

        row = config_box.row(align=True)
        row.label(text="Config:", icon="DOCUMENTS")
        active_name = "Select Config"
        idx = prefs.active_config_index
        if 0 <= idx < len(prefs.configs):
            active_config = prefs.configs[idx]
            if not is_builtin_config(active_config.path):
                active_name = os.path.splitext(
                    os.path.basename(active_config.path)
                )[0]
        row.menu(
            "QM_MT_config_selector", text=active_name, icon="DOWNARROW_HLT"
        )

        row2 = config_box.row(align=True)
        row2.operator("qm.create_config", text="New", icon="ADD")
        row2.operator("qm.delete_config", text="Delete", icon="TRASH")
        row2.operator("qm.open_configs_folder", text="", icon="FILE_FOLDER")
        row2.operator("qm.reload_menu_items", text="", icon="FILE_REFRESH")

        # Selected entry
        idx = scene.qm_item_list_index
        se = scene.qm_item_list[idx] if 0 <= idx < len(scene.qm_item_list) else None
        group_path = se.group_path if se else ""

        if not scene.qm_item_list:
            layout.label(text="No items loaded", icon="INFO")
            layout.operator(
                "qm.add_group", text="Add Group", icon="FILE_FOLDER"
            ).group_path = ""
            layout.operator("qm.add_item", text="Add Item", icon="ADD").group_path = ""
            return

        row = layout.row()
        row.template_list(
            "UI_UL_QuickMenuItemList",
            "",
            scene,
            "qm_item_list",
            scene,
            "qm_item_list_index",
            rows=16,
        )

        col = row.column(align=True)
        col.operator(
            "qm.add_group", icon="FILE_FOLDER", text=""
        ).group_path = group_path
        col.operator("qm.add_item", icon="ADD", text="").group_path = group_path

        if se and se.address:
            remove_op = col.operator("qm.remove_item", icon="TRASH", text="")
            remove_op.address = se.address
            remove_op.config_path_prop = se.config_path
            if se.is_group:
                remove_op.group_path = se.group_path

        col.operator("qm.add_separator", icon="GRIP", text="").group_path = group_path

        if se and se.address:
            col.separator()
            for icon, direction in [("TRIA_UP", "UP"), ("TRIA_DOWN", "DOWN")]:
                op = col.operator("qm.move_item", icon=icon, text="")
                op.address = se.address
                op.config_path_prop = se.config_path
                op.direction = direction

        # Inline edit
        if se and not se.is_separator:
            box = layout.box()
            column = box.column(align=True)
            if se.is_group:
                column.prop(scene, "qm_edit_name", text="Group Name")
            else:
                column.prop(scene, "qm_edit_name", text="Name")
                column.separator(factor=_FORM_SPACING)
                if se.is_menu:
                    column.prop(scene, "qm_edit_menu", text="Menu")
                else:
                    column.prop_search(
                        scene,
                        "qm_edit_operator",
                        context.window_manager,
                        "qm_operator_list",
                        text="Operator",
                    )
                column.separator(factor=_FORM_SPACING)
                column.prop(scene, "qm_edit_mode", text="Mode")
                if not se.is_menu and scene.qm_edit_params:
                    column.separator(factor=_FORM_SPACING)
                    _draw_params(scene.qm_edit_params, column)


classes = (
    QuickMenuOperatorEntry,
    QuickMenuParamEntry,
    QuickMenuItemEntry,
    QuickMenuToggleGroupOperator,
    UI_UL_QuickMenuItemList,
    VIEW3D_PT_QuickMenuEditor,
    QuickMenuAddItemOperator,
    QuickMenuRemoveItemOperator,
    QuickMenuMoveItemOperator,
    QuickMenuAddSeparatorOperator,
    QuickMenuAddGroupOperator,
    QuickMenuCreateConfigOperator,
    QuickMenuDeleteConfigOperator,
    QuickMenuOpenConfigsFolderOperator,
    QuickMenuSwitchConfigOperator,
    QM_MT_ConfigSelector,
    QuickMenuReloadMenuItemsOperator,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.qm_item_list = bpy.props.CollectionProperty(type=QuickMenuItemEntry)
    bpy.types.Scene.qm_item_list_index = bpy.props.IntProperty(
        update=_on_selection_changed
    )
    bpy.types.WindowManager.qm_operator_list = bpy.props.CollectionProperty(
        type=QuickMenuOperatorEntry
    )
    bpy.types.Scene.qm_edit_name = bpy.props.StringProperty(
        name="Name", update=_on_edit_field
    )
    bpy.types.Scene.qm_edit_operator = bpy.props.StringProperty(
        name="Operator", update=_on_edit_operator_field
    )
    bpy.types.Scene.qm_edit_mode = bpy.props.EnumProperty(
        name="Mode", items=MODE_ITEMS, default="ANY", update=_on_edit_field
    )
    bpy.types.Scene.qm_edit_menu = bpy.props.StringProperty(
        name="Menu", update=_on_edit_field
    )
    bpy.types.Scene.qm_edit_params = bpy.props.CollectionProperty(
        type=QuickMenuParamEntry
    )


def unregister():
    del bpy.types.Scene.qm_edit_params
    del bpy.types.Scene.qm_edit_menu
    del bpy.types.Scene.qm_edit_mode
    del bpy.types.Scene.qm_edit_operator
    del bpy.types.Scene.qm_edit_name
    del bpy.types.WindowManager.qm_operator_list
    del bpy.types.Scene.qm_item_list_index
    del bpy.types.Scene.qm_item_list
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
