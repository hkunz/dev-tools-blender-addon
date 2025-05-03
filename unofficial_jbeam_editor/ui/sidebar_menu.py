import bpy
import logging

from typing import List, Tuple
from bpy.app.handlers import persistent

from unofficial_jbeam_editor.operators.file.beamng.beamng_export_node_mesh_to_jbeam import DEVTOOLS_JBEAMEDITOR_EXPORT_OT_BeamngExportNodeMeshToJbeam
from unofficial_jbeam_editor.operators.file.beamng.beamng_import_jbeam_as_node_mesh import DEVTOOLS_JBEAMEDITOR_IMPORT_OT_BeamngImportJbeamToNodeMesh
from unofficial_jbeam_editor.operators.file.beamng.beamng_import_pc_file_as_node_meshes import DEVTOOLS_JBEAMEDITOR_IMPORT_OT_BeamngImportPcFileToNodeMeshes
from unofficial_jbeam_editor.operators.object.armature.armature_create_bones_random_vertices_operator import OBJECT_OT_ArmatureCreateBonesRandomVertices
from unofficial_jbeam_editor.operators.object.armature.armature_create_bones_from_edge_selection_operator import OBJECT_OT_ArmatureCreateBonesFromEdgeSelection
from unofficial_jbeam_editor.operators.object.armature.armature_assign_closest_vertex_to_bone_tails_operator import OBJECT_OT_ArmatureAssignClosestVertexToBoneTails
from unofficial_jbeam_editor.operators.object.bake.bake_prepare_object_operator import OBJECT_OT_BakePrepareObject
from unofficial_jbeam_editor.operators.object.bake.bake_generate_object_operator import OBJECT_OT_BakeGenerateObject
from unofficial_jbeam_editor.operators.object.beamng.utils.beamng_jbeam_print_attributes_operators import OBJECT_OT_BeamngPrintJbeamNodeProps,  OBJECT_OT_BeamngPrintJbeamBeamProps, OBJECT_OT_BeamngPrintJbeamTriangleProps
from unofficial_jbeam_editor.operators.object.beamng.beamng_create_empties_base_operator import OBJECT_OT_BeamngCreateEmptiesBase
from unofficial_jbeam_editor.operators.object.beamng.beamng_create_metaball_cloud_operator import OBJECT_OT_BeamngCreateMetaBallCloud
from unofficial_jbeam_editor.operators.object.beamng.beamng_parent_to_start01_empty_operator import OBJECT_OT_BeamngParentToStart01Empty, OBJECT_OT_BeamngClearChildrenStart01Empty
from unofficial_jbeam_editor.operators.object.beamng.beamng_parent_to_start01_empty_operator import OBJECT_OT_BeamngClearChildrenStart01Empty, OBJECT_OT_BeamngParentToStart01Empty
from unofficial_jbeam_editor.operators.object.beamng.beamng_convert_jbeam_to_node_mesh import OBJECT_OT_BeamngConvertJbeamToNodeMesh
from unofficial_jbeam_editor.operators.object.beamng.beamng_jbeam_node_props_manager import OBJECT_OT_BeamngSaveJbeamNodeProp, OBJECT_OT_BeamngSaveJbeamBeamProp, OBJECT_OT_BeamngSaveJbeamTriangleProp, OBJECT_OT_BeamngSaveAllJbeamNodeProps, OBJECT_OT_BeamngSaveAllJbeamBeamProps, OBJECT_OT_BeamngSaveAllJbeamTriangleProps, OBJECT_OT_BeamngAddJbeamNodeProp, OBJECT_OT_BeamngAddJbeamBeamProp, OBJECT_OT_BeamngAddJbeamTriangleProp, OBJECT_OT_BeamngRemoveJbeamNodeProp, OBJECT_OT_BeamngRemoveJbeamBeamProp, OBJECT_OT_BeamngRemoveJbeamTriangleProp, OBJECT_OT_BeamngSelectJbeamNodesByProperty, OBJECT_OT_BeamngSelectJbeamBeamsByProperty, OBJECT_OT_BeamngSelectJbeamTrianglesByProperty, JbeamStructurePropertyItem, JbeamStructure, JbeamHiddenElements
from unofficial_jbeam_editor.operators.object.beamng.beamng_jbeam_rename_selected_nodes import OBJECT_OT_BeamngJbeamRenameSelectedNodes  # type:ignore
from unofficial_jbeam_editor.operators.object.beamng.beamng_jbeam_create_node_mesh import OBJECT_OT_BeamngJbeamCreateNodeMesh
from unofficial_jbeam_editor.operators.object.beamng.beamng_jbeam_set_refnode_operator import OBJECT_OT_BeamngJbeamSetRefnodeOperator
from unofficial_jbeam_editor.operators.object.beamng.utils.beamng_jbeam_select_element_operator import OBJECT_OT_BeamngJbeamSelectSpecificElement
from unofficial_jbeam_editor.operators.object.beamng.utils.beamng_jbeam_select_ref_element_operator import OBJECT_OT_BeamngJbeamSelectRefNode
from unofficial_jbeam_editor.utils.jbeam.jbeam_utils import JbeamRefnodeUtils as jr
from unofficial_jbeam_editor.operators.common.ui.toggle_dynamic_button_operator import ButtonItem, ButtonItemSelector, ToggleDynamicButtonOperator, ManageDynamicButtonsOperator


