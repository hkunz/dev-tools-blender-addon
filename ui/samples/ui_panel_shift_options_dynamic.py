import bpy

class ButtonItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Button Name", default="")  # type: ignore

class ToggleDynamicButtonOperator(bpy.types.Operator):
    """Toggle Buttons with Shift+Click for Multi-Select"""
    bl_idname = "wm.toggle_dynamic_button"
    bl_label = "Toggle Dynamic Button"

    index: bpy.props.IntProperty()  # type: ignore

    def invoke(self, context, event):
        settings = context.scene.dynamic_buttons
        is_shift = event.shift

        if is_shift:
            # Toggle the current button
            settings[self.index].name = (
                "" if settings[self.index].name else f"Button {self.index + 1}"
            )
        else:
            # Deselect all buttons and select only the clicked one
            for item in settings:
                item.name = ""
            settings[self.index].name = f"Button {self.index + 1}"

        return {'FINISHED'}

class DynamicButtonPanel(bpy.types.Panel):
    bl_label = "Dynamic Buttons"
    bl_idname = "PT_DYNAMIC_BUTTON_PANEL"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Example'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.dynamic_buttons

        row = layout.row(align=True)

        # Dynamically create buttons
        for i, item in enumerate(settings):
            row.operator(
                "wm.toggle_dynamic_button",
                text=f"Button {i + 1}" if not item.name else item.name,
                depress=bool(item.name)
            ).index = i

        # Display selected buttons
        selected = [item.name for item in settings if item.name]
        layout.label(text=f"Selected: {', '.join(selected) if selected else 'None'}")

def register_dynamic_buttons(num_buttons):
    """Populate the dynamic button collection with the desired number of buttons."""
    settings = bpy.context.scene.dynamic_buttons
    settings.clear()
    for i in range(num_buttons):
        item = settings.add()
        item.name = ""

# Registration
classes = [ButtonItem, ToggleDynamicButtonOperator, DynamicButtonPanel]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dynamic_buttons = bpy.props.CollectionProperty(type=ButtonItem)
    register_dynamic_buttons(num_buttons=5)  # Set the default number of buttons here

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.dynamic_buttons

if __name__ == "__main__":
    register()
