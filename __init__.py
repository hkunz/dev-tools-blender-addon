# "Dev Tools"
# Author: Harry McKenzie
#
# ##### BEGIN LICENSE BLOCK #####
#
# Dev Tools
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
    "name": "Dev Tools",
    "description": "Dev Tools",
    "author" : "Harry McKenzie",
    "version": (0, 0, 0),
    "blender": (4, 2, 0),
    "location": "N-Panel > Dev Tools",
    "warning": "",
    "doc_url": "https://blendermarket.com/products/dev_tools/docs",
    "wiki_url": "https://blendermarket.com/products/dev_tools/docs",
    "tracker_url": "https://blendermarket.com/products/dev_tools/docs",
    "support": "COMMUNITY",
    "category": "Import-Export",
}

import bpy

from bpy.app.handlers import persistent

from dev_tools.ui.addon_preferences import register as register_preferences, unregister as unregister_preferences # type: ignore
from dev_tools.utils.file_utils import FileUtils # type: ignore
from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j # type: ignore
from dev_tools.utils.temp_file_manager import TempFileManager # type: ignore
from dev_tools.utils.icons_manager import IconsManager # type: ignore
from dev_tools.utils.jbeam.jbeam_props_storage import JbeamPropsStorage  # type: ignore
from dev_tools.utils.jbeam.jbeam_selection_tracker import JbeamSelectionTracker # type: ignore
from dev_tools.translation.translations import register as register_translations, unregister as unregister_translations # type: ignore
from dev_tools.ui.sidebar_menu import register as register_devtools_panel, unregister as unregister_devtools_panel # type: ignore
from dev_tools.operators.common.operator_generic_popup import register as register_generic_popup, unregister as unregister_generic_popup # type: ignore
from dev_tools.operators.file.beamng.beamng_export_node_mesh_to_jbeam import DEVTOOLS_JBEAMEDITOR_EXPORT_OT_BeamngExportNodeMeshToJbeam # type: ignore
from dev_tools.operators.file.beamng.beamng_import_jbeam_as_node_mesh import DEVTOOLS_JBEAMEDITOR_IMPORT_OT_BeamngImportJbeamToNodeMesh  # type: ignore

