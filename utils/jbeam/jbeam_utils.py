import bpy
import bmesh
import json
import os

from dev_tools.utils.file_utils import FileUtils # type: ignore

class JbeamUtils:

    ATTR_NODE_ID = "jbeam_node_id"
    ATTR_NODE_PROPS = "jbeam_node_props"

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
            if vertex_index >= len(bm.verts):
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
    def set_gn_jbeam_visualizer_selected_vertices(obj, vertex_group):
        modifier_name = "__gn_jbeam_visualizer_modifier"
        mod = obj.modifiers.get(modifier_name)
        if not mod:
            return
        for key in mod.keys():
            if key.endswith("_attribute_name"):
                print(f"Found attribute name: {key}")
                mod[key] = vertex_group

    @staticmethod
    def append_gn_jbeam_visualizer():
        blend_path = os.path.join(FileUtils.get_addon_root_dir(), "resources/blend/gn.blend")
        node_tree_name = "__gn_jbeam_visualizer"

        if node_tree_name in bpy.data.node_groups:
            print(f"Node tree '{node_tree_name}' already exists. Skipping append.")
            return

        if not os.path.exists(blend_path):
            print(f"Blend file not found: {blend_path}")
            return

        with bpy.data.libraries.load(blend_path, link=False) as (data_from, data_to):
            if node_tree_name in data_from.node_groups:
                data_to.node_groups.append(node_tree_name)
                print(f"Appended node tree: {node_tree_name}")

                # Ensure the node tree is not purged
                node_tree = bpy.data.node_groups.get(node_tree_name)
                if node_tree:
                    node_tree.use_fake_user = True
                    print(f"Enabled fake user for: {node_tree_name}")
            else:
                print(f"Node tree '{node_tree_name}' not found in {blend_path}")


    @staticmethod
    def add_gn_jbeam_visualizer_modifier(obj):
        modifier_name = "__gn_jbeam_visualizer_modifier"
        mod = obj.modifiers.get(modifier_name)
        if mod is None:
            mod = obj.modifiers.new(name=modifier_name, type='NODES')

        node_tree_name = "__gn_jbeam_visualizer"
        node_tree = bpy.data.node_groups.get(node_tree_name)
        if not node_tree:
            # need to re-append when Ctrl+Z was done after adding this modifier, use_fake_user does not prevent cleanup by blender from Ctrl+Z
            JbeamUtils.append_gn_jbeam_visualizer()
            node_tree = bpy.data.node_groups.get(node_tree_name)

        mod.node_group = node_tree
        print(f"Assigned '{node_tree_name}' to '{repr(obj)}'")
