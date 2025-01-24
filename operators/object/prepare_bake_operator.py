import bpy


class OBJECT_OT_PrepareBake(bpy.types.Operator):
    """Prepare Object for Baking"""
    bl_idname = "object.devtools_prepare_bake"
    bl_label = "DevTools: Prepare Bake"
    bl_options = {'REGISTER', 'UNDO'}

    def create_bake_uv_and_select(self, obj, bake_uv):
        uvs = obj.data.uv_layers
        if not uvs:
            self.report({'WARNING'}, "No UV Maps to bake")
            return False
        
        if bake_uv not in uvs:
            uvs.new(name=bake_uv)
            self.report({'INFO'}, "Created 'bake' UV map")
        else:
            self.report({'INFO'}, "'bake' UV map already exists")
        
        bake_uv_map = uvs[bake_uv]
        bake_uv_map.active = True
        uvs.active = bake_uv_map
        self.report({'INFO'}, f"Selected '{bake_uv_map.name}' UV map")
        return True

    def create_bake_texture_and_image(self, bake_texture_name, bake_image_name, width, height):
        if bake_image_name in bpy.data.images:
            bake_image = bpy.data.images[bake_image_name]
            bpy.data.images.remove(bake_image)
            self.report({'INFO'}, f"Deleted existing image: {bake_image_name}")

        bake_image = bpy.data.images.new(name=bake_image_name, width=width, height=height)
        self.report({'INFO'}, f"Created new image: {bake_image_name}")

        if bake_texture_name in bpy.data.textures:
            bake_texture = bpy.data.textures[bake_texture_name]
            self.report({'INFO'}, f"Reusing existing texture: {bake_texture_name}")
        else:
            bake_texture = bpy.data.textures.new(name=bake_texture_name, type='IMAGE')
            self.report({'INFO'}, f"Created new texture: {bake_texture_name}")

        bake_texture.image = bake_image
        return bake_image

    def check_materials(self, obj):
        empty_slots = False
        if len(obj.data.materials) == 0:
            self.report({'WARNING'}, "No materials assigned to this object.")
            return False
        
        for slot in obj.material_slots:
            if slot.material is None:
                empty_slots = True
                break

        if empty_slots:
            self.report({'WARNING'}, "There is at least one empty material slot.")
        else:
            self.report({'INFO'}, f"This object has {len(obj.data.materials)} material(s) assigned and all slots are filled.")
        return not empty_slots

    def add_bake_image_texture_node_to_materials_and_select(self, obj, bake_texture_node_name, bake_image):
        for material in obj.data.materials:
            if not material.use_nodes:
                material.use_nodes = True

            for node in material.node_tree.nodes:
                node.select = False

            existing_node = None
            for node in material.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.name == bake_texture_node_name:
                    existing_node = node
                    break

            if existing_node is None:
                texture_node = material.node_tree.nodes.new(type='ShaderNodeTexImage')
                texture_node.name = bake_texture_node_name
                texture_node.location = (-300, 300)
                existing_node = texture_node
                self.report({'INFO'}, f"Applied 'BakeTexture' to the material: {material.name}")
            else:
                self.report({'INFO'}, f"'BakeTexture' node already exists in material: {material.name}")

            existing_node.select = True
            existing_node.image = bake_image
            material.node_tree.nodes.active = existing_node

    def pack_uv_islands(self):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.select_all(action='SELECT')
        bpy.ops.uv.pack_islands()
        self.report({'INFO'}, " Packed UV Islands. Check results in UV Editor.\n \
* Make island size adjustments if needed then repeat UV > Pack Islands.\n \
* Then click 'Bake' under 'Render Properties'.\n \
* Save image in Image > Save Image\n \
* Duplicate object and remove all uv maps exept 'bake' and rename it to 'UVMap'\n \
* Remove all materials and create new material and connect Image Texture with baked image")
        self.report({'INFO'}, " Object ready to bake")

    def set_bake_settings(self):
        bpy.context.scene.render.engine = 'CYCLES'
        bpy.context.scene.cycles.device = 'GPU'
        bpy.context.scene.cycles.bake_type = 'DIFFUSE'
        bpy.context.scene.render.bake.use_pass_direct = False
        bpy.context.scene.render.bake.use_pass_indirect = False

    def execute(self, context):
        obj = context.active_object

        if obj not in context.selected_objects:
            self.report({'ERROR'}, "No active object selected")
            return {'CANCELLED'}

        if not self.check_materials(obj):
            return {'CANCELLED'}
        
        bake_uv = "bake"
        bake_image = "BakeImage"
        bake_texture = "BakeTexture"

        success = self.create_bake_uv_and_select(obj, bake_uv)
        if not success:
            return {'CANCELLED'}
        image = self.create_bake_texture_and_image(bake_texture, bake_image, 4096, 4096)
        self.add_bake_image_texture_node_to_materials_and_select(obj, bake_texture, image)
        self.pack_uv_islands()
        self.set_bake_settings()

        return {'FINISHED'}
