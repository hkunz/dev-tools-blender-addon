import bpy

class JbeamMeshCreator:
    def __init__(self, nodes, beams_list, tris_list):
        self.nodes: dict[str, object] = nodes
        self.beams_list: list[object] = beams_list
        self.tris_list: list[object] = tris_list

    def create_mesh(self, mesh_name="JBeamMesh"):
        vertices = []
        vertex_indices = {}  # Map NodeID to vertex index for edges and faces
        edges = []
        faces = []

        # Create vertices
        for i, (node_id, node) in enumerate(self.nodes):  # Enumerate through nodes
            print(f"Processing NodeID: {node_id}, Position: {node.position}")
            vertices.append(node.position)
            vertex_indices[node_id] = i  # Map NodeID to its vertex index

        # Create edges based on beams
        for beam in self.beams_list:
            # Access the Node ID from the Node object
            start_index = vertex_indices[beam.node_id1.id]
            end_index = vertex_indices[beam.node_id2.id]
            edges.append((start_index, end_index))

        # Create faces based on tris_list
        for tri in self.tris_list:
            # Map Node IDs in the triangle to vertex indices
            try:
                vertex_1 = vertex_indices[tri.node_id1.id]
                vertex_2 = vertex_indices[tri.node_id2.id]
                vertex_3 = vertex_indices[tri.node_id3.id]
                faces.append((vertex_1, vertex_2, vertex_3))  # Add face as a triangle
            except KeyError as e:
                print(f"Warning: Missing node ID {e} for triangle {tri}. Skipping.")

        # Create mesh object
        mesh = bpy.data.meshes.new(mesh_name)
        obj = bpy.data.objects.new(mesh_name, mesh)
        bpy.context.collection.objects.link(obj)

        # Assign vertices, edges, and faces to the mesh
        mesh.from_pydata(vertices, edges, faces)
        mesh.update()

        print(f"Mesh '{mesh_name}' created with {len(vertices)} vertices, {len(edges)} edges, and {len(faces)} faces.")

