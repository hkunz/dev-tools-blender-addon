import bpy
import bmesh

from dev_tools.utils.jbeam.jbeam_utils import JbeamRefnodeUtils as jr  # type: ignore

class OBJECT_OT_BeamngJbeamSetRefnodeOperator(bpy.types.Operator):
    """Operator to set the refnode ID of a selected Node"""
    bl_idname = "mesh.devtools_beamng_set_refnode_id"
    bl_label = "DevTools: Set Refnode ID"
    bl_options = {'INTERNAL', 'UNDO'}

    refnode_enum: bpy.props.EnumProperty(
        name="Refnode",
        items=[(e.name, e.name, "") for e in jr.RefNode],
        default=jr.RefNode.NONE.name,
    )  # type: ignore

    @classmethod
    def description(cls, context, properties):
        return f"Set the node to {properties.refnode_enum} (ID: {jr.RefNode[properties.refnode_enum].value})"

    def execute(self, context):
        obj = context.active_object

        if obj and obj.type == 'MESH':
            # Ensure we are in Edit Mode
            if obj.mode != 'EDIT':
                self.report({'ERROR'}, "Please enter Edit Mode")
                return {'CANCELLED'}

            bm = bmesh.from_edit_mesh(obj.data)
            selected_verts = [v for v in bm.verts if v.select]

            if len(selected_verts) == 1:
                vertex_index = selected_verts[0].index
                enum = jr.RefNode[self.refnode_enum]
                self.report({'INFO'}, f"Set Node as {enum.name}({enum.value})")
                jr.set_refnode_id(obj, vertex_index, enum.value)
                bmesh.update_edit_mesh(obj.data)  # Update the mesh after making changes
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, "Please select exactly one Node")
                return {'CANCELLED'}
        else:
            self.report({'ERROR'}, "Active object is not a mesh")
            return {'CANCELLED'}
