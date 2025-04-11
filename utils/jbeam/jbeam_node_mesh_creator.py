import bpy

class JbeamNodeMeshCreator:
    def __init__(self):
        self.vertex_indices: dict[str, int] = {}  # Map NodeID to vertex index
        self.mesh = None
        self.obj = None

    def create_object(self, mesh_name="NodeMesh"):
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
        for i, node in enumerate(nodes_list):  # `i` will serve as the vertex index
            print(f"Processing NodeID: {node.id}, Position: {node.position}")
            node.index = i
            vertices.append(node.position)
            self.vertex_indices[node.id] = i  # Map NodeID to its vertex index

        # Update the mesh with vertices
        self.mesh.from_pydata(vertices, [], [])
        self.mesh.update()
        print(f"Added {len(vertices)} vertices to the mesh.")

    def add_edges(self, beam_list: list[object]):
        """Add edges to the existing mesh from the beam list, ensuring duplicates are handled."""
        if not self.mesh:
            raise RuntimeError("Mesh object has not been created yet. Call 'create_object' first.")
        if not beam_list:
            return
        edges = []
        unique_beams = {}  # Dictionary to store unique beams and their assigned indices
        for i, beam in enumerate(beam_list):  # Enumerate to generate indices
            # Get the node IDs for both ends of the beam
            node_id1 = beam.node_id1
            node_id2 = beam.node_id2

            beam_key = tuple(sorted([node_id1, node_id2]))  # Generate a key for the beam based on node IDs (order doesn't matter)

            # Check if the beam is unique or already exists in the dictionary
            if beam_key not in unique_beams:
                unique_beams[beam_key] = i  # If it's a new beam, assign a new index and add it to the dictionary

            beam.index = unique_beams[beam_key]  # Use the same index for duplicate beams

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
        """Add faces to the existing mesh from the triangle list, ensuring duplicates are handled."""
        if not self.mesh:
            raise RuntimeError("Mesh object has not been created yet. Call 'create_object' first.")
        if not tris_list:
            return
        faces = []
        unique_faces = {}  # Dictionary to ensure unique faces and track indices

        for triangle in tris_list:
            node_id1, node_id2, node_id3 = triangle.node_id1, triangle.node_id2, triangle.node_id3

            # Ensure all nodes exist in vertex_indices
            if node_id1 in self.vertex_indices and node_id2 in self.vertex_indices and node_id3 in self.vertex_indices:
                index1 = self.vertex_indices[node_id1]
                index2 = self.vertex_indices[node_id2]
                index3 = self.vertex_indices[node_id3]
                face = tuple((index1, index2, index3))

                if face not in unique_faces:
                    unique_faces[face] = len(unique_faces)  # Assign a unique index
                    faces.append(face)

                triangle.index = unique_faces[face]  # Ensure `triangle.index` is properly stored
            else:
                missing = [n for n in (node_id1, node_id2, node_id3) if n not in self.vertex_indices]
                print(f"Warning: Missing vertex indices for {missing}")
                triangle.index = -1  # Set to -1 if missing (to trigger the error print)

        # Update the mesh with the faces
        self.mesh.from_pydata([], [], faces)
        self.mesh.update()
        print(f"Added {len(faces)} unique faces to the mesh.")



