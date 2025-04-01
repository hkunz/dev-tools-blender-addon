import bpy
import bmesh
import re

from dev_tools.utils.object_utils import ObjectUtils as o  # type: ignore
from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j, JbeamRefnodeUtils as jr # type: ignore

class OBJECT_OT_BeamngJbeamSelectRefNode(bpy.types.Operator):
    bl_idname = "object.devtools_beamng_jbeam_select_ref_node"
    bl_label = "DevTools: Select Ref Node Element"
    bl_options = {'INTERNAL', 'UNDO'}

    refnode_enum: bpy.props.EnumProperty(
        name="Refnode",
        items=[(e.name, e.name, "") for e in jr.RefNode],
        default=jr.RefNode.NONE.name,
    )  # type: ignore

    @classmethod
    def description(cls, context, properties):
        return f"Search for the Node's '{jr.ATTR_REFNODE_ID}' attribute containing the ref node value '{properties.refnode_enum}' (ID: {jr.RefNode[properties.refnode_enum].value})"

    def execute(self, context):
        obj = context.object
        bm = bmesh.from_edit_mesh(obj.data)
        print("YES")

        return {'FINISHED'}
