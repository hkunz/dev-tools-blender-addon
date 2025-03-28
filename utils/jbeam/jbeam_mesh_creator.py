import bpy

class JbeamMeshCreator:
    def __init__(self):
        self.vertex_indices: dict[str, int] = {}  # Map NodeID to vertex index
        self.mesh = None  # To store the mesh object
        self.obj = None   # To store the Blender object

    def create_empty_object(self, mesh_name="EmptyJBeamMesh"):
        """Create an empty mesh object."""
        self.mesh = bpy.data.meshes.new(mesh_name)
        self.obj = bpy.data.objects.new(mesh_name, self.mesh)
        bpy.context.collection.objects.link(self.obj)
        print(f"Empty mesh object '{mesh_name}' created.")
        return self.obj

    def add_vertices(self, nodes_list: list[object]):
        """Add vertices to the existing mesh."""
        if not self.mesh:
            raise RuntimeError("Mesh object has not been created yet. Call 'create_empty_object' first.")

        vertices = []
        for i, node in enumerate(nodes_list):
            print(f"Processing NodeID: {node.id}, Position: {node.position}")
            node.index = i  # Set the node's index
            vertices.append(node.position)  # Add node position (Vector)
            self.vertex_indices[node.id] = i  # Map NodeID to its vertex index

        # Update the mesh with vertices
        self.mesh.from_pydata(vertices, [], [])
        self.mesh.update()
        print(f"Added {len(vertices)} vertices to the mesh.")

    def add_edges(self, beams_list: list[object]):
        """Add edges to the existing mesh."""
        if not self.mesh:
            raise RuntimeError("Mesh object has not been created yet. Call 'create_empty_object' first.")

        edges = []
        for beam in beams_list:
            start_index = self.vertex_indices.get(beam.node_id1.id)
            end_index = self.vertex_indices.get(beam.node_id2.id)

            if start_index is None or end_index is None:
                print(f"Skipping beam {beam.id}: One or both nodes not found in vertices.")
                continue

            edges.append((start_index, end_index))  # Add edge based on indices

        # Ensure there are edges to add
        if not edges:
            print("No valid edges to add.")
            return

        # Update the mesh with edges
        self.mesh.from_pydata(self.mesh.vertices[:], edges, [])
        self.mesh.update()
        print(f"Added {len(edges)} edges to the mesh.")
    
    def add_faces(self, tris_list: list[object]):
        """Add faces to the existing mesh."""
        if not self.mesh:
            raise RuntimeError("Mesh object has not been created yet. Call 'create_empty_object' first.")

        faces = []
        for tri in tris_list:
            try:
                vertex_1 = self.vertex_indices[tri.node_id1.id]
                vertex_2 = self.vertex_indices[tri.node_id2.id]
                vertex_3 = self.vertex_indices[tri.node_id3.id]
                faces.append((vertex_1, vertex_2, vertex_3))
            except KeyError as e:
                print(f"Warning: Missing node ID {e} for triangle {tri}. Skipping.")

        # Update the mesh with faces
        self.mesh.from_pydata(self.mesh.vertices[:], self.mesh.edges[:], faces)
        self.mesh.update()
        print(f"Added {len(faces)} faces to the mesh.")
