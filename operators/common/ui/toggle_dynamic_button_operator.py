import bpy

class ButtonItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Button Name", default="")  # type: ignore

class ButtonItemSelector(bpy.types.PropertyGroup):
    buttons: bpy.props.CollectionProperty(type=ButtonItem)  # type: ignore
    active_instance: bpy.props.IntProperty()  # type: ignore

class ToggleDynamicButtonOperator(bpy.types.Operator):
    """Toggle Buttons with Shift+Click for Multi-Select"""
    bl_idname = "wm.toggle_dynamic_button"
    bl_label = "Toggle Dynamic Button"

    button_name: bpy.props.StringProperty()  # type: ignore
    index: bpy.props.IntProperty()  # type: ignore

    def invoke(self, context, event):
        settings = context.scene.beamng_jbeam_instance.buttons
        is_shift = event.shift

        if is_shift:
            # Toggle the current button
            settings[self.index].name = (
                "" if settings[self.index].name else f"{self.button_name} {self.index + 1}"
            )
        else:
            # Deselect all buttons and select only the clicked one
            for item in settings:
                item.name = ""
            settings[self.index].name = f"{self.button_name} {self.index + 1}"

        return {'FINISHED'}

class ManageDynamicButtonsOperator(bpy.types.Operator):
    """Add or Remove Buttons"""
    bl_idname = "wm.manage_dynamic_buttons"
    bl_label = "Manage Dynamic Buttons"

    button_name: bpy.props.StringProperty()  # type: ignore
    action: bpy.props.EnumProperty(
        items=[
            ('ADD', "Add Button", "Add a new button"),
            ('REMOVE', "Remove Button", "Remove highlighted buttons")
        ],
        name="Action"
    )  # type: ignore

    def execute(self, context):
        settings = context.scene.beamng_jbeam_instance.buttons

        if self.action == 'ADD':
            # Add a new button and deselect others
            for item in settings:
                item.name = ""  # Deselect all
            item = settings.add()  # Add new button
            item.name = f"{self.button_name} {len(settings)}"  # Make it the active one
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
                    settings[last_index].name = f"{self.button_name} {last_index + 1}"
                elif len(settings) > 0:
                    # Otherwise, highlight the previous button
                    settings[len(settings) - 1].name = f"{self.button_name} {len(settings)}"
            else:
                self.report({'WARNING'}, "No buttons are highlighted to remove!")

        return {'FINISHED'}
