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
    "name": "JBeam Editor",
    "description": "The Unofficial JBeam Editor",
    "author" : "Harry McKenzie",
    "version": (0, 0, 0),
    "blender": (4, 2, 0),
    "location": "N-Panel > JBeam Editor",
    "warning": "",
    "doc_url": "https://blendermarket.com/products/jbeam_editor/docs",
    "wiki_url": "https://blendermarket.com/products/jbeam_editor/docs",
    "tracker_url": "https://blendermarket.com/products/jbeam_editor/docs",
    "support": "COMMUNITY",
    "category": "Import-Export",
}

import bpy
import logging

from bpy.app.handlers import persistent

from unofficial_jbeam_editor.config.logging_config import configure_logging
from unofficial_jbeam_editor.ui.addon_preferences import register as register_preferences, unregister as unregister_preferences
from unofficial_jbeam_editor.utils.file_utils import FileUtils
from unofficial_jbeam_editor.utils.jbeam.jbeam_utils import JbeamUtils as j
from unofficial_jbeam_editor.utils.temp_file_manager import TempFileManager
from unofficial_jbeam_editor.utils.icons_manager import IconsManager
from unofficial_jbeam_editor.utils.jbeam.jbeam_props_storage import JbeamPropsStorage, JbeamPropsStorageManager
from unofficial_jbeam_editor.utils.jbeam.jbeam_selection_tracker import JbeamSelectionTracker
from unofficial_jbeam_editor.translation.translations import register as register_translations, unregister as unregister_translations
from unofficial_jbeam_editor.ui.sidebar_menu import register as register_devtools_panel, unregister as unregister_devtools_panel
from unofficial_jbeam_editor.operators.debug.operator_set_log_level import DEVTOOLS_OT_logging_level
from unofficial_jbeam_editor.operators.common.operator_generic_popup import register as register_generic_popup, unregister as unregister_generic_popup
from unofficial_jbeam_editor.operators.file.beamng.beamng_export_node_mesh_to_jbeam import DEVTOOLS_JBEAMEDITOR_EXPORT_OT_BeamngExportNodeMeshToJbeam
from unofficial_jbeam_editor.operators.file.beamng.beamng_import_jbeam_as_node_mesh import DEVTOOLS_JBEAMEDITOR_IMPORT_OT_BeamngImportJbeamToNodeMesh
from unofficial_jbeam_editor.operators.file.beamng.beamng_import_pc_file_as_node_meshes import DEVTOOLS_JBEAMEDITOR_IMPORT_OT_BeamngImportPcFileToNodeMeshes

from unofficial_jbeam_editor.operators.object.armature.armature_create_bones_random_vertices_operator import OBJECT_OT_ArmatureCreateBonesRandomVertices
from unofficial_jbeam_editor.operators.object.armature.armature_create_bones_from_edge_selection_operator import OBJECT_OT_ArmatureCreateBonesFromEdgeSelection
from unofficial_jbeam_editor.operators.object.armature.armature_assign_closest_vertex_to_bone_tails_operator import OBJECT_OT_ArmatureAssignClosestVertexToBoneTails
from unofficial_jbeam_editor.operators.object.bake.bake_prepare_object_operator import OBJECT_OT_BakePrepareObject
from unofficial_jbeam_editor.operators.object.bake.bake_generate_object_operator import OBJECT_OT_BakeGenerateObject
from unofficial_jbeam_editor.operators.object.beamng.beamng_create_empties_base_operator import OBJECT_OT_BeamngCreateEmptiesBase
from unofficial_jbeam_editor.operators.object.beamng.beamng_create_metaball_cloud_operator import OBJECT_OT_BeamngCreateMetaBallCloud
from unofficial_jbeam_editor.operators.object.beamng.beamng_parent_to_start01_empty_operator import OBJECT_OT_BeamngClearChildrenStart01Empty, OBJECT_OT_BeamngParentToStart01Empty
from unofficial_jbeam_editor.operators.object.beamng.beamng_convert_jbeam_to_node_mesh import OBJECT_OT_BeamngConvertJbeamToNodeMesh
from unofficial_jbeam_editor.operators.object.beamng.beamng_jbeam_node_props_manager import OBJECT_OT_BeamngLoadJbeamNodeProps, OBJECT_OT_BeamngLoadJbeamBeamProps, OBJECT_OT_BeamngLoadJbeamTriangleProps, OBJECT_OT_BeamngSaveJbeamNodeProp, OBJECT_OT_BeamngSaveJbeamBeamProp, OBJECT_OT_BeamngSaveJbeamTriangleProp, OBJECT_OT_BeamngSaveAllJbeamNodeProps, OBJECT_OT_BeamngSaveAllJbeamBeamProps, OBJECT_OT_BeamngSaveAllJbeamTriangleProps, OBJECT_OT_BeamngAddJbeamTriangleProp, OBJECT_OT_BeamngAddJbeamNodeProp, OBJECT_OT_BeamngAddJbeamBeamProp, OBJECT_OT_BeamngRemoveJbeamNodeProp, OBJECT_OT_BeamngRemoveJbeamBeamProp, OBJECT_OT_BeamngRemoveJbeamTriangleProp, OBJECT_OT_BeamngSelectJbeamNodesByProperty, OBJECT_OT_BeamngSelectJbeamBeamsByProperty, OBJECT_OT_BeamngSelectJbeamTrianglesByProperty
from unofficial_jbeam_editor.operators.object.beamng.beamng_jbeam_rename_selected_nodes import OBJECT_OT_BeamngJbeamRenameSelectedNodes
from unofficial_jbeam_editor.operators.object.beamng.beamng_jbeam_create_node_mesh import OBJECT_OT_BeamngJbeamCreateNodeMesh
from unofficial_jbeam_editor.operators.object.beamng.beamng_jbeam_set_refnode_operator import OBJECT_OT_BeamngJbeamSetRefnodeOperator
from unofficial_jbeam_editor.operators.object.beamng.utils.beamng_jbeam_print_attributes_operators import OBJECT_OT_BeamngPrintJbeamNodeProps, OBJECT_OT_BeamngPrintJbeamBeamProps, OBJECT_OT_BeamngPrintJbeamTriangleProps
from unofficial_jbeam_editor.operators.object.beamng.utils.beamng_jbeam_select_element_operator import OBJECT_OT_BeamngJbeamSelectSpecificElement
from unofficial_jbeam_editor.operators.object.beamng.utils.beamng_jbeam_select_element_by_jbeam_path import OBJECT_OT_BeamngJbeamSelectElementByJbeamPath
from unofficial_jbeam_editor.operators.object.beamng.utils.beamng_jbeam_select_ref_element_operator import OBJECT_OT_BeamngJbeamSelectRefNode

