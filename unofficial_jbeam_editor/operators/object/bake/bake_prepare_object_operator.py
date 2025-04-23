import bpy
import logging

from unofficial_jbeam_editor.utils.utils import Utils

class OBJECT_OT_BakePrepareObject(bpy.types.Operator):
    """Prepare Object for Baking"""
    bl_idname = "object.devtools_bake_prepare_object"
    bl_label = "DevTools: Prepare Bake"
    bl_options = {'REGISTER', 'UNDO'}


    def create_bake_uv_and_select(self, obj, bake_uv):
        uvs = obj.data.uv_layers
        if not uvs:
            self.report({'WARNING'}, f"No UV Maps to bake in object '{obj.name}'")
            return False

        if bake_uv in uvs:
            if uvs.active.name == bake_uv:
                self.report({'ERROR'}, "Please select a UV map you want as a reference to bake on.")
                return False
            else:
                logging.debug(f"{obj.name}: Removing existing 'bake' UV map...")
                uvs.remove(uvs[bake_uv])

        bake_uv_map = uvs.new(name=bake_uv)
        uvs.active = bake_uv_map
        logging.debug(f"{obj.name}: UV map '{bake_uv_map.name}' created, ready and selected")
        return True


    def delete_bake_image(self, bake_image_name):
        bake_image = bpy.data.images.get(bake_image_name)
        if bake_image:
            bpy.data.images.remove(bake_image)
            logging.debug(f"Deleted existing image: {bake_image_name}")
            bake_image = None

    def create_bake_texture_and_image(self, bake_texture_name, bake_image_name, width, height):
        bake_image = bpy.data.images.get(bake_image_name)

        if not bake_image:
            bake_image = bpy.data.images.new(name=bake_image_name, width=width, height=height)
            logging.debug(f"Created new image: {bake_image_name}")

        if bake_texture_name in bpy.data.textures:
            bake_texture = bpy.data.textures[bake_texture_name]
            logging.debug(f"Reusing existing texture: {bake_texture_name}")
        else:
            bake_texture = bpy.data.textures.new(name=bake_texture_name, type='IMAGE')
            logging.debug(f"Created new texture: {bake_texture_name}")

        bake_texture.image = bake_image
        return bake_image

    def check_materials(self, obj):
        empty_slots = False
        if len(obj.data.materials) == 0:
            self.report({'WARNING'}, f"No materials assigned to object '{obj.name}'")
            return False
        
        for slot in obj.material_slots:
            if slot.material is None:
                empty_slots = True
                break

        if empty_slots:
            self.report({'WARNING'}, f"There is at least one empty material slot in object '{obj.name}'")
        else:
            logging.debug(f"{obj.name}: {len(obj.data.materials)} material(s) assigned and all slots are filled.")
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
                texture_node.location = (1000, 500)
                existing_node = texture_node
                logging.debug(f"{obj.name}: Applied 'BakeTexture' to the material: {material.name}")
            else:
                logging.debug(f"{obj.name}: 'BakeTexture' node already exists in material: {material.name}. Ignore.")

            existing_node.select = True
            existing_node.image = bake_image
            material.node_tree.nodes.active = existing_node

    def pack_uv_islands(self):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.select_all(action='SELECT')
        bpy.ops.uv.pack_islands()

    def set_bake_settings(self):
        bpy.context.scene.render.engine = 'CYCLES'
        bpy.context.scene.cycles.device = 'GPU'
        bpy.context.scene.cycles.bake_type = 'DIFFUSE'
        bpy.context.scene.render.bake.use_pass_direct = False
        bpy.context.scene.render.bake.use_pass_indirect = False

    def execute(self, context):
        obj = context.active_object

        if obj not in context.selected_objects:
            self.report({'WARNING'}, "No active mesh object selected")
            return {'CANCELLED'}

        properties = context.scene.my_property_group_pointer
        bake_resolution = int(Utils.get_bake_dimension(properties.bake_image_resolution))
        logging.debug(f"Selected Bake Resolution: {bake_resolution}")

        bake_uv = "bake"
        bake_image = "BakeImage"
        bake_texture = "BakeTexture"

        self.delete_bake_image(bake_image)

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                self.report({'WARNING'}, f"{obj.name}: All selected objects must be of type 'MESH'")
                return {'CANCELLED'}
            if not self.check_materials(obj):
                return {'CANCELLED'}

            success = self.create_bake_uv_and_select(obj, bake_uv)
            if not success:
                return {'CANCELLED'}

            image = self.create_bake_texture_and_image(bake_texture, bake_image, bake_resolution, bake_resolution)
            self.add_bake_image_texture_node_to_materials_and_select(obj, bake_texture, image)
            auto_bake = context.scene.my_property_group_pointer.auto_bake_pack_uv_islands
            if auto_bake:
                self.pack_uv_islands()
            self.set_bake_settings()

        logging.debug("Packed UV Islands. Check results in UV Editor.\n \
* Make island size adjustments if needed then repeat UV > Pack Islands.\n \
* Configure baking properties in Render Properties > Bake\n \
* Click 'Generate Bake Object' to bake and duplicate object (that will get setup with bake material)")
        self.report({'INFO'}, f"Objects ready to bake: {[obj.name for obj in context.selected_objects]}")

        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'
