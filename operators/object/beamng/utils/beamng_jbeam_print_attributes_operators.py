import bpy
import json

from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j, JbeamPropsStorage  # type: ignore


import bpy
import json

class OBJECT_OT_PrintJBeamPropsBase(bpy.types.Operator):
    """Base class for printing JBeam properties"""
    bl_idname = "object.print_jbeam_props_base"
    bl_label = "Print JBeam Properties"
    bl_options = {'REGISTER', 'UNDO'}

    attr_name = ""
    domain = ""
    id_function = None

    def execute(self, context):
        if bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        for obj in context.selected_objects:
            if not j.is_node_mesh(obj):
                print(f"Object '{obj.name}' ({self.attr_name}): Object is not a Node Mesh")
                continue

            mesh = obj.data
            elements = getattr(mesh, self.domain)  # Get vertices, edges, or faces
            print(f"Object '{obj.name}' ({self.attr_name}):")
            for index in range(len(elements)):  # Iterate over elements
                key = j.get_attribute_value(obj, index, self.attr_name, self.domain)
                id_str = self.id_function(obj, index)  # Use subclass-defined function
                if key:
                    props = JbeamPropsStorage.get_instance().fetch_props(key)
                    print(f"{id_str}({index}): {key} => {json.dumps(props)}")
                else:
                    print(f"{id_str}({index}): {key} => nothing found")

        return {'FINISHED'}


class OBJECT_OT_BeamngPrintJbeamNodeProps(OBJECT_OT_PrintJBeamPropsBase):
    """Prints the jbeam_node_props attribute values of selected objects"""
    bl_idname = "object.beamng_jbeam_print_jbeam_node_props"
    bl_label = "Print JBeam Node Props"
    attr_name = j.ATTR_NODE_PROPS
    domain = "vertices"
    id_function = staticmethod(j.get_node_id)


class OBJECT_OT_BeamngPrintJbeamBeamProps(OBJECT_OT_PrintJBeamPropsBase):
    """Prints the jbeam_beam_props attribute values of selected objects"""
    bl_idname = "object.beamng_jbeam_print_jbeam_beam_props"
    bl_label = "Print JBeam Beam Props"
    attr_name = j.ATTR_BEAM_PROPS
    domain = "edges"
    id_function = staticmethod(j.get_beam_id)


class OBJECT_OT_BeamngPrintJbeamTriangleProps(OBJECT_OT_PrintJBeamPropsBase):
    """Prints the jbeam_triangle_props attribute values of selected objects"""
    bl_idname = "object.beamng_jbeam_print_jbeam_triangle_props"
    bl_label = "Print JBeam Triangle Props"
    attr_name = j.ATTR_TRIANGLE_PROPS
    domain = "polygons"
    id_function = staticmethod(j.get_triangle_id)