DEVTOOLS_CLASSES = [
    DEVTOOLS_OT_logging_level,
    OBJECT_OT_ArmatureCreateBonesRandomVertices,
    OBJECT_OT_ArmatureAssignClosestVertexToBoneTails,
    OBJECT_OT_ArmatureCreateBonesFromEdgeSelection,
    OBJECT_OT_BakePrepareObject,
    OBJECT_OT_BakeGenerateObject,
    OBJECT_OT_BeamngJbeamSelectSpecificElement,
    OBJECT_OT_BeamngJbeamSelectElementByJbeamPath,
    OBJECT_OT_BeamngJbeamSelectRefNode,
    DEVTOOLS_JBEAMEDITOR_IMPORT_OT_BeamngImportJbeamToNodeMesh,
    DEVTOOLS_JBEAMEDITOR_EXPORT_OT_BeamngExportNodeMeshToJbeam,
    DEVTOOLS_JBEAMEDITOR_IMPORT_OT_BeamngImportPcFileToNodeMeshes,
    OBJECT_OT_BeamngCreateEmptiesBase,
    OBJECT_OT_BeamngCreateMetaBallCloud,
    OBJECT_OT_BeamngParentToStart01Empty,
    OBJECT_OT_BeamngClearChildrenStart01Empty,
    OBJECT_OT_BeamngConvertJbeamToNodeMesh,
    OBJECT_OT_BeamngLoadJbeamNodeProps,
    OBJECT_OT_BeamngLoadJbeamBeamProps,
    OBJECT_OT_BeamngLoadJbeamTriangleProps,
    OBJECT_OT_BeamngSaveJbeamNodeProp,
    OBJECT_OT_BeamngSaveJbeamBeamProp,
    OBJECT_OT_BeamngSaveJbeamTriangleProp,
    OBJECT_OT_BeamngSaveAllJbeamNodeProps,
    OBJECT_OT_BeamngSaveAllJbeamBeamProps,
    OBJECT_OT_BeamngSaveAllJbeamTriangleProps,
    OBJECT_OT_BeamngAddJbeamNodeProp,
    OBJECT_OT_BeamngAddJbeamBeamProp,
    OBJECT_OT_BeamngAddJbeamTriangleProp,
    OBJECT_OT_BeamngRemoveJbeamNodeProp,
    OBJECT_OT_BeamngRemoveJbeamBeamProp,
    OBJECT_OT_BeamngRemoveJbeamTriangleProp,
    OBJECT_OT_BeamngJbeamRenameSelectedNodes,
    OBJECT_OT_BeamngSelectJbeamNodesByProperty,
    OBJECT_OT_BeamngSelectJbeamBeamsByProperty,
    OBJECT_OT_BeamngSelectJbeamTrianglesByProperty,
    OBJECT_OT_BeamngJbeamCreateNodeMesh,
    OBJECT_OT_BeamngPrintJbeamNodeProps,
    OBJECT_OT_BeamngPrintJbeamBeamProps,
    OBJECT_OT_BeamngPrintJbeamTriangleProps,
    OBJECT_OT_BeamngJbeamSetRefnodeOperator
]

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

    for cls in DEVTOOLS_CLASSES:
        bpy.utils.register_class(cls)

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

    for cls in reversed(DEVTOOLS_CLASSES):
        bpy.utils.unregister_class(cls)

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.app.handlers.save_pre.remove(save_pre_handler)
    bpy.app.handlers.load_post.remove(on_load_post_handler)
    logging.debug("DevTools addon Unregistration Complete <========\n")
