import bpy
import bmesh

from dev_tools.utils.object_utils import ObjectUtils as o  # type: ignore

class OBJECT_OT_SelectSpecificElement(bpy.types.Operator):
    bl_idname = "object.select_specific_element"
    bl_label = "Select Specific Element"
    bl_options = {'REGISTER', 'UNDO'}

    element_index: bpy.props.IntProperty(name="Element Index", default=0)

    def execute(self, context):
        print(f"Operator executed with Element Index: {self.element_index}")
        obj = context.object
        bm = bmesh.from_edit_mesh(obj.data)
        
        # Deselect all elements
        for v in bm.verts:
            v.select = False
        for e in bm.edges:
            e.select = False
        for f in bm.faces:
            f.select = False
        
        # Now select the specific element
        if o.is_vertex_selection_mode():
            if 0 <= self.element_index < len(bm.verts):
                bm.verts[self.element_index].select = True
        elif o.is_edge_selection_mode():
            if 0 <= self.element_index < len(bm.edges):
                bm.edges[self.element_index].select = True
        elif o.is_face_selection_mode():
            if 0 <= self.element_index < len(bm.faces):
                bm.faces[self.element_index].select = True

        # Update the mesh to reflect changes
        bmesh.update_edit_mesh(obj.data)

        return {'FINISHED'}
