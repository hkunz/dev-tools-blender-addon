import bpy
import json

from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j, JbeamPropsStorage  # type: ignore


class OBJECT_OT_PrintJBeamPropsBase(bpy.types.Operator):
    """Base class for printing JBeam properties"""
    bl_label = "Print JBeam Properties"
    bl_options = {'REGISTER', 'UNDO'}

    attr_name = ""
    domain = ""
    id_function = None

    def execute(self, context):
        mode = context.object.mode
        if mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        def restore_mode():
            if mode != context.object.mode:
                bpy.ops.object.mode_set(mode=mode)

        storage_inst = JbeamPropsStorage.get_instance()
        for obj in context.selected_objects:
            if not j.is_node_mesh(obj):
                self.report({'WARNING'}, f"Object '{obj.name}' ({self.attr_name}): Object is not a Node Mesh")
                continue

            mesh = obj.data
            elements = getattr(mesh, self.domain)  # Get vertices, edges, or faces

            selected_elements = [element for element in elements if element.select]

            if not selected_elements:
                self.report({'WARNING'}, f"Object '{obj.name}' ({self.attr_name}): No selected {self.domain}")
                continue

            info = f"Object '{obj.name}' ({self.attr_name})"
            print(f"{info}:")

            for i, element in enumerate(selected_elements):
                index = element.index
                domain = storage_inst.resolve_domain(self.domain)
                key = j.get_attribute_value(obj, index, self.attr_name, domain)
                id_str = self.id_function(obj, index)
                if key:
                    props = storage_inst.storage.get(domain, {}).get(key, {})
                    if props:
                        for instance_key, instance_props in props.items():
                            # Convert properties to a single-line JSON string
                            props_str = json.dumps(instance_props, separators=(",", ":"))
                            print(f"{id_str}({index}): {key} [{instance_key}] => {props_str}")
                    else:
                        print(f"{id_str}({index}): {key} => No properties found")
                else:
                    print(f"{id_str}({index}): No key, no attribute value (no scope modifiers assigned)")

        if len(context.selected_objects) > 0:
            self.report({'INFO'}, "Node Mesh Attributes have been printed. Check the console for detailed output.")
        print("==============================================\n")
        restore_mode()
        return {'FINISHED'}


class OBJECT_OT_BeamngPrintJbeamNodeProps(OBJECT_OT_PrintJBeamPropsBase):
    """Prints the jbeam_node_props attribute values of selected objects"""
    bl_idname = "devtools_jbeameditor.beamng_jbeam_print_jbeam_node_props"
    bl_label = "Print JBeam Node Props"
    attr_name = j.ATTR_NODE_PROPS
    domain = "vertices"
    id_function = staticmethod(j.get_node_id)


class OBJECT_OT_BeamngPrintJbeamBeamProps(OBJECT_OT_PrintJBeamPropsBase):
    """Prints the jbeam_beam_props attribute values of selected objects"""
    bl_idname = "devtools_jbeameditor.beamng_jbeam_print_jbeam_beam_props"
    bl_label = "Print JBeam Beam Props"
    attr_name = j.ATTR_BEAM_PROPS
    domain = "edges"
    id_function = staticmethod(j.get_beam_id)


class OBJECT_OT_BeamngPrintJbeamTriangleProps(OBJECT_OT_PrintJBeamPropsBase):
    """Prints the jbeam_triangle_props attribute values of selected objects"""
    bl_idname = "devtools_jbeameditor.beamng_jbeam_print_jbeam_triangle_props"
    bl_label = "Print JBeam Triangle Props"
    attr_name = j.ATTR_TRIANGLE_PROPS
    domain = "polygons"
    id_function = staticmethod(j.get_triangle_id)
