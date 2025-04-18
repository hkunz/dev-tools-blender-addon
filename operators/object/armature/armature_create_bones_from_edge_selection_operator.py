import bpy
import bmesh
from collections import defaultdict, deque

from dev_tools.utils.object_utils import ObjectUtils

# Make sure Mesh and Armature both have their Origins at World Origin
# Select Mesh Objects and go into Edit mode and select Edges where you want create and position bones
# Run operator which creates Armature/Bones exactly on selected edges
# Run operator OBJECT_OT_ArmatureAssignClosestVertexToBoneTails

class OBJECT_OT_ArmatureCreateBonesFromEdgeSelection(bpy.types.Operator):
    """
    Create an armature with bones based on selected edges and vertices.
    """
    bl_idname = "object.devtools_armature_create_bones_from_edge_selection"
    bl_label = "DevTools: Create Armature Bones from Edge Selection"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object

        if obj.mode != 'EDIT' or obj.type != 'MESH':
            self.report({'ERROR'}, "Object must be a mesh in edit mode.")
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='EDGE')

        islands = self.get_vertex_islands(obj)
        bpy.ops.object.mode_set(mode='OBJECT')
        obj.select_set(False)

        armature = bpy.data.armatures.new("Armature")
        armature_obj = bpy.data.objects.new("Armature", armature)
        context.collection.objects.link(armature_obj)
        context.view_layer.objects.active = armature_obj

        bpy.ops.object.mode_set(mode='EDIT')

        for i, island in enumerate(islands):
            self.create_armature_bones(obj, island, armature_obj)

        bpy.ops.object.mode_set(mode='OBJECT')
        context.view_layer.objects.active = armature_obj
        armature_obj.select_set(True)

        return {'FINISHED'}

    def get_vertex_islands(self, obj):
        bm = bmesh.from_edit_mesh(obj.data)
        selected_verts = [v for v in bm.verts if v.select]
        if not ObjectUtils.get_selected_edges(obj):
            self.report({'WARNING'}, "No selected edges detected")
            return []

        visited = set()
        islands = []

        def find_connected(vertex, island):
            stack = [vertex]
            while stack:
                current = stack.pop()
                if current not in visited and current.select:
                    visited.add(current)
                    island.append(current.index)
                    for edge in current.link_edges:
                        stack.append(edge.other_vert(current))

        for vert in selected_verts:
            if vert not in visited:
                island = []
                find_connected(vert, island)
                islands.append(island)

        return islands

    def reorder_island_with_junctions(self, obj, island):
        mesh = obj.data
        neighbors = defaultdict(list)

        for edge in mesh.edges:
            v1, v2 = edge.vertices
            if v1 in island and v2 in island and edge.select:
                neighbors[v1].append(v2)
                neighbors[v2].append(v1)

        start_vertices = [v for v in island if len(neighbors[v]) == 1]
        if not start_vertices:
            raise ValueError("No start vertex found. Is the island cyclic?")

        visited = set()
        paths = []

        for start in start_vertices:
            if start not in visited:
                queue = deque([(start, None)])
                path = []
                while queue:
                    vertex, parent = queue.popleft()
                    if vertex not in visited:
                        visited.add(vertex)
                        path.append((vertex, parent))
                        for neighbor in neighbors[vertex]:
                            if neighbor not in visited:
                                queue.append((neighbor, vertex))
                paths.extend(path)

        return paths, neighbors

    def create_armature_bones(self, obj, island, armature_obj):
        mesh = obj.data
        paths, neighbors = self.reorder_island_with_junctions(obj, island)
        bones = {}

        for vertex, parent in paths:
            vert_co = obj.matrix_world @ mesh.vertices[vertex].co
            if parent is not None:
                parent_co = obj.matrix_world @ mesh.vertices[parent].co

                edge = next((e for e in mesh.edges if vertex in e.vertices and parent in e.vertices), None)
                bone_name = f"Bone_Edge_{edge.index}" if edge else f"Bone_{vertex}"
                armature = armature_obj.data
                bone = armature.edit_bones.new(bone_name)
                bone.head = parent_co
                bone.tail = vert_co

                if parent in bones:
                    bone.parent = bones[parent]
                    bone.use_connect = True

                bones[vertex] = bone

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'