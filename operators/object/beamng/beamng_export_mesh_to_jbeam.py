import bpy
import bpy_types
import os
import io
import json
from pprint import pprint

from dev_tools.utils.json_cleanup import json_cleanup # type: ignore
from dev_tools.utils.jbeam.jbeam_helper import PreJbeamStructureHelper, RedundancyReducerJbeamNodesGenerator # type: ignore
from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j # type: ignore

import io
import json

class JBeamProcessor:
    def __init__(self, json_data):
        self.json_data = json_data
        self.input_stream = None
        self.output_stream = io.StringIO()
        self.modified_data = json_data

    def remove_node_contents(self, key):
        self.output_stream = io.StringIO()
        self.input_stream = io.StringIO(self.modified_data)

        depth = 0
        skipping = False
        key_buffer = []
        inside_string = False

        while True:
            ch = self.input_stream.read(1)
            if not ch:
                break

            if ch == '"':
                inside_string = not inside_string

            if inside_string and depth == 0:
                key_buffer.append(ch)
                if len(key_buffer) > 255:
                    key_buffer = key_buffer[:255]

            if not inside_string and key_buffer:
                key_str = ''.join(key_buffer)
                key_buffer = []
                if key_str[1:] == key:
                    skipping = True
                    self.output_stream.write('"' + ':' + ' ')

            if ch == '[' and not inside_string:
                if skipping:
                    depth += 1
                    if depth == 1:
                        self.output_stream.write('[')
                    continue

            if ch == ']' and not inside_string:
                if depth > 0:
                    depth -= 1
                    if depth == 0:
                        skipping = False

            if not skipping:
                self.output_stream.write(ch)

        return self.output_stream.getvalue()


    def get_key_indent(self, key):
        current_pos = self.input_stream.tell()
        self.input_stream.seek(0)

        for line in self.input_stream:
            stripped_line = line.lstrip()
            if stripped_line.startswith(f'"{key}"'):
                indent = len(line) - len(stripped_line)
                self.input_stream.seek(current_pos)
                return indent

        self.input_stream.seek(current_pos) 
        return -1

    def insert_node_contents(self, key, new_contents):
        self.remove_node_contents(key)
        spaces = self.get_key_indent(key)
        indent = " " * spaces
        result = self.get_result()
        if spaces < 0:
            return result
        indented_contents = "\n".join(indent + line for line in new_contents.splitlines())
        result = result.replace(f'"{key}": []', f'"{key}": [\n    {indented_contents}\n{indent}]')
        self.modified_data = result
        return result

    def get_result(self):
        return self.output_stream.getvalue()


class OBJECT_OT_BeamngCreateRefnodesVertexGroups(bpy.types.Operator):
    """Create BeamNG refNodes vertex groups if they do not exist"""
    bl_idname = "object.devtools_beamng_create_refnodes_vertex_groups"
    bl_label = "DevTools: Create BeamNG refNodes Vertex Groups"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        group_names = ["up", "left", "back", "leftCorner", "rightCorner"]
        obj = context.active_object

        if obj and obj.type == "MESH":
            created_groups = []
            for name in group_names:
                if name not in obj.vertex_groups:
                    obj.vertex_groups.new(name=name)
                    created_groups.append(name)
            
            self.report({'INFO'}, f"{obj.name}: Vertex groups created: {', '.join(created_groups)}" if created_groups else "All groups already exist.")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "No valid mesh object selected!")
            return {'CANCELLED'}
        
    @classmethod
    def poll(cls, context: bpy_types.Context) -> bool:
        active_object: bpy_types.Object = context.active_object
        return active_object and active_object.type == "MESH"

