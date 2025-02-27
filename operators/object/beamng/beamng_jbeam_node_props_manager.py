import bpy
import bmesh
import json

class JbeamPropertyItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Property Name") # type: ignore
    value: bpy.props.StringProperty(name="Value") # type: ignore


class OBJECT_OT_BeamngLoadJbeamNodeProps(bpy.types.Operator):
    """Load JBeam properties of the selected vertex"""
    bl_idname = "object.devtools_beamng_load_jbeam_node_props"
    bl_label = "DevTools: BeamNG Load JBeam Node Properties"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No valid mesh object selected")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        layer = bm.verts.layers.string.get("jbeam_node_props")
        selected_verts = [v for v in bm.verts if v.select]

        if not selected_verts or not layer:
            self.report({'WARNING'}, "No selected vertices or no property data found")
            return {'CANCELLED'}

        context.scene.beamng_jbeam_vertex_props.clear()
        properties = {}

        for v in selected_verts:
            try:
                props = json.loads(v[layer].decode("utf-8")) if v[layer] else {}
                for key, value in props.items():
                    properties[key] = value
            except Exception as e:
                self.report({'ERROR'}, f"Failed to load properties: {e}")

        for key, value in properties.items():
            prop = context.scene.beamng_jbeam_vertex_props.add()
            prop.name = key
            prop.value = str(value)

        return {'FINISHED'}


class OBJECT_OT_BeamngSaveJbeamNodeProp(bpy.types.Operator):
    """Save a single JBeam node property"""
    bl_idname = "object.devtools_beamng_save_jbeam_node_prop"
    bl_label = "DevTools: BeamNG Save JBeam Node Property"
    bl_options = {'INTERNAL', 'UNDO'}

    prop_name: bpy.props.StringProperty() # type: ignore

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No valid mesh object selected")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        layer = bm.verts.layers.string.get("jbeam_node_props")
        selected_verts = [v for v in bm.verts if v.select]

        if not selected_verts or not layer:
            self.report({'WARNING'}, "No selected vertices or no property data found")
            return {'CANCELLED'}

        for v in selected_verts:
            try:
                props = json.loads(v[layer].decode("utf-8")) if v[layer] else {}
                for prop in context.scene.beamng_jbeam_vertex_props:
                    if prop.name == self.prop_name:
                        props[prop.name] = prop.value
                        break
                v[layer] = json.dumps(props).encode("utf-8")
            except Exception as e:
                self.report({'ERROR'}, f"Failed to save property: {e}")

        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Saved property: {self.prop_name}")
        return {'FINISHED'}


class OBJECT_OT_BeamngSaveAllJbeamNodeProps(bpy.types.Operator):
    """Save all JBeam node properties"""
    bl_idname = "object.devtools_beamng_save_all_jbeam_node_props"
    bl_label = "DevTools: BeamNG Save All JBeam Node Properties"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No valid mesh object selected")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        layer = bm.verts.layers.string.get("jbeam_node_props")
        selected_verts = [v for v in bm.verts if v.select]

        if not selected_verts or not layer:
            self.report({'WARNING'}, "No selected vertices or no property data found")
            return {'CANCELLED'}

        # Get current properties in the UI
        ui_props = {prop.name: prop.value for prop in context.scene.beamng_jbeam_vertex_props}

        for v in selected_verts:
            try:
                props = json.loads(v[layer].decode("utf-8")) if v[layer] else {}

                # Remove properties that are missing from the UI
                props = {k: v for k, v in props.items() if k in ui_props}

                # Update values from the UI
                for prop_name, prop_value in ui_props.items():
                    props[prop_name] = prop_value

                v[layer] = json.dumps(props).encode("utf-8")

            except Exception as e:
                self.report({'ERROR'}, f"Failed to save properties: {e}")

        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, "Saved all properties")
        return {'FINISHED'}


class OBJECT_OT_BeamngAddJbeamNodeProp(bpy.types.Operator):
    """Add a new JBeam node property"""
    bl_idname = "object.devtools_beamng_add_jbeam_node_prop"
    bl_label = "DevTools: BeamNG Add JBeam Node Property"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        prop = context.scene.beamng_jbeam_vertex_props.add()
        prop.name = "NewProp"
        prop.value = "0"
        return {'FINISHED'}


class OBJECT_OT_BeamngRemoveJbeamNodeProp(bpy.types.Operator):
    """Remove a JBeam node property"""
    bl_idname = "object.devtools_beamng_remove_jbeam_node_prop"
    bl_label = "DevTools: BeamNG Remove JBeam Node Property"
    bl_options = {'INTERNAL', 'UNDO'}

    prop_name: bpy.props.StringProperty() # type: ignore

    def execute(self, context):
        scene = context.scene
        for i, prop in enumerate(scene.beamng_jbeam_vertex_props):
            if prop.name == self.prop_name:
                scene.beamng_jbeam_vertex_props.remove(i)
                break
        return {'FINISHED'}
