import bpy
from unofficial_jbeam_editor.utils.jbeam.jbeam_models import JBeamElement, Node, Beam, Triangle

class JbeamNodeMeshCreator:
    def __init__(self):
        self.vertex_indices: dict[str, int] = {}  # Map NodeID to vertex index
        self.mesh = None
        self.obj = None

        # Internal storage for cumulative mesh data
        self._vertices: list = []
        self._edges: list[tuple[int, int]] = []
        self._faces: list[tuple[int, int, int]] = []

    def create_object(self, mesh_name="NodeMesh"):
        """Create an empty mesh object."""
        self.mesh = bpy.data.meshes.new(mesh_name)
        self.obj = bpy.data.objects.new(mesh_name, self.mesh)
        bpy.context.collection.objects.link(self.obj)
        print(f"🧊 [JbeamNodeMeshCreator] Created container Node Mesh object '{mesh_name}'.")
        return self.obj

    def check_mesh_created(self):
        if not self.mesh:
            raise RuntimeError("❌ Mesh object has not been created yet. Call 'create_object' first.")

    def _rebuild_mesh(self):
        """Rebuild the mesh from current internal state."""
        self.mesh.clear_geometry()
        self.mesh.from_pydata(self._vertices, self._edges, self._faces)
        self.mesh.update()

    def add_vertices(self, nodes_list: list[Node]):
        """Append vertices to the existing mesh."""
        self.check_mesh_created()
        start_index = len(self._vertices)
        for i, node in enumerate(nodes_list):
            global_index = start_index + i
            node.index = global_index
            self.vertex_indices[node.id] = global_index
            self._vertices.append(node.position)

        self._rebuild_mesh()
        print(f"    - Added {len(nodes_list)} vertices to the mesh (total: {len(self._vertices)}).")

    def _process_elements(self, element_list: list[JBeamElement], node_count: int, get_node_ids: callable, assign_index: callable) -> list[tuple[int, ...]]:
        """Generic handler for processing edges or faces."""
        result: list[tuple[int, ...]] = []
        unique_map: dict[tuple[int, ...], int] = {}

        for element in element_list:
            node_ids = get_node_ids(element)

            if len(node_ids) != node_count:
                print(f"⚠️  Warning: Expected {node_count} node IDs, got {len(node_ids)}")
                assign_index(element, -1)
                continue

            if all(nid in self.vertex_indices for nid in node_ids):
                vert_indices = tuple(self.vertex_indices[nid] for nid in node_ids)
                key = tuple(sorted(vert_indices)) if node_count == 2 else vert_indices

                if key not in unique_map:
                    unique_map[key] = len(self._edges if node_count == 2 else self._faces)
                    result.append(vert_indices)

                assign_index(element, unique_map[key])
            else:
                missing = [nid for nid in node_ids if nid not in self.vertex_indices]
                print(f"⚠️  Warning: Missing vertex indices for {missing}")
                assign_index(element, -1)

        return result

    def add_edges(self, beam_list: list[Beam]) -> None:
        self.check_mesh_created()
        if not beam_list:
            return

        new_edges = self._process_elements(
            element_list=beam_list,
            node_count=2,
            get_node_ids=lambda b: (b.node_id1, b.node_id2),
            assign_index=lambda b, i: setattr(b, 'index', i)
        )

        self._edges.extend(new_edges)
        self._rebuild_mesh()
        print(f"    - Added {len(new_edges)} edges to the mesh (total: {len(self._edges)}).")

    def add_faces(self, tris_list: list[Triangle]) -> None:
        self.check_mesh_created()
        if not tris_list:
            return

        new_faces = self._process_elements(
            element_list=tris_list,
            node_count=3,
            get_node_ids=lambda t: (t.node_id1, t.node_id2, t.node_id3),
            assign_index=lambda t, i: setattr(t, 'index', i)
        )

        self._faces.extend(new_faces)
        self._rebuild_mesh()
        print(f"    - Added {len(new_faces)} faces to the mesh (total: {len(self._faces)}).")
