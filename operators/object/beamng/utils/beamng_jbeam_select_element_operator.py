import bpy

class OBJECT_OT_SelectSpecificElement(bpy.types.Operator):
    """Select a specific vertex, edge, or face by index"""
    bl_idname = "object.select_specific_element"
    bl_label = "Select Specific Element"
    bl_options = {'REGISTER', 'UNDO'}

    element_index: bpy.props.IntProperty(name="Element Index", default=0)  # type: ignore
    element_type: bpy.props.EnumProperty(
        name="Element Type",
        items=[
            ('VERT', "Vertex", "Select a vertex"),
            ('EDGE', "Edge", "Select an edge"),
            ('FACE', "Face", "Select a face"),
        ],
        default='VERT',
    )  # type: ignore

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}

        mesh = obj.data
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')  # Deselect everything
        bpy.ops.object.mode_set(mode='OBJECT')

        elements = {
            'VERT': mesh.vertices,
            'EDGE': mesh.edges,
            'FACE': mesh.polygons
        }
        
        if self.element_index < 0 or self.element_index >= len(elements[self.element_type]):
            self.report({'ERROR'}, "Invalid element index")
            return {'CANCELLED'}

        # Select the specified element
        elements[self.element_type][self.element_index].select = True

        # Switch back to edit mode
        bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}

# Register
def register():
    bpy.utils.register_class(OBJECT_OT_SelectSpecificElement)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_SelectSpecificElement)

if __name__ == "__main__":
    register()
