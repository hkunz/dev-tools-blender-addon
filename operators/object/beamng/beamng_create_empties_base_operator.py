import bpy

class OBJECT_OT_BeamngCreateEmptiesBase(bpy.types.Operator):
    """Create 'base00' and 'start01' empties with 'start01' as a child of 'base00'"""
    bl_idname = "object.devtools_beamng_create_empties_base"
    bl_label = "DevTools: Create BeamnNG.drive 'base00' and 'start01' Empties"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        base_empty = bpy.data.objects.get("base00")
        start_empty = bpy.data.objects.get("start01")

        if base_empty or start_empty:
            self.report({'WARNING'}, "Empty 'base00 and/or start01 already exist")
            return {'CANCELLED'}

        base_empty = bpy.data.objects.new("base00", None)
        context.collection.objects.link(base_empty)
        base_empty.location = (0, 0, 0)
        self.report({'INFO'}, "Empty 'base00' created.")

        start_empty = bpy.data.objects.new("start01", None)
        context.collection.objects.link(start_empty)
        start_empty.location = (0, 0, 0)
        self.report({'INFO'}, "Empty 'start01' created.")

        start_empty.parent = base_empty
        self.report({'INFO'}, "Empty 'start01' set as child of 'base00'.")
        
        return {'FINISHED'}
