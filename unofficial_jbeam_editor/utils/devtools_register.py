import bpy

from unofficial_jbeam_editor.operators.file.beamng.beamng_export_node_mesh_to_jbeam import DEVTOOLS_JBEAMEDITOR_EXPORT_OT_BeamngExportNodeMeshToJbeam
from unofficial_jbeam_editor.operators.file.beamng.beamng_import_jbeam_as_node_mesh import DEVTOOLS_JBEAMEDITOR_IMPORT_OT_BeamngImportJbeamToNodeMesh
from unofficial_jbeam_editor.operators.file.beamng.beamng_import_pc_file_as_node_meshes import DEVTOOLS_JBEAMEDITOR_IMPORT_OT_BeamngImportPcFileToNodeMeshes

from unofficial_jbeam_editor.operators.debug.operator_set_log_level import DEVTOOLS_OT_logging_level
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
from unofficial_jbeam_editor.operators.object.beamng.utils.beamng_jbeam_save_elements_jbeam_path import OBJECT_OT_BeamngJbeamSaveElementsJbeamPath

class DevToolsRegister:
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
        OBJECT_OT_BeamngJbeamSaveElementsJbeamPath,
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

    @staticmethod
    def register():
        for cls in DevToolsRegister.DEVTOOLS_CLASSES:
            bpy.utils.register_class(cls)
    
    @staticmethod
    def unregister():
        for cls in reversed(DevToolsRegister.DEVTOOLS_CLASSES):
            bpy.utils.unregister_class(cls)
