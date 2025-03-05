import bmesh

class JbeamUtils:

    @staticmethod
    def get_node_id(obj, vertex_index) -> str:
        attr_name = 'jbeam_node_id'

        if not obj or obj.type != 'MESH':
            print(f"Invalid object: {repr(obj)}")
            return None

        mesh = obj.data

        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(mesh)
            if vertex_index >= len(bm.verts):
                print(f"{repr(obj)}: Vertex index {vertex_index} out of range in Edit Mode")
                return None

            v = bm.verts[vertex_index]
            layer = bm.verts.layers.string.get(attr_name)

            if layer is None:
                print(f"{repr(obj)}: Layer '{attr_name}' not found in Edit Mode")
                return None

            return v[layer].decode('utf-8')

        elif obj.mode == 'OBJECT':
            if attr_name not in mesh.attributes:
                print(f"{repr(obj)}: Attribute '{attr_name}' not found in Object Mode")
                return None

            attr_data = mesh.attributes[attr_name].data

            if vertex_index >= len(attr_data):
                print(f"{repr(obj)}: Vertex index {vertex_index} out of range in Object Mode")
                return None

            return attr_data[vertex_index].value.decode('utf-8')

        print(f"{repr(obj)}: Unknown object mode {obj.mode}")
        return None

    @staticmethod
    def set_node_id(obj, vertex_index, node_id: str):
        attr_name = 'jbeam_node_id'

        if not obj or obj.type != 'MESH':
            print(f"Invalid object: {repr(obj)}")
            return False

        mesh = obj.data

        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(mesh)
            if vertex_index >= len(bm.verts):
                print(f"{repr(obj)}: Vertex index {vertex_index} out of range in Edit Mode")
                return False

            v = bm.verts[vertex_index]
            layer = bm.verts.layers.string.get(attr_name) or bm.verts.layers.string.new(attr_name)

            v[layer] = node_id.encode('utf-8')
            return True

        elif obj.mode == 'OBJECT':
            if attr_name not in mesh.attributes:
                mesh.attributes.new(name=attr_name, type='STRING', domain='POINT')

            attr_data = mesh.attributes[attr_name].data

            if vertex_index >= len(attr_data):
                print(f"{repr(obj)}: Vertex index {vertex_index} out of range in Object Mode")
                return False

            attr_data[vertex_index].value = node_id.encode('utf-8')
            return True

        print(f"{repr(obj)}: Unknown object mode {obj.mode}")
        return False
