import bpy
import bmesh

from unofficial_jbeam_editor.utils.utils import Utils
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

        # Deselect all elements
        mesh = obj.data
        for v in mesh.vertices:
            v.select = False
        for e in mesh.edges:
            e.select = False
        for f in mesh.polygons:
            f.select = False

        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)

        if not o.is_vertex_selection_mode():
            return {'CANCELLED'}

        refnode_id = jr.RefNode[self.refnode_enum].value
        indices = jr.find_nodes_with_refnode_id(obj, refnode_id)
        if not indices:
            Utils.log_and_report(f"No nodes found with '{self.refnode_enum}' (ID: {refnode_id})", self, 'INFO')
            return {'FINISHED'}

        element = None
        for idx in indices:
            element = bm.verts[idx]
            element.select = True

        if element:
            bm.select_history.add(element)
            bmesh.update_edit_mesh(obj.data)
            Utils.log_and_report(f"Selected {len(indices)} Node(s)", self, 'INFO')
        return {'FINISHED'}
