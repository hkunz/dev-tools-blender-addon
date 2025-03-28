import bpy
import json

from pprint import pprint
from bpy.types import Operator

from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j  # type: ignore
from dev_tools.utils.jbeam.jbeam_parser import JbeamParser  # type: ignore
from dev_tools.utils.jbeam.jbeam_mesh_creator import JbeamMeshCreator  # type: ignore

class OBJECT_OT_BeamngConvertJbeamToNodeMesh(Operator):
    """Convert object to Node Mesh by removing custom properties and merging by distance"""
    bl_idname = "object.devtools_beamng_convert_jbeam_to_node_mesh"
    bl_label = "DevTools: Convert JBeam to Mesh Object (v2)"
    bl_options = {'REGISTER', 'UNDO'}

    def remove_custom_data_props(self, obj):
        for key in list(obj.keys()):
            del obj[key]
        for key in list(obj.data.keys()):
            del obj.data[key]

    def assign_ref_nodes_to_vertex_groups(self, obj, ref_nodes, nodes):
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
                self.report({'ERROR'}, f"No vertex index assigned to {node.id}")
                continue
            vg.add([idx], 1.0, 'REPLACE')
            print(f"Assigned vertex {idx} to vertex group '{group_name}'.")

    def create_node_mesh_attributes(self, obj):
        j.remove_old_jbeam_attributes(obj)
        j.create_node_mesh_attributes(obj)

    def store_node_props_in_vertex_attributes(self, obj):
        nodes_list = self.parser.get_nodes_list()
        for node in nodes_list:
            if not hasattr(node, "index") or node.index < 0:
                self.report({'ERROR'}, f"Invalid vertex index for node {node.id}")
                continue

            idx = node.index
            flat_data = {}

            if hasattr(node, "props") and isinstance(node.props, dict):
                flat_data.update({k: json.dumps(v) for k, v in node.props.items()})

            j.set_node_id(obj, idx, str(node.id))
            j.set_node_props(obj, idx, flat_data)

    def store_beam_props_in_edge_attributes(self, obj, beams):
        self.store_props_in_attributes(obj, beams, "beams", "edge", j.set_beam_props)

    def store_triangle_props_in_face_attributes(self, obj, triangles):
        self.store_props_in_attributes(obj, triangles, "triangles", "face", j.set_triangle_props)

    def store_props_in_attributes(self, obj, parsed_data, data_type, element_type, set_props_function):
        for item in parsed_data:
            if item.index is None:
                self.report({'ERROR'}, f"Structure missing: No {element_type} found for {data_type[:-1]} {item.id}")
                continue
            set_props_function(obj, item.index, item.props, item.instance)

    def execute(self, context):
        obj = context.object

        if not obj:
            self.report({'WARNING'}, "No mesh object selected!")
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='OBJECT')
        if obj.type == 'CURVE':
            bpy.ops.object.convert(target='MESH')
        elif j.is_node_mesh(obj):
            j.add_gn_jbeam_visualizer_modifier(obj)
            self.report({'INFO'}, "Object is already a Node Mesh")
            return {'CANCELLED'}
        elif obj.type != 'MESH':
            self.report({'WARNING'}, f"{repr(obj)} is not a mesh object!")
            return {'CANCELLED'}

        j.set_jbeam_visuals(obj)
        j.add_gn_jbeam_visualizer_modifier(obj)

        jbeam_path = obj.data.get('jbeam_file_path', None)
        ref_nodes = None
        is_jbeam_part = False  # flag to check if the jbeam part object is an import from the original jbeam editor from BeamNG team

        if not jbeam_path:
            self.report({'WARNING'}, "Object is not a JBeam part or missing JBeam file path!")
        else:
            is_jbeam_part = True

        self.remove_custom_data_props(obj)

        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.0005)
        bpy.ops.object.mode_set(mode='OBJECT')

        if is_jbeam_part:

            self.parser = JbeamParser()
            try:
                self.parser.load_jbeam(jbeam_path)
                self.parser.parse_data_for_jbeam_object_conversion(obj)
            except Exception as e:
                self.report({'ERROR'}, f"Failed to read file: {e}")
                return {'CANCELLED'}

            nodes = self.parser.get_nodes()
            beams_list = self.parser.get_beams_list()
            tris_list = self.parser.get_triangles_list()
            #self.parser.debug_print_nodes()
            ref_nodes = self.parser.get_ref_nodes()
            self.assign_ref_nodes_to_vertex_groups(obj, ref_nodes, nodes)
            self.create_node_mesh_attributes(obj)
            self.store_node_props_in_vertex_attributes(obj)
            self.store_beam_props_in_edge_attributes(obj, beams_list)
            self.store_triangle_props_in_face_attributes(obj, tris_list)
        else:
            j.setup_default_scope_modifiers_and_node_ids(obj)

        bpy.ops.object.devtools_beamng_create_refnodes_vertex_groups()

        self.report({'INFO'}, f"Converted {obj.name} to Node Mesh!")
        return {'FINISHED'}
