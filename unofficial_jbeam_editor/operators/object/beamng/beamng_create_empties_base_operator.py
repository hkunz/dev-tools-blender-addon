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
            Utils.log_and_report("Collection 'beamng_export' created.", self, 'INFO')

        # Get or create 'base00'
        base_empty = bpy.data.objects.get("base00")
        if base_empty:
            base_empty.location = (0, 0, 0)
            Utils.log_and_report("Existing 'base00' position reset to (0, 0, 0).", self, 'INFO')
        else:
            base_empty = bpy.data.objects.new("base00", None)
            base_empty.location = (0, 0, 0)
            Utils.log_and_report("Empty 'base00' created.", self, 'INFO')

        # Get or create 'start01'
        start_empty = bpy.data.objects.get("start01")
        if start_empty:
            start_empty.location = (0, 0, 0)
            Utils.log_and_report("Existing 'start01' position reset to (0, 0, 0).", self, 'INFO')
        else:
            start_empty = bpy.data.objects.new("start01", None)
            start_empty.location = (0, 0, 0)
            Utils.log_and_report("Empty 'start01' created.", self, 'INFO')

        # Ensure the empties are in the 'beamng_export' collection
        for empty in [base_empty, start_empty]:
            if empty.name not in export_collection.objects:
                for col in empty.users_collection:
                    col.objects.unlink(empty)
                export_collection.objects.link(empty)
                Utils.log_and_report(f"Moved '{empty.name}' to 'beamng_export' collection.", self, 'INFO')

        # Set parenting relationship
        if start_empty.parent != base_empty:
            start_empty.parent = base_empty
            Utils.log_and_report("'start01' set as child of 'base00'.", self, 'INFO')

        return {'FINISHED'}
