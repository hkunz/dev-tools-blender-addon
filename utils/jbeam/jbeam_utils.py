import bpy
import bmesh
import json
import re
import os

from dev_tools.utils.file_utils import FileUtils # type: ignore
from dev_tools.utils.object_utils import ObjectUtils # type: ignore

class JbeamUtils:

    ATTR_NODE_ID = "jbeam_node_id"
    ATTR_NODE_PROPS = "jbeam_node_props"

    VG_SELECTED_VERTICES = "selected_vertices"

    GN_JBEAM_VISUALIZER_ATTR = "jbeam_visualizer_id"
    GN_JBEAM_VISUALIZER_ATTR_VALUE = "__gn_jbeam_visualizer"

    @staticmethod
    def has_jbeam_node_id(obj):
        return JbeamUtils.ATTR_NODE_ID in obj.data.attributes if obj else False

    @staticmethod
    def has_jbeam_node_props(obj):
        return JbeamUtils.ATTR_NODE_PROPS in obj.data.attributes if obj else False

    def is_node_mesh(obj):
        return JbeamUtils.has_jbeam_node_id(obj) and JbeamUtils.has_jbeam_node_props(obj)

    @staticmethod
    def remove_old_jbeam_attributes(obj):
        if not obj or obj.type != 'MESH':
            print(f"Cannot remove attributes from invalid object: {repr(obj)}")
            return

        mesh = obj.data
        attributes_to_remove = [attr.name for attr in mesh.attributes if attr.name.startswith("jbeam_")]

        for attr_name in attributes_to_remove:
            mesh.attributes.remove(mesh.attributes[attr_name])
            print(f"Removed attribute '{attr_name}' from {repr(obj)}")

    @staticmethod
    def create_attribute(obj, attr_name):
        if not obj or obj.type != 'MESH':
            print(f"Cannot add attribute '{attr_name}' to invalid object: {repr(obj)}")
            return None

        mesh = obj.data

        if attr_name in mesh.attributes:
            print(f"{repr(obj)}: already has attribute '{attr_name}'")
            return mesh.attributes[attr_name]

        return mesh.attributes.new(name=attr_name, type="STRING", domain="POINT")

    @staticmethod
    def create_attribute_node_id(obj):
        return JbeamUtils.create_attribute(obj, JbeamUtils.ATTR_NODE_ID)

    @staticmethod
    def create_attribute_node_props(obj):
        return JbeamUtils.create_attribute(obj, "jbeam_node_props")

    @staticmethod
    def get_attribute_value(obj, vertex_index, attr_name) -> str:

        if not obj or obj.type != 'MESH':
            print(f"Invalid object: {repr(obj)}")
            return None

        mesh = obj.data

        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(mesh)
            num_verts = len(bm.verts)
            if vertex_index >= num_verts or num_verts <= 0:
                print(f"{repr(obj)}: Vertex index {vertex_index} out of range in Edit Mode")
                return None

            v = bm.verts[vertex_index]
            layer = bm.verts.layers.string.get(attr_name)

            if layer is None:
                print(f"{repr(obj)}: Layer '{attr_name}' not found in Edit Mode")
                return None

            return v[layer].decode('utf-8')

        elif obj.mode == 'OBJECT':
            if attr_name not in mesh.attributes:
                print(f"{repr(obj)}: Attribute '{attr_name}' not found in Object Mode")
                return None

            attr_data = mesh.attributes[attr_name].data

            if vertex_index >= len(attr_data):
                print(f"{repr(obj)}: Vertex index {vertex_index} out of range in Object Mode")
                return None

            return attr_data[vertex_index].value.decode('utf-8')

        print(f"{repr(obj)}: Unknown object mode {obj.mode}")
        return None

    @staticmethod
    def get_node_id(obj, vertex_index) -> str:
        return JbeamUtils.get_attribute_value(obj, vertex_index, JbeamUtils.ATTR_NODE_ID)

    @staticmethod
    def get_node_props_str(obj, vertex_index) -> str:
        return JbeamUtils.get_attribute_value(obj, vertex_index, JbeamUtils.ATTR_NODE_PROPS)

    @staticmethod
    def get_node_props(obj, vertex_index) -> dict:
        props_str = JbeamUtils.get_node_props_str(obj, vertex_index)
        try:
            return json.loads(props_str) if props_str else {}
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON at vertex {vertex_index}")
            return {}

    @staticmethod
    def set_attribute_value(obj, vertex_index: int, attr_name: str, attr_value: str):

        if not obj or obj.type != 'MESH':
            print(f"Invalid object: {repr(obj)}")
            return False

        mesh = obj.data

        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(mesh)
            if vertex_index >= len(bm.verts):
                print(f"{repr(obj)}: Vertex index {vertex_index} out of range in Edit Mode")
                return False

            v = bm.verts[vertex_index]
            layer = bm.verts.layers.string.get(attr_name) or bm.verts.layers.string.new(attr_name)

            v[layer] = attr_value.encode('utf-8')
            return True

        elif obj.mode == 'OBJECT':
            if attr_name not in mesh.attributes:
                mesh.attributes.new(name=attr_name, type='STRING', domain='POINT')

            attr_data = mesh.attributes[attr_name].data

            if vertex_index >= len(attr_data):
                print(f"{repr(obj)}: Vertex index {vertex_index} out of range in Object Mode")
                return False

            attr_data[vertex_index].value = attr_value.encode('utf-8')
            return True

        print(f"{repr(obj)}: Unknown object mode {obj.mode}")
        return False

    @staticmethod
    def set_node_id(obj, vertex_index, node_id: str):
        JbeamUtils.set_attribute_value(obj, vertex_index, JbeamUtils.ATTR_NODE_ID, node_id)

    @staticmethod
    def set_node_props(obj, vertex_index, node_props: dict):
        JbeamUtils.set_attribute_value(obj, vertex_index, JbeamUtils.ATTR_NODE_PROPS, json.dumps(node_props))

    @staticmethod
    def setup_default_scope_modifiers_and_node_ids(obj):
        num_verts = len(obj.data.vertices)
        node_ids = {i: f"n{i+1}" for i in range(num_verts)}
        node_props = {
            i: {
                "collision": "true",
                "selfCollision": "false",
                "frictionCoef": 1.2,
                "nodeMaterial": "|NM_METAL",
                "nodeWeight": (1 + i)
            }
            for i in range(num_verts)
        }
        JbeamUtils.create_attribute_node_id(obj) 
        JbeamUtils.create_attribute_node_props(obj)
        for vertex_idx in range(num_verts):
            JbeamUtils.set_node_id(obj, vertex_idx, node_ids[vertex_idx])
            JbeamUtils.set_node_props(obj, vertex_idx, node_props[vertex_idx])

    @staticmethod
    def set_jbeam_visuals(obj):
        if obj:
            obj.show_wire = True
            obj.color = (0.0, 1.0, 0.0, 1.0)  # RGBA, Green with full opacity

        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.wireframe_color_type = 'OBJECT'

    @staticmethod
    def get_required_vertex_group_names(minimal=True) -> list[str]:
        return ["up", "left", "back"] if minimal else ["up", "left", "back", "leftCorner", "rightCorner"]

    @staticmethod
    def get_gn_jbeam_modifier(obj):
        # Find the node tree by attribute
        node_tree = next((nt for nt in bpy.data.node_groups if nt.get(JbeamUtils.GN_JBEAM_VISUALIZER_ATTR) == JbeamUtils.GN_JBEAM_VISUALIZER_ATTR_VALUE), None)
        if not node_tree:
            print("Error: Node tree not found. Cannot set selected vertices.")
            return None
        mod = next((m for m in obj.modifiers if m.type == 'NODES' and m.node_group == node_tree), None)
        if not mod:
            print("Error: Modifier using the node tree not found.")
        return mod

    @staticmethod
    def set_gn_jbeam_socket_mode(obj, socket_name, value=None, attribute_name=None):
        mod = JbeamUtils.get_gn_jbeam_modifier(obj)
        ObjectUtils.set_gn_socket_mode(mod, socket_name, value, attribute_name)

    @staticmethod
    def set_gn_jbeam_visualizer_selection_mode(obj):
        mode = next(i + 1 for i, v in enumerate(bpy.context.tool_settings.mesh_select_mode) if v) # 1 (vertex), 2 (edge), or 3 (edge)
        JbeamUtils.set_gn_jbeam_socket_mode(obj, "Selection Mode", value=mode)
        #bpy.context.object.data.update()

    @staticmethod
    def set_gn_jbeam_visualizer_selected_vertices(obj):
        JbeamUtils.set_gn_jbeam_socket_mode(obj, "Selection", attribute_name=JbeamUtils.VG_SELECTED_VERTICES)
        #bpy.context.object.data.update()

    @staticmethod
    def append_gn_jbeam_visualizer():
        blend_path = os.path.join(FileUtils.get_addon_root_dir(), "resources/blend/gn.blend")
        existing_node_tree = next((nt for nt in bpy.data.node_groups if nt.get(JbeamUtils.GN_JBEAM_VISUALIZER_ATTR) == JbeamUtils.GN_JBEAM_VISUALIZER_ATTR_VALUE), None)

        if existing_node_tree:
            print(f"Node tree '{existing_node_tree.name}' already exists. Skipping append.")
            return

        if not os.path.exists(blend_path):
            print(f"Blend file not found: {blend_path}")
            return

        with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
            if JbeamUtils.GN_JBEAM_VISUALIZER_ATTR_VALUE in data_from.node_groups:
                data_to.node_groups.append(JbeamUtils.GN_JBEAM_VISUALIZER_ATTR_VALUE)
                print(f"Appended node tree: {JbeamUtils.GN_JBEAM_VISUALIZER_ATTR_VALUE}")

        # Find the newly appended node tree, even if renamed using custom attribute
        appended_node_tree = next((nt for nt in bpy.data.node_groups if JbeamUtils.GN_JBEAM_VISUALIZER_ATTR_VALUE in nt.name), None)

        if appended_node_tree:
            appended_node_tree.use_fake_user = True
            appended_node_tree[JbeamUtils.GN_JBEAM_VISUALIZER_ATTR] = JbeamUtils.GN_JBEAM_VISUALIZER_ATTR_VALUE  # Store unique ID in case node group is renamed so it can still be found
            print(f"Enabled fake user and set attribute for: {appended_node_tree.name}")
        else:
            print(f"Error: Node tree '{JbeamUtils.GN_JBEAM_VISUALIZER_ATTR_VALUE}' not found after append.")

    @staticmethod
    def add_gn_jbeam_visualizer_modifier(obj):
        # Find the node tree by attribute instead of name
        node_tree = next((nt for nt in bpy.data.node_groups if nt.get(JbeamUtils.GN_JBEAM_VISUALIZER_ATTR) == JbeamUtils.GN_JBEAM_VISUALIZER_ATTR_VALUE), None)

        if not node_tree:
            # Re-append only if the node tree does not exist
            JbeamUtils.append_gn_jbeam_visualizer()
            node_tree = next((nt for nt in bpy.data.node_groups if nt.get(JbeamUtils.GN_JBEAM_VISUALIZER_ATTR) == JbeamUtils.GN_JBEAM_VISUALIZER_ATTR_VALUE), None)

        if not node_tree:
            print("Error: Node tree could not be found or appended.")
            return

        # Check if any existing modifier is already using this node tree
        for mod in obj.modifiers:
            if mod.type == 'NODES' and mod.node_group == node_tree:
                print(f"Modifier '{mod.name}' already uses '{node_tree.name}'. Skipping add.")
                return  # Modifier already exists, exit function

        modifier_name = "__gn_jbeam_visualizer_modifier"
        mod = obj.modifiers.new(name=modifier_name, type='NODES')
        mod.node_group = node_tree
        JbeamUtils.set_gn_jbeam_visualizer_selection_mode(obj)
        JbeamUtils.set_gn_jbeam_visualizer_selected_vertices(obj)

        print(f"Assigned '{node_tree.name}' to '{repr(obj)}' via modifier '{mod.name}'")
