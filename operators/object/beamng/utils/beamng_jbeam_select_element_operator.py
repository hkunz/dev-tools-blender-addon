import bpy
import bmesh
import re

from dev_tools.utils.object_utils import ObjectUtils as o  # type: ignore
from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j # type: ignore

class OBJECT_OT_SelectSpecificElement(bpy.types.Operator):
    bl_idname = "object.select_specific_element"
    bl_label = "Select Specific Element"
    bl_options = {'REGISTER', 'UNDO'}

    element_id: bpy.props.StringProperty(name="Element Index", default="")  # type: ignore
    element_index: bpy.props.IntProperty(name="Element Index", default=-1)  # type: ignore

    def execute(self, context):
        print(f"Operator select  Element ID {self.element_id} or Element Index: {self.element_index} if no ID is specified")
        obj = context.object
        bm = bmesh.from_edit_mesh(obj.data)

        def get_element_index(id, getter_func):
            if not id:
                return self.element_index
            index = getter_func()
            if index < 0:
                self.report({'WARNING'}, f"Node ID '{id}' not found")
            else:
                self.report({'INFO'}, f"Node ID '{id}' in Selection")
            return index

        def parse_node_ids(node_string):
            node_string = node_string.strip('[]')
            node_string = node_string.replace(';', ',').replace('|', ',')  # Convert all delimiters to commas, Replace all delimiters (comma, semicolon, pipe) with a common delimiter (e.g., comma)
            node_ids = re.findall(r'n\d+', node_string)
            return node_ids

        # Deselect all elements
        for v in bm.verts:
            v.select = False
        for e in bm.edges:
            e.select = False
        for f in bm.faces:
            f.select = False

        # FIXME: this code only puts element in selection but not active
        if o.is_vertex_selection_mode():
            index = get_element_index(self.element_id, lambda: j.get_node_index(obj, self.element_id))
            if 0 <= index < len(bm.verts):
                bm.verts[index].select = True
        elif o.is_edge_selection_mode():
            node_ids = parse_node_ids(self.element_id)
            index = get_element_index(self.element_id, lambda: j.get_beam_index(obj, node_ids[0], node_ids[1]))
            if 0 <= index < len(bm.edges):
                bm.edges[index].select = True
        elif o.is_face_selection_mode():
            node_ids = parse_node_ids(self.element_id)
            index = get_element_index(self.element_id, lambda: j.get_triangle_index(obj, node_ids[0], node_ids[1], node_ids[2]))
            if 0 <= index < len(bm.faces):
                bm.faces[index].select = True

        # Update the mesh to reflect changes
        bmesh.update_edit_mesh(obj.data)

        return {'FINISHED'}
