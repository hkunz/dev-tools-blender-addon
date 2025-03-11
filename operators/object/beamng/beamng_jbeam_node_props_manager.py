import bpy
import bmesh

from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j # type: ignore

class JbeamPropertyItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Property Name") # type: ignore
    value: bpy.props.StringProperty(name="Value") # type: ignore


class OBJECT_OT_BeamngLoadJbeamPropsBase(bpy.types.Operator):
    """Base class for loading JBeam properties"""
    
    bl_options = {'INTERNAL', 'UNDO'}
    
    domain = None  # Must be set in subclasses
    layer_name = ""
    scene_property_name = ""
    get_props_function = None

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No valid mesh object selected")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        layer = getattr(bm, self.domain).layers.string.get(self.layer_name)
        selected_elements = [e for e in getattr(bm, self.domain) if e.select]

        if not layer:
            self.report({'WARNING'}, "No layer found")

        if not selected_elements:
            print("No selection or no property data found")
            return {'CANCELLED'}

        scene_props = getattr(context.scene, self.scene_property_name)
        scene_props.clear()
        properties = {}

        for elem in selected_elements:
            props = self.get_props_function(obj, elem.index)
            for key, value in props.items():
                properties[key] = value

        # Sort properties alphabetically (case-insensitive)
        sorted_props = sorted(properties.items(), key=lambda item: item[0].lower())

        # Add sorted properties to scene properties
        for key, value in sorted_props:
            prop = scene_props.add()
            prop.name = key
            prop.value = str(value)

        return {'FINISHED'}

class OBJECT_OT_BeamngLoadJbeamNodeProps(OBJECT_OT_BeamngLoadJbeamPropsBase):
    """Load JBeam properties of the selected vertex"""
    
    bl_idname = "object.devtools_beamng_load_jbeam_node_props"
    bl_label = "DevTools: BeamNG Load JBeam Node Properties"

    domain = "verts"
    layer_name = "jbeam_node_props"
    scene_property_name = "beamng_jbeam_vertex_props"
    get_props_function = staticmethod(j.get_node_props)  # Set function for nodes

class OBJECT_OT_BeamngLoadJbeamBeamProps(OBJECT_OT_BeamngLoadJbeamPropsBase):
    """Load JBeam properties of the selected edge beam"""
    
    bl_idname = "object.devtools_beamng_load_jbeam_beam_props"
    bl_label = "DevTools: BeamNG Load JBeam Beam Properties"

    domain = "edges"
    layer_name = "jbeam_beam_props"
    scene_property_name = "beamng_jbeam_edge_props"
    get_props_function = staticmethod(j.get_beam_props)  # Set function for beams


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
                props = j.get_node_props(obj, v.index)
                if any(prop.name.lower() == "group" for prop in context.scene.beamng_jbeam_vertex_props):
                    self.report({'WARNING'}, "Keyword 'group' is reserved. Use vertex groups prefixed 'group_' to assign nodes to groups.")
                    return {'CANCELLED'}
                for prop in context.scene.beamng_jbeam_vertex_props:
                    if prop.name == self.prop_name:
                        props[prop.name] = prop.value
                        break
                j.set_node_props(obj, v.index, props)
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
                props = j.get_node_props(obj, v.index)
                props = {k: v for k, v in props.items() if k in ui_props} # Remove properties that are missing from the UI

                # Update values from the UI
                for prop_name, prop_value in ui_props.items():
                    props[prop_name] = prop_value

                j.set_node_props(obj, v.index, props)

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