from dev_tools.operators.object.armature.armature_create_bones_random_vertices_operator import OBJECT_OT_ArmatureCreateBonesRandomVertices # type: ignore
from dev_tools.operators.object.armature.armature_create_bones_from_edge_selection_operator import OBJECT_OT_ArmatureCreateBonesFromEdgeSelection # type: ignore
from dev_tools.operators.object.armature.armature_assign_closest_vertex_to_bone_tails_operator import OBJECT_OT_ArmatureAssignClosestVertexToBoneTails # type: ignore
from dev_tools.operators.object.bake.bake_prepare_object_operator import OBJECT_OT_BakePrepareObject # type: ignore
from dev_tools.operators.object.bake.bake_generate_object_operator import OBJECT_OT_BakeGenerateObject # type: ignore
from dev_tools.operators.object.beamng.beamng_create_empties_base_operator import OBJECT_OT_BeamngCreateEmptiesBase # type: ignore
from dev_tools.operators.object.beamng.beamng_create_metaball_cloud_operator import OBJECT_OT_BeamngCreateMetaBallCloud # type: ignore
from dev_tools.operators.object.beamng.beamng_parent_to_start01_empty_operator import OBJECT_OT_BeamngClearChildrenStart01Empty, OBJECT_OT_BeamngParentToStart01Empty # type: ignore
from dev_tools.operators.object.beamng.beamng_convert_jbeam_to_node_mesh import OBJECT_OT_BeamngConvertJbeamToNodeMesh # type: ignore
from dev_tools.operators.object.beamng.beamng_jbeam_node_props_manager import OBJECT_OT_BeamngLoadJbeamNodeProps, OBJECT_OT_BeamngLoadJbeamBeamProps, OBJECT_OT_BeamngLoadJbeamTriangleProps, OBJECT_OT_BeamngSaveJbeamNodeProp, OBJECT_OT_BeamngSaveJbeamBeamProp, OBJECT_OT_BeamngSaveJbeamTriangleProp, OBJECT_OT_BeamngSaveAllJbeamNodeProps, OBJECT_OT_BeamngSaveAllJbeamBeamProps, OBJECT_OT_BeamngSaveAllJbeamTriangleProps, OBJECT_OT_BeamngAddJbeamTriangleProp, OBJECT_OT_BeamngAddJbeamNodeProp, OBJECT_OT_BeamngAddJbeamBeamProp, OBJECT_OT_BeamngRemoveJbeamNodeProp, OBJECT_OT_BeamngRemoveJbeamBeamProp, OBJECT_OT_BeamngRemoveJbeamTriangleProp, OBJECT_OT_BeamngSelectJbeamNodesByProperty, OBJECT_OT_BeamngSelectJbeamBeamsByProperty, OBJECT_OT_BeamngSelectJbeamTrianglesByProperty  # type: ignore
from dev_tools.operators.object.beamng.beamng_jbeam_rename_selected_nodes import OBJECT_OT_BeamngJbeamRenameSelectedNodes # type: ignore
from dev_tools.operators.object.beamng.beamng_jbeam_create_node_mesh import OBJECT_OT_BeamngJbeamCreateNodeMesh # type: ignore
from dev_tools.operators.object.beamng.beamng_jbeam_set_refnode_operator import OBJECT_OT_BeamngJbeamSetRefnodeOperator  # type: ignore
from dev_tools.operators.object.beamng.utils.beamng_jbeam_print_attributes_operators import OBJECT_OT_BeamngPrintJbeamNodeProps, OBJECT_OT_BeamngPrintJbeamBeamProps, OBJECT_OT_BeamngPrintJbeamTriangleProps  # type: ignore
from dev_tools.operators.object.beamng.utils.beamng_jbeam_select_element_operator import OBJECT_OT_BeamngJbeamSelectSpecificElement  # type: ignore
from dev_tools.operators.object.beamng.utils.beamng_jbeam_select_ref_element_operator import OBJECT_OT_BeamngJbeamSelectRefNode  # type: ignore

DEVTOOLS_CLASSES = [
    OBJECT_OT_ArmatureCreateBonesRandomVertices,
    OBJECT_OT_ArmatureAssignClosestVertexToBoneTails,
    OBJECT_OT_ArmatureCreateBonesFromEdgeSelection,
    OBJECT_OT_BakePrepareObject,
    OBJECT_OT_BakeGenerateObject,
    OBJECT_OT_BeamngJbeamSelectSpecificElement,
    OBJECT_OT_BeamngJbeamSelectRefNode,
    DEVTOOLS_JBEAMEDITOR_IMPORT_OT_BeamngImportJbeamToNodeMesh,
    DEVTOOLS_JBEAMEDITOR_EXPORT_OT_BeamngExportNodeMeshToJbeam,
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
    print("DevTools::save_pre_handler ==============>")
    JbeamPropsStorage.get_instance().save_jbeam_props_to_mesh()

@persistent
def on_load_post_handler(scene):
    print("DevTools::on_load_post_handler ==============>")
    JbeamPropsStorage.get_instance().load_jbeam_props_from_mesh()
    JbeamSelectionTracker.get_instance().register()

def menu_func_import(self, context):
    self.layout.operator(DEVTOOLS_JBEAMEDITOR_IMPORT_OT_BeamngImportJbeamToNodeMesh.bl_idname, text="JBeam File (.jbeam)")

def register() -> None:
    print("DevTools addon Registration Begin ==============>")
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

    print("DevTools addon Registration Complete <==========\n")

def unregister() -> None:
    print("DevTools addon Unregistration Begin ============>")
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
    print("DevTools addon Unregistration Complete <========\n")
