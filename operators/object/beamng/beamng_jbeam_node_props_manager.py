import bpy
import bmesh
import json

from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j, JbeamRefnodeUtils as jr  # type: ignore
from dev_tools.utils.ui_utils import UiUtils  # type: ignore

def update_element_index(self, context):
    # FIXME this function gets called 3 times preventing IntProperty change, workaround delay also useless
    return
    struct = context.scene.beamng_jbeam_active_structure
    struct.update_in_progress = True

    print(f"Element Index updated: {self.index} {struct.index}")

    struct_name = struct.name
    index = struct.index
    obj = context.object

    bm = bmesh.from_edit_mesh(obj.data)

    for v in bm.verts:
        v.select = False
    for e in bm.edges:
        e.select = False
    for f in bm.faces:
        f.select = False

    if struct_name == "Node":
        if 0 <= index < len(bm.verts):
            bm.verts[index].select = True
    elif struct_name == "Beam":
        if 0 <= index < len(bm.edges):
            bm.edges[index].select = True
    elif struct_name == "Triangle":
        if 0 <= index < len(bm.faces):
            bm.faces[index].select = True

    def set_update_in_progress_to_false():
        struct = bpy.context.scene.beamng_jbeam_active_structure
        struct.update_in_progress = False

    def start_delay_set_update_in_progress_to_false():
        delay_time = 0.1
        bpy.app.timers.register(set_update_in_progress_to_false, first_interval=delay_time)

    start_delay_set_update_in_progress_to_false()  # struct.update_in_progress = False
    #bmesh.update_edit_mesh(obj.data)

class JbeamStructurePropertyItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Property Name")  # type: ignore
    value: bpy.props.StringProperty(name="Value")  # type: ignore

