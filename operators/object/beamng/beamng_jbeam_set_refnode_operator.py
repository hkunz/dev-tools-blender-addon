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
        return f"Set the Node's '{jr.ATTR_REFNODE_ID}' attribute with ref node value '{properties.refnode_enum}' (ID: {jr.RefNode[properties.refnode_enum].value})"

    def execute(self, context):
        obj = context.active_object

        if obj and obj.type == 'MESH':
            if obj.mode != 'EDIT':
                self.report({'ERROR'}, "Please enter Edit Mode")
                return {'CANCELLED'}

            bm = bmesh.from_edit_mesh(obj.data)
            selected_verts = [v for v in bm.verts if v.select]
            enum = jr.RefNode[self.refnode_enum]
            refnode_id = enum.value
            if len(selected_verts) == 1 and refnode_id != jr.RefNode.NONE.value:
                vertex_index = selected_verts[0].index
                indices = jr.find_nodes_with_refnode_id(obj, refnode_id)
                for idx in indices:
                    print(f"Found match at index={idx}, overwriting with RefNode.NONE")
                    jr.set_refnode_id(obj, idx, jr.RefNode.NONE.value)
                jr.set_refnode_id(obj, vertex_index, refnode_id)
                self.report({'INFO'}, f"Set Node as Ref Node {enum.name}({refnode_id})")
                bmesh.update_edit_mesh(obj.data)
                return {'FINISHED'}
            if len(selected_verts) >= 1 and refnode_id == jr.RefNode.NONE.value:
                self.report({'INFO'}, f"Reset Selected Nodes with Ref Node value {enum.name}({refnode_id})")
                for v in bm.verts:
                    value = jr.get_refnode_id(obj, v.index)
                    if value == refnode_id:
                        continue
                    print(f"Reset Node({v.index}) with Ref Node value {enum.name}({refnode_id})")
                    jr.set_refnode_id(obj, v.index, refnode_id)
                return {'FINISHED'}

            self.report({'WARNING'}, "Please select exactly one Node")
            return {'CANCELLED'}
        else:
            self.report({'ERROR'}, "Active object is not a mesh")
            return {'CANCELLED'}
