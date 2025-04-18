import bpy

from unofficial_jbeam_editor.utils.utils import Utils

class OBJECT_OT_BeamngCreateEmptiesBase(bpy.types.Operator):
    """Create 'base00' and 'start01' empties with 'start01' as a child of 'base00', placed in a 'beamng_export' collection"""
    bl_idname = "object.devtools_beamng_create_empties_base"
    bl_label = "DevTools: Create BeamNG.drive 'base00' and 'start01' Empties"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Ensure the 'beamng_export' collection exists
        export_collection = bpy.data.collections.get("beamng_export")
        if not export_collection:
            export_collection = Utils.create_collection_at_top("beamng_export")
            self.report({'INFO'}, "Collection 'beamng_export' created.")

        # Get or create 'base00'
        base_empty = bpy.data.objects.get("base00")
        if base_empty:
            base_empty.location = (0, 0, 0)
            self.report({'INFO'}, "Existing 'base00' position reset to (0, 0, 0).")
        else:
            base_empty = bpy.data.objects.new("base00", None)
            base_empty.location = (0, 0, 0)
            self.report({'INFO'}, "Empty 'base00' created.")

        # Get or create 'start01'
        start_empty = bpy.data.objects.get("start01")
        if start_empty:
            start_empty.location = (0, 0, 0)
            self.report({'INFO'}, "Existing 'start01' position reset to (0, 0, 0).")
        else:
            start_empty = bpy.data.objects.new("start01", None)
            start_empty.location = (0, 0, 0)
            self.report({'INFO'}, "Empty 'start01' created.")

        # Ensure the empties are in the 'beamng_export' collection
        for empty in [base_empty, start_empty]:
            if empty.name not in export_collection.objects:
                for col in empty.users_collection:
                    col.objects.unlink(empty)
                export_collection.objects.link(empty)
                self.report({'INFO'}, f"Moved '{empty.name}' to 'beamng_export' collection.")

        # Set parenting relationship
        if start_empty.parent != base_empty:
            start_empty.parent = base_empty
            self.report({'INFO'}, "'start01' set as child of 'base00'.")

        return {'FINISHED'}