from unofficial_jbeam_editor.ui.addon_preferences import MyAddonPreferences as a
from unofficial_jbeam_editor.utils.jbeam.jbeam_selection_tracker import JbeamSelectionTracker
from unofficial_jbeam_editor.utils.utils import Utils
from unofficial_jbeam_editor.utils.object_utils import ObjectUtils as o
from unofficial_jbeam_editor.utils.icons_manager import IconsManager
from unofficial_jbeam_editor.utils.jbeam.jbeam_utils import JbeamUtils as j

IDNAME_ICONS = {
    "NodeSocketMaterial": "MATERIAL_DATA",
    "NodeSocketCollection": "OUTLINER_COLLECTION",
    "NodeSocketTexture": "TEXTURE_DATA",
    "NodeSocketImage": "IMAGE_DATA",
}
IDNAME_TYPE = {
    "NodeSocketMaterial": "materials",
    "NodeSocketCollection": "collections",
    "NodeSocketTexture": "textures",
    "NodeSocketImage": "images",
}

@persistent
def on_depsgraph_update(scene, depsgraph=None):
    context = bpy.context
    if not hasattr(context, "active_object"): # context is different when baking image
        return
    obj = context.active_object
    if not obj:
        return
    properties: MyPropertyGroup1 = context.scene.my_property_group_pointer # type: ignore
    check_object_selection_change(context, properties, obj)

def get_bake_image_resolutions(self: bpy.types.Scene, context: bpy.types.Context) -> List[Tuple[str, str, str]]:
    dimensions: List[Tuple[str, str, str]] = [
        ("ONE_K", "1024 x 1024", "1k Ideal for small textures or low-resolution objects."),
        ("TWO_K", "2048 x 2048", "2k Standard resolution for most objects and characters."),
        ("FOUR_K", "4096 x 4096", "4k High resolution for detailed textures or close-ups."),
        ("EIGHT_K", "8192 x 8192", "8k Extremely high resolution for very detailed textures."),
    ]
    return dimensions

def my_sample_update_rgb_nodes(self, context):
    mat = self.id_data
    nodes = [n for n in mat.node_tree.nodes if isinstance(n, bpy.types.ShaderNodeRGB)]
    for n in nodes:
        n.outputs[0].default_value = self.rgb_controller

def check_object_selection_change(context, properties, obj):
    # if PREVIOUS_ACTIVE_OBJECT == obj:
    #     return
    # PREVIOUS_ACTIVE_OBJECT = obj
    pass

