import bpy
import logging

class OBJECT_OT_BakeGenerateObject(bpy.types.Operator):
    """Bake then Duplicate object, clean up materials and UV maps, and create a new material with BakeImage"""
    bl_idname = "object.devtools_bake_generate_object"
    bl_label = "DevTools: Generate Baked Object"
    bl_options = {'REGISTER', 'UNDO'}

    def duplicate_object(self, obj, mat):
        duplicated_obj = obj.copy()
        duplicated_obj.data = obj.data.copy()
        duplicated_obj.animation_data_clear()
        bpy.context.collection.objects.link(duplicated_obj)
        
        logging.debug(f"Duplicated object: {duplicated_obj.name}")

        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = duplicated_obj
        duplicated_obj.select_set(True)

        duplicated_obj.data.materials.clear()
        duplicated_obj.data.materials.append(mat)
        logging.debug(f"{duplicated_obj.name}: Removed all materials and added new material {mat.name}")

        return duplicated_obj

    def clear_old_uv_maps(self, duplicated_obj):
        uv_layers = duplicated_obj.data.uv_layers
        logging.debug("Removing all UV maps except 'bake'...")
        uv_to_remove = [uv_layer.name for uv_layer in uv_layers if uv_layer.name != "bake"]

        for uv_name in uv_to_remove:
            logging.debug(f"Removing UV map: {uv_name}")
            uv_layers.remove(uv_layers[uv_name])

        bake_uv_layer = uv_layers.get("bake")

        if bake_uv_layer:
            logging.debug(f"Renaming UV map 'bake' to 'UVMap'")
            bake_uv_layer.name = "UVMap"
        else:
            logging.debug("Warning: 'bake' UV map not found, no renaming done.")


    def create_new_material(self):
        new_material = bpy.data.materials.new(name="material_baked")
        new_material.use_nodes = True

        texture_node = new_material.node_tree.nodes.new(type='ShaderNodeTexImage')
        texture_node.image = bpy.data.images.get("BakeImage")
        texture_node.location = (-350, 300)
        
        logging.debug(f"Assigned image texture 'BakeImage' to material.")

        bsdf_node = new_material.node_tree.nodes.get("Principled BSDF")
        if bsdf_node:
            new_material.node_tree.links.new(texture_node.outputs["Color"], bsdf_node.inputs["Base Color"])
        
        return new_material

    def select_baked_objects(self, context, baked_objects):
        for obj in context.view_layer.objects:
            obj.select_set(False)
        for new_obj in baked_objects:
            new_obj.select_set(True)
        if baked_objects:
            bpy.context.view_layer.objects.active = baked_objects[0]


    def execute(self, context):
        bpy.ops.object.mode_set(mode='OBJECT')
        obj = context.active_object

        if obj not in context.selected_objects:
            self.report({'WARNING'}, "Please select one active object")
            return {'CANCELLED'}

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                self.report({'WARNING'}, f"{obj.name}: All selected objects must be of type 'MESH'")
                return {'CANCELLED'}

            if "bake" not in obj.data.uv_layers:
                self.report({'WARNING'}, f"{obj.name}: Missing 'bake' UV map. Click 'Prepare Bake'")
                return {'CANCELLED'}

        logging.debug(f"{obj.name}: Found 'bake' UV map. Start baking object/s {[obj.name for obj in context.selected_objects]}")
        bpy.ops.object.bake(type='DIFFUSE')

        mat = self.create_new_material()

        baked_objects = []

        for obj in context.selected_objects:
            duplicated_obj = self.duplicate_object(obj, mat)
            baked_objects.append(duplicated_obj)
            self.clear_old_uv_maps(duplicated_obj)

        self.select_baked_objects(context, baked_objects)

        self.report({'INFO'}, "Duplicated object's shader setup ready with Image Texture containing baked image\n \
* Don't forget to save baked image in UV Editor under Image > Save Image\n \
* Rename your material and the baked image to something more meaningful")
        self.report({'INFO'}, "Baked Object(s) Ready")

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'