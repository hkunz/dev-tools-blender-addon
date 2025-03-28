import bpy

class JbeamMeshCreator:
    def __init__(self):
        self.vertex_indices: dict[str, int] = {}  # Map NodeID to vertex index
        self.mesh = None  # To store the mesh object
        self.obj = None   # To store the Blender object

    def create_object(self, mesh_name="EmptyJBeamMesh"):
        """Create an empty mesh object."""
        self.mesh = bpy.data.meshes.new(mesh_name)
        self.obj = bpy.data.objects.new(mesh_name, self.mesh)
        bpy.context.collection.objects.link(self.obj)
        print(f"Empty mesh object '{mesh_name}' created.")
        return self.obj

    def add_vertices(self, nodes_list: list[object]):
        """Add vertices to the existing mesh."""
        if not self.mesh:
            raise RuntimeError("Mesh object has not been created yet. Call 'create_object' first.")

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

    def add_edges(self, beam_list: list[object]):
        """Add edges to the existing mesh from the beam list."""
        if not self.mesh:
            raise RuntimeError("Mesh object has not been created yet. Call 'create_object' first.")

        edges = []
        for beam in beam_list:
            # Get the node IDs for both ends of the beam
            node_id1 = beam.node_id1
            node_id2 = beam.node_id2

            # Check if the node IDs exist in vertex_indices (which maps NodeID to vertex index)
            if node_id1 in self.vertex_indices and node_id2 in self.vertex_indices:
                index1 = self.vertex_indices[node_id1]
                index2 = self.vertex_indices[node_id2]
                edges.append((index1, index2))  # Add the edge as a tuple of vertex indices
            else:
                print(f"Warning: Could not find vertices for Beam with NodeIDs {node_id1} and {node_id2}")

        # Update the mesh with the edges
        self.mesh.from_pydata([], edges, [])
        self.mesh.update()
        print(f"Added {len(edges)} edges to the mesh.")
    
    def add_faces(self, tris_list: list[object]):
        """Add faces to the existing mesh from the triangle list."""
        if not self.mesh:
            raise RuntimeError("Mesh object has not been created yet. Call 'create_object' first.")

        faces = []
        for triangle in tris_list:
            # Get the node IDs for the three vertices of the triangle
            node_id1 = triangle.node_id1
            node_id2 = triangle.node_id2
            node_id3 = triangle.node_id3

            # Check if the node IDs exist in vertex_indices (which maps NodeID to vertex index)
            if node_id1 in self.vertex_indices and node_id2 in self.vertex_indices and node_id3 in self.vertex_indices:
                index1 = self.vertex_indices[node_id1]
                index2 = self.vertex_indices[node_id2]
                index3 = self.vertex_indices[node_id3]
                faces.append((index1, index2, index3))  # Add the face as a tuple of vertex indices
            else:
                print(f"Warning: Could not find vertices for Triangle with NodeIDs {node_id1}, {node_id2}, and {node_id3}")

        # Update the mesh with the faces
        self.mesh.from_pydata([], [], faces)
        self.mesh.update()
        print(f"Added {len(faces)} faces to the mesh.")

