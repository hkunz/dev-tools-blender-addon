import bpy
import bmesh
import os
import copy
import logging

from enum import Enum
from typing import Union

from unofficial_jbeam_editor.ui.addon_preferences import MyAddonPreferences as a
from unofficial_jbeam_editor.utils.file_utils import FileUtils
from unofficial_jbeam_editor.utils.object_utils import ObjectUtils
from unofficial_jbeam_editor.utils.jbeam.jbeam_props_storage import JbeamPropsStorage, JbeamPropsStorageManager

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
            logging.debug(f"Cannot remove attributes from invalid object: {repr(obj)}")
            return

        mesh = obj.data
        attributes_to_remove = [attr.name for attr in mesh.attributes if attr.name.startswith("jbeam_")]

        for attr_name in attributes_to_remove:
            mesh.attributes.remove(mesh.attributes[attr_name])
            logging.debug(f"Removed attribute '{attr_name}' from {repr(obj)}")

    @staticmethod
    def create_attribute(obj, attr_name, type="STRING", domain="POINT"):
        if not obj or obj.type != 'MESH':
            logging.debug(f"Cannot add attribute '{attr_name}' to invalid object: {repr(obj)}")
            return None

        mesh = obj.data

        if attr_name in mesh.attributes:
            logging.debug(f"{repr(obj)}: already has attribute '{attr_name}'")
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
        JbeamRefnodeUtils.create_attribute_refnode(obj)

    @staticmethod
    def get_attribute_value(obj, index, attr_name, domain="verts") -> str | int | None:
        mesh = obj.data

        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(mesh)
            bm_data = getattr(bm, domain, None)

            if not bm_data:
                logging.error(f"{repr(obj)}: Unsupported domain '{domain}' in Edit Mode")
                return None

            bm_data.ensure_lookup_table()

            if index >= len(bm_data):
                logging.error(f"{repr(obj)}: Index {index} out of range in Edit Mode ({domain})")
                return None

            element = bm_data[index]
            layer = bm_data.layers.string.get(attr_name) or bm_data.layers.int.get(attr_name)
            if not layer:
                logging.error(f"{repr(obj)}: Layer '{attr_name}' not found in Edit Mode ({domain})")
                return None

            value = element[layer]
            return value.decode('utf-8') if isinstance(value, bytes) else value

        elif obj.mode == 'OBJECT':
            attr = mesh.attributes.get(attr_name)
            if not attr:
                logging.error(f"{repr(obj)}: Attribute '{attr_name}' not found in Object Mode ({domain})")
                return None

            attr_data = attr.data
            if index >= len(attr_data):
                logging.error(f"Get:{repr(obj)}: Index {index} out of range in Object Mode ({domain})")
                return None

            value = attr_data[index].value
            return value.decode('utf-8') if isinstance(value, bytes) else value

        logging.error(f"{repr(obj)}: Unknown object mode '{obj.mode}'")
        return None

    @staticmethod
    def find_elements_with_attribute_value(obj, attr_name, attr_value, domain="verts", bm=None) -> list[int]:
        """Finds the indices of elements (vertices, edges, or faces) with a specific attribute value."""
        mesh = obj.data
        matching_element_indices = []

        if obj.mode == 'EDIT':
            # If bm is not provided, get the current bmesh from the mesh
            if not bm:
                bm = bmesh.from_edit_mesh(obj.data)
            
            bm_data = getattr(bm, domain, None)
            if not bm_data:
                logging.error(f"{repr(obj)}: Unsupported domain '{domain}' in Edit Mode")
                return []

            bm_data.ensure_lookup_table()

            string_layer = bm_data.layers.string.get(attr_name)
            int_layer = bm_data.layers.int.get(attr_name)

            # Iterate through each element in the bm_data (verts, edges, or faces)
            for idx, element in enumerate(bm_data):
                value = None
                if string_layer:
                    value = element[string_layer].decode('utf-8')
                elif int_layer:
                    value = element[int_layer]

                if value == attr_value:
                    matching_element_indices.append(idx)  # Append the index of the element

        elif obj.mode == 'OBJECT':
            if attr_name not in mesh.attributes:
                logging.debug(f"{repr(obj)}: Attribute '{attr_name}' not found in Object Mode ({domain})")
                return []

            attr_data = mesh.attributes[attr_name].data

            # In OBJECT mode, we cannot directly access BMVerts, BMEdges, or BMFaces, 
            # but we can lookup the index of the element and retrieve them by index from the mesh.
            for idx, entry in enumerate(attr_data):
                value = entry.value
                if isinstance(value, bytes):
                    value = value.decode('utf-8')

                if value == attr_value:
                    matching_element_indices.append(idx)  # Append the index of the element

        else:
            logging.error(f"{repr(obj)}: Unknown object mode '{obj.mode}'")

        return matching_element_indices


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
        return JbeamUtils.format_node_ids(n1, n2)

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
        return JbeamUtils.format_node_ids(*node_ids)

    @staticmethod
    def format_node_ids(*node_ids):
        return f"[{'|'.join(sorted(map(lambda x: x or '?', node_ids)))}]"  # Format the result as "[id1|id2|id3|...]"

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
        v1_idx, v2_idx, v3_idx = face.vertices
        n1 = JbeamUtils.get_node_id(obj, v1_idx) or "?"
        n2 = JbeamUtils.get_node_id(obj, v2_idx) or "?"
        n3 = JbeamUtils.get_node_id(obj, v3_idx) or "?"
        return n1, n2, n3

    @staticmethod
    def get_node_props(obj, vertex_index, instance=1) -> str:
        domain = "verts"
        key = JbeamUtils.get_attribute_value(obj, vertex_index, JbeamUtils.ATTR_NODE_PROPS, domain)
        storage_inst: JbeamPropsStorage = JbeamPropsStorageManager.get_instance().get_props_storage(obj)
        return storage_inst.fetch_props(domain, key, instance)

    @staticmethod
    def get_beam_props(obj, edge_index, instance=1) -> str:
        domain = "edges"
        key = JbeamUtils.get_attribute_value(obj, edge_index, JbeamUtils.ATTR_BEAM_PROPS, domain)
        storage_inst: JbeamPropsStorage = JbeamPropsStorageManager.get_instance().get_props_storage(obj)
        return storage_inst.fetch_props(domain, key, instance)

    @staticmethod
    def get_triangle_props(obj, face_index, instance=1) -> str:
        domain = "faces"
        key = JbeamUtils.get_attribute_value(obj, face_index, JbeamUtils.ATTR_TRIANGLE_PROPS, domain)
        storage_inst: JbeamPropsStorage = JbeamPropsStorageManager.get_instance().get_props_storage(obj)
        return storage_inst.fetch_props(domain, key, instance)

    @staticmethod
    def set_node_props(obj, vertex_index, node_props: dict, instance=1) -> bool:
        domain = "verts"
        key = JbeamUtils.get_attribute_value(obj, vertex_index, JbeamUtils.ATTR_NODE_PROPS, domain)
        storage_inst: JbeamPropsStorage = JbeamPropsStorageManager.get_instance().get_props_storage(obj)
        key = storage_inst.store_props(domain, key, node_props, instance=instance)
        return JbeamUtils.set_attribute_value(obj, vertex_index, JbeamUtils.ATTR_NODE_PROPS, key, domain=domain)

    @staticmethod
    def set_beam_props(obj, edge_index, beam_props: dict, instance: int=1) -> bool:
        domain = "edges"
        key = JbeamUtils.get_attribute_value(obj, edge_index, JbeamUtils.ATTR_BEAM_PROPS, domain)
        storage_inst: JbeamPropsStorage = JbeamPropsStorageManager.get_instance().get_props_storage(obj)
        key = storage_inst.store_props(domain, key, beam_props, instance=instance)
        # Update the Blender attribute with the (possibly new) key
        return JbeamUtils.set_attribute_value(obj, edge_index, JbeamUtils.ATTR_BEAM_PROPS, key, domain=domain)

    @staticmethod
    def set_triangle_props(obj, face_index, triangle_props: dict, instance: int=1) -> bool:
        domain = "faces"
        key = JbeamUtils.get_attribute_value(obj, face_index, JbeamUtils.ATTR_TRIANGLE_PROPS, domain)
        storage_inst: JbeamPropsStorage = JbeamPropsStorageManager.get_instance().get_props_storage(obj)
        key = storage_inst.store_props(domain, key, triangle_props, instance=instance)
        return JbeamUtils.set_attribute_value(obj, face_index, JbeamUtils.ATTR_TRIANGLE_PROPS, key, domain=domain)

    @staticmethod
    def delete_props(obj, domain, index, attr_name, instance: int=None) -> bool:
        key = JbeamUtils.get_attribute_value(obj, index, attr_name, domain)
        if key:
            storage_inst: JbeamPropsStorage = JbeamPropsStorageManager.get_instance().get_props_storage(obj)
            storage_inst.delete_props(domain, key, instance)
        else:
            logging.debug(f"⚠️  Warning: key '{key}' does not exist")
        return JbeamUtils.set_attribute_value(obj, index, attr_name, key, domain=domain)

    @staticmethod
    def delete_beam_props(obj, edge_index, instance: int=None):
        JbeamUtils.delete_props(obj, "edges", edge_index, JbeamUtils.ATTR_BEAM_PROPS, instance)

    @staticmethod
    def delete_triangle_props(obj, face_index, instance: int=None):
        JbeamUtils.delete_props(obj, "faces", face_index, JbeamUtils.ATTR_TRIANGLE_PROPS, instance)

    @staticmethod
    def get_total_node_instances(obj, vertex_index) -> str:
        return 1

    @staticmethod
    def get_total_beam_instances(obj, edge_index) -> str:
        domain = "edges"
        key = JbeamUtils.get_attribute_value(obj, edge_index, JbeamUtils.ATTR_BEAM_PROPS, domain)
        storage_inst: JbeamPropsStorage = JbeamPropsStorageManager.get_instance().get_props_storage(obj)
        return storage_inst.get_total_instances(domain, key)

    @staticmethod
    def get_total_triangle_instances(obj, face_index) -> str:
        domain = "faces"
        key = JbeamUtils.get_attribute_value(obj, face_index, JbeamUtils.ATTR_TRIANGLE_PROPS, domain)
        storage_inst: JbeamPropsStorage = JbeamPropsStorageManager.get_instance().get_props_storage(obj)
        return storage_inst.get_total_instances(domain, key)

    @staticmethod
    def validate_and_fix_storage_keys(obj, bm):
        """Ensures unique keys in attributes and fixes duplicates for each domain separately."""
        logging.debug("🔎 Running integrity check: Ensuring JBeam data storage consistency...")
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
        storage_inst: JbeamPropsStorage = JbeamPropsStorageManager.get_instance().get_props_storage(obj)
        for domain, (elements, attr_name) in domains.items():
            layer = elements.layers.string.get(attr_name)
            if not layer:
                continue
            for elem in elements:
                key = elem[layer].decode('utf-8') if elem[layer] else None
                if key and key in key_sets[domain]:
                    props = storage_inst.fetch_props(domain, key)
                    new_key = storage_inst.store_props(domain, None, copy.deepcopy(props))
                    elem[layer] = new_key.encode('utf-8')
                    logging.debug(f"🔧 Duplicate detected in domain '{domain}' for key '{key}'. Generated new key: '{new_key}'")
                    modified = True
                else:
                    key_sets[domain].add(key)
        if modified:
            bmesh.update_edit_mesh(obj.data)
        else:
            logging.debug("JBeam storage check complete: No duplicates found.")

    @staticmethod
    def set_attribute_value(obj, index: int, attr_name: str, attr_value: str | int, domain="verts", alert_error=True) -> bool:
        mesh = obj.data

        # Handle 'EDIT' mode
        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(mesh)
            bm_data = getattr(bm, domain)  # Access verts, edges, or faces dynamically

            if index >= len(bm_data):
                logging.warning(f"{repr(obj)}: Index {index} out of range in Edit Mode ({domain})")
                return False

            element = bm_data[index]
            if isinstance(attr_value, str):  # For string values
                layer = bm_data.layers.string.get(attr_name) or bm_data.layers.string.new(attr_name)
                element[layer] = attr_value.encode('utf-8')
            elif isinstance(attr_value, int):  # For integer values
                layer = bm_data.layers.int.get(attr_name) or bm_data.layers.int.new(attr_name)
                element[layer] = attr_value
            else:
                logging.error(f"{repr(obj)}: Unsupported attribute value type")
                return False
            return True

        # Handle 'OBJECT' mode
        elif obj.mode == 'OBJECT':
            domain_map = {"verts": "POINT", "edges": "EDGE", "faces": "FACE"}

            if domain not in domain_map:
                logging.error(f"{repr(obj)}: Unsupported domain '{domain}'")
                return False

            if attr_name not in mesh.attributes:
                # Define the attribute as integer for 'verts' if it's not present
                if isinstance(attr_value, int):
                    mesh.attributes.new(name=attr_name, type='INT', domain=domain_map[domain])
                else:
                    mesh.attributes.new(name=attr_name, type='STRING', domain=domain_map[domain])

            attr_data = mesh.attributes[attr_name].data

            if index >= len(attr_data):
                if alert_error:
                    logging.error(f"Set:{repr(obj)}: Try set '{attr_name}' with value '{attr_value}' failed with: Index {index} out of range in Object Mode ({domain})")
                return False

            if isinstance(attr_value, str):  # For string values
                attr_data[index].value = attr_value.encode('utf-8')
            elif isinstance(attr_value, int):  # For integer values
                attr_data[index].value = attr_value
            else:
                logging.error(f"{repr(obj)}: Unsupported attribute value type")
                return False

            return True

        logging.error(f"{repr(obj)}: Unknown object mode {obj.mode}")
        return False


    @staticmethod
    def set_node_id(obj, vertex_index, node_id: str) -> bool:
        return JbeamUtils.set_attribute_value(obj, vertex_index, JbeamUtils.ATTR_NODE_ID, node_id)

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
        if not a.is_addon_visualizer_enabled():
            return None
        # Find the node tree by attribute
        node_tree = next((nt for nt in bpy.data.node_groups if nt.get(JbeamUtils.GN_JBEAM_VISUALIZER_GROUP_NODE_NAME) == JbeamUtils.GN_JBEAM_VISUALIZER_GROUP_NODE_NAME), None)
        if not node_tree:
            logging.debug("❌ Error: Node tree not found. Cannot set selected vertices.")
            return None
        mod = next((m for m in obj.modifiers if m.type == 'NODES' and m.node_group == node_tree), None)
        if not mod:
            pass #logging.debug("❌ Error: Modifier using the node tree not found.")
        return mod

    @staticmethod
    def set_gn_jbeam_active_node_index(obj, vertex_index):
        JbeamUtils.set_gn_jbeam_socket_value(obj, "Active Node Vertex Index", value=vertex_index)

    @staticmethod
    def set_gn_jbeam_active_beam_index(obj, edge_index):
        JbeamUtils.set_gn_jbeam_socket_value(obj, "Active Beam Edge Index", value=edge_index)

    @staticmethod
    def set_gn_jbeam_active_triangle_index(obj, face_index):
        return # TODO: not sure if we need colored triangle faces for actively selected triangles, if yes then we have to add a socket to the GN modifier
        JbeamUtils.set_gn_jbeam_socket_value(obj, "Active Triangle Face Index", value=face_index)

    @staticmethod
    def set_gn_jbeam_socket_value(obj, socket_name, value=None, attribute_name=None):
        if not a.is_addon_visualizer_enabled():
            return
        mod = JbeamUtils.get_gn_jbeam_modifier(obj)
        if not mod:
            return
        ObjectUtils.set_gn_socket_value(mod, socket_name, value, attribute_name)

    @staticmethod
    def set_gn_jbeam_visualizer_selection_mode(obj):
        if not JbeamUtils.get_gn_jbeam_modifier(obj):
            return ObjectUtils.get_selection_mode()
        mode = next(i + 1 for i, v in enumerate(bpy.context.tool_settings.mesh_select_mode) if v) # 1 (vertex), 2 (edge), or 3 (edge)
        if JbeamUtils.get_gn_jbeam_visualizer_selection_mode(obj) == mode:
            return mode
        JbeamUtils.set_gn_jbeam_socket_value(obj, "Selection Mode", value=mode)
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
        if not a.is_addon_visualizer_enabled():
            return None
        # Find the node tree by attribute instead of name
        group_node_name = JbeamUtils.GN_JBEAM_VISUALIZER_GROUP_NODE_NAME
        node_tree = next((nt for nt in bpy.data.node_groups if nt.get(group_node_name) == group_node_name), None)

        if not node_tree:
            JbeamUtils.append_gn_jbeam_visualizer() # Re-append only if the node tree does not exist
            node_tree = next((nt for nt in bpy.data.node_groups if nt.get(group_node_name) == group_node_name), None)

        if not node_tree:
            logging.debug("❌ Error: Node tree could not be found or appended.")
            return

        # Check if any existing modifier is already using this node tree
        for mod in obj.modifiers:
            if mod.type == 'NODES' and mod.node_group == node_tree:
                logging.debug(f"Modifier '{mod.name}' already uses '{node_tree.name}'. Skipping add.")
                return  # Modifier already exists, exit function

        modifier_name = JbeamUtils.GN_JBEAM_VISUALIZER_GROUP_NODE_NAME + "_modifier"
        mod = obj.modifiers.new(name=modifier_name, type='NODES')
        mod.node_group = node_tree
        ObjectUtils.gn_hide_modifier_input_by_name(node_tree, "Selection Mode")
        ObjectUtils.gn_hide_modifier_input_by_name(node_tree, "Active Node Vertex Index")
        ObjectUtils.gn_hide_modifier_input_by_name(node_tree, "Active Beam Edge Index")
        JbeamUtils.set_gn_jbeam_socket_value(obj, "Node Radius", 0.03)
        JbeamUtils.set_gn_jbeam_socket_value(obj, "Beam Radius", 0.008)
        JbeamUtils.set_gn_jbeam_visualizer_selection_mode(obj)

        logging.debug(f"Assigned '{node_tree.name}' to '{repr(obj)}' via modifier '{mod.name}'")

    @staticmethod
    def get_indices_by_id(obj, target_id, domain, attr_name) -> list[int]:
        mesh = obj.data
        indices = []  # List to store matching indices

        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(mesh)
            bm_data = getattr(bm, domain, None)
            if bm_data:
                bm_data.ensure_lookup_table()
            else:
                logging.error(f"{obj!r}: Unsupported domain '{domain}' in Edit Mode")
                return []

            # Iterate through elements and check for the ID
            for index, element in enumerate(bm_data):
                layer = bm_data.layers.string.get(attr_name)
                if layer is None:
                    logging.error(f"{repr(obj)}: Layer '{attr_name}' not found in Edit Mode ({domain})")
                    return []

                if element[layer].decode('utf-8') == target_id:
                    indices.append(index)  # Add index to the list

            if not indices:
                logging.error(f"{repr(obj)}: {attr_name} '{target_id}' not found in Edit Mode ({domain})")
            return indices

        elif obj.mode == 'OBJECT':
            if attr_name not in mesh.attributes:
                logging.debug(f"{repr(obj)}: Attribute '{attr_name}' not found in Object Mode ({domain})")
                return []

            attr_data = mesh.attributes[attr_name].data

            # Iterate through elements and check for the ID
            for index, data in enumerate(attr_data):
                if data.value.decode('utf-8') == target_id:
                    indices.append(index)  # Add index to the list

            if not indices:
                logging.debug(f"{repr(obj)}: {attr_name} '{target_id}' not found in Object Mode ({domain})")
            return indices

        logging.error(f"{repr(obj)}: Unknown object mode {obj.mode}")
        return []

    @staticmethod
    def get_beam_indices(obj, node_id1, node_id2, bm=None):
        """
        Get the indices of the beams defined by two node IDs (node_id1, node_id2).
        """
        # List to store matching indices
        indices = []

        # Iterate through all the edges in the mesh
        mesh = obj.data
        if obj.mode == 'EDIT':
            if not bm:
                bm = bmesh.from_edit_mesh(mesh)
                bm.edges.ensure_lookup_table()
            bm_data = bm.edges
        elif obj.mode == 'OBJECT':
            bm_data = mesh.edges
        else:
            logging.error(f"{repr(obj)}: Unknown object mode {obj.mode}")
            return []

        # Iterate through all edges (beams)
        for index, edge in enumerate(bm_data):
            v1, v2 = sorted(edge.verts, key=lambda v: v.index)
            n1 = JbeamUtils.get_node_id(obj, v1.index)
            n2 = JbeamUtils.get_node_id(obj, v2.index)
            # Check if the node IDs match
            if {n1, n2} == {node_id1, node_id2}:
                indices.append(index)  # Add index to the list if the IDs match

        if not indices:
            logging.debug(f"{repr(obj)}: Beam with node IDs '{node_id1}' and '{node_id2}' not found")
        
        return indices  # Return all matching indices

    @staticmethod
    def get_face_indices(obj, *node_ids, bm=None):
        """
        Get the indices of faces (triangles, n-gons) defined by the given node IDs.
        """
        # Ensure we have a sorted list of node IDs for comparison
        target_node_ids = sorted(node_ids)
        indices = []
        mesh = obj.data
        if obj.mode == 'EDIT':
            if not bm:
                bm = bmesh.from_edit_mesh(mesh)
                bm.faces.ensure_lookup_table()
            bm_data = bm.faces
        elif obj.mode == 'OBJECT':
            bm_data = mesh.polygons
        else:
            logging.error(f"{repr(obj)}: Unknown object mode {obj.mode}")
            return []

        # Iterate through all faces
        for index, face in enumerate(bm_data):
            verts = face.verts if hasattr(face, "verts") else face.vertices
            face_node_ids = sorted([JbeamUtils.get_node_id(obj, v.index) for v in verts])

            # Check if the face contains the same node IDs (order-independent)
            if face_node_ids == target_node_ids:
                indices.append(index)

        if not indices:
            logging.error(f"{repr(obj)}: Face with node IDs {target_node_ids} not found")
        
        return indices  # Return all matching face indices

    @staticmethod
    def get_node_indices(obj, node_id) -> list[int]:
        return JbeamUtils.get_indices_by_id(obj, node_id, domain="verts", attr_name=JbeamUtils.ATTR_NODE_ID)

    @staticmethod
    def check_unique_node_names(obj: bpy.types.Object) -> tuple[bool, str]:
        """Checks if all nodes have a unique name."""
        node_names = set()

        for index in range(len(obj.data.vertices)):
            node_name = JbeamUtils.get_node_id(obj, index).strip()

            if not node_name:
                return False, f"Node at index {index} has an empty name."

            if node_name in node_names:
                return False, f"Duplicate node name detected: '{node_name}' at index {index}."

            node_names.add(node_name)

        return True

    @staticmethod  # deprecated method
    def check_vertex_groups(obj: bpy.types.Object) -> tuple[bool, str]:
        """Checks if each required vertex group has exactly one assigned vertex 
        and that no vertex is assigned to more than one required group.
        """
        required_groups = set(JbeamUtils.get_required_vertex_group_names(minimal=True))
        existing_groups = {vg.name for vg in obj.vertex_groups}

        # Ensure all required groups exist
        if not required_groups.issubset(existing_groups):
            missing = required_groups - existing_groups
            return False, f"Missing vertex groups: {', '.join(missing)}"

        vertex_assignment = {}  # {vertex_index: group_name}
        
        # Check vertex assignments
        for group_name in required_groups:
            vgroup = obj.vertex_groups.get(group_name)
            if not vgroup:
                continue  # Shouldn't happen due to poll, but just in case

            # Get assigned vertices
            assigned_verts = [
                v.index for v in obj.data.vertices
                if any(g.group == vgroup.index for g in v.groups)
            ]
            count = len(assigned_verts)

            if count == 0:
                return False, f"Vertex Group '{group_name}' has no vertex/node assigned."
            elif count > 1:
                return False, f"Vertex Group '{group_name}' has {count} vertices assigned (should be 1 only)."

            # Ensure unique vertex assignment
            vertex_index = assigned_verts[0]
            if vertex_index in vertex_assignment:
                return False, f"Vertex {vertex_index} is assigned to both '{vertex_assignment[vertex_index]}' and '{group_name}', which is not allowed."
            
            vertex_assignment[vertex_index] = group_name  # Store assigned vertex

        return True, "All vertex groups are correctly assigned."