class MyPropertyGroup1(bpy.types.PropertyGroup):

    bake_image_resolution: bpy.props.EnumProperty(
        name="Bake Image Resolution",
        description="Bake Image Resolution",
        items=get_bake_image_resolutions,
        #default="FOUR_K", # cannot set a default when using dynamic EnumProperty
    ) # type: ignore https://blender.stackexchange.com/questions/311578/how-do-you-correctly-add-ui-elements-to-adhere-to-the-typing-spec/311770#311770

    auto_bake_pack_uv_islands: bpy.props.BoolProperty(
        name="Auto Bake Pack UV Islands",
        description="Automatically pack UV Islands else if unticked use the same UV Map configuration as selected UV Map",
        default=True,
        #update=on_bool_input_change,
    ) # type: ignore

    my_float_prop: bpy.props.FloatProperty(
        name="My Float Prop",
        description="My float prop description",
        default=0,
        min=-10.0,
        max=10.0,
        precision=2,
        #update=on_float_input_change,
        #set=validate_input # does not work. so we can only update in on_input_voxelsize_change
    ) # type: ignore

    my_string_prop: bpy.props.StringProperty(
        name="My String Prop",
        description="My string prop description",
        #update=on_string_input_change
    ) # type: ignore

    my_file_input_prop: bpy.props.StringProperty(
        name="File Path",
        subtype='FILE_PATH'
    ) # type: ignore


class MyPropertyGroup2(bpy.types.PropertyGroup):
    rgb_controller: bpy.props.FloatVectorProperty(
        name="Diffuse color",
        subtype='COLOR',
        default=(1, 1, 1, 1),
        size=4,
        min=0, max=1,
        description="color picker",
        update = my_sample_update_rgb_nodes
    ) # type: ignore

