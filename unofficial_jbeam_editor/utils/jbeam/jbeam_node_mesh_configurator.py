import bpy
import json
import logging

from unofficial_jbeam_editor.utils.jbeam.jbeam_utils import JbeamUtils as j, JbeamRefnodeUtils as jr
from unofficial_jbeam_editor.utils.jbeam.jbeam_props_storage import JbeamPropsStorageManager

class JbeamNodeMeshConfigurator:

    @staticmethod
    def remove_double_vertices(obj):
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.0005)
        bpy.ops.object.mode_set(mode='OBJECT')

    @staticmethod
    def process_node_mesh_props(obj, parser=None, part_id="", init=True):
        JbeamNodeMeshConfigurator.process_node_mesh_props_for_nodes(obj, parser, part_id, init)
        JbeamNodeMeshConfigurator.process_node_mesh_props_for_beams_and_tris(obj, parser, part_id)
        if parser:
            JbeamNodeMeshConfigurator.assign_ref_nodes(obj, parser.get_ref_nodes(part_id), parser.get_nodes(part_id))

    @staticmethod
    def process_node_mesh_props_for_nodes(obj, parser, part_id, init):
        if init:
            j.set_jbeam_visuals(obj)
            j.add_gn_jbeam_visualizer_modifier(obj)
        if not parser:
            return
        nodes_list = parser.get_nodes_list(part_id)
        if not nodes_list:
            return
        if init:
            JbeamPropsStorageManager.get_instance().register_object(obj)
            JbeamNodeMeshConfigurator.create_node_mesh_attributes(obj)
        JbeamNodeMeshConfigurator.store_node_props_in_vertex_attributes(obj, nodes_list)

    @staticmethod
    def process_node_mesh_props_for_beams_and_tris(obj, parser=None, part_id=""):
        if not parser:
            return
        JbeamNodeMeshConfigurator.store_beam_props_in_edge_attributes(obj, parser.get_beams_list(part_id))
        JbeamNodeMeshConfigurator.store_triangle_props_in_face_attributes(obj, parser.get_triangles_list(part_id))

    @staticmethod
    def remove_custom_data_props(obj):
        for key in list(obj.keys()):
            del obj[key]
        for key in list(obj.data.keys()):
            del obj.data[key]

    @staticmethod
    def assign_ref_nodes(obj, ref_nodes, nodes) -> bool:
        for refnode_name, node_id in ref_nodes.items():
            node = nodes.get(node_id)
            ref_label = jr.get_refnode_from_label(refnode_name)
            if node is None:
                logging.debug(f"⚠️  Unable to assign refnode '{ref_label}' to Node ID '{node_id}': node might be missing or belong to a base JBeam part.")
                continue
            idx = node.index
            if idx < 0:
                logging.debug(f"❌ Error: No vertex index assigned to '{node.id}'")
                continue
            success = jr.set_refnode_id(obj, idx, ref_label.value)
            if not success:
                return False
            logging.debug(f"🎯 Assigned Node '{node.id}' with index {idx} as ref node '{refnode_name}({ref_label.value})'.")
        return True

    @staticmethod
    def create_node_mesh_attributes(obj):
        j.remove_old_jbeam_attributes(obj)
        j.create_node_mesh_attributes(obj)

    @staticmethod
    def store_node_props_in_vertex_attributes(obj, nodes):
        for node in nodes:
            if node.index < 0:
                logging.debug(f"❌ Error: Invalid vertex index for node '{node.id}'")
                continue

            idx = node.index
            flat_data = {k: json.dumps(v) for k, v in node.props.items()}

            j.set_node_id(obj, idx, str(node.id))
            j.set_node_props(obj, idx, flat_data)
            j.set_jbeam_source(obj, idx, "verts", node.source_jbeam)

    @staticmethod
    def store_beam_props_in_edge_attributes(obj, beams):
        if beams:
            JbeamNodeMeshConfigurator.store_props_in_attributes(obj, beams, j.set_beam_props, "edges", "beams")

    @staticmethod
    def store_triangle_props_in_face_attributes(obj, triangles):
        if triangles:
            JbeamNodeMeshConfigurator.store_props_in_attributes(obj, triangles, j.set_triangle_props, "faces", "triangles")

    @staticmethod
    def store_props_in_attributes(obj, parsed_data, set_props_function, domain, data_type):
        for item in parsed_data:
            idx = item.index
            if idx < 0 or idx is None:
                #logging.debug(f"❌ Error: Structure missing: No {domain} found for {data_type[:-1]} {item.id}")
                continue
            flat_data = {k: json.dumps(v) for k, v in item.props.items()}
            set_props_function(obj, idx, flat_data, item.instance)
            j.set_jbeam_source(obj, idx, domain, item.source_jbeam)