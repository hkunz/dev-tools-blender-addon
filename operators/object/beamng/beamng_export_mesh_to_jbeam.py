import bpy
import bpy_types

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
        if not active_object or active_object.type != "MESH":
            return False
        return True

class EXPORT_OT_BeamngExportMeshToJbeam(bpy.types.Operator):
    """Export mesh to JBeam JSON format"""
    bl_idname = "export.dev_tools_beamng_export_mesh_to_jbeam"
    bl_label = "DevTools: Export Mesh to JBeam JSON Format"
    bl_options = {'REGISTER'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH") # type: ignore

    def execute(self, context):
        self.export_jbeam_format(self.filepath)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        context.window_manager.operators[-1].bl_label = "Save JBeam File"
        return {'RUNNING_MODAL'}

    def export_jbeam_format(self, filepath):
        obj = bpy.context.active_object
        if obj is None or obj.type != "MESH":
            self.report({'ERROR'}, "No valid mesh object selected!")
            return

        mesh = obj.data
        mesh.calc_loop_triangles()

        def get_fixed_vertices(obj):
            fixed_group = obj.vertex_groups.get("fixed")
            fixed_vertices = set()
            if fixed_group:
                for vert in obj.data.vertices:
                    for g in vert.groups:
                        if g.group == fixed_group.index:
                            fixed_vertices.add(vert.index)
            return fixed_vertices

        def find_reference_nodes(obj):
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

        nodes = [["id", "posX", "posY", "posZ"]]
        vertex_map = {}
        fixed_vertices = get_fixed_vertices(obj)
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

        ref_nodes = find_reference_nodes(obj)
        ref_nodes_data = [
            ["ref:", "back:", "left:", "up:", "leftCorner:", "rightCorner:"],
            [ref_nodes["ref"], ref_nodes["back"], ref_nodes["left"], ref_nodes["up"], ref_nodes["leftCorner"], ref_nodes["rightCorner"]],
        ]

        beams = [["id1:", "id2:"]]
        for edge in mesh.edges:
            v1, v2 = edge.vertices
            beams.append([vertex_map[v1], vertex_map[v2]])

        triangles = [["id1:", "id2:", "id3:"]]
        for tri in mesh.loop_triangles:
            v1, v2, v3 = tri.vertices
            triangles.append([vertex_map[v1], vertex_map[v2], vertex_map[v3]])

        def format_list(data):
            return '[\n    ' + ",\n    ".join(str(item).replace("'", '"') for item in data) + "\n]"

        json_output = "{\n"
        json_output += f'    "nodes": {format_list(nodes)},\n'
        json_output += f'    "beams": {format_list(beams)},\n'
        json_output += f'    "triangles": {format_list(triangles)},\n'
        json_output += f'    "refNodes": {format_list(ref_nodes_data)}\n'
        json_output += "}"

        with open(filepath, "w") as f:
            f.write(json_output)

        self.report({'INFO'}, f"{obj.name}: JBeam exported to {filepath}")

    @classmethod
    def poll(cls, context: bpy_types.Context) -> bool:
        active_object: bpy_types.Object = context.active_object
        if not active_object or active_object.type != "MESH":
            return False
        
        required_groups = {"up", "left", "back", "leftCorner", "rightCorner"}
        existing_groups = {vg.name for vg in active_object.vertex_groups}
    
        return required_groups.issubset(existing_groups)  # Check if all groups are present
