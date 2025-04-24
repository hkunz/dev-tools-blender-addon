import bpy
import time
import os

from bpy_extras.io_utils import ExportHelper
from mathutils import Vector
from typing import List
from abc import ABC, abstractmethod

from unofficial_jbeam_editor.translation.translations import get_translation
from unofficial_jbeam_editor.operators.common.operator_generic_popup import create_generic_popup
from unofficial_jbeam_editor.utils.file_utils import FileUtils
from unofficial_jbeam_editor.utils.time_utils import TimeUtils

class OperatorFileExporter(bpy.types.Operator, ExportHelper):
    bl_description = "Operator Base Exporter"
    bl_options = {'INTERNAL', 'UNDO'}
    filename_ext: str = ""

    filter_glob: bpy.props.StringProperty(
        default="*.*",
        options={'HIDDEN'},
        maxlen=255,
    ) # type: ignore https://blender.stackexchange.com/questions/311578/how-do-you-correctly-add-ui-elements-to-adhere-to-the-typing-spec/311770#311770

    my_float_prop: bpy.props.FloatProperty(
        name="My Float Prop",
        description="My Float Prop Description",
        default=1.0,
        min=0.0,
        max=100.0,
    ) # type: ignore

    my_string_prop: bpy.props.StringProperty(
        name="My String Prop",
        description="My String Prop Description",
        default="built-in:nippon",
        subtype='FILE_PATH',
    ) # type: ignore

    my_bool_prop: bpy.props.BoolProperty(
        name="My Bool Prop",
        description="My Bool Prop Description",
        default=False,
    ) # type: ignore

    def draw(self, context: bpy.types.Context) -> None:
        self.options_panel = self.layout.box().column()
        self.options_panel.prop(self, "my_float_prop")
        self.options_panel.prop(self, "my_string_prop")
        self.options_panel.prop(self, "my_bool_prop")

    def execute(self, context: bpy.types.Context) -> set[str]:
        duration: int = time.time()
        self.create_popup(f"Execute", time.time() - duration)
        return {'FINISHED'}

    def create_popup(self, header, duration):
        size = FileUtils.get_file_size(self.filepath)
        sduration = TimeUtils.format_duration(duration)
        self.report({'INFO'}, f"{get_translation('addon_name')} {self.filepath} ({size}) in {sduration}")
        create_generic_popup(message=f"{header}|Directory: {os.path.dirname(self.filepath)}|Size: {size}|Duration: {sduration}|Check the Info Editor for more information.")

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        active_object: bpy.types.Object = context.active_object
        if not active_object:
            return False
        selected_objects: List[bpy.types.Object] = context.selected_objects
        if context.mode != 'OBJECT' or not selected_objects or active_object not in selected_objects:
            return False
        for obj in selected_objects:
            if obj.type != 'MESH' or not obj.data.polygons:
                return False
        return True

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        self.options_panel = None
        if False:
            return {'PASS_THROUGH'}
        wm: bpy.types.WindowManager = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}