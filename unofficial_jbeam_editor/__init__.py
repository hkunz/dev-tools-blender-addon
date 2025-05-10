# "The Unofficial JBeam Editor"
# Author: Harry McKenzie
#
# ##### BEGIN LICENSE BLOCK #####
#
# The Unofficial JBeam Editor
# Copyright (c) 2025 Harry McKenzie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# ##### END LICENSE BLOCK #####

bl_info = {
    "name": "JBeam Editor (Unofficial)",
    "description": "The Unofficial JBeam Editor",
    "author" : "Harry McKenzie",
    "version": (0, 0, 1),
    "blender": (4, 0, 0),
    "location": "N-Panel > JBeam Editor",
    "warning": "",
    "doc_url": "https://github.com/hkunz/dev-tools-blender-addon/tree/main/unofficial_jbeam_editor",
    "wiki_url": "https://github.com/hkunz/dev-tools-blender-addon",
    "tracker_url": "https://github.com/hkunz/dev-tools-blender-addon/issues",
    "support": "COMMUNITY",
    "category": "Import-Export",
}

import bpy
import logging

from bpy.app.handlers import persistent

from unofficial_jbeam_editor.utils.devtools_register import DevToolsRegister
from unofficial_jbeam_editor.config.logging_config import configure_logging
from unofficial_jbeam_editor.ui.addon_preferences import register as register_preferences, unregister as unregister_preferences

from unofficial_jbeam_editor.utils.temp_file_manager import TempFileManager
from unofficial_jbeam_editor.utils.icons_manager import IconsManager
from unofficial_jbeam_editor.utils.jbeam.jbeam_props_storage import JbeamPropsStorageManager
from unofficial_jbeam_editor.utils.jbeam.jbeam_selection_tracker import JbeamSelectionTracker
from unofficial_jbeam_editor.translation.translations import register as register_translations, unregister as unregister_translations
from unofficial_jbeam_editor.ui.sidebar_menu import register as register_devtools_panel, unregister as unregister_devtools_panel

from unofficial_jbeam_editor.operators.common.operator_generic_popup import register as register_generic_popup, unregister as unregister_generic_popup
from unofficial_jbeam_editor.operators.file.beamng.beamng_import_jbeam_as_node_mesh import DEVTOOLS_JBEAMEDITOR_IMPORT_OT_BeamngImportJbeamToNodeMesh

@persistent
def save_pre_handler(dummy):
    logging.debug("DevTools::save_pre_handler ==============>")
    JbeamPropsStorageManager.get_instance().save_all_jbeam_props_to_mesh()

@persistent
def on_load_post_handler(scene):
    logging.debug("DevTools::on_load_post_handler ==============>")
    JbeamPropsStorageManager.get_instance().load_all_jbeam_props_from_mesh()
    JbeamSelectionTracker.get_instance().register()

def menu_func_import(self, context):
    self.layout.operator(DEVTOOLS_JBEAMEDITOR_IMPORT_OT_BeamngImportJbeamToNodeMesh.bl_idname, text="JBeam File (.jbeam)")

def register() -> None:
    configure_logging()
    logging.info("DevTools Application Start")
    logging.debug("DevTools addon Registration Begin ==============>")
    #add_executable_permission(FileUtils.get_executable_filepath())

    DevToolsRegister.register()

    register_devtools_panel()
    register_preferences()
    register_translations()
    register_generic_popup()
    TempFileManager().init()
    IconsManager().init()
    JbeamSelectionTracker.get_instance().register()
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.app.handlers.save_pre.append(save_pre_handler)
    bpy.app.handlers.load_post.append(on_load_post_handler)

    logging.debug("DevTools addon Registration Complete <==========\n")

def unregister() -> None:
    logging.debug("DevTools addon Unregistration Begin ============>")
    unregister_devtools_panel()
    unregister_preferences()
    unregister_translations()
    unregister_generic_popup()
    TempFileManager().cleanup()
    IconsManager().cleanup()
    JbeamSelectionTracker.get_instance().unregister()

    DevToolsRegister.unregister()

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.app.handlers.save_pre.remove(save_pre_handler)
    bpy.app.handlers.load_post.remove(on_load_post_handler)
    logging.debug("DevTools addon Unregistration Complete <========\n")
