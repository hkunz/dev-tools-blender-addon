import bpy
import json

from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j  # type: ignore

class JbeamNodeMeshConfigurator:

    @staticmethod
    def remove_double_vertices(obj):
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.0005)
        bpy.ops.object.mode_set(mode='OBJECT')

    @staticmethod
    def process_node_mesh_props(obj, parser=None):
        j.set_jbeam_visuals(obj)
        j.add_gn_jbeam_visualizer_modifier(obj)
        if not parser:
            return
        ref_nodes = parser.get_ref_nodes()
        nodes = parser.get_nodes()
        nodes_list = parser.get_nodes_list()
        beams_list = parser.get_beams_list()
        tris_list = parser.get_triangles_list()
        JbeamNodeMeshConfigurator.assign_ref_nodes_to_vertex_groups(obj, ref_nodes, nodes)
        JbeamNodeMeshConfigurator.create_node_mesh_attributes(obj)
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
    def assign_ref_nodes_to_vertex_groups(obj, ref_nodes, nodes):
        for group_name, node_id in ref_nodes.items():
            vg = obj.vertex_groups.get(group_name)
            if vg is None:
                print(f"Vertex group '{group_name}' not found, creating it.")
                vg = obj.vertex_groups.new(name=group_name)

            node = nodes.get(node_id)
            if node is None:
                print(f"Node ID '{node_id}' not found in 'jbeam_parser::nodes', skipping.")
                continue
            idx = node.index
            if idx < 0:
                print(f"Error: No vertex index assigned to {node.id}")
                continue
            vg.add([idx], 1.0, 'REPLACE')
            print(f"Assigned vertex {idx} to vertex group '{group_name}'.")

    @staticmethod
    def create_node_mesh_attributes(obj):
        j.remove_old_jbeam_attributes(obj)
        j.create_node_mesh_attributes(obj)

    @staticmethod
    def store_node_props_in_vertex_attributes(obj, nodes):
        for node in nodes:
            if node.index < 0:
                print(f"Error: Invalid vertex index for node {node.id}")
                continue

            idx = node.index
            flat_data = {}

            if hasattr(node, "props") and isinstance(node.props, dict):
                flat_data.update({k: json.dumps(v) for k, v in node.props.items()})

            j.set_node_id(obj, idx, str(node.id))
            j.set_node_props(obj, idx, flat_data)

    @staticmethod
    def store_beam_props_in_edge_attributes(obj, beams):
        JbeamNodeMeshConfigurator.store_props_in_attributes(obj, beams, "beams", "edge", j.set_beam_props)

    @staticmethod
    def store_triangle_props_in_face_attributes(obj, triangles):
        JbeamNodeMeshConfigurator.store_props_in_attributes(obj, triangles, "triangles", "face", j.set_triangle_props)

    @staticmethod
    def store_props_in_attributes(obj, parsed_data, data_type, element_type, set_props_function):
        for item in parsed_data:
            if item.index < 0 or item.index is None:
                print(f"Error: Structure missing: No {element_type} found for {data_type[:-1]} {item.id}")
                continue
            set_props_function(obj, item.index, item.props, item.instance)