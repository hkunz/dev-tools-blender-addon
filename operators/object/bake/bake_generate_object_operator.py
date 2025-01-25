import bpy

class OBJECT_OT_BakeGenerateObject(bpy.types.Operator):
    """Bake then Duplicate object, clean up materials and UV maps, and create a new material with BakeImage"""
    bl_idname = "object.devtools_bake_generate_object"
    bl_label = "DevTools: Generate Baked Object"

    def execute(self, context):
        bpy.ops.object.mode_set(mode='OBJECT')
        obj = context.active_object

        if obj not in context.selected_objects or len(context.selected_objects) > 1:
            self.report({'WARNING'}, "Please select one active object")
            return {'CANCELLED'}

        if "bake" not in obj.data.uv_layers:
            self.report({'WARNING'}, "Object no 'bake' UV map. Click 'Prepare Bake'")
            return {'CANCELLED'}
        
        print(f"Found 'bake' UV map. Start baking ...")
        bpy.ops.object.bake(type='DIFFUSE')

        duplicated_obj = obj.copy()
        duplicated_obj.data = obj.data.copy()
        duplicated_obj.animation_data_clear()
        bpy.context.collection.objects.link(duplicated_obj)
        
        print(f"Duplicated object: {duplicated_obj.name}")

        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = duplicated_obj
        duplicated_obj.select_set(True)

        duplicated_obj.data.materials.clear()
        print(f"Removed all materials from: {duplicated_obj.name}")

        uv_layers = duplicated_obj.data.uv_layers

        print("Removing all UV maps except 'bake'...")
        
        uv_to_remove = [uv_layer for uv_layer in uv_layers if uv_layer.name != "bake"]
        for uv_layer in uv_to_remove:
            print(f"Removing UV map: {uv_layer.name}")
            uv_layers.remove(uv_layer)

        bake_uv_layer = None
        for uv_layer in uv_layers:
            if uv_layer.name == "bake":
                bake_uv_layer = uv_layer
                break

        if bake_uv_layer:
            print(f"Renaming UV map 'bake' to 'UVMap'")
            bake_uv_layer.name = "UVMap"

        new_material = bpy.data.materials.new(name="material_baked")
        new_material.use_nodes = True
        duplicated_obj.data.materials.append(new_material)

        texture_node = new_material.node_tree.nodes.new(type='ShaderNodeTexImage')
        texture_node.image = bpy.data.images.get("BakeImage")
        
        print(f"Assigned image texture 'BakeImage' to material.")

        bsdf_node = new_material.node_tree.nodes.get("Principled BSDF")
        if bsdf_node:
            new_material.node_tree.links.new(texture_node.outputs["Color"], bsdf_node.inputs["Base Color"])

        self.report({'INFO'}, "Duplicated object's shader setup ready with Image Texture containing baked image\n \
* Don't forget to save baked image in UV Editor under Image > Save Image\n \
* Rename your material and the baked image to something more meaningful")
        self.report({'INFO'}, "Baked Object Ready")

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'