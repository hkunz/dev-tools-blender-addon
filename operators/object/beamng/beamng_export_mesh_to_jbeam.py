import bpy
import bpy_types
import os
import json
import io


class JBeamProcessor:
    def __init__(self, json_data):
        self.json_data = json_data
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

    def insert_node_contents(self, key, new_contents):
        self.remove_node_contents(key)
        result = self.get_result()
        result = result.replace(f'"{key}": []', f'"{key}": [\n\t{new_contents}\n]')
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
        group_names = ["up", "left", "back", "leftCorner", "rightCorner", "fixed"]
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
    """Export mesh to JBeam JSON format"""
    bl_idname = "export.dev_tools_beamng_export_mesh_to_jbeam"
    bl_label = "DevTools: Export Mesh to JBeam JSON Format"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH") # type: ignore

    def execute(self, context):
        bpy.ops.object.mode_set(mode='OBJECT')
        success = self.export_jbeam_format(self.filepath)
        return {'FINISHED'} if success else {'CANCELLED'} 

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        context.window_manager.operators[-1].bl_label = "Save JBeam File"
        return {'RUNNING_MODAL'}

    def get_starting_props(self, data, jbeam_prop): # jbeam_prop i.e. "nodes", "beams", "triangles", "quads", etc
        if not jbeam_prop in data:
            self.report({'ERROR'}, f"No jbeam prop named \"{jbeam_prop}\" found!")
            return []
        starting_props = []
        for item in data[jbeam_prop][1:]:
            if isinstance(item, dict):
                starting_props.append(item)
            elif isinstance(item, list):
                break  # Stop when encountering the first node array
        return starting_props

    def get_ending_props(self, data, jbeam_prop):
        if not jbeam_prop in data:
            self.report({'ERROR'}, f"No jbeam prop named \"{jbeam_prop}\" found!")
            return []
        ending_props = []
        for item in reversed(data[jbeam_prop]):
            if isinstance(item, dict):
                ending_props.append(item)
            elif isinstance(item, list):
                break  # Stop when encountering the first node array
        ending_props.reverse()
        return ending_props

    def get_final_struct(self, json, items, jbeam_prop, prepend):
        starting_props = self.get_starting_props(json, jbeam_prop)
        ending_props = self.get_ending_props(json, jbeam_prop)
        if starting_props == ending_props:
            ending_props = []
        arr = prepend + starting_props + items + ending_props
        return ',\n\t'.join(
        str(item).replace("'", '"').replace("[", "[").replace("]", "]").replace(",", ",").replace("}", "}") 
        for item in arr
    )

    def export_jbeam_format(self, filepath):
        obj = bpy.context.active_object
        if obj is None or obj.type != "MESH":
            self.report({'ERROR'}, "No valid mesh object selected!")
            return False

        mesh = obj.data
        mesh.calc_loop_triangles()

        fixed_vertices = self.get_fixed_vertices(obj)
        nodes, vertex_map = self.get_nodes(mesh, fixed_vertices)
        beams = self.get_beams(mesh, vertex_map)
        triangles = self.get_triangles(mesh, vertex_map)
        quads = self.get_quads(mesh, vertex_map)
        ngons = self.get_ngons(mesh, vertex_map)
        ref_nodes = self.find_reference_nodes(obj)

        ref_nodes_data = [
            ["ref:", "back:", "left:", "up:", "leftCorner:", "rightCorner:"],
            ["ref"] + [ref_nodes[key] if ref_nodes[key] is not None else "" for key in ["back", "left", "up", "leftCorner", "rightCorner"]],
        ]

        def format_list(data):
            return '[\n    ' + ",\n    ".join(str(item).replace("'", '"') for item in data) + "\n]"


        def format_compact(nodes):
            # This will generate the correct format for each node as a single line without string escaping
            return "[" + ", ".join([json.dumps(node, separators=(",", ":")) for node in nodes]) + "]"


        is_manual_data = True

        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                try:
                    existing_data = json.load(f)
                    is_manual_data = "manual_data_file" in existing_data
                    f.seek(0)
                    existing_data_str = f.read()
                except json.JSONDecodeError:
                    self.report({'ERROR'}, f"Error parsing {filepath}")
                    return False

        if is_manual_data:
            # Generate manual data .json file
            json_output = "{\n"
            json_output += f'"manual_data_file": "you need to manually copy these nodes to the .jbeam file",\n'
            json_output += f'"refNodes": {format_list(ref_nodes_data)},\n'
            json_output += f'"nodes": {format_list(nodes)},\n'
            json_output += f'"beams": {format_list(beams)},\n'
            json_output += f'"triangles": {format_list(triangles)},\n'
            json_output += f'"quads": {format_list(quads)},\n'
            json_output += f'"ngons": {format_list(ngons)}\n'
            json_output += "}"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(json_output)
        else:
            print(f"Replace nodes, beams, triangles, refNodes, etc in {filepath}")
            nodes_str = self.get_final_struct(existing_data, nodes, "nodes", [["id", "posX", "posY", "posZ"]])
            beams_str = self.get_final_struct(existing_data, beams, "beams", [["id1:", "id2:"]])
            tris_str = self.get_final_struct(existing_data, triangles, "triangles", [["id1:","id2:","id3:"]])
            quads_str = self.get_final_struct(existing_data, quads, "quads", [["id1:","id2:","id3:","id4:"]])
            
            processor = JBeamProcessor(existing_data_str)

            # Modify "nodes", then "beams", and "triangles" successively:
            existing_data_str = processor.insert_node_contents("nodes", nodes_str)
            existing_data_str = processor.insert_node_contents("beams", beams_str)
            existing_data_str = processor.insert_node_contents("triangles", tris_str)

            #json_text = processor.insert_node_contents("beamsn", beams_str)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(existing_data_str)

        


            self.report({'INFO'}, f"{obj.name}: JBeam exported to {filepath}")

        return True

    def get_fixed_vertices(self, obj):
        fixed_group = obj.vertex_groups.get("fixed")
        fixed_vertices = set()
        if fixed_group:
            for vert in obj.data.vertices:
                for g in vert.groups:
                    if g.group == fixed_group.index:
                        fixed_vertices.add(vert.index)
        return fixed_vertices

    def get_nodes(self, mesh, fixed_vertices):
        nodes = []
        vertex_map = {}
        currently_fixed = False

        for i, vert in enumerate(mesh.vertices):
            node_name = f"b{i+1}"
            pos = (round(vert.co.x, 4), round(vert.co.y, 4), round(vert.co.z, 4))
            if i in fixed_vertices and not currently_fixed:
                nodes.append({"fixed": "true"})
                currently_fixed = True
            elif i not in fixed_vertices and currently_fixed:
                nodes.append({"fixed": "false"})
                currently_fixed = False
            nodes.append([node_name, *pos])
            vertex_map[i] = node_name

        if currently_fixed:
            nodes.append({"fixed": "false"})

        nodes.insert(0, ["ref", 0, 0, 0])
        return nodes, vertex_map

    def get_beams(self, mesh, vertex_map):
        return [[vertex_map[v1], vertex_map[v2]] for v1, v2 in (edge.vertices for edge in mesh.edges)]

    def get_triangles(self, mesh, vertex_map):
        triangles = []
        for poly in mesh.polygons:
            if len(poly.vertices) == 3:
                v1, v2, v3 = poly.vertices
                triangles.append([vertex_map[v1], vertex_map[v2], vertex_map[v3]])
        return triangles

    def get_quads(self, mesh, vertex_map):
        quads = []
        for poly in mesh.polygons:
            if len(poly.vertices) == 4:
                v1, v2, v3, v4 = poly.vertices
                quads.append([vertex_map[v1], vertex_map[v2], vertex_map[v3], vertex_map[v4]])
        return quads

    def get_ngons(self, mesh, vertex_map):
        ngons = []
        for poly in mesh.polygons:
            if len(poly.vertices) > 4:
                ngons.append([vertex_map[v] for v in poly.vertices])
        return ngons

    def find_reference_nodes(self, obj):
        ref_nodes = {"ref": None, "back": None, "left": None, "up": None, "leftCorner": None, "rightCorner": None}
        for group_name in ref_nodes.keys():
            group = obj.vertex_groups.get(group_name)
            if group:
                for vert in obj.data.vertices:
                    for g in vert.groups:
                        if g.group == group.index:
                            ref_nodes[group_name] = f"b{vert.index + 1}"
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
