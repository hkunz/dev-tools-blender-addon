import bpy

from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper

from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j  # type: ignore
from dev_tools.utils.jbeam.jbeam_parser import JbeamParser  # type: ignore
from dev_tools.utils.jbeam.jbeam_mesh_creator import JbeamMeshCreator  # type: ignore

class DEVTOOLS_JBEAM_EDITOR_OT_import_jbeam_as_node_mesh(Operator, ImportHelper):
    """Import a .jbeam file"""
    bl_idname = "devtools_jbeam_editor.beamng_import_jbeam_file_as_node_mesh"
    bl_label = "DevTools: Import Jbeam File"

    filename_ext = ".jbeam"
    filter_glob: StringProperty(
        default="*.jbeam",
        options={'HIDDEN'},
        maxlen=255,
    )  # type: ignore

    def execute(self, context):
        jbeam_path = self.filepath
        self.parser = JbeamParser()
        try:
            self.parser.load_jbeam(jbeam_path)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to read file: {e}")
            return {'CANCELLED'}

        nodes_list = self.parser.get_nodes_list()
        jmc = JbeamMeshCreator()
        obj = jmc.create_empty_object()
        jmc.add_vertices(nodes_list)
        self.parser.parse_data_for_jbeam_object_conversion(obj, False)

        beams_list = self.parser.get_beams_list()
        print("beams ====", beams_list[0])
        #tris_list = self.parser.get_triangles_list()
        #jmc.add_edges(beams_list)
        #jmc.add_faces(tris_list)

        #self.parser.debug_print_nodes()
        ref_nodes = self.parser.get_ref_nodes()

        #self.assign_ref_nodes_to_vertex_groups(obj, ref_nodes, nodes)
        #self.create_node_mesh_attributes(obj)
        #self.store_node_props_in_vertex_attributes(obj)
        #self.store_beam_props_in_edge_attributes(obj, beams_list)
        #self.store_triangle_props_in_face_attributes(obj, tris_list)

        return {'FINISHED'}