class OBJECT_OT_BeamngRemoveJbeamNodeProp(bpy.types.Operator):
    """Remove a JBeam node property (Shift+Click to also save)"""
    bl_idname = "object.devtools_beamng_remove_jbeam_node_prop"
    bl_label = "DevTools: BeamNG Remove JBeam Node Property"
    bl_options = {'INTERNAL', 'UNDO'}

    prop_name: bpy.props.StringProperty()  # type: ignore

    def invoke(self, context, event):
        """Detect Shift and pass it to execute"""
        self.do_save = bool(event.shift)
        return self.execute(context)

    def execute(self, context):
        scene = context.scene
        obj = context.object

        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No valid mesh object selected")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        layer = bm.verts.layers.string.get("jbeam_node_props")

        if not layer:
            self.report({'WARNING'}, "No property data found")
            return {'CANCELLED'}

        selected_verts = [v for v in bm.verts if v.select]
        if not selected_verts:
            self.report({'WARNING'}, "No selected vertices found")
            return {'CANCELLED'}

        removed_from_ui = False
        removed_from_mesh = False

        # Always remove from the UI list
        for i, prop in enumerate(scene.beamng_jbeam_vertex_props):
            if prop.name == self.prop_name:
                scene.beamng_jbeam_vertex_props.remove(i)
                removed_from_ui = True
                break  # Ensure only one instance is removed

        if self.do_save:
            # Remove property from mesh (SAVE MODE)
            for v in selected_verts:
                if not v[layer]:
                    continue  # Skip if no stored data

                try:
                    props = j.get_node_props(obj, v.index)
                    if self.prop_name in props:
                        del props[self.prop_name]  # Remove property
                        j.set_node_props(obj, v.index, props if props else {})
                        removed_from_mesh = True

                except Exception as e:
                    self.report({'ERROR'}, f"Failed to remove property: {e}")
                    return {'CANCELLED'}

            bmesh.update_edit_mesh(obj.data) # Commit changes to mesh

        if removed_from_ui and removed_from_mesh:
            self.report({'INFO'}, f"Removed property '{self.prop_name}' from UI and saved")
        elif removed_from_ui:
            self.report({'INFO'}, f"Removed property '{self.prop_name}' from UI (unsaved)")
        else:
            self.report({'WARNING'}, f"Property '{self.prop_name}' not found")

        return {'FINISHED' if removed_from_ui else 'CANCELLED'}


class OBJECT_OT_BeamngSelectJbeamNodesByProperty(bpy.types.Operator):
    """Select all vertices that share the same JBeam property and value"""
    bl_idname = "object.devtools_beamng_select_jbeam_nodes_by_property"
    bl_label = "DevTools: BeamNG Select JBeam Nodes by Property"
    bl_options = {'INTERNAL', 'UNDO'}

    prop_name: bpy.props.StringProperty(name="Property Name") # type: ignore

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No valid mesh object selected")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        layer = bm.verts.layers.string.get("jbeam_node_props")

        if not layer:
            self.report({'WARNING'}, "No property data found")
            return {'CANCELLED'}

        # Retrieve the property value from the UI
        selected_prop_value = None
        for prop in context.scene.beamng_jbeam_vertex_props:
            if prop.name == self.prop_name:
                selected_prop_value = prop.value
                break

        if selected_prop_value is None:
            self.report({'WARNING'}, f"Property '{self.prop_name}' not found in UI")
            return {'CANCELLED'}

        selected_prop_value = str(selected_prop_value).strip().lower()

        print(f"\n[DEBUG] Searching for vertices with {self.prop_name} = {selected_prop_value}")

        for v in bm.verts:
            v.select = False

        bm.select_flush(False)
        bmesh.update_edit_mesh(obj.data, loop_triangles=True) 

        matched_count = 0

        for v in bm.verts:
            stored_data = j.get_node_props(obj, v.index)
            stored_value = stored_data.get(self.prop_name, None)

            # Convert values to string for comparison
            if stored_value is not None and str(stored_value).strip().lower() == selected_prop_value:
                v.select = True
                matched_count += 1

        bmesh.update_edit_mesh(obj.data)

        print(f"Total Matched Vertices: {matched_count}")
        self.report({'INFO'}, f"Selected {matched_count} vertices with {self.prop_name} = {selected_prop_value}")
        return {'FINISHED'}
