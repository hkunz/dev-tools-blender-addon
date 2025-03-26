import bpy
import bmesh

from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j  # type: ignore

class JbeamElement(bpy.types.PropertyGroup):
    id: bpy.props.StringProperty(
        name="Element ID",
        default=""
    )  # type: ignore

    index: bpy.props.IntProperty(
        name="Element Index",
        description="Index of the associated vertex/edge/face",
        default=-1
    )  # type: ignore

    num_instances: bpy.props.IntProperty(
        name="Number of Instances",
        description="Specifies the total number of repeated occurrences for the structure (beams/triangles) in the JBeam file",
        default=1
    )  # type: ignore

    position: bpy.props.FloatVectorProperty(
        name="Position",
        description="3D position of the element",
        default=(0.0, 0.0, 0.0),
        subtype="TRANSLATION"
    )  # type: ignore

    selection: bpy.props.StringProperty(
        name="Selection List",
        default=""
    )  # type: ignore

class JbeamHiddenElements(bpy.types.PropertyGroup):
    num_hidden_nodes: bpy.props.IntProperty(
        name="Number of Hidden Nodes",
        default=0
    )  # type: ignore
    num_hidden_beams: bpy.props.IntProperty(
        name="Number of Hidden Beams",
        default=0
    )  # type: ignore
    num_hidden_faces: bpy.props.IntProperty(
        name="Number of Hidden Faces",
        default=0
    )  # type: ignore

class JbeamPropertyItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Property Name")  # type: ignore
    value: bpy.props.StringProperty(name="Value")  # type: ignore


class OBJECT_OT_BeamngLoadJbeamPropsBase(bpy.types.Operator):
    """Base class for loading JBeam properties"""
    
    bl_options = {'INTERNAL', 'UNDO'}
    
    domain = None
    layer_name = ""
    get_props_function = None

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No valid mesh object selected")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        layers = getattr(bm, self.domain).layers.string
        if self.layer_name not in layers:
            self.report({'WARNING'}, f"Layer '{self.layer_name}' not found in domain '{self.domain}'")
            return {'CANCELLED'}

        layer = layers[self.layer_name]
        selected_elements = [e for e in getattr(bm, self.domain) if e.select]

        if not layer:
            self.report({'WARNING'}, "No layer found")

        if not selected_elements:
            #print("No selection or no property data found")
            return {'CANCELLED'}

        scene_props = context.scene.beamng_jbeam_structure_props
        scene_props.clear()
        properties = {}

        for elem in selected_elements:
            props = self.get_props_function(obj, elem.index)
            for key, value in props.items():
                properties[key] = value

        
        sorted_props = sorted(properties.items(), key=lambda item: item[0].lower()) # Sort properties alphabetically (case-insensitive)

        for key, value in sorted_props:
            prop = scene_props.add()
            prop.name = key
            prop.value = str(value)

        return {'FINISHED'}

class OBJECT_OT_BeamngLoadJbeamNodeProps(OBJECT_OT_BeamngLoadJbeamPropsBase):
    """Load JBeam properties of the selected nodes"""
    bl_idname = "object.devtools_beamng_load_jbeam_node_props"
    bl_label = "DevTools: BeamNG Load JBeam Node Properties"
    domain = "verts"
    layer_name = j.ATTR_NODE_PROPS
    get_props_function = staticmethod(j.get_node_props)

class OBJECT_OT_BeamngLoadJbeamBeamProps(OBJECT_OT_BeamngLoadJbeamPropsBase):
    """Load JBeam properties of the selected beams"""
    bl_idname = "object.devtools_beamng_load_jbeam_beam_props"
    bl_label = "DevTools: BeamNG Load JBeam Beam Properties"
    domain = "edges"
    layer_name = j.ATTR_BEAM_PROPS
    get_props_function = staticmethod(j.get_beam_props)

class OBJECT_OT_BeamngLoadJbeamTriangleProps(OBJECT_OT_BeamngLoadJbeamPropsBase):
    """Load JBeam properties of the selected triangles"""
    bl_idname = "object.devtools_beamng_load_jbeam_triangle_props"
    bl_label = "DevTools: BeamNG Load JBeam Triangle Properties"
    domain = "faces"
    layer_name = j.ATTR_TRIANGLE_PROPS
    get_props_function = staticmethod(j.get_triangle_props)


