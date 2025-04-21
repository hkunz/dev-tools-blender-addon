import bpy
import bmesh

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

    def add_vertices(self, nodes_list: list[Node]):
        self.check_mesh_created()

        num_new = len(nodes_list)
        start_index = len(self.mesh.vertices)

        self.mesh.vertices.add(num_new)

        for i, node in enumerate(nodes_list):
            global_index = start_index + i
            node.index = global_index
            self.vertex_indices[node.id] = global_index
            self.mesh.vertices[global_index].co = node.position
            self._vertices.append(node.position)

        print(f"    - Added {num_new} vertices (total: {len(self.mesh.vertices)}).")

    def _process_elements(self, element_list: list[JBeamElement], node_count: int, get_node_ids: callable, assign_index: callable) -> list[tuple[int, ...]]:
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

        num_new = len(new_edges)
        start_index = len(self.mesh.edges)

        self.mesh.edges.add(num_new)
        for i, edge in enumerate(new_edges):
            self.mesh.edges[start_index + i].vertices = edge
            self._edges.append(edge)

        print(f"    - Added {num_new} edges (total: {len(self.mesh.edges)}).")


    def add_faces(self, tris_list: list[Triangle]) -> None:
        self.check_mesh_created()
        if not tris_list:
            return

        bm = bmesh.new()
        bm.from_mesh(self.mesh)

        new_faces = self._process_elements(
            element_list=tris_list,
            node_count=3,
            get_node_ids=lambda t: (t.node_id1, t.node_id2, t.node_id3),
            assign_index=lambda t, i: setattr(t, 'index', i)
        )

        verts = [v for v in bm.verts]

        for face in new_faces:
            try:
                bm.verts.ensure_lookup_table()
                bm.faces.new([verts[i] for i in face])
                self._faces.append(face)
            except ValueError:
                # Face already exists, ignore
                continue

        bm.to_mesh(self.mesh)
        bm.free()

        print(f"    - Added {len(new_faces)} faces (total: {len(self.mesh.polygons)}).")

