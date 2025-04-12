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
            #print(f"Processing NodeID: {node.id}, Position: {node.position}")
            node.index = i
            vertices.append(node.position)
            self.vertex_indices[node.id] = i  # Map NodeID to its vertex index
        print(f"Processing Node ID list complete")
        self.mesh.from_pydata(vertices, [], [])
        self.mesh.update()
        print(f"Added {len(vertices)} vertices to the mesh.")

    def _process_elements(self, element_list: list[object], node_count: int, get_node_ids: callable, assign_index: callable) -> list[tuple[int, ...]]:
        """Generic handler for processing edges or faces."""
        result: list[tuple[int, ...]] = []
        unique_map: dict[tuple[int, ...], int] = {}

        for element in element_list:
            node_ids = get_node_ids(element)

            if len(node_ids) != node_count:
                print(f"Warning: Expected {node_count} node IDs, got {len(node_ids)}")
                assign_index(element, -1)
                continue

            if all(nid in self.vertex_indices for nid in node_ids): # Check all node IDs exist
                vert_indices = tuple(self.vertex_indices[nid] for nid in node_ids)
                key = tuple(sorted(vert_indices)) if node_count == 2 else vert_indices  # For edges, sort the tuple to make order irrelevant

                if key not in unique_map:
                    unique_map[key] = len(unique_map)
                    result.append(vert_indices)

                assign_index(element, unique_map[key])
            else:
                missing = [nid for nid in node_ids if nid not in self.vertex_indices]
                print(f"Warning: Missing vertex indices for {missing}")
                assign_index(element, -1)

        return result

    def add_edges(self, beam_list: list[object]) -> None:
        if not self.mesh:
            raise RuntimeError("Mesh object has not been created yet. Call 'create_object' first.")
        if not beam_list:
            return

        edges = self._process_elements(
            element_list=beam_list,
            node_count=2,
            get_node_ids=lambda b: (b.node_id1, b.node_id2),
            assign_index=lambda b, i: setattr(b, 'index', i)
        )

        self.mesh.from_pydata([], edges, [])
        self.mesh.update()
        print(f"Added {len(edges)} edges to the mesh.")

    def add_faces(self, tris_list: list[object]) -> None:
        if not self.mesh:
            raise RuntimeError("Mesh object has not been created yet. Call 'create_object' first.")
        if not tris_list:
            return

        faces = self._process_elements(
            element_list=tris_list,
            node_count=3,
            get_node_ids=lambda t: (t.node_id1, t.node_id2, t.node_id3),
            assign_index=lambda t, i: setattr(t, 'index', i)
        )

        self.mesh.from_pydata([], [], faces)
        self.mesh.update()
        print(f"Added {len(faces)} unique faces to the mesh.")
