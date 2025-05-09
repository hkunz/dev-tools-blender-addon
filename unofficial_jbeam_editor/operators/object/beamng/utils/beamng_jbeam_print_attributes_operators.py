import bpy
import json
import logging

from unofficial_jbeam_editor.utils.utils import Utils
from unofficial_jbeam_editor.utils.jbeam.jbeam_utils import JbeamUtils as j, JbeamPropsStorage, JbeamPropsStorageManager

class OBJECT_OT_PrintJBeamPropsBase(bpy.types.Operator):
    """Base class for printing JBeam properties"""
    bl_label = "Print JBeam Properties"
    bl_options = {'REGISTER', 'UNDO'}

    attr_name = ""
    domain = ""
    id_function = None
    emoji = None

    def execute(self, context):
        mode = context.object.mode
        if mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        def restore_mode():
            if mode != context.object.mode:
                bpy.ops.object.mode_set(mode=mode)

        props_manager = JbeamPropsStorageManager.get_instance()
        for obj in context.selected_objects:
            storage_inst: JbeamPropsStorage = props_manager.get_props_storage(obj)
            if not j.is_node_mesh(obj):
                Utils.log_and_report(f"⚠️  Object '{obj.name}' ({self.attr_name}): Object is not a Node Mesh", self, 'WARNING')
                continue

            mesh = obj.data
            elements = getattr(mesh, self.domain)  # Get vertices, edges, or faces

            selected_elements = [element for element in elements if element.select]

            if not selected_elements:
                Utils.log_and_report(f"⚠️  Object '{obj.name}' ({self.attr_name}): No selected {self.domain}", self, 'WARNING')
                continue

            info = f"ℹ️  Object '{obj.name}' ({self.attr_name})"
            logging.info(f"{info}:")

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
                            logging.info(f"{self.emoji}{id_str}({index}): {key} [{instance_key}] => {props_str}")
                    else:
                        logging.info(f"{self.emoji}{id_str}({index}): {key} => No properties found")
                else:
                    logging.info(f"{self.emoji}{id_str}({index}): No key, no attribute value (no scope modifiers assigned)")

        if len(context.selected_objects) > 0:
            Utils.log_and_report("Node Mesh Attributes have been printed. Check the console for detailed output.", self, 'INFO')
        logging.info("==============================================\n")
        restore_mode()
        return {'FINISHED'}


class OBJECT_OT_BeamngPrintJbeamNodeProps(OBJECT_OT_PrintJBeamPropsBase):
    """Prints the 'jbeam_node_props' attribute values of selected Nodes in selected objects"""
    bl_idname = "devtools_jbeameditor.beamng_jbeam_print_jbeam_node_props"
    bl_label = "Print JBeam Node Props"
    attr_name = j.ATTR_NODE_PROPS
    domain = "vertices"
    id_function = staticmethod(j.get_node_id)
    emoji = "⚪ "


class OBJECT_OT_BeamngPrintJbeamBeamProps(OBJECT_OT_PrintJBeamPropsBase):
    """Prints the 'jbeam_beam_props' attribute values of selected Beams in selected objects"""
    bl_idname = "devtools_jbeameditor.beamng_jbeam_print_jbeam_beam_props"
    bl_label = "Print JBeam Beam Props"
    attr_name = j.ATTR_BEAM_PROPS
    domain = "edges"
    id_function = staticmethod(j.get_beam_id)
    emoji = "🟰  "


class OBJECT_OT_BeamngPrintJbeamTriangleProps(OBJECT_OT_PrintJBeamPropsBase):
    """Prints the 'jbeam_triangle_props' attribute values of selected Faces in selected objects"""
    bl_idname = "devtools_jbeameditor.beamng_jbeam_print_jbeam_triangle_props"
    bl_label = "Print JBeam Triangle Props"
    attr_name = j.ATTR_TRIANGLE_PROPS
    domain = "polygons"
    id_function = staticmethod(j.get_triangle_id)
    emoji = "📐 "
