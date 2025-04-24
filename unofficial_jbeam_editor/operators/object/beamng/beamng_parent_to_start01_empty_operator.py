import bpy
import re
import logging

from unofficial_jbeam_editor.utils.utils import Utils

class OBJECT_OT_BeamngClearChildrenStart01Empty(bpy.types.Operator):
    """Operator to clear children from an empty object based on naming pattern"""
    bl_idname = "object.devtools_beamng_clear_children_for_empty"
    bl_label = "Clear Children for 'start01' Empty"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        empty_obj = bpy.data.objects.get("start01")
        if not empty_obj:
            Utils.log_and_report(f"Empty 'start01' missing", self, 'WARNING')
            return {'CANCELLED'}
        prefix = "Colmesh-"
        pattern = re.compile(f"^{re.escape(prefix)}\\d+$")
        children_to_process = list(empty_obj.children)
        for child in children_to_process:
            if pattern.match(child.name):
                bpy.data.objects.remove(child, do_unlink=True)
            else:
                child.parent = None
        return {'FINISHED'}

class OBJECT_OT_BeamngParentToStart01Empty(bpy.types.Operator):
    """Finds Colmesh and main object/armature named like collection with postfix _a# (i.e. '_a5000')"""
    bl_idname = "object.devtools_beamng_parent_to_start01_empty"
    bl_label = "DevTools: Find collision and main object/armature named like collection with postfix '_a#' (i.e. '<collection_name>_a5000')"
    bl_description = "Find within selected collection the object 'Colmesh-1.<name>' (duplicated as 'Colmesh-1') and '<collection_name>_a#' (# is estimated vertices) and parent both to the 'start01' empty"
    bl_options = {'REGISTER', 'UNDO'}

    def find_objects_matching_collection_name(self, collection_name):
        """Finds objects in the collection with names matching <collection_name>_aX."""
        found_objects = []
        pattern = re.compile(f"^{re.escape(collection_name)}_a(\\d+)$")

        for obj in bpy.context.collection.objects:
            if obj.type in {'MESH', 'ARMATURE'}:
                match = pattern.match(obj.name)
                if match:
                    found_objects.append(obj)
        
        if not found_objects:
            Utils.log_and_report(f"Missing object/s with naming convention \"{collection_name}_a#\" (example: \"{collection_name}_a1000\")", self, 'WARNING')
        
        return found_objects

    def get_collision_mesh(self, collection):
        """Finds a collision mesh in the collection with a name starting with 'Colmesh-1.'"""
        for obj in collection.objects:
            if obj.type == 'MESH' and obj.name.startswith("Colmesh-1."):
                return obj
        
        Utils.log_and_report("No collision mesh with the prefix 'Colmesh-1.' found.", self, 'WARNING')
        return None

    def duplicate_with_linked_mesh_and_rename(self, ob, new_name):
        """Duplicates an object with a linked mesh and renames it."""
        dup = ob.copy()
        dup.data = ob.data
        dup.name = new_name
        export_collection = bpy.data.collections.get("beamng_export")
        if export_collection:
            export_collection.objects.link(dup)
        else:
            Utils.log_and_report("Export collection 'beamng_export' not found.", self, 'WARNING')
        return dup

    def clear_children(self, empty_obj):
        """Clears children from the given empty object based on a specific naming pattern."""
        prefix = "Colmesh-"
        pattern = re.compile(f"^{re.escape(prefix)}\\d+$")
        children_to_process = list(empty_obj.children)
        for child in children_to_process:
            if pattern.match(child.name):
                bpy.data.objects.remove(child, do_unlink=True)
            else:
                child.parent = None

    def parent_to_empty(self, ob, empty_obj):
        """Parents the given object to an empty object."""
        ob.hide_set(False)
        ob.select_set(True)
        empty_obj.select_set(True)
        bpy.context.view_layer.objects.active = empty_obj
        ob.parent = empty_obj

    def execute(self, context):
        empty_obj = bpy.data.objects.get("start01")
        if not empty_obj:
            Utils.log_and_report("Empty object 'start01' not found.", self, 'WARNING')
            return {'CANCELLED'}

        bpy.ops.object.devtools_beamng_clear_children_for_empty()

        collection = bpy.context.collection
        if not collection:
            Utils.log_and_report("No collection is selected! Please select a collection first.", self, 'WARNING')
            return {'CANCELLED'}

        collection_name = collection.name
        found_assets = self.find_objects_matching_collection_name(collection_name)

        logging.debug(f"Collection \"{collection_name}\" => Mesh objects matching '{collection_name}_a#':")
        for ob in found_assets:
            logging.debug(f"\tObject: {ob.name}")
            self.parent_to_empty(ob, empty_obj)

        colmesh = self.get_collision_mesh(collection)
        if colmesh:
            colmesh = self.duplicate_with_linked_mesh_and_rename(colmesh, "Colmesh-1")
            self.parent_to_empty(colmesh, empty_obj)
            logging.debug(f"Collision Object: {colmesh.name}")

        return {'FINISHED'}
