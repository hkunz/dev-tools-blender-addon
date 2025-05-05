import bpy
import os
import io
import json
import logging

from pprint import pprint

from unofficial_jbeam_editor.utils.utils import Utils
from unofficial_jbeam_editor.utils.object_utils import ObjectUtils as o
from unofficial_jbeam_editor.utils.json_cleanup import json_cleanup
from unofficial_jbeam_editor.utils.jbeam.jbeam_helper import PreJbeamStructureHelper, RedundancyReducerJbeamGenerator
from unofficial_jbeam_editor.utils.jbeam.jbeam_utils import JbeamUtils as j, JbeamRefnodeUtils as jr
from unofficial_jbeam_editor.utils.jbeam.jbeam_export_processor import JbeamExportProcessor


class DEVTOOLS_JBEAMEDITOR_EXPORT_OT_BeamngExportNodeMeshToJbeam(bpy.types.Operator):
    bl_idname = "export.dev_tools_beamng_export_node_mesh_to_jbeam"
    bl_label = "DevTools: Export Mesh to JBeam Format"
    bl_description = "Export a Node Mesh to the JBeam format. In Edit Mode, the operator checks the JBeam path of the active element and exports all related elements with the same JBeam path. In Object Mode, all elements are exported to a single JBeam file."
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH") # type: ignore

    def check_unique_node_names(self, obj: bpy.types.Object) -> tuple[bool, str]:
        """Checks if all nodes have a unique name."""
        node_names = set()

        for index in range(len(obj.data.vertices)):
            node_name = j.get_node_id(obj, index).strip()

            if not node_name:
                return False, f"Node at index {index} has an empty name."

            if node_name in node_names:
                return False, f"Duplicate node name detected: '{node_name}' at index {index}."

            node_names.add(node_name)

        return True, "All nodes have unique names."

    def execute(self, context):
        success = self.export_jbeam_format(self.filepath)
        return {'FINISHED'} if success else {'CANCELLED'} 

    def invoke(self, context, event):
        mode = context.object.mode
        if mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        def restore_mode():
            if mode != context.object.mode:
                bpy.ops.object.mode_set(mode=mode)

        obj = context.object
        if not context.active_object or not context.selected_objects:
            Utils.log_and_report("No objects selected!", self, 'WARNING')
            restore_mode()
            return {'CANCELLED'}

        if not j.is_node_mesh(obj):
            Utils.log_and_report(f"{repr(obj)} is not a Node Mesh", self, 'WARNING')
            restore_mode()
            return {'CANCELLED'}

        if o.has_ngons(obj):
            Utils.log_and_report("Jbeam does not support quads and N-gons. Triangulate these faces with Ctrl+T", self, 'ERROR')
            restore_mode()
            return {'CANCELLED'}

        # Check vertex groups
        '''
        is_valid, message = j.check_vertex_groups(obj)
        if not is_valid:
            Utils.log_and_report(message, self, 'WARNING')
            restore_mode()
            return {'CANCELLED'}
        '''

        refnodes = jr.get_refnode_values()
        for refnode in refnodes:
            items = jr.find_nodes_with_refnode_id(obj, refnode)
            if len(items) > 1:
                enum = jr.get_refnode_name(refnode)
                Utils.log_and_report(f"Multiple nodes assigned with {enum}. Only 1 Node can be labeled as {enum}", self, 'WARNING')
                return {'CANCELLED'}

        # Check unique node names
        is_valid, message = self.check_unique_node_names(obj)
        if not is_valid:
            Utils.log_and_report(message, self, 'WARNING')
            restore_mode()
            return {'CANCELLED'}

        Utils.log_and_report(message, self, 'INFO')
        context.window_manager.fileselect_add(self)
        #context.window_manager.operators[-1].bl_label = "Save JBeam File"
        restore_mode()

        return {'RUNNING_MODAL'}

    def generate_jbeam_node_list(self, obj):

        jbeam = PreJbeamStructureHelper(obj, domain="vertex")
        data = jbeam.structure_data()
        reducer = RedundancyReducerJbeamGenerator(obj, data, domain="vertex")
        data_actual = reducer.reduce_redundancy()

        node_data = [] #[["id", "posX", "posY", "posZ"]]
        for item in data_actual:
            node_data.append(item)
        return node_data

    def generate_jbeam_beam_list(self, obj):

        jbeam = PreJbeamStructureHelper(obj, domain="edge")
        data = jbeam.structure_data()
        reducer = RedundancyReducerJbeamGenerator(obj, data, domain="edge")
        data_actual = reducer.reduce_redundancy()

        beam_data = [] #[["id1:", "id2:"]]
        for item in data_actual:
            beam_data.append(item)
        return beam_data

    def generate_jbeam_triangle_list(self, obj):

        jbeam = PreJbeamStructureHelper(obj, domain="face")
        data = jbeam.structure_data()
        reducer = RedundancyReducerJbeamGenerator(obj, data, domain="face")
        data_actual = reducer.reduce_redundancy()

        beam_data = [] #[["id1:", "id2:", "id3:"]]
        for item in data_actual:
            beam_data.append(item)
        return beam_data

    def export_jbeam_format(self, filepath):
        obj = bpy.context.active_object
        if obj is None or obj.type != "MESH":
            Utils.log_and_report("No valid mesh object selected!", self, 'ERROR')
            return False

        mesh = obj.data
        mesh.calc_loop_triangles()

        nodes = self.generate_jbeam_node_list(obj)
        beams = self.generate_jbeam_beam_list(obj)
        triangles = self.generate_jbeam_triangle_list(obj)
        quads = self.get_quads(obj)
        ngons = self.get_ngons(obj)
        ref_nodes = self.find_reference_nodes(obj)

        ref_nodes_keys = jr.get_refnode_labels_list()
        ref_nodes_data = [
            [f"{key}:" for key in ref_nodes_keys],
            [ref_nodes.get(key, "") or "" for key in ref_nodes_keys]
        ]

        def format_list(data, prepend="", newfile=True):
            spaces = 12 if newfile else 4
            indent = " " * spaces
            prepend = (indent if newfile else '') + prepend + '\n' if prepend else ""   
            formatted_data = ',\n'.join(
                indent + str(item)
                .replace("'true'", "true")
                .replace("'false'", "false")
                .replace("'", '"')
                for item in data
            )
            return prepend + formatted_data + '\n' + ' ' * (spaces - 4)

        is_manual_data = True

        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                try:
                    raw_text = f.read()
                    clean_text = json_cleanup(raw_text)
                    existing_data = json.load(io.StringIO(clean_text))  # Convert cleaned text to file-like object, changes true to True & false to False but jbeam needs small case bools
                    is_manual_data = "manual_data_file" in existing_data
                    f.seek(0)
                    existing_data_str = f.read()
                except json.JSONDecodeError:
                    Utils.log_and_report(f"Error parsing {filepath}", self, 'ERROR')
                    logging.debug(f"Error parsing {filepath}:, maybe check for missing commas or other json-type formatting in jbeam")
                    return False

        if is_manual_data:
            # Generate manual data .json file
            t1 = " " * 4
            t2 = " " * 8
            json_output = "{\n"
            json_output += f'{t1}"manual_data_file": {{"note":"you need to manually copy these nodes to the .jbeam file"}},\n'
            json_output += f'{t1}"partname": {{\n'
            json_output += t2 + '"refNodes": ' + '[\n' + format_list(ref_nodes_data) + '],\n'
            json_output += t2 + '"nodes": ' + '[\n' + format_list(nodes, '["id", "posX", "posY", "posZ"],') + '],\n'
            json_output += t2 + '"beams": ' + '[\n' + format_list(beams, '["id1:", "id2:"],') + '],\n'
            json_output += t2 + '"triangles": ' + '[\n' + format_list(triangles, '["id1:","id2:","id3:"],') + '],\n'
            json_output += t2 + '"quads": ' + '[\n' + format_list(quads, '["id1:","id2:","id3:","id4:"],') + '],\n'
            json_output += t2 + '"ngons": ' + '[\n' + format_list(ngons, '["ngons:"]') + '],\n'
            json_output += t1 + "}\n"
            json_output += "}"

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(json_output)
        else:
            logging.debug(f"Replace nodes, beams, triangles, refNodes, etc in {filepath}")
            refnodes_str = ',\n    '.join(str(item).replace("'", '"') for item in ref_nodes_data)
            nodes_str = format_list(nodes, '["id", "posX", "posY", "posZ"],', False)
            beams_str = format_list(beams, '["id1:","id2:"],', False)
            tris_str = format_list(triangles, '["id1:","id2:","id3:"],', False)

            processor = JbeamExportProcessor(existing_data_str)

            # Modify "nodes", then "beams", and "triangles" successively:
            existing_data_str = processor.insert_node_contents("refNodes", refnodes_str)
            existing_data_str = processor.insert_node_contents("nodes", nodes_str)
            existing_data_str = processor.insert_node_contents("beams", beams_str)
            existing_data_str = processor.insert_node_contents("triangles", tris_str)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(existing_data_str)

        Utils.log_and_report(f"{obj.name}: JBeam exported to {filepath}", self, 'INFO')

        return True

    def get_quads(self, o):
        quads = []
        for poly in o.data.polygons:
            if len(poly.vertices) == 4:
                v1, v2, v3, v4 = poly.vertices
                quads.append([j.get_node_id(o,v1), j.get_node_id(o,v2), j.get_node_id(o,v3), j.get_node_id(o,v4)])
        return quads

    def get_ngons(self, o):
        ngons = []
        for poly in o.data.polygons:
            if len(poly.vertices) > 4:
                ngons.append([j.get_node_id(o,v) for v in poly.vertices])
        return ngons

    def find_reference_nodes(self, o):
        ref_nodes = jr.get_ref_nodes()  # {"ref": None, "back": None, "left": None, "up": None, "leftCorner": None, "rightCorner": None}
        for label in ref_nodes.keys():
            refnode_enum = jr.get_refnode_from_label(label)
            indices = jr.find_nodes_with_refnode_id(o, refnode_enum.value)
            if indices:
                ref_nodes[label] = j.get_node_id(o, indices[0])
        return ref_nodes

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        obj: bpy.types.Object = context.active_object

        if not obj or not j.is_node_mesh(obj) or len(context.selected_objects) > 1:
            return False

        # Check if required vertex groups exist
        #required_groups = {"up", "left", "back", "leftCorner", "rightCorner"}
        #existing_groups = {vg.name for vg in active_object.vertex_groups}
        
        return True #required_groups.issubset(existing_groups)