class OBJECT_OT_BeamngSaveJbeamProp(bpy.types.Operator):
    """Base class for saving JBeam properties"""
    bl_options = {'INTERNAL', 'UNDO'}

    prop_type = ""
    prop_name: bpy.props.StringProperty()  # type: ignore

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No valid mesh object selected")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        domain_map = {
            'NODE': ('verts', j.ATTR_NODE_PROPS, j.get_node_props, j.set_node_props),
            'BEAM': ('edges', j.ATTR_BEAM_PROPS, j.get_beam_props, j.set_beam_props),
            'TRIANGLE': ('faces', j.ATTR_TRIANGLE_PROPS, j.get_triangle_props, j.set_triangle_props),
        }

        if self.prop_type in domain_map:
            domain, attr_name, get_props, set_props = domain_map[self.prop_type]
            layers = getattr(bm, domain).layers
            layer = layers.string.get(attr_name)
            elements = [elem for elem in getattr(bm, domain) if elem.select]
            prop_collection = context.scene.beamng_jbeam_structure_props
        else:
            self.report({'ERROR'}, f"Unknown property type: {self.prop_type}")
            return {'CANCELLED'}

        if not elements:
            self.report({'WARNING'}, "No selected elements")
            return {'CANCELLED'}
        if not layer:
            self.report({'WARNING'}, "No property data found")
            return {'CANCELLED'}

        # Reserved keyword check
        for reserved in j.RESERVED_KEYWORDS:
            if any(prop.name.lower() == reserved.lower() for prop in prop_collection):
                self.report({'WARNING'}, f"Keyword '{reserved}' is reserved. Use vertex groups prefixed '{reserved}_' to assign nodes to a {reserved}.")
                return {'CANCELLED'}

        # Find the property to apply
        prop_to_save = next((prop for prop in prop_collection if prop.name == self.prop_name), None)
        if not prop_to_save:
            self.report({'WARNING'}, f"Property '{self.prop_name}' not found in scene properties")
            return {'CANCELLED'}

        # Apply property to selected elements
        for element in elements:
            try:
                props = get_props(obj, element.index)
                props[self.prop_name] = prop_to_save.value
                set_props(obj, element.index, props)
            except Exception as e:
                self.report({'ERROR'}, f"Failed to save property: {e}")

        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Saved property: {self.prop_name}")
        return {'FINISHED'}

class OBJECT_OT_BeamngSaveJbeamNodeProp(OBJECT_OT_BeamngSaveJbeamProp):
    """Save a single JBeam node property for selected nodes"""
    bl_idname = "object.devtools_beamng_save_jbeam_node_prop"
    bl_label = "DevTools: BeamNG Save JBeam Node Property"
    prop_type = 'NODE'

class OBJECT_OT_BeamngSaveJbeamBeamProp(OBJECT_OT_BeamngSaveJbeamProp):
    """Save a single JBeam edge property for selected beams"""
    bl_idname = "object.devtools_beamng_save_jbeam_beam_prop"
    bl_label = "DevTools: BeamNG Save JBeam Beam Property"
    prop_type = 'BEAM'

class OBJECT_OT_BeamngSaveJbeamTriangleProp(OBJECT_OT_BeamngSaveJbeamProp):
    """Save a single JBeam edge property for selected triangles"""
    bl_idname = "object.devtools_beamng_save_jbeam_triangle_prop"
    bl_label = "DevTools: BeamNG Save JBeam Triangle Property"
    prop_type = 'TRIANGLE'


