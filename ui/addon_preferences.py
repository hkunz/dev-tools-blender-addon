import bpy
import bpy_types

from bpy.types import UILayout
from typing import List

from dev_tools.utils.utils import Utils # type: ignore
from dev_tools.utils.ui_utils import UiUtils  # type: ignore

def on_addon_preferences_change(update_ui=True) -> None:
    addon: bpy.types.Addon = bpy.context.preferences.addons[MyAddonPreferences.bl_idname]
    prefs: MyAddonPreferences = addon.preferences
    print(f"on_addon_preferences_change: {prefs}: update any menus when preferences have changed")
    if update_ui:
        UiUtils.force_update_ui(bpy.context)

def on_property_update(self, _: bpy_types.Context, sample_type: str) -> None:
    print(f"on_property_update: {self}::{sample_type}")
    on_addon_preferences_change()

class PREFERENCES_OT_CheckCheckboxesOperator(bpy.types.Operator):
    bl_idname = "preferences.dev_tools_check_checkboxes"
    bl_label = "Check All"
    bl_description = "Tick all checkboxes"
    bl_options = {'INTERNAL'}

    def execute(self, context) -> set[str]:
        addon_preferences: bpy.types.Addon = context.preferences.addons[MyAddonPreferences.bl_idname]
        preferences: MyAddonPreferences = addon_preferences.preferences
        preferences.check_all_checkboxes()
        return {'FINISHED'}

class PREFERENCES_OT_ClearCheckboxesOperator(bpy.types.Operator):
    bl_idname = "preferences.dev_tools_clear_checkboxes"
    bl_label = "Uncheck All"
    bl_description = "Untick all checkboxes"
    bl_options = {'INTERNAL'}

    def execute(self, context) -> set[str]:
        addon_preferences: bpy.types.Addon = context.preferences.addons[MyAddonPreferences.bl_idname]
        preferences: MyAddonPreferences = addon_preferences.preferences
        preferences.clear_all_checkboxes()
        return {'FINISHED'}

class MyAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = Utils.get_addon_module_name() # __name__ if the class is defined inside __init__.py

    debug_options: bpy.props.BoolProperty(
        name="Show Debug Options",
        default=True,
        update=lambda self, context: on_property_update(self, context, "debug")
    ) # type: ignore

    use_vizualizer: bpy.props.BoolProperty(
        name="Geometry Nodes Visualizer",
        default=True,
        update=lambda self, context: on_property_update(self, context, "visualizer")
    ) # type: ignore

    show_import_warnings: bpy.props.BoolProperty(
        name="Show Import Warnings",
        default=False,
        update=lambda self, context: on_property_update(self, context, "import_warnings")
    ) # type: ignore

    armature_options: bpy.props.BoolProperty(
        name="Show Armature Options",
        default=False,
        update=lambda self, context: on_property_update(self, context, "armature")
    ) # type: ignore

    bake_options: bpy.props.BoolProperty(
        name="Show Bake Options",
        default=False,
        update=lambda self, context: on_property_update(self, context, "bake")
    ) # type: ignore

    empty_options: bpy.props.BoolProperty(
        name="Show Empty Object Options",
        default=False,
        update=lambda self, context: on_property_update(self, context, "empty")
    ) # type: ignore

    CHECKBOXES: List[str] = ["debug_options", "use_vizualizer", "show_import_warnings", "armature_options", "bake_options", "empty_options"]

    def set_checkbox(self, prop_name: str, value: bool) -> None:
        if getattr(self, prop_name) != value:
            setattr(self, prop_name, value)

    def check_all_checkboxes(self) -> None:
        for prop_name in self.CHECKBOXES:
            self.set_checkbox(prop_name, True)

    def clear_all_checkboxes(self) -> None:
        for prop_name in self.CHECKBOXES:
            self.set_checkbox(prop_name, False)

    def draw(self, _: bpy_types.Context) -> None:
        layout: UILayout = self.layout
        #options_box: UILayout = layout.box()
        #box: UILayout = options_box.box()
        #split: UILayout = box.split(factor=0.5)
        #col1: UILayout = split.column()
        #col1.operator(PREFERENCES_OT_ClearCheckboxesOperator.bl_idname, text="Uncheck All Boxes")
        #col2 = split.column()
        #col2.operator(PREFERENCES_OT_CheckCheckboxesOperator.bl_idname, text="Check All Boxes")

        box = layout.box()
        for checkbox in self.CHECKBOXES:
            box.prop(self, checkbox)

    @staticmethod
    def is_addon_option_enabled(option):
        addon_name = Utils.get_addon_module_name()
        prefs = bpy.context.preferences.addons.get(addon_name).preferences
        return getattr(prefs, option, False)

    @staticmethod
    def is_addon_visualizer_enabled():
        return MyAddonPreferences.is_addon_option_enabled("use_vizualizer")

    @staticmethod
    def is_warnings_enabled():
        return MyAddonPreferences.is_addon_option_enabled("show_import_warnings")

def register() -> None:
    bpy.utils.register_class(MyAddonPreferences)
    bpy.utils.register_class(PREFERENCES_OT_CheckCheckboxesOperator)
    bpy.utils.register_class(PREFERENCES_OT_ClearCheckboxesOperator)
    on_addon_preferences_change(False)

def unregister() -> None:
    bpy.utils.unregister_class(MyAddonPreferences)
    bpy.utils.unregister_class(PREFERENCES_OT_CheckCheckboxesOperator)
    bpy.utils.unregister_class(PREFERENCES_OT_ClearCheckboxesOperator)