class JbeamStructure(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name="Element Name",
        default=""  # Node, Beam, Triangle
    )  # type: ignore

    id: bpy.props.StringProperty(
        name="Element ID",
        default=""
    )  # type: ignore

    index: bpy.props.IntProperty(
        name="Element Index",
        description="Index of the associated vertex/edge/face",
        default=-1,
        update=update_element_index
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

    refnode_enum: bpy.props.EnumProperty(
        name="RefNode",
        description="Choose a RefNode type",
        items=jr.refnode_enum(),
        default="NONE"
    )  # type: ignore

    prop_items: bpy.props.CollectionProperty(type=JbeamStructurePropertyItem)  # type: ignore # items representing scope modifiers on the strucutre
    update_in_progress: bpy.props.BoolProperty(default=False)   # type: ignore # needed so that when we modify a value in the panel, we will ignore all draw function in sidepanel until update is complete

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

class OBJECT_OT_BeamngLoadJbeamPropsBase(bpy.types.Operator):
    """Base class for loading JBeam properties"""
    
    bl_options = {'INTERNAL', 'UNDO'}
    
    domain = None
    layer_name = ""
    get_props_function = None

    instances: bpy.props.StringProperty(default="[]")  # JSON-encoded list of instances # type: ignore

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No valid mesh object selected")
            return {'CANCELLED'}

        try:
            instance_list = json.loads(self.instances)
            if not instance_list:
                instance_list = [1]
        except json.JSONDecodeError:
            self.report({'ERROR'}, "Invalid format for instances")
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
            return {'CANCELLED'}

        scene_props = context.scene.beamng_jbeam_active_structure.prop_items
        scene_props.clear()
        properties = {}

        for instance in instance_list:  # Loop through all provided instances
            for elem in selected_elements:
                props = self.get_props_function(obj, elem.index, instance)
                for key, value in props.items():
                    properties[key] = value

        sorted_props = sorted(properties.items(), key=lambda item: item[0].lower())  # Sort properties alphabetically

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
        domain, attr_name, get_props, set_props = self.get_domain_data()
        if not domain:
            self.report({'ERROR'}, f"Unknown property type: {self.prop_type}")
            return {'CANCELLED'}

        layers = getattr(bm, domain).layers
        layer = layers.string.get(attr_name)
        elements = [elem for elem in getattr(bm, domain) if elem.select]
        prop_collection = context.scene.beamng_jbeam_active_structure.prop_items

        if not elements:
            self.report({'WARNING'}, "No selected elements")
            return {'CANCELLED'}
        if not layer:
            self.report({'WARNING'}, "No property data found")
            return {'CANCELLED'}

        # Reserved keyword check
        for reserved in j.RESERVED_KEYWORDS:
            if any(prop.name.lower() == reserved.lower() for prop in prop_collection):
                self.report({'WARNING'}, f"Keyword '{reserved}' is reserved.")
                return {'CANCELLED'}

        # Find the property to apply
        prop_to_save = next((prop for prop in prop_collection if prop.name == self.prop_name), None)
        if not prop_to_save:
            self.report({'WARNING'}, f"Property '{self.prop_name}' not found in scene properties")
            return {'CANCELLED'}

        # Apply property to selected elements
        instances = context.scene.beamng_jbeam_instance.get_selected_instances()
        for element in elements:
            for instance in instances:
                props = get_props(obj, element.index, instance)
                props[self.prop_name] = prop_to_save.value
                set_props(obj, element.index, props, instance)

        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Saved property: {self.prop_name}")
        return {'FINISHED'}

    @staticmethod
    def get_domain_data():
        """To be overridden in subclasses for domain-specific data."""
        return None, None, None, None


class OBJECT_OT_BeamngSaveJbeamNodeProp(OBJECT_OT_BeamngSaveJbeamProp):
    """Save a single JBeam node property for selected nodes"""
    bl_idname = "object.devtools_beamng_save_jbeam_node_prop"
    bl_label = "DevTools: BeamNG Save JBeam Node Property"
    prop_type = 'NODE'

    get_domain_data = staticmethod(lambda: (
        'verts', j.ATTR_NODE_PROPS, j.get_node_props, j.set_node_props
    ))


class OBJECT_OT_BeamngSaveJbeamBeamProp(OBJECT_OT_BeamngSaveJbeamProp):
    """Save a single JBeam edge property for selected beams"""
    bl_idname = "object.devtools_beamng_save_jbeam_beam_prop"
    bl_label = "DevTools: BeamNG Save JBeam Beam Property"
    prop_type = 'BEAM'

    get_domain_data = staticmethod(lambda: (
        'edges', j.ATTR_BEAM_PROPS, j.get_beam_props, j.set_beam_props
    ))


class OBJECT_OT_BeamngSaveJbeamTriangleProp(OBJECT_OT_BeamngSaveJbeamProp):
    """Save a single JBeam triangle property for selected triangles"""
    bl_idname = "object.devtools_beamng_save_jbeam_triangle_prop"
    bl_label = "DevTools: BeamNG Save JBeam Triangle Property"
    prop_type = 'TRIANGLE'

    get_domain_data = staticmethod(lambda: (
        'faces', j.ATTR_TRIANGLE_PROPS, j.get_triangle_props, j.set_triangle_props
    ))


class OBJECT_OT_BeamngSaveAllJbeamProps(bpy.types.Operator):
    """Base class for saving JBeam properties"""
    bl_options = {'INTERNAL', 'UNDO'}

    domain = ""  # 'verts', 'edges', or 'faces'
    prop_type = ""  # 'node', 'beam', or 'triangle'

    @classmethod
    def get_bmesh_layer(cls, bm):
        """Retrieve the correct BMesh layer based on the property type."""
        layer_attr = cls.get_layer_attr()
        if not layer_attr:
            return None
        layers = getattr(bm, cls.domain).layers.string
        return layers.get(layer_attr) if layers else None

    @classmethod
    def get_layer_attr(cls):
        """Should be implemented by subclasses to return the layer attribute."""
        raise NotImplementedError("Subclasses must define get_layer_attr")

    @classmethod
    def get_selected_elements(cls, bm):
        """Retrieve selected elements dynamically."""
        return [elem for elem in getattr(bm, cls.domain, []) if elem.select]

    def save_jbeam_props(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            return f"No valid mesh object selected", 'CANCELLED'

        bm = bmesh.from_edit_mesh(obj.data)
        layer = self.get_bmesh_layer(bm)
        selected_elements = self.get_selected_elements(bm)

        if not selected_elements or not layer:
            return f"No selected {self.prop_type} or no property data found", 'CANCELLED'

        ui_props = {prop.name: prop.value for prop in context.scene.beamng_jbeam_active_structure.prop_items}

        for reserved in j.RESERVED_KEYWORDS:
            if any(prop_name.lower() == reserved.lower() for prop_name in ui_props):
                return f"Keyword '{reserved}' is reserved.", 'CANCELLED'

        instances = context.scene.beamng_jbeam_instance.get_selected_instances()
        for element in selected_elements:
            for instance in instances:
                props = self.get_props(obj, element.index, instance)
                props = {k: v for k, v in props.items() if k in ui_props}  # Remove missing properties
                for prop_name, prop_value in ui_props.items():
                    props[prop_name] = prop_value
                self.set_props(obj, element.index, props, instance)

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

    @classmethod
    def get_layer_attr(cls):
        return j.ATTR_NODE_PROPS

    @staticmethod
    def get_props(obj, index, instance):
        return j.get_node_props(obj, index, instance)

    @staticmethod
    def set_props(obj, index, props, instance):
        j.set_node_props(obj, index, props, instance)


class OBJECT_OT_BeamngSaveAllJbeamBeamProps(OBJECT_OT_BeamngSaveAllJbeamProps):
    """Save all JBeam beam properties for selected edges"""
    bl_idname = "object.devtools_beamng_save_all_jbeam_beam_props"
    bl_label = "DevTools: BeamNG Save All JBeam Beam Properties"
    prop_type = "beam"
    domain = "edges"

    @classmethod
    def get_layer_attr(cls):
        return j.ATTR_BEAM_PROPS

    @staticmethod
    def get_props(obj, index, instance):
        return j.get_beam_props(obj, index, instance)

    @staticmethod
    def set_props(obj, index, props, instance):
        j.set_beam_props(obj, index, props, instance)


class OBJECT_OT_BeamngSaveAllJbeamTriangleProps(OBJECT_OT_BeamngSaveAllJbeamProps):
    """Save all JBeam triangle properties for selected faces"""
    bl_idname = "object.devtools_beamng_save_all_jbeam_triangle_props"
    bl_label = "DevTools: BeamNG Save All JBeam Triangle Properties"
    prop_type = "triangle"
    domain = "faces"

    @classmethod
    def get_layer_attr(cls):
        return j.ATTR_TRIANGLE_PROPS

    @staticmethod
    def get_props(obj, index, instance):
        return j.get_triangle_props(obj, index, instance)

    @staticmethod
    def set_props(obj, index, props, instance):
        j.set_triangle_props(obj, index, props, instance)


class OBJECT_OT_BeamngAddJbeamProp(bpy.types.Operator):
    """Base class for adding JBeam properties"""
    bl_options = {'INTERNAL', 'UNDO'}

    prop_type = ""

    def execute(self, context):
        prop = context.scene.beamng_jbeam_active_structure.prop_items.add()
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
        ui_list = scene.beamng_jbeam_active_structure.prop_items

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
            instances = context.scene.beamng_jbeam_instance.get_selected_instances()
            for element in selected_elements:
                if not element[layer]:  # Ensure there's data before proceeding
                    continue
                for instance in instances:
                    props = self.get_props(obj, element.index, instance)
                    if self.prop_name in props:
                        del props[self.prop_name]  # Remove property
                        self.set_props(obj, element.index, props, instance)  # Update stored properties
                        removed_from_mesh = True

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
        prop_collection = context.scene.beamng_jbeam_active_structure.prop_items

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
        return j.get_beam_props(obj, element.index) # TODO pass instance

class OBJECT_OT_BeamngSelectJbeamTrianglesByProperty(OBJECT_OT_BeamngSelectByPropertyBase):
    """Select all faces (triangles) that share the same JBeam property and value"""
    bl_idname = "object.devtools_beamng_select_jbeam_triangles_by_property"
    bl_label = "DevTools: BeamNG Select JBeam Triangles by Property"

    def get_elements(self, bm):
        return bm.faces

    def get_property_data(self, obj, element):
        return j.get_triangle_props(obj, element.index) # TODO pass instance
