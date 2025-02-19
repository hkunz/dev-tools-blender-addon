import bpy
from bpy.types import Operator

class OBJECT_OT_BeamngConvertJbeamToMesh(Operator):
    """Convert jbeam to mesh object by removing custom properties and merge by distance"""
    bl_idname = "object.devtools_beamng_convert_jbeam_to_mesh"
    bl_label = "DevTools: Convert JBeam to Mesh Object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        
        if obj and obj.type == 'MESH':
            for key in list(obj.keys()):
                del obj[key]
            for key in list(obj.data.keys()):
                del obj.data[key]

            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.remove_doubles()
            bpy.ops.object.mode_set(mode='OBJECT')

            bpy.ops.object.devtools_beamng_create_refnodes_vertex_groups()
            
            self.report({'INFO'}, f"Cleaned object and mesh data: {obj.name}")
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, "No mesh object selected!")
            return {'CANCELLED'}