class EXPORT_OT_BeamngExportMeshToJbeam(bpy.types.Operator):
    """Export mesh to JBeam format"""
    bl_idname = "export.dev_tools_beamng_export_mesh_to_jbeam"
    bl_label = "DevTools: Export Mesh to JBeam Format"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH") # type: ignore

    def execute(self, context):
        bpy.ops.object.mode_set(mode='OBJECT')
        success = self.export_jbeam_format(self.filepath)
        return {'FINISHED'} if success else {'CANCELLED'} 

    def invoke(self, context, event):
        if not context.active_object or not context.selected_objects:
            self.report({'WARNING'}, "No objects selected!")
            return {'CANCELLED'}
        context.window_manager.fileselect_add(self)
        #context.window_manager.operators[-1].bl_label = "Save JBeam File"
        return {'RUNNING_MODAL'}

    def get_starting_props(self, data, jbeam_prop):  # jbeam_prop i.e. "nodes", "beams", "triangles", "quads", etc
        partnames = [key for key in data]
        if not partnames:
            self.report({'WARNING'}, "No partname-like property found!")
            return []
        last_partname = partnames[-1]
        part_data = data[last_partname]
        if jbeam_prop not in part_data:
            self.report({'WARNING'}, f"No jbeam prop named \"{jbeam_prop}\" found!")
            return []
        starting_props = []
        for item in part_data[jbeam_prop][1:]:
            if isinstance(item, dict):
                starting_props.append(item)
            elif isinstance(item, list):
                break
        return starting_props

    def get_ending_props(self, data, jbeam_prop):  # jbeam_prop i.e. "nodes", "beams", "triangles", "quads", etc
        partnames = [key for key in data]
        if not partnames:
            self.report({'ERROR'}, "No partname-like property found!")
            return []
        last_partname = partnames[-1]
        part_data = data[last_partname]
        if jbeam_prop not in part_data:
            self.report({'ERROR'}, f"No jbeam prop named \"{jbeam_prop}\" found!")
            return []
        ending_props = []
        for item in reversed(part_data[jbeam_prop]):
            if isinstance(item, dict):
                ending_props.append(item)
            elif isinstance(item, list):
                break
        ending_props.reverse()
        return ending_props

    def get_final_struct(self, json, items, jbeam_prop, prepend=[]):
        starting_props = self.get_starting_props(json, jbeam_prop)
        ending_props = self.get_ending_props(json, jbeam_prop)
        if starting_props == ending_props:
            ending_props = []
        arr = prepend + starting_props + items + ending_props
        formatted_str = ',\n    '.join(
            str(item).replace("'", '"')
            for item in arr
        )
        formatted_str = formatted_str.replace('True', 'true').replace('False', 'false')
        return formatted_str

    def generate_jbeam_node_list(self, obj):

        jbeam = PreJbeamStructureHelper(obj)
        data = jbeam.structure_vertex_data()
        reducer = RedundancyReducerJbeamNodesGenerator(obj, data)
        data_actual = reducer.reduce_redundancy()

        node_data = [] #[["id", "posX", "posY", "posZ"]]
        for item in data_actual:
            node_data.append(item)
        return node_data

    def export_jbeam_format(self, filepath):
        obj = bpy.context.active_object
        if obj is None or obj.type != "MESH":
            self.report({'ERROR'}, "No valid mesh object selected!")
            return False

        mesh = obj.data
        mesh.calc_loop_triangles()

        nodes = self.generate_jbeam_node_list(obj)
        beams = self.get_beams(obj)
        triangles = self.get_triangles(obj)
        quads = self.get_quads(obj)
        ngons = self.get_ngons(obj)
        ref_nodes = self.find_reference_nodes(obj)

        ref_nodes_data = [
            ["ref:", "back:", "left:", "up:", "leftCorner:", "rightCorner:"],
            ["ref"] + [ref_nodes[key] if ref_nodes[key] is not None else "" for key in ["back", "left", "up", "leftCorner", "rightCorner"]],
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
                    self.report({'ERROR'}, f"Error parsing {filepath}")
                    print(f"Error parsing {filepath}:, maybe check for missing commas or other json-type formatting in jbeam")
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
            print(f"Replace nodes, beams, triangles, refNodes, etc in {filepath}")
            refnodes_str = self.get_final_struct(existing_data, ref_nodes_data, "refNodes")
            nodes_str = format_list(nodes, '["id", "posX", "posY", "posZ"],', False)
            #nodes_str = self.get_final_struct(existing_data, nodes, "nodes", [["id", "posX", "posY", "posZ"]])
            beams_str = self.get_final_struct(existing_data, beams, "beams", [["id1:", "id2:"]])
            tris_str = self.get_final_struct(existing_data, triangles, "triangles", [["id1:","id2:","id3:"]])
            if quads: quads_str = self.get_final_struct(existing_data, quads, "quads", [["id1:","id2:","id3:","id4:"]])
            if ngons: ngons_str = self.get_final_struct(existing_data, ngons, "ngons", [["ngons:"]])
            
            processor = JBeamProcessor(existing_data_str)

            # Modify "nodes", then "beams", and "triangles" successively:
            existing_data_str = processor.insert_node_contents("refNodes", refnodes_str)
            existing_data_str = processor.insert_node_contents("nodes", nodes_str)
            existing_data_str = processor.insert_node_contents("beams", beams_str)
            existing_data_str = processor.insert_node_contents("triangles", tris_str)
            if quads: existing_data_str = processor.insert_node_contents("quads", quads_str)
            if ngons: existing_data_str = processor.insert_node_contents("ngons", ngons_str)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(existing_data_str)

        self.report({'INFO'}, f"{obj.name}: JBeam exported to {filepath}")

        return True

    def get_beams(self, o):
        return [[j.get_node_id(o,v1), j.get_node_id(o,v2)] for v1, v2 in (edge.vertices for edge in o.data.edges)]

    def get_triangles(self, o):
        triangles = []
        for poly in o.data.polygons:
            if len(poly.vertices) == 3:
                v1, v2, v3 = poly.vertices
                triangles.append([j.get_node_id(o,v1), j.get_node_id(o,v2), j.get_node_id(o,v3)])
        return triangles

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
        ref_nodes = {"ref": None, "back": None, "left": None, "up": None, "leftCorner": None, "rightCorner": None}
        for group_name in ref_nodes.keys():
            group = o.vertex_groups.get(group_name)
            if group:
                for vert in o.data.vertices:
                    for g in vert.groups:
                        if g.group == group.index:
                            ref_nodes[group_name] = j.get_node_id(o,vert.index)
                            break
        return ref_nodes

    @classmethod
    def poll(cls, context: bpy_types.Context) -> bool:
        active_object: bpy_types.Object = context.active_object
        if not active_object or active_object.type != "MESH":
            return False
        required_groups = {"up", "left", "back", "leftCorner", "rightCorner"}
        existing_groups = {vg.name for vg in active_object.vertex_groups}
        return required_groups.issubset(existing_groups)


# Test

json_data = """
{
    "manual_datfa_file": "you need to manually copy these nodes to the .jbeam file",
    "partname": {
        "refNodes": [
            ["ref:", "back:", "left:", "up:", "leftCorner:", "rightCorner:"],
            ["ref", "", "", "", "", ""]
        ],
        "nodes": [
            ["id", "posX", "posY", "posZ"],
            {"asdf":"asdf"},
            {"asdf":"asdf2"},
            ["ref", 0, 0, 0],
            ["b7", -1.0, -1.0, 1.0],
            ["b8", -1.0, -1.0, -1.0],
            {"asdf":"asdf"},
            {"asdf":"asdf3"}
        ]
    }
}
"""
#processor = JBeamProcessor(json_data)
#result = processor.remove_node_contents("nodes")
#print("Processed JSON:\n", result)