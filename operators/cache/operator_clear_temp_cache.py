import bpy
import bpy_types

from dev_tools.utils.temp_file_manager import TempFileManager # type: ignore
from dev_tools.operators.common.operator_generic_popup import OperatorGenericPopup # type: ignore

class FILE_OT_ClearTempCacheOperator(OperatorGenericPopup):
    bl_idname = "file.dev_tools_clear_temp_cache"
    bl_label = "Clear Dev Tools Cache"
    bl_description = "Delete temporary Dev Tools directories of current Blender and addon version"
    bl_options = {'REGISTER'}

    def draw(self, context: bpy_types.Context) -> None:
        self.message = "Delete temporary Dev Tools directories?"
        self.exec_message = "Deleted temporary Dev Tools directories"
        super().draw(context)

    def execute(self, context:bpy_types.Context) -> set[str]:
        TempFileManager().clear_temp_directories()
        super().execute(context)
        return {'FINISHED'}

def register() -> None:
    bpy.utils.register_class(FILE_OT_ClearTempCacheOperator)

def unregister() -> None:
    bpy.utils.unregister_class(FILE_OT_ClearTempCacheOperator)