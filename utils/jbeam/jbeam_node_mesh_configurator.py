import bpy
import json

from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j, JbeamRefnodeUtils as jr  # type: ignore
from dev_tools.utils.jbeam.jbeam_props_storage import JbeamPropsStorageManager  # type: ignore

class JbeamNodeMeshConfigurator:

    @staticmethod
    def remove_double_vertices(obj):
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.0005)
        bpy.ops.object.mode_set(mode='OBJECT')

    @staticmethod
    def process_node_mesh_props(obj, parser=None, part_name=""):
        j.set_jbeam_visuals(obj)
        j.add_gn_jbeam_visualizer_modifier(obj)
        if not parser:
            return
        ref_nodes = parser.get_ref_nodes(part_name)
        nodes = parser.get_nodes(part_name)
        nodes_list = parser.get_nodes_list(part_name)
        if not nodes_list:
            return
        JbeamPropsStorageManager.get_instance().register_object(obj)
        beams_list = parser.get_beams_list(part_name)
        tris_list = parser.get_triangles_list(part_name)
        JbeamNodeMeshConfigurator.create_node_mesh_attributes(obj)
        JbeamNodeMeshConfigurator.assign_ref_nodes(obj, ref_nodes, nodes)
        JbeamNodeMeshConfigurator.store_node_props_in_vertex_attributes(obj, nodes_list)
        JbeamNodeMeshConfigurator.store_beam_props_in_edge_attributes(obj, beams_list)
        JbeamNodeMeshConfigurator.store_triangle_props_in_face_attributes(obj, tris_list)

    @staticmethod
    def remove_custom_data_props(obj):
        for key in list(obj.keys()):
            del obj[key]
        for key in list(obj.data.keys()):
            del obj.data[key]

    @staticmethod
    def assign_ref_nodes(obj, ref_nodes, nodes):
        for refnode_name, node_id in ref_nodes.items():
            node = nodes.get(node_id)
            ref_label = jr.get_refnode_from_label(refnode_name)
            if node is None:
                print(f"⚠️  Trying to assign refnode '{ref_label}' to Node ID '{node_id}' but it's not found in 'jbeam_parser::nodes', might be in another part but that's an addon limitation (work-in-progress). skipping.")
                continue
            idx = node.index
            if idx < 0:
                print(f"❌ Error: No vertex index assigned to '{node.id}'")
                continue
            jr.set_refnode_id(obj, idx, ref_label.value)
            print(f"Assigned Node '{node.id}' with index {idx} as ref node '{refnode_name}({ref_label.value})'.")

    @staticmethod
    def create_node_mesh_attributes(obj):
        j.remove_old_jbeam_attributes(obj)
        j.create_node_mesh_attributes(obj)

    @staticmethod
    def store_node_props_in_vertex_attributes(obj, nodes):
        for node in nodes:
            if node.index < 0:
                print(f"❌ Error: Invalid vertex index for node '{node.id}'")
                continue

            idx = node.index
            flat_data = {}

            if hasattr(node, "props") and isinstance(node.props, dict):
                flat_data.update({k: json.dumps(v) for k, v in node.props.items()})

            j.set_node_id(obj, idx, str(node.id))
            j.set_node_props(obj, idx, flat_data)

    @staticmethod
    def store_beam_props_in_edge_attributes(obj, beams):
        if beams:
            JbeamNodeMeshConfigurator.store_props_in_attributes(obj, beams, "beams", "edge", j.set_beam_props)

    @staticmethod
    def store_triangle_props_in_face_attributes(obj, triangles):
        if triangles:
            JbeamNodeMeshConfigurator.store_props_in_attributes(obj, triangles, "triangles", "face", j.set_triangle_props)

    @staticmethod
    def store_props_in_attributes(obj, parsed_data, data_type, element_type, set_props_function):
        for item in parsed_data:
            if item.index < 0 or item.index is None:
                print(f"Error: Structure missing: No {element_type} found for {data_type[:-1]} {item.id}")
                continue
            set_props_function(obj, item.index, item.props, item.instance)