import bpy
import bmesh
import os
import copy

from dev_tools.utils.file_utils import FileUtils  # type: ignore
from dev_tools.utils.object_utils import ObjectUtils  # type: ignore
from dev_tools.utils.jbeam.jbeam_props_storage import JbeamPropsStorage  # type: ignore

class JbeamUtils:

    ATTR_NODE_ID = "jbeam_node_id"
    ATTR_NODE_PROPS = "jbeam_node_props"
    ATTR_BEAM_PROPS = "jbeam_beam_props"
    ATTR_TRIANGLE_PROPS = "jbeam_triangle_props"
    ATTR_SELECTED_EDGES = "selected_edges"

    RESERVED_KEYWORDS = []

    GN_JBEAM_VISUALIZER_GROUP_NODE_NAME = "__gn_jbeam_visualizer"

    @staticmethod
    def has_jbeam_node_id(obj):
        return obj.type == 'MESH' and JbeamUtils.ATTR_NODE_ID in obj.data.attributes if obj else False

    @staticmethod
    def has_jbeam_node_props(obj):
        return obj.type == 'MESH' and JbeamUtils.ATTR_NODE_PROPS in obj.data.attributes if obj else False

    @staticmethod
    def has_jbeam_beam_props(obj):
        return obj.type == 'MESH' and JbeamUtils.ATTR_BEAM_PROPS in obj.data.attributes if obj else False

    def is_node_mesh(obj):
        return obj and JbeamUtils.has_jbeam_node_id(obj) and JbeamUtils.has_jbeam_node_props(obj) and JbeamUtils.has_jbeam_beam_props(obj)

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
    def create_attribute(obj, attr_name, type="STRING", domain="POINT"):
        if not obj or obj.type != 'MESH':
            print(f"Cannot add attribute '{attr_name}' to invalid object: {repr(obj)}")
            return None

        mesh = obj.data

        if attr_name in mesh.attributes:
            print(f"{repr(obj)}: already has attribute '{attr_name}'")
            return mesh.attributes[attr_name]

        return mesh.attributes.new(name=attr_name, type=type, domain=domain)

    @staticmethod
    def create_attribute_node_id(obj):
        return JbeamUtils.create_attribute(obj, JbeamUtils.ATTR_NODE_ID)

    @staticmethod
    def create_attribute_node_props(obj):
        return JbeamUtils.create_attribute(obj, JbeamUtils.ATTR_NODE_PROPS, domain="POINT")

    @staticmethod
    def create_attribute_beam_props(obj):
        return JbeamUtils.create_attribute(obj, JbeamUtils.ATTR_BEAM_PROPS, domain="EDGE")

    @staticmethod
    def create_attribute_triangle_props(obj):
        return JbeamUtils.create_attribute(obj, JbeamUtils.ATTR_TRIANGLE_PROPS, domain="FACE")

    @staticmethod
    def create_node_mesh_attributes(obj):
        JbeamUtils.create_attribute_node_id(obj) 
        JbeamUtils.create_attribute_node_props(obj)
        JbeamUtils.create_attribute_beam_props(obj)
        JbeamUtils.create_attribute_triangle_props(obj)

    @staticmethod
    def get_attribute_value(obj, index, attr_name, domain="verts") -> str:
        mesh = obj.data
        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(mesh)
            bm_data_map = {
                "verts": bm.verts,
                "edges": bm.edges,
                "faces": bm.faces
            }
            if domain in bm_data_map:
                bm_data_map[domain].ensure_lookup_table()
            else:
                print(f"{repr(obj)}: Unsupported domain '{domain}' in Edit Mode")
                return None
            
            bm_data = getattr(bm, domain, None)  # Access verts, edges, or faces dynamically

            if bm_data is None:
                print(f"{repr(obj)}: Unsupported domain '{domain}' in Edit Mode")
                return None

            num_elements = len(bm_data)
            if index >= num_elements or num_elements <= 0:
                print(f"{repr(obj)}: Index {index} out of range in Edit Mode ({domain})")
                return None

            element = bm_data[index]
            layer = bm_data.layers.string.get(attr_name)

            if layer is None:
                print(f"{repr(obj)}: Layer '{attr_name}' not found in Edit Mode ({domain})")
                return None

            return element[layer].decode('utf-8')

        elif obj.mode == 'OBJECT':
            if attr_name not in mesh.attributes:
                print(f"{repr(obj)}: Attribute '{attr_name}' not found in Object Mode ({domain})")
                return None

            attr_data = mesh.attributes[attr_name].data

            if index >= len(attr_data):
                print(f"{repr(obj)}: Index {index} out of range in Object Mode ({domain})")
                return None

            return attr_data[index].value.decode('utf-8')

        print(f"{repr(obj)}: Unknown object mode {obj.mode}")
        return None

    @staticmethod
    def get_node_id(obj, vertex_index, bm=None) -> str:
        return JbeamUtils.get_attribute_value(obj, vertex_index, JbeamUtils.ATTR_NODE_ID, 'verts')

    @staticmethod
    def get_beam_id(obj, edge_index, bm=None) -> str:
        if edge_index < 0:
            return None
        if bm is None:
            mesh = obj.data
            edge = mesh.edges[edge_index]
            v1, v2 = sorted(edge.vertices)
        else:
            edge = bm.edges[edge_index]
            v1, v2 = sorted(edge.verts, key=lambda v: v.index)
            v1, v2 = v1.index, v2.index
        n1 = JbeamUtils.get_node_id(obj, v1) or "?"
        n2 = JbeamUtils.get_node_id(obj, v2) or "?"
        return f"[{n1}|{n2}]"

    @staticmethod
    def get_triangle_id(obj, face_index, bm=None) -> str:
        if face_index < 0:
            return None
        if bm is None:
            mesh = obj.data
            face = mesh.polygons[face_index]
            verts = face.vertices  # Get all vertex indices of the face
        else:
            face = bm.faces[face_index]
            verts = [v.index for v in face.verts]  # Get all vertex indices

        node_ids = [JbeamUtils.get_node_id(obj, v) or "?" for v in verts]
        return f"[{'|'.join(node_ids)}]" # Format the result as "[id1|id2|id3|...]"

    @staticmethod
    def get_beam_node_ids(obj, edge_index) -> tuple[str, str]:
        edge = obj.data.edges[edge_index]
        v1_idx, v2_idx = sorted(edge.vertices)
        n1 = JbeamUtils.get_node_id(obj, v1_idx) or "?"
        n2 = JbeamUtils.get_node_id(obj, v2_idx) or "?"
        return n1, n2

    @staticmethod
    def get_triangle_node_ids(obj, face_index) -> tuple[str, str, str]:
        face = obj.data.polygons[face_index]
        v1_idx, v2_idx, v3_idx = sorted(face.vertices)
        n1 = JbeamUtils.get_node_id(obj, v1_idx) or "?"
        n2 = JbeamUtils.get_node_id(obj, v2_idx) or "?"
        n3 = JbeamUtils.get_node_id(obj, v3_idx) or "?"
        return n1, n2, n3

    @staticmethod
    def get_node_props(obj, vertex_index, instance=1) -> str:
        domain = "verts"
        key = JbeamUtils.get_attribute_value(obj, vertex_index, JbeamUtils.ATTR_NODE_PROPS, domain)
        return JbeamPropsStorage.get_instance().fetch_props(domain, key, instance)

    @staticmethod
    def get_beam_props(obj, edge_index, instance=1) -> str:
        domain = "edges"
        key = JbeamUtils.get_attribute_value(obj, edge_index, JbeamUtils.ATTR_BEAM_PROPS, domain)
        return JbeamPropsStorage.get_instance().fetch_props(domain, key, instance)

    @staticmethod
    def get_triangle_props(obj, face_index, instance=1) -> str:
        domain = "faces"
        key = JbeamUtils.get_attribute_value(obj, face_index, JbeamUtils.ATTR_TRIANGLE_PROPS, domain)
        return JbeamPropsStorage.get_instance().fetch_props(domain, key, instance)

    @staticmethod
    def set_node_props(obj, vertex_index, node_props: dict, instance=1):
        domain = "verts"
        key = JbeamUtils.get_attribute_value(obj, vertex_index, JbeamUtils.ATTR_NODE_PROPS, domain)
        key = JbeamPropsStorage.get_instance().store_props(domain, key, node_props, instance=instance)
        JbeamUtils.set_attribute_value(obj, vertex_index, JbeamUtils.ATTR_NODE_PROPS, key, domain=domain)

    @staticmethod
    def set_beam_props(obj, edge_index, beam_props: dict, instance: int=1):
        domain = "edges"
        key = JbeamUtils.get_attribute_value(obj, edge_index, JbeamUtils.ATTR_BEAM_PROPS, domain)
        key = JbeamPropsStorage.get_instance().store_props(domain, key, beam_props, instance=instance)
        # Update the Blender attribute with the (possibly new) key
        JbeamUtils.set_attribute_value(obj, edge_index, JbeamUtils.ATTR_BEAM_PROPS, key, domain=domain)

    @staticmethod
    def set_triangle_props(obj, face_index, triangle_props: dict, instance: int=1):
        domain = "faces"
        key = JbeamUtils.get_attribute_value(obj, face_index, JbeamUtils.ATTR_TRIANGLE_PROPS, domain)
        key = JbeamPropsStorage.get_instance().store_props(domain, key, triangle_props, instance=instance)
        JbeamUtils.set_attribute_value(obj, face_index, JbeamUtils.ATTR_TRIANGLE_PROPS, key, domain=domain)

    @staticmethod
    def delete_props(obj, domain, index, attr_name, instance: int=None):
        key = JbeamUtils.get_attribute_value(obj, index, attr_name, domain)
        if key:
            JbeamPropsStorage.get_instance().delete_props(domain, key, instance)
        else:
            print(f"Warning: key '{key}' does not exist")
        JbeamUtils.set_attribute_value(obj, index, attr_name, key, domain=domain)

    @staticmethod
    def delete_beam_props(obj, edge_index, instance: int=None):
        JbeamUtils.delete_props(obj, "edges", edge_index, JbeamUtils.ATTR_BEAM_PROPS, instance)

    @staticmethod
    def delete_triangle_props(obj, face_index, instance: int=None):
        JbeamUtils.delete_props(obj, "faces", face_index, JbeamUtils.ATTR_TRIANGLE_PROPS, instance)

    @staticmethod
    def get_total_beam_instances(obj, edge_index) -> str:
        domain = "edges"
        key = JbeamUtils.get_attribute_value(obj, edge_index, JbeamUtils.ATTR_BEAM_PROPS, domain)
        return JbeamPropsStorage.get_instance().get_total_instances(domain, key)

    @staticmethod
    def get_total_triangle_instances(obj, face_index) -> str:
        domain = "faces"
        key = JbeamUtils.get_attribute_value(obj, face_index, JbeamUtils.ATTR_TRIANGLE_PROPS, domain)
        return JbeamPropsStorage.get_instance().get_total_instances(domain, key)

    @staticmethod
    def validate_and_fix_storage_keys(obj, bm):
        """Ensures unique keys in attributes and fixes duplicates for each domain separately."""
        print("Running integrity check: Ensuring JBeam data storage consistency...")
        key_sets = {
            'verts': set(),
            'edges': set(),
            'faces': set(),
        }
        domains = {
            'verts': (bm.verts, JbeamUtils.ATTR_NODE_PROPS),
            'edges': (bm.edges, JbeamUtils.ATTR_BEAM_PROPS),
            'faces': (bm.faces, JbeamUtils.ATTR_TRIANGLE_PROPS),
        }
        modified = False
        for domain, (elements, attr_name) in domains.items():
            layer = elements.layers.string.get(attr_name)
            if not layer:
                continue
            for elem in elements:
                key = elem[layer].decode('utf-8') if elem[layer] else None
                if key and key in key_sets[domain]:
                    storage = JbeamPropsStorage.get_instance()
                    props = storage.fetch_props(domain, key)
                    new_key = storage.store_props(domain, None, copy.deepcopy(props))
                    elem[layer] = new_key.encode('utf-8')
                    print(f"Duplicate detected in domain '{domain}' for key '{key}'. Generated new key: '{new_key}'")
                    modified = True
                else:
                    key_sets[domain].add(key)
        if modified:
            bmesh.update_edit_mesh(obj.data)
        else:
            print("JBeam storage check complete: No duplicates found.")

    @staticmethod
    def set_attribute_value(obj, index: int, attr_name: str, attr_value: str, domain="verts", instance=1):
        mesh = obj.data

        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(mesh)
            bm_data = getattr(bm, domain)  # Access verts, edges, or faces dynamically

            if index >= len(bm_data):
                print(f"{repr(obj)}: Index {index} out of range in Edit Mode ({domain})")
                return False

            element = bm_data[index]
            layer = bm_data.layers.string.get(attr_name) or bm_data.layers.string.new(attr_name)

            element[layer] = attr_value.encode('utf-8')
            return True

        elif obj.mode == 'OBJECT':
            domain_map = {"verts": "POINT", "edges": "EDGE", "faces": "FACE"}

            if domain not in domain_map:
                print(f"{repr(obj)}: Unsupported domain '{domain}'")
                return False

            if attr_name not in mesh.attributes:
                mesh.attributes.new(name=attr_name, type='STRING', domain=domain_map[domain])

            attr_data = mesh.attributes[attr_name].data

            if index >= len(attr_data):
                print(f"{repr(obj)}: Index {index} out of range in Object Mode ({domain})")
                return False

            attr_data[index].value = attr_value.encode('utf-8')
            return True

        print(f"{repr(obj)}: Unknown object mode {obj.mode}")
        return False

    @staticmethod
    def set_node_id(obj, vertex_index, node_id: str):
        JbeamUtils.set_attribute_value(obj, vertex_index, JbeamUtils.ATTR_NODE_ID, node_id)

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
        JbeamUtils.create_node_mesh_attributes(obj)

        for vertex_idx in range(num_verts):
            JbeamUtils.set_node_id(obj, vertex_idx, node_ids[vertex_idx])
            JbeamUtils.set_node_props(obj, vertex_idx, node_props[vertex_idx])

    @staticmethod
    def set_jbeam_visuals(obj):
        if obj:
            #obj.show_wire = True
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
        node_tree = next((nt for nt in bpy.data.node_groups if nt.get(JbeamUtils.GN_JBEAM_VISUALIZER_GROUP_NODE_NAME) == JbeamUtils.GN_JBEAM_VISUALIZER_GROUP_NODE_NAME), None)
        if not node_tree:
            print("Error: Node tree not found. Cannot set selected vertices.")
            return None
        mod = next((m for m in obj.modifiers if m.type == 'NODES' and m.node_group == node_tree), None)
        if not mod:
            print("Error: Modifier using the node tree not found.")
        return mod

    @staticmethod
    def set_gn_jbeam_active_node_index(obj, vertex_index):
        JbeamUtils.set_gn_jbeam_socket_mode(obj, "Active Node Vertex Index", value=vertex_index)

    @staticmethod
    def set_gn_jbeam_active_beam_index(obj, edge_index):
        JbeamUtils.set_gn_jbeam_socket_mode(obj, "Active Beam Edge Index", value=edge_index)

    @staticmethod
    def set_gn_jbeam_active_triangle_index(obj, face_index):
        return # TODO: not sure if we need colored triangle faces for actively selected triangles, if yes then we have to add a socket to the GN modifier
        JbeamUtils.set_gn_jbeam_socket_mode(obj, "Active Triangle Face Index", value=face_index)

    @staticmethod
    def set_gn_jbeam_socket_mode(obj, socket_name, value=None, attribute_name=None):
        mod = JbeamUtils.get_gn_jbeam_modifier(obj)
        ObjectUtils.set_gn_socket_mode(mod, socket_name, value, attribute_name)

    @staticmethod
    def set_gn_jbeam_visualizer_selection_mode(obj):
        mode = next(i + 1 for i, v in enumerate(bpy.context.tool_settings.mesh_select_mode) if v) # 1 (vertex), 2 (edge), or 3 (edge)
        if JbeamUtils.get_gn_jbeam_visualizer_selection_mode(obj) == mode:
            return mode
        JbeamUtils.set_gn_jbeam_socket_mode(obj, "Selection Mode", value=mode)
        return mode

    @staticmethod
    def get_gn_jbeam_visualizer_selection_mode(obj):
        mod = JbeamUtils.get_gn_jbeam_modifier(obj)
        socket_value = ObjectUtils.get_gn_socket_mode(mod, "Selection Mode")
        return socket_value['value']

    @staticmethod
    def append_gn_jbeam_visualizer():
        blend_path = os.path.normpath(os.path.join(FileUtils.get_addon_root_dir(), "resources/blend/gn.blend"))
        #ng = ObjectUtils.gn_append_node_group(blend_path, JbeamUtils.GN_JBEAM_VISUALIZER_GROUP_NODE_NAME)
        ng = ObjectUtils.gn_link_node_group(blend_path, JbeamUtils.GN_JBEAM_VISUALIZER_GROUP_NODE_NAME)
        # mute Split Edges nodes due to bug https://projects.blender.org/blender/blender/issues/121619
        #ng.nodes.get('gn_beams_unselected_split_edges_node').mute = False
        #ng.nodes.get('gn_beams_selected_split_edges_node').mute = False

        for mat in bpy.data.materials:
            if mat.name.startswith("mat_jbeam_"):
                mat.use_backface_culling = True

    @staticmethod
    def add_gn_jbeam_visualizer_modifier(obj):
        # Find the node tree by attribute instead of name
        group_node_name = JbeamUtils.GN_JBEAM_VISUALIZER_GROUP_NODE_NAME
        node_tree = next((nt for nt in bpy.data.node_groups if nt.get(group_node_name) == group_node_name), None)

        if not node_tree:
            JbeamUtils.append_gn_jbeam_visualizer() # Re-append only if the node tree does not exist
            node_tree = next((nt for nt in bpy.data.node_groups if nt.get(group_node_name) == group_node_name), None)

        if not node_tree:
            print("Error: Node tree could not be found or appended.")
            return

        # Check if any existing modifier is already using this node tree
        for mod in obj.modifiers:
            if mod.type == 'NODES' and mod.node_group == node_tree:
                print(f"Modifier '{mod.name}' already uses '{node_tree.name}'. Skipping add.")
                return  # Modifier already exists, exit function

        modifier_name = JbeamUtils.GN_JBEAM_VISUALIZER_GROUP_NODE_NAME + "_modifier"
        mod = obj.modifiers.new(name=modifier_name, type='NODES')
        mod.node_group = node_tree
        ObjectUtils.gn_hide_modifier_input_by_name(node_tree, "Selection Mode")
        ObjectUtils.gn_hide_modifier_input_by_name(node_tree, "Active Node Vertex Index")
        ObjectUtils.gn_hide_modifier_input_by_name(node_tree, "Active Beam Edge Index")
        JbeamUtils.set_gn_jbeam_visualizer_selection_mode(obj)

        print(f"Assigned '{node_tree.name}' to '{repr(obj)}' via modifier '{mod.name}'")
