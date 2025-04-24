import bpy

from unofficial_jbeam_editor.utils.utils import Utils

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

class ManageDynamicButtonsOperator(bpy.types.Operator):
    """Add or Remove Buttons"""
    bl_idname = "wm.manage_dynamic_buttons"
    bl_label = "Manage Dynamic Buttons"

    action: bpy.props.EnumProperty(
        items=[
            ('ADD', "Add Button", "Add a new button"),
            ('REMOVE', "Remove Button", "Remove highlighted buttons")
        ],
        name="Action"
    )  # type: ignore

    def execute(self, context):
        settings = context.scene.dynamic_buttons

        if self.action == 'ADD':
            # Add a new button and deselect others
            for item in settings:
                item.name = ""  # Deselect all
            item = settings.add()  # Add new button
            item.name = f"Button {len(settings)}"  # Make it the active one
        elif self.action == 'REMOVE' and settings:
            # Get indices of highlighted buttons
            highlighted_indices = [i for i, item in enumerate(settings) if item.name]

            if highlighted_indices:
                # Remove all highlighted buttons
                for index in reversed(highlighted_indices):
                    settings.remove(index)

                # Determine the button to highlight next
                last_index = highlighted_indices[-1]
                if last_index < len(settings):
                    # Highlight the next button if it exists
                    settings[last_index].name = f"Button {last_index + 1}"
                elif len(settings) > 0:
                    # Otherwise, highlight the previous button
                    settings[len(settings) - 1].name = f"Button {len(settings)}"
            else:
                Utils.log_and_report("No buttons are highlighted to remove!", self, 'WARNING')

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

        # Create a row and divide it into two parts (80% and 20%)
        split = layout.row(align=True).split(factor=0.8)

        # First part for the dynamically created buttons (80%)
        button_row = split.row(align=True)
        for i, item in enumerate(settings):
            button_row.operator(
                "wm.toggle_dynamic_button",
                text=f"Button {i + 1}" if not item.name else item.name,
                depress=bool(item.name)
            ).index = i

        # Second part for the `+` and `X` buttons (20%)
        control_row = split.row(align=True)
        control_row.operator(ManageDynamicButtonsOperator.bl_idname, text="+").action = 'ADD'
        control_row.operator(ManageDynamicButtonsOperator.bl_idname, text="X").action = 'REMOVE'

        # Display selected buttons
        selected = [item.name for item in settings if item.name]
        layout.label(text=f"Selected: {', '.join(selected) if selected else 'None'}")


# Registration
classes = [ButtonItem, ToggleDynamicButtonOperator, ManageDynamicButtonsOperator, DynamicButtonPanel]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.dynamic_buttons = bpy.props.CollectionProperty(type=ButtonItem)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.dynamic_buttons

if __name__ == "__main__":
    register()
