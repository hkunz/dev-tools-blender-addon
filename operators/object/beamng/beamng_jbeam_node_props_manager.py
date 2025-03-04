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

        # Sort properties alphabetically (case-insensitive)
        sorted_props = sorted(properties.items(), key=lambda item: item[0].lower())

        # Add sorted properties to scene properties
        for key, value in sorted_props:
            prop = context.scene.beamng_jbeam_vertex_props.add()
            prop.name = key
            prop.value = str(value)

        return {'FINISHED'}



class OBJECT_OT_BeamngSaveJbeamNodeProp(bpy.types.Operator):
    """Save a single JBeam node property for selected vertices"""
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
                if any(prop.name.lower() == "group" for prop in context.scene.beamng_jbeam_vertex_props):
                    self.report({'WARNING'}, "Keyword 'group' is reserved. Use vertex groups prefixed 'group_' to assign nodes to groups.")
                    return {'CANCELLED'}
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
    """Save all JBeam node properties for selected vertices"""
    bl_idname = "object.devtools_beamng_save_all_jbeam_node_props"
    bl_label = "DevTools: BeamNG Save All JBeam Node Properties"
    bl_options = {'INTERNAL', 'UNDO'}

    @staticmethod
    def save_jbeam_node_props(context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            return "No valid mesh object selected", 'CANCELLED'

        bm = bmesh.from_edit_mesh(obj.data)
        layer = bm.verts.layers.string.get("jbeam_node_props")
        selected_verts = [v for v in bm.verts if v.select]

        if not selected_verts or not layer:
            return "No selected vertices or no property data found", 'CANCELLED'

        # Get current properties in the UI
        ui_props = {prop.name: prop.value for prop in context.scene.beamng_jbeam_vertex_props}
        if any(prop_name.lower() == "group" for prop_name in ui_props):
            return "Keyword 'group' is reserved. Use vertex groups prefixed 'group_' to assign nodes to groups.", 'CANCELLED'

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
                return f"Failed to save properties: {e}", 'ERROR'

        bmesh.update_edit_mesh(obj.data)
        return "Saved all properties", 'FINISHED'

    def execute(self, context):
        msg, status = self.save_jbeam_node_props(context)
        self.report({'INFO' if status == 'FINISHED' else 'WARNING'}, msg)
        return {status}


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

'''
class OBJECT_OT_BeamngRemoveJbeamNodeProp(bpy.types.Operator):
    """Remove a JBeam node property (Shift+Click to also save)"""
    bl_idname = "object.devtools_beamng_remove_jbeam_node_prop"
    bl_label = "DevTools: BeamNG Remove JBeam Node Property"
    bl_descrikption = "Remove JBeam Node Property (hold Shift to also directly save change)"
    bl_options = {'INTERNAL', 'UNDO'}

    prop_name: bpy.props.StringProperty() # type: ignore

    def invoke(self, context, event):
        """Detect Shift and pass it to execute"""
        self.do_save = event.shift  # Store Shift state
        return self.execute(context)

    def execute(self, context):
        scene = context.scene

        # Remove property from UI list
        for i, prop in enumerate(scene.beamng_jbeam_vertex_props):
            if prop.name == self.prop_name:
                scene.beamng_jbeam_vertex_props.remove(i)
                break

        # If Shift was held, save immediately
        if getattr(self, "do_save", False):
            save_jbeam_node_props(context)  # Call the function directly
            self.report({'INFO'}, "Property removed and saved")

        return {'FINISHED'}
'''