class OBJECT_PT_devtools_addon_panel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_devtools_addon_panel"
    bl_label = f"JBeam Editor {Utils.get_addon_version()}"
    #use these 3 lines if you want the addon to be under a tab within N-Panel
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'JBeam Editor'
    #use these 3 lines if you want the addon to be a custom tab under Object Properties
    #bl_space_type = 'PROPERTIES'
    #bl_region_type = 'WINDOW'
    #bl_context = "object"
    #https://blender.stackexchange.com/questions/201360/how-to-control-spacing-alignment-of-label-horizontal-enum-property

    def draw(self, context) -> None:
        layout: bpy.types.UILayout = self.layout
        # box.label(text="Icon Label", icon=IconsManager.BUILTIN_ICON_MESH_DATA)
        # self.draw_sample_modifier_exposed_props(context, layout, "GeometryNodes")
        self.draw_expanded_beamng_options(context, layout, context.active_object)
        if a.is_addon_option_enabled("armature_options"):
            self.draw_expanded_armature_options(context, layout)
        if a.is_addon_option_enabled("bake_options"):
            self.draw_expanded_bake_options(context, layout)
        # self.draw_sample_color_picker(context, layout)

    def draw_sample_modifier_exposed_props(self, context, layout, md_name = "GeometryNodes"):
        # to test this function add a Geometry Nodes Modifier by the name "GeometryNodes" and add some inputs to it which will get exposed in the addon panel
        # https://blender.stackexchange.com/questions/317739/unable-to-access-exposed-material-input-in-addon-from-geometry-nodes-modifier
        ob = context.object
        if not hasattr(ob, "modifiers") or md_name not in ob.modifiers:
            return
        md = ob.modifiers[md_name]
        if md.type == "NODES" and md.node_group:
            for rna in md.node_group.interface.items_tree:
                if hasattr(rna, "in_out") and rna.in_out == "INPUT":
                    self.add_layout_gn_prop_pointer(layout, md, rna)

    def draw_expanded_armature_options(self, context, layout):
        s = context.scene
        ebox = layout.box()
        row = ebox.box().row()
        row.prop(
            s, "expanded_armature_options",
            icon=IconsManager.BUILTIN_ICON_DOWN if s.expanded_bake_options else IconsManager.BUILTIN_ICON_RIGHT,
            icon_only=True, emboss=False
        )
        row.label(text="Armature Options")
        if s.expanded_armature_options:
            col = layout.column()
            col.operator(OBJECT_OT_ArmatureCreateBonesRandomVertices.bl_idname, text="Create Bones Random Vertices")
            col.operator(OBJECT_OT_ArmatureCreateBonesFromEdgeSelection.bl_idname, text="Create Edge Bones")
            col.operator(OBJECT_OT_ArmatureAssignClosestVertexToBoneTails.bl_idname, text="Assign Vertex to Bone Tails")

    def draw_expanded_beamng_options(self, context, layout, obj):
        s = context.scene
        ebox = layout.box()
        row = ebox.box().row()
        row.prop(
            s, "expanded_beamng_options",
            icon=IconsManager.BUILTIN_ICON_DOWN if s.expanded_beamng_options else IconsManager.BUILTIN_ICON_RIGHT,
            icon_only=True, emboss=False
        )
        row.label(text="BeamNG Options")
        if not s.expanded_beamng_options:
            return

        col = layout.column()
        if a.is_addon_option_enabled("empty_options"):
            col.operator(OBJECT_OT_BeamngCreateEmptiesBase.bl_idname, text="Create Empties")
            row = col.row(align=True)
            row.operator(OBJECT_OT_BeamngClearChildrenStart01Empty.bl_idname, text="Clear Empty")
            row.separator()
            row.operator(OBJECT_OT_BeamngParentToStart01Empty.bl_idname, text="Parent Empty")
            col.separator()

        col = col.box().column()

        if not context.selected_objects:
            col.operator(DEVTOOLS_JBEAMEDITOR_IMPORT_OT_BeamngImportPcFileToNodeMeshes.bl_idname, text="Import PC File", icon="IMPORT")
            col.operator(DEVTOOLS_JBEAMEDITOR_IMPORT_OT_BeamngImportJbeamToNodeMesh.bl_idname, text="Import JBeam File", icon="IMPORT")
            col.operator(OBJECT_OT_BeamngJbeamCreateNodeMesh.bl_idname, text="Create Node Mesh", icon="OUTLINER_OB_MESH")
        elif len(context.selected_objects) == 1:
            if j.is_node_mesh(context.selected_objects[0]):
                if a.is_addon_option_enabled("debug_options"):
                    r = col.row(align=True)
                    r.operator(OBJECT_OT_BeamngPrintJbeamNodeProps.bl_idname, text="Nodes Debug", icon="CONSOLE")
                    r.operator(OBJECT_OT_BeamngPrintJbeamBeamProps.bl_idname, text="Beams Debug", icon="CONSOLE")
                    r.operator(OBJECT_OT_BeamngPrintJbeamTriangleProps.bl_idname, text="Triangles Debug", icon="CONSOLE")
            else:
                col.operator(OBJECT_OT_BeamngConvertJbeamToNodeMesh.bl_idname, text="Convert to Node Mesh", icon="OUTLINER_OB_MESH")

        if obj and obj.mode == 'EDIT':
            if s.beamng_jbeam_hidden_elements.num_hidden_nodes or s.beamng_jbeam_hidden_elements.num_hidden_beams or s.beamng_jbeam_hidden_elements.num_hidden_faces:
                h_nodes = f"Nodes({s.beamng_jbeam_hidden_elements.num_hidden_nodes}) " if s.beamng_jbeam_hidden_elements.num_hidden_nodes else ""
                h_beams = f"Beams({s.beamng_jbeam_hidden_elements.num_hidden_beams}) " if s.beamng_jbeam_hidden_elements.num_hidden_beams else ""
                h_faces = f"Faces({s.beamng_jbeam_hidden_elements.num_hidden_faces}) " if s.beamng_jbeam_hidden_elements.num_hidden_faces else ""
                row = col.row()
                split = row.split(factor=0.7)
                split.label(text=f"Hidden: {h_nodes} {h_beams} {h_faces}")
                split.operator("mesh.reveal", text="Unhide", icon="HIDE_OFF")

        msg = None
        if obj and obj.mode == 'EDIT' and obj.type == 'MESH' and j.is_node_mesh(obj):
            self.draw_jbeam_editor_options(context, col, obj)
        elif len(context.selected_objects) > 1:
            msg = "Select one Node Mesh"
        elif j.is_node_mesh(obj):
            msg = "Edit Node Mesh in Edit Mode"
        else:
            msg = "Convert to Node Mesh" if j.has_jbeam_node_id(obj) else "No Node Mesh selected"
        if msg:
            col.label(text=msg)

        col.operator(DEVTOOLS_JBEAMEDITOR_EXPORT_OT_BeamngExportNodeMeshToJbeam.bl_idname, text="Export JBeam", icon="EXPORT")

    def draw_jbeam_editor_options(self, context, box, obj):
        s = context.scene
        struct = None

        def draw_active_element(box, struct, info, factor=0.5):
            split = box.row().split(factor=factor)
            split.label(text=f"Active: {struct.name}")
            split.alignment = 'RIGHT'
            split.label(text=f"({info})")
            box.label(text=f"Selected: {struct.selection}")

        def draw_element_search(box, struct):
            r = box.row(align=True)
            label_col = r.column(align=True)
            label_col.scale_x = 0.35
            label_col.label(text="ID:")
            text_col = r.column(align=True)
            text_col.scale_x = 1.6  # Slightly increased to keep it maximized
            text_col.prop(struct, "id", text="")
            action_col = r.column(align=True)
            action_col.scale_x = 1
            sub_r = action_col.row(align=True)
            sub_r.prop(struct, "index", text="", emboss=True)
            op = sub_r.operator(OBJECT_OT_BeamngJbeamSelectSpecificElement.bl_idname, text="", icon="RESTRICT_SELECT_OFF")
            op.element_index = struct.index
            op.element_id = struct.id

        def draw_jbeam_path_input(box, struct):
            r = box.row(align=True)
            label_col = r.column(align=True)
            label_col.scale_x = 0.45
            label_col.label(text="Jbeam:")
            text_col = r.column(align=True)
            text_col.prop(struct, "jbeam_source", text="")

        def draw_scope_modifier_list(select, save, remove):
            if not s.beamng_jbeam_active_structure.prop_items:
                box.label(text=f"No Scope Modifers on Selection")
                return
            for prop in s.beamng_jbeam_active_structure.prop_items:
                r = box.row(align=True)
                split = r.split(factor=0.55, align=True)
                split.prop(prop, "name", text="")
                split.prop(prop, "value", text="")
                button_row = r.row(align=True)
                button_row.operator(select, text="", icon="RESTRICT_SELECT_OFF").prop_name = prop.name
                button_row.operator(save, text="", icon="FILE_TICK").prop_name = prop.name
                button_row.operator(remove, text="", icon="TRASH").prop_name = prop.name

        def draw_element_instances_buttons(layout):
            settings = context.scene.beamng_jbeam_instance.buttons
            r = layout.row(align=True)
            button_name = ButtonItem.BUTTON_NAME
            for i, item in enumerate(settings):
                o = r.operator(
                    "wm.toggle_dynamic_button",
                    text=ButtonItem.generate_button_name(i) if not item.name else item.name,
                    depress=bool(item.name)
                )
                o.index = i
                o.button_name = button_name
            #r.separator()
            o = r.operator(ManageDynamicButtonsOperator.bl_idname, text="", icon="EVENT_PLUS")
            o.action = 'ADD'
            o.button_name = button_name
            if len(settings) > 1:
                o = r.operator(ManageDynamicButtonsOperator.bl_idname, text="", icon="TRASH")
                o.action = 'REMOVE'
                o.button_name = button_name

            #selected = [item.name for item in settings if item.name]
            #logging.debug(f"Selected: {', '.join(selected) if selected else 'None'}")

        def draw_bottom_options(add, save):
            box.operator(add, text="Add Scope Modifier", icon="RNA_ADD")
            box.operator(save, text="Save All", icon="FILE_TICK")

        struct = s.beamng_jbeam_active_structure
        index = struct.index

        if index < 0 or not struct.selection:
            msg = "Select elements to view Scope Modifiers" if j.is_node_mesh(obj) else "Convert to Node Mesh"
            box.label(text=msg)
            draw_element_search(box, struct)
            return

        if o.is_vertex_selection_mode():
            draw_active_element(box, struct, f"{struct.position.x:.2f}, {struct.position.y:.2f}, {struct.position.z:.2f}", 0.35)
            draw_element_search(box, struct)
            box.operator(OBJECT_OT_BeamngJbeamRenameSelectedNodes.bl_idname, text="Assign Node ID", icon="GREASEPENCIL")
            r = box.row(align=True)
            label_col = r.column(align=True)
            label_col.scale_x = 0.4
            label_col.label(text="REF:")
            enum_col = r.column(align=True)
            enum_col.scale_x = 1.3
            enum_col.prop(struct, "refnode_enum", text="")
            action_col = r.column(align=True)
            action_col.scale_x = 1
            sub_r = action_col.row(align=True)
            sub_r.operator(OBJECT_OT_BeamngJbeamSetRefnodeOperator.bl_idname, text="Assign").refnode_enum = struct.refnode_enum
            op = sub_r.operator(OBJECT_OT_BeamngJbeamSelectRefNode.bl_idname, text="", icon="RESTRICT_SELECT_OFF")
            op.refnode_enum = struct.refnode_enum
            draw_jbeam_path_input(box, struct)
            draw_scope_modifier_list(OBJECT_OT_BeamngSelectJbeamNodesByProperty.bl_idname, OBJECT_OT_BeamngSaveJbeamNodeProp.bl_idname, OBJECT_OT_BeamngRemoveJbeamNodeProp.bl_idname)
            draw_bottom_options(OBJECT_OT_BeamngAddJbeamNodeProp.bl_idname, OBJECT_OT_BeamngSaveAllJbeamNodeProps.bl_idname)

        elif o.is_edge_selection_mode():
            draw_active_element(box, struct, f"Length={struct.calc_info:.2f}", 0.35)
            draw_element_search(box, struct)
            draw_jbeam_path_input(box, struct)
            draw_element_instances_buttons(box.row())
            draw_scope_modifier_list(OBJECT_OT_BeamngSelectJbeamBeamsByProperty.bl_idname, OBJECT_OT_BeamngSaveJbeamBeamProp.bl_idname, OBJECT_OT_BeamngRemoveJbeamBeamProp.bl_idname)
            draw_bottom_options(OBJECT_OT_BeamngAddJbeamBeamProp.bl_idname, OBJECT_OT_BeamngSaveAllJbeamBeamProps.bl_idname)

        elif o.is_face_selection_mode():
            draw_active_element(box, struct, f"Area={struct.calc_info:.2f}")
            draw_element_search(box, struct)
            draw_jbeam_path_input(box, struct)
            draw_element_instances_buttons(box.row())
            draw_scope_modifier_list(OBJECT_OT_BeamngSelectJbeamTrianglesByProperty.bl_idname, OBJECT_OT_BeamngSaveJbeamTriangleProp.bl_idname, OBJECT_OT_BeamngRemoveJbeamTriangleProp.bl_idname)
            draw_bottom_options(OBJECT_OT_BeamngAddJbeamTriangleProp.bl_idname, OBJECT_OT_BeamngSaveAllJbeamTriangleProps.bl_idname)

    def draw_expanded_bake_options(self, context, layout):
        ebox = layout.box()
        row = ebox.box().row()
        row.prop(
            context.scene, "expanded_bake_options",
            icon=IconsManager.BUILTIN_ICON_DOWN if context.scene.expanded_bake_options else IconsManager.BUILTIN_ICON_RIGHT,
            icon_only=True, emboss=False
        )
        row.label(text="Bake Options")
        if context.scene.expanded_bake_options:
            col = layout.column()
            row = col.row()
            properties: MyPropertyGroup1 = context.scene.my_property_group_pointer
            col.prop(properties, "bake_image_resolution", text="")
            col.prop(properties, "auto_bake_pack_uv_islands", text="Auto Pack UV Islands")
            col.operator(OBJECT_OT_BakePrepareObject.bl_idname, text="Prepare Bake")
            col.operator(OBJECT_OT_BakeGenerateObject.bl_idname, text="Generate Bake Object")
            
            #col.prop(data=context.scene.render,property="fps",text="Frame Rate") # https://blender.stackexchange.com/questions/317553/how-to-exposure-render-settings-to-addon-panel/317565#317565
            #self.add_layout_gn_prop(layout, context.object.modifiers["Geometry Nodes"], "Socket_2") # https://blender.stackexchange.com/questions/317571/how-can-i-expose-geometry-nodes-properties-in-my-addon-panel/317586
            #col.operator(EXPORT_OT_file_vox.bl_idname, text="Export Button")

    def draw_sample_color_picker(self, context, layout):
        ob = context.object
        if not ob: return
        mat = ob.active_material
        layout.prop(mat.my_slot_setting, "rgb_controller")
        # sample to set the color via python:
        # ob.active_material.slot_setting.rgb_controller = (1, 0, 0, 1)

    def add_layout_gn_prop(self, layout, modifier, prop_id):
        name = o.get_modifier_prop_name(modifier, prop_id)
        layout.prop(data=modifier, property=f'["{prop_id}"]', text=name)

    def add_layout_gn_prop_pointer(self, layout, md, rna): # Need to ensure that md and identifier are correct
        if rna.bl_socket_idname == "NodeSocketGeometry":
            return
        if rna.bl_socket_idname in IDNAME_ICONS:
            layout.prop_search(md, f'["{rna.identifier}"]',
                search_data = bpy.data,
                search_property = IDNAME_TYPE[rna.bl_socket_idname],
                icon = IDNAME_ICONS[rna.bl_socket_idname],
                text = "My " + rna.name
            )
        else:
            layout.prop(md, f'["{rna.identifier}"]', text=rna.name)

    @classmethod
    def poll(cls, context):
        return True

