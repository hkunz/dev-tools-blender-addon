import bpy

class OBJECT_OT_GenerateBakeObject(bpy.types.Operator):
    """Duplicate object, clean up materials and UV maps, and create a new material with BakeImage"""
    bl_idname = "object.devtools_generate_baked_object"
    bl_label = "DevTools: Generate Baked Object"

    def execute(self, context):
        # Ensure only one object is selected
        if len(bpy.context.selected_objects) != 1:
            self.report({'WARNING'}, "Please select only one object.")
            return {'CANCELLED'}
        
        obj = bpy.context.active_object
        bpy.ops.object.bake(type='DIFFUSE')
        
        # Ensure object has a UV map named "bake"
        if "bake" not in obj.data.uv_layers:
            self.report({'ERROR'}, "The object does not have a 'bake' UV map.")
            return {'CANCELLED'}
        
        print(f"Found 'bake' UV map: bake")
        
        # Duplicate the object
        duplicated_obj = obj.copy()
        duplicated_obj.data = obj.data.copy()  # Copy the mesh data to the new object
        duplicated_obj.animation_data_clear()  # Clear any animation data
        bpy.context.collection.objects.link(duplicated_obj)
        
        print(f"Duplicated object: {duplicated_obj.name}")
        
        # Ensure the duplicated object is the active one
        bpy.context.view_layer.objects.active = duplicated_obj
        duplicated_obj.select_set(True)
        obj.select_set(False)  # Deselect the original object
        
        # Remove all materials from the duplicated object
        duplicated_obj.data.materials.clear()
        print(f"Removed all materials from: {duplicated_obj.name}")
        
        # Access UV layers of the duplicated object
        uv_layers = duplicated_obj.data.uv_layers
        
        # Debug: Print all UV maps of the duplicated object
        print(f"UV maps for {duplicated_obj.name}:")
        for uv_layer in uv_layers:
            print(f"- {uv_layer.name}")
        
        print("Removing all UV maps except 'bake'...")
        
        # Remove all UV maps except the "bake" map
        for uv_layer in uv_layers:
            print(f"Checking UV map: {uv_layer.name}")
            if uv_layer.name != "bake":
                print(f"Removing UV map: {uv_layer.name}")
                uv_layers.remove(uv_layer)
        
        # Create a new material and assign to the duplicated object
        new_material = bpy.data.materials.new(name="material_baked")
        new_material.use_nodes = True  # Enable node-based material
        duplicated_obj.data.materials.append(new_material)
        
        # Create an image texture and assign it to the new material
        texture_node = new_material.node_tree.nodes.new(type='ShaderNodeTexImage')
        texture_node.image = bpy.data.images.get("BakeImage")  # Ensure BakeImage exists
        print(f"Assigned image texture 'BakeImage' to material.")
        
        # Find the Principled BSDF node and connect the image texture
        bsdf_node = new_material.node_tree.nodes.get("Principled BSDF")
        if bsdf_node:
            new_material.node_tree.links.new(texture_node.outputs["Color"], bsdf_node.inputs["Base Color"])
        
        return {'FINISHED'}