class JbeamRefnodeUtils:

    DOMAIN = "verts"
    ATTR_REFNODE_ID = "jbeam_refnode_id"

    class RefNode(Enum):
        NONE = 0
        REF = 1
        UP = 2
        LEFT = 3
        BACK = 4
        LEFT_CORNER = 5
        RIGHT_CORNER = 6

    REFNODE_MAP = {
        RefNode.NONE: "",
        RefNode.REF: "ref",
        RefNode.UP: "up",
        RefNode.LEFT: "left",
        RefNode.BACK: "back",
        RefNode.LEFT_CORNER: "leftCorner",
        RefNode.RIGHT_CORNER: "rightCorner",
    }

    def get_refnode_name(value: int) -> RefNode:
        try:
            return JbeamRefnodeUtils.RefNode(value)
        except ValueError:
            logging.debug(f"❌ [JbeamRefnodeUtils] Invalid value: {value}")
        return None

    @staticmethod
    def get_ref_nodes() -> dict[str, None]:
        """Generate a dictionary of ref nodes initialized to None, excluding NONE."""
        return {label: None for key, label in JbeamRefnodeUtils.REFNODE_MAP.items() if key != JbeamRefnodeUtils.RefNode.NONE}

    @staticmethod
    def get_refnode_labels_list() -> list[str]:
        return [value for value in JbeamRefnodeUtils.REFNODE_MAP.values() if value]

    @staticmethod
    def get_refnode_label(refnode: RefNode) -> str:
        """Return the mapped label (up, left, back..) for a given RefNode."""
        return JbeamRefnodeUtils.REFNODE_MAP.get(refnode, "")

    @staticmethod
    def get_refnode_from_label(label: str) -> RefNode:
        """Return the corresponding RefNode from a string label."""
        reverse_map = {v: k for k, v in JbeamRefnodeUtils.REFNODE_MAP.items()}
        return reverse_map.get(label, JbeamRefnodeUtils.RefNode.NONE)

    @staticmethod
    def refnode_enum_list() -> list[tuple[str, str, str]]:
        # Return the enum items in the correct format for EnumProperty
        return [(e.name, e.name, f"Set the node to {e.name}") for e in JbeamRefnodeUtils.RefNode]

    def get_refnode_values() -> list[int]:
        return [node.value for node in JbeamRefnodeUtils.RefNode if node.value != 0]

    @staticmethod
    def create_attribute_refnode(obj):
        return JbeamUtils.create_attribute(obj, JbeamRefnodeUtils.ATTR_REFNODE_ID, type="INT")
    
    @staticmethod
    def set_refnode_id(obj, vertex_index, refnode_enum: int) -> bool:
        return JbeamUtils.set_attribute_value(obj, vertex_index, JbeamRefnodeUtils.ATTR_REFNODE_ID, refnode_enum, domain=JbeamRefnodeUtils.DOMAIN, alert_error=False)

    @staticmethod
    def get_refnode_id(obj, vertex_index) -> int:
        return JbeamUtils.get_attribute_value(obj, vertex_index, JbeamRefnodeUtils.ATTR_REFNODE_ID, domain=JbeamRefnodeUtils.DOMAIN)
    
    def find_nodes_with_refnode_id(obj, refnode) -> list[int]:
        indices = JbeamUtils.find_elements_with_attribute_value(obj, JbeamRefnodeUtils.ATTR_REFNODE_ID, refnode, domain="verts")
        return indices