def on_register_complete():
    ToggleDynamicButtonOperator.handler = ManageDynamicButtonsOperator.handler = JbeamSelectionTracker.get_instance()

def register() -> None:
    bpy.utils.register_class(OBJECT_PT_devtools_addon_panel)
    bpy.utils.register_class(MyPropertyGroup1)
    bpy.utils.register_class(MyPropertyGroup2)
    bpy.utils.register_class(JbeamStructurePropertyItem)
    bpy.utils.register_class(JbeamStructure)
    bpy.utils.register_class(JbeamHiddenElements)
    bpy.utils.register_class(ButtonItem)
    bpy.utils.register_class(ButtonItemSelector)
    bpy.utils.register_class(ToggleDynamicButtonOperator)
    bpy.utils.register_class(ManageDynamicButtonsOperator)
    bpy.types.Material.my_slot_setting = bpy.props.PointerProperty(type=MyPropertyGroup2)
    bpy.types.Scene.my_property_group_pointer = bpy.props.PointerProperty(type=MyPropertyGroup1)
    bpy.types.Scene.expanded_armature_options = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.expanded_bake_options = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.expanded_beamng_options = bpy.props.BoolProperty(default=True)
    bpy.types.Scene.beamng_jbeam_active_structure = bpy.props.PointerProperty(type=JbeamStructure)
    bpy.types.Scene.beamng_jbeam_hidden_elements = bpy.props.PointerProperty(type=JbeamHiddenElements)
    bpy.types.Scene.beamng_jbeam_instance = bpy.props.PointerProperty(type=ButtonItemSelector)
    bpy.app.handlers.depsgraph_update_post.append(on_depsgraph_update)
    on_register_complete()

def unregister() -> None:
    bpy.utils.unregister_class(OBJECT_PT_devtools_addon_panel)
    bpy.utils.unregister_class(MyPropertyGroup1)
    bpy.utils.unregister_class(MyPropertyGroup2)
    bpy.utils.unregister_class(JbeamStructurePropertyItem)
    bpy.utils.unregister_class(JbeamStructure)
    bpy.utils.unregister_class(JbeamHiddenElements)
    bpy.utils.unregister_class(ButtonItemSelector)  
    bpy.utils.unregister_class(ButtonItem)
    bpy.utils.unregister_class(ToggleDynamicButtonOperator)
    bpy.utils.unregister_class(ManageDynamicButtonsOperator)
    del bpy.types.Material.my_slot_setting
    del bpy.types.Scene.expanded_armature_options
    del bpy.types.Scene.expanded_bake_options
    del bpy.types.Scene.expanded_beamng_options
    del bpy.types.Scene.my_property_group_pointer
    del bpy.types.Scene.beamng_jbeam_active_structure
    del bpy.types.Scene.beamng_jbeam_hidden_elements
    del bpy.types.Scene.beamng_jbeam_instance
    bpy.app.handlers.depsgraph_update_post.remove(on_depsgraph_update)