class OBJECT_OT_BeamngSaveAllJbeamProps(bpy.types.Operator):
    """Base class for saving JBeam properties"""
    bl_options = {'INTERNAL', 'UNDO'}
    
    domain = ""  # uses 'verts', 'edges', or 'faces'
    prop_type = ""  # uses 'node', 'beam', or 'triangle'

    @classmethod
    def get_bmesh_layer(cls, bm):
        """Retrieve the correct BMesh layer based on the property type."""
        layer_attr = {
            "verts": j.ATTR_NODE_PROPS,
            "edges": j.ATTR_BEAM_PROPS,
            "faces": j.ATTR_TRIANGLE_PROPS,
        }.get(cls.domain)

        if not layer_attr:
            return None
        # Dynamically access the layers using self.domain
        layers = getattr(bm, cls.domain).layers.string
        return layers.get(layer_attr) if layers else None

    @classmethod
    def get_selected_elements(cls, bm):
        """Retrieve selected elements dynamically."""
        return [elem for elem in getattr(bm, cls.domain, []) if elem.select]

    @classmethod
    def get_props(cls, obj, index):
        """Retrieve JBeam properties for the given element index."""
        return getattr(j, f"get_{cls.prop_type}_props", lambda *_: {})(obj, index)

    @classmethod
    def set_props(cls, obj, index, props):
        """Set JBeam properties for the given element index."""
        setter = getattr(j, f"set_{cls.prop_type}_props", None)
        if setter:
            setter(obj, index, props)

    def save_jbeam_props(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            return f"No valid mesh object selected", 'CANCELLED'
        
        bm = bmesh.from_edit_mesh(obj.data)
        layer = self.get_bmesh_layer(bm)
        selected_elements = self.get_selected_elements(bm)

        if not selected_elements or not layer:
            return f"No selected {self.prop_type} or no property data found", 'CANCELLED'
        
        ui_props = {prop.name: prop.value for prop in getattr(context.scene, f'beamng_jbeam_{self.prop_type}_props')}

        for reserved in j.RESERVED_KEYWORDS:
            if any(prop_name.lower() == reserved.lower() for prop_name in ui_props):
                return f"Keyword '{reserved}' is reserved. Use vertex groups prefixed '{reserved}_' to assign nodes to a {reserved}.", 'CANCELLED'

        for element in selected_elements:
            try:
                props = self.get_props(obj, element.index)
                props = {k: v for k, v in props.items() if k in ui_props}  # Remove missing properties
                for prop_name, prop_value in ui_props.items():
                    props[prop_name] = prop_value
                self.set_props(obj, element.index, props)
            except Exception as e:
                return f"Failed to save properties: {e}", 'ERROR'
        
        bmesh.update_edit_mesh(obj.data)
        return f"Saved all {self.prop_type} properties", 'FINISHED'
    
    def execute(self, context):
        msg, status = self.save_jbeam_props(context)
        self.report({'INFO' if status == 'FINISHED' else 'WARNING'}, msg)
        return {status}

class OBJECT_OT_BeamngSaveAllJbeamNodeProps(OBJECT_OT_BeamngSaveAllJbeamProps):
    """Save all JBeam node properties for selected vertices"""
    bl_idname = "object.devtools_beamng_save_all_jbeam_node_props"
    bl_label = "DevTools: BeamNG Save All JBeam Node Properties"
    prop_type = "node"
    domain = "verts"

class OBJECT_OT_BeamngSaveAllJbeamBeamProps(OBJECT_OT_BeamngSaveAllJbeamProps):
    """Save all JBeam beam properties for selected edges"""
    bl_idname = "object.devtools_beamng_save_all_jbeam_beam_props"
    bl_label = "DevTools: BeamNG Save All JBeam Beam Properties"
    prop_type = "beam"
    domain = "edges"

class OBJECT_OT_BeamngSaveAllJbeamTriangleProps(OBJECT_OT_BeamngSaveAllJbeamProps):
    """Save all JBeam triangle properties for selected faces"""
    bl_idname = "object.devtools_beamng_save_all_jbeam_triangle_props"
    bl_label = "DevTools: BeamNG Save All JBeam Triangle Properties"
    prop_type = "triangle"
    domain = "faces"


class OBJECT_OT_BeamngAddJbeamProp(bpy.types.Operator):
    """Base class for adding JBeam properties"""
    bl_options = {'INTERNAL', 'UNDO'}

    prop_type = ""

    def execute(self, context):
        prop = context.scene.beamng_jbeam_structure_props.add()
        prop.name = f"{self.prop_type.capitalize()}Prop"
        prop.value = "0"
        return {'FINISHED'}

class OBJECT_OT_BeamngAddJbeamNodeProp(OBJECT_OT_BeamngAddJbeamProp):
    """Add a new JBeam node property"""
    bl_idname = "object.devtools_beamng_add_jbeam_node_prop"
    bl_label = "DevTools: BeamNG Add JBeam Node Property"
    prop_type = 'NODE'

class OBJECT_OT_BeamngAddJbeamBeamProp(OBJECT_OT_BeamngAddJbeamProp):
    """Add a new JBeam Beam property"""
    bl_idname = "object.devtools_beamng_add_jbeam_edge_prop"
    bl_label = "DevTools: BeamNG Add JBeam Beam Property"
    prop_type = 'BEAM'

class OBJECT_OT_BeamngAddJbeamTriangleProp(OBJECT_OT_BeamngAddJbeamProp):
    """Add a new JBeam Triangle property"""
    bl_idname = "object.devtools_beamng_add_jbeam_triangle_prop"
    bl_label = "DevTools: BeamNG Add JBeam Triangle Property"
    prop_type = 'TRIANGLE'


class OBJECT_OT_BeamngRemoveJbeamProp(bpy.types.Operator):
    """Remove a JBeam property (Shift+Click to also save)"""
    bl_options = {'INTERNAL', 'UNDO'}

    domain = ""  # verts (node), edges (beam), faces (triangle)
    attr_layer = ""
    get_props = None
    set_props = None

    prop_name: bpy.props.StringProperty()  # type: ignore

    def invoke(self, context, event):
        """Detect Shift and pass it to execute"""
        self.do_save = bool(event.shift)
        return self.execute(context)

    def execute(self, context):
        self.do_save = getattr(self, "do_save", False)  # Ensure `do_save` exists

        scene = context.scene
        obj = context.object

        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No valid mesh object selected")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)

        # Fetch relevant attributes from subclass
        layer = bm.__getattribute__(self.domain).layers.string.get(self.attr_layer)
        selected_elements = [elem for elem in bm.__getattribute__(self.domain) if elem.select]
        ui_list = scene.beamng_jbeam_structure_props

        if layer is None:
            self.report({'WARNING'}, "No property data found")
            return {'CANCELLED'}

        if not selected_elements:
            self.report({'WARNING'}, f"No selection on domain '{self.domain}' found")
            return {'CANCELLED'}

        removed_from_ui = False
        removed_from_mesh = False

        # Always remove from the UI list
        for i, prop in enumerate(ui_list):
            if prop.name == self.prop_name:
                ui_list.remove(i)
                removed_from_ui = True
                break  # Ensure only one instance is removed

        if self.do_save:
            # Remove property from mesh (SAVE MODE)
            for element in selected_elements:
                if element[layer]:  # Ensure there's data before proceeding
                    try:
                        props = self.get_props(obj, element.index)
                        if self.prop_name in props:
                            del props[self.prop_name]  # Remove property
                            self.set_props(obj, element.index, props)  # Update stored properties
                            removed_from_mesh = True
                    except Exception as e:
                        self.report({'ERROR'}, f"Failed to remove property: {e}")
                        return {'CANCELLED'}

            bmesh.update_edit_mesh(obj.data)  # Commit changes to mesh

        if removed_from_ui and removed_from_mesh:
            self.report({'INFO'}, f"Removed property '{self.prop_name}' from UI and saved")
        elif removed_from_ui:
            self.report({'INFO'}, f"Removed property '{self.prop_name}' from UI (unsaved)")
        else:
            self.report({'WARNING'}, f"Property '{self.prop_name}' not found")

        return {'FINISHED' if removed_from_ui else 'CANCELLED'}


class OBJECT_OT_BeamngRemoveJbeamNodeProp(OBJECT_OT_BeamngRemoveJbeamProp):
    """Remove a JBeam node property (Shift+Click to also save)"""
    bl_idname = "object.devtools_beamng_remove_jbeam_node_prop"
    bl_label = "DevTools: BeamNG Remove JBeam Node Property"
    domain = "verts"
    attr_layer = j.ATTR_NODE_PROPS
    get_props = staticmethod(j.get_node_props)
    set_props = staticmethod(j.set_node_props)

class OBJECT_OT_BeamngRemoveJbeamBeamProp(OBJECT_OT_BeamngRemoveJbeamProp):
    """Remove a JBeam beam property (Shift+Click to also save)"""
    bl_idname = "object.devtools_beamng_remove_jbeam_beam_prop"
    bl_label = "DevTools: BeamNG Remove JBeam Beam Property"
    domain = "edges"
    attr_layer = j.ATTR_BEAM_PROPS
    get_props = staticmethod(j.get_beam_props)
    set_props = staticmethod(j.set_beam_props)

class OBJECT_OT_BeamngRemoveJbeamTriangleProp(OBJECT_OT_BeamngRemoveJbeamProp):
    """Remove a JBeam triangle property (Shift+Click to also save)"""
    bl_idname = "object.devtools_beamng_remove_jbeam_triangle_prop"
    bl_label = "DevTools: BeamNG Remove JBeam Triangle Property"
    domain = "faces"
    attr_layer = j.ATTR_TRIANGLE_PROPS
    get_props = staticmethod(j.get_triangle_props)
    set_props = staticmethod(j.set_triangle_props)


class OBJECT_OT_BeamngSelectByPropertyBase(bpy.types.Operator):
    """Base class for selecting elements based on JBeam property"""
    bl_options = {'INTERNAL', 'UNDO'}

    prop_name: bpy.props.StringProperty(name="Property Name")  # type: ignore

    def get_elements(self, bm):
        """Return the elements to iterate over (verts for nodes, edges for beams)."""
        pass

    def get_property_data(self, obj, element):
        """Retrieve property data for the given element."""
        pass

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No valid mesh object selected")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        prop_collection = context.scene.beamng_jbeam_structure_props

        # Retrieve the property value from the UI
        selected_prop_value = None
        selected_prop_value_orig = None
        for prop in prop_collection:
            if prop.name == self.prop_name:
                selected_prop_value_orig = str(prop.value).strip()
                selected_prop_value = selected_prop_value_orig.lower().strip("\"'")
                break

        if selected_prop_value is None:
            self.report({'WARNING'}, f"Property '{self.prop_name}' not found in UI")
            return {'CANCELLED'}

        print(f"\n[DEBUG] Searching for elements with {self.prop_name} = {selected_prop_value_orig}")

        # Deselect all elements first
        for elem in self.get_elements(bm):
            elem.select = False

        bm.select_flush(False)
        bmesh.update_edit_mesh(obj.data, loop_triangles=True)

        matched_count = 0

        for elem in self.get_elements(bm):
            stored_data = self.get_property_data(obj, elem)
            stored_value = stored_data.get(self.prop_name, None)

            if stored_value is not None and str(stored_value).strip().lower().strip("\"'") == selected_prop_value:
                elem.select = True
                matched_count += 1

        bmesh.update_edit_mesh(obj.data)

        print(f"Total Matched Elements: {matched_count}")
        self.report({'INFO'}, f"Selected {matched_count} elements with {self.prop_name} = {selected_prop_value_orig}")
        return {'FINISHED'}

class OBJECT_OT_BeamngSelectJbeamNodesByProperty(OBJECT_OT_BeamngSelectByPropertyBase):
    """Select all vertices (nodes) that share the same JBeam property and value"""
    bl_idname = "object.devtools_beamng_select_jbeam_nodes_by_property"
    bl_label = "DevTools: BeamNG Select JBeam Nodes by Property"

    def get_elements(self, bm):
        return bm.verts

    def get_property_data(self, obj, element):
        return j.get_node_props(obj, element.index)

class OBJECT_OT_BeamngSelectJbeamBeamsByProperty(OBJECT_OT_BeamngSelectByPropertyBase):
    """Select all edges (beams) that share the same JBeam property and value"""
    bl_idname = "object.devtools_beamng_select_jbeam_beams_by_property"
    bl_label = "DevTools: BeamNG Select JBeam Beams by Property"

    def get_elements(self, bm):
        return bm.edges

    def get_property_data(self, obj, element):
        return j.get_beam_props(obj, element.index)

class OBJECT_OT_BeamngSelectJbeamTrianglesByProperty(OBJECT_OT_BeamngSelectByPropertyBase):
    """Select all faces (triangles) that share the same JBeam property and value"""
    bl_idname = "object.devtools_beamng_select_jbeam_triangles_by_property"
    bl_label = "DevTools: BeamNG Select JBeam Triangles by Property"

    def get_elements(self, bm):
        return bm.faces

    def get_property_data(self, obj, element):
        return j.get_triangle_props(obj, element.index)
