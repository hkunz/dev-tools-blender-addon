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

        edges: list[tuple[int, int]] = []
        unique_beams: dict[tuple[str, str], int] = {}  # Dictionary to store unique beam keys and their assigned indices
        next_unique_index: int = 0

        for beam in beam_list:
            node_id1 = beam.node_id1
            node_id2 = beam.node_id2
            beam_key = tuple(sorted([node_id1, node_id2]))

            if beam_key not in unique_beams:
                unique_beams[beam_key] = next_unique_index
                next_unique_index += 1

            beam.index = unique_beams[beam_key]

            if node_id1 in self.vertex_indices and node_id2 in self.vertex_indices:
                index1 = self.vertex_indices[node_id1]
                index2 = self.vertex_indices[node_id2]
                edges.append((index1, index2))
            else:
                print(f"Warning: Could not find vertices for Beam with NodeIDs {node_id1} and {node_id2}")

        self.mesh.from_pydata([], edges, [])
        self.mesh.update()
        print(f"Added {len(edges)} edges to the mesh.")

    def add_faces(self, tris_list: list[object]) -> None:
        """Add faces to the existing mesh from the triangle list, ensuring duplicates are handled."""
        if not self.mesh:
            raise RuntimeError("Mesh object has not been created yet. Call 'create_object' first.")
        if not tris_list:
            return

        faces: list[tuple[int, int, int]] = []
        unique_faces: dict[tuple[int, int, int], int] = {}

        for triangle in tris_list:
            node_id1, node_id2, node_id3 = triangle.node_id1, triangle.node_id2, triangle.node_id3

            # Ensure all nodes exist in vertex_indices
            if all(node_id in self.vertex_indices for node_id in (node_id1, node_id2, node_id3)):
                index1 = self.vertex_indices[node_id1]
                index2 = self.vertex_indices[node_id2]
                index3 = self.vertex_indices[node_id3]
                face = (index1, index2, index3)

                if face not in unique_faces:
                    unique_faces[face] = len(unique_faces)
                    faces.append(face)

                triangle.index = unique_faces[face]  # Store the face index
            else:
                missing = [nid for nid in (node_id1, node_id2, node_id3) if nid not in self.vertex_indices]
                print(f"Warning: Missing vertex indices for nodes {missing}")
                triangle.index = -1  # Mark as invalid

        # Apply the faces to the mesh
        self.mesh.from_pydata([], [], faces)
        self.mesh.update()
        print(f"Added {len(faces)} unique faces to the mesh.")




