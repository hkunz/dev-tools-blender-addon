import bpy
import bmesh
import re

from unofficial_jbeam_editor.utils.object_utils import ObjectUtils as o
from unofficial_jbeam_editor.utils.jbeam.jbeam_utils import JbeamUtils as j, JbeamRefnodeUtils as jr

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
        return f"Select the Nodes assigned with ref node '{properties.refnode_enum}' (ID: {jr.RefNode[properties.refnode_enum].value})"

    def execute(self, context):

        obj = context.object
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)

        # Deselect all elements
        for v in bm.verts:
            v.select = False
        for e in bm.edges:
            e.select = False
        for f in bm.faces:
            f.select = False

        if not o.is_vertex_selection_mode():
            return {'CANCELLED'}

        refnode_id = jr.RefNode[self.refnode_enum].value
        indices = jr.find_nodes_with_refnode_id(obj, refnode_id)
        if not indices:
            self.report({'INFO'}, f"No nodes found with '{self.refnode_enum}' (ID: {refnode_id})")
            return {'FINISHED'}

        element = None
        for idx in indices:
            element = bm.verts[idx]
            element.select = True

        if element:
            bm.select_history.add(element)
            bmesh.update_edit_mesh(obj.data)
            self.report({'INFO'}, f"Selected {len(indices)} Node(s)")
        return {'FINISHED'}
