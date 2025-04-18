import bpy
import bpy_types

from dev_tools.utils.temp_file_manager import TempFileManager
from dev_tools.operators.common.operator_generic_popup import OperatorGenericPopup

class FILE_OT_ClearAllTempCacheOperator(OperatorGenericPopup):
    bl_idname = "file.dev_tools_clear_all_temp_cache"
    bl_label = "Clear All Dev Tools Cache"
    bl_description = "Delete all temporary Dev Tools cache directories regardless of Blender or addon versions"
    bl_options = {'REGISTER'}

    def draw(self, context: bpy_types.Context) -> None:
        self.message = "Delete all temporary Dev Tools directories?"
        self.exec_message = "Deleted all temporary Dev Tools directories"
        super().draw(context)

    def execute(self, context:bpy_types.Context) -> set[str]:
        TempFileManager().clear_temp_directories()
        super().execute(context)
        return {'FINISHED'}

def register() -> None:
    bpy.utils.register_class(FILE_OT_ClearAllTempCacheOperator)

def unregister() -> None:
    bpy.utils.unregister_class(FILE_OT_ClearAllTempCacheOperator)