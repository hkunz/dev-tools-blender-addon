import bpy

class ButtonItem(bpy.types.PropertyGroup):
    BUTTON_NAME = "# Instance"
    name: bpy.props.StringProperty(name="Button Name", default="")  # type: ignore

    @staticmethod
    def generate_button_name(index, ordinal=True):
        """Generate button name by replacing '#' with the index."""
        suffix = f"{index + 1}"  # Convert index to 1-based numbering
        if ordinal:
            if suffix.endswith("1") and suffix != "11":
                suffix += "st"
            elif suffix.endswith("2") and suffix != "12":
                suffix += "nd"
            elif suffix.endswith("3") and suffix != "13":
                suffix += "rd"
            else:
                suffix += "th"
        return ButtonItem.BUTTON_NAME.replace("#", suffix)

class ButtonItemSelector(bpy.types.PropertyGroup):
    buttons: bpy.props.CollectionProperty(type=ButtonItem)  # type: ignore
    active_instance: bpy.props.IntProperty()  # type: ignore

class ToggleDynamicButtonOperator(bpy.types.Operator):
    """Toggle Buttons with Shift+Click for Multi-Select"""
    bl_idname = "wm.toggle_dynamic_button"
    bl_label = "Toggle Dynamic Button"

    button_name: bpy.props.StringProperty(default="TheButton#")  # type: ignore
    index: bpy.props.IntProperty()  # type: ignore

    def invoke(self, context, event):
        settings = context.scene.beamng_jbeam_instance.buttons
        is_shift = event.shift
        button_name = ButtonItem.generate_button_name(self.index)

        if is_shift:
            # Toggle the current button
            settings[self.index].name = (
                "" if settings[self.index].name else button_name
            )
        else:
            # Deselect all buttons and select only the clicked one
            for item in settings:
                item.name = ""
            settings[self.index].name = button_name

        return {'FINISHED'}

class ManageDynamicButtonsOperator(bpy.types.Operator):
    """Add or Remove Buttons"""
    bl_idname = "wm.beamng_jbeam_manage_jbeam_instance_buttons"
    bl_label = "Manage Dynamic Buttons"

    button_amount: bpy.props.IntProperty(default=1, min=1)  # type: ignore - Number of buttons to add
    button_name: bpy.props.StringProperty(default="Button #")  # type: ignore - Template for button names
    action: bpy.props.EnumProperty(
        items=[
            ('ADD', "Add Button", "Add new buttons"),
            ('REMOVE', "Remove Button", "Remove highlighted buttons")
        ],
        name="Action"
    )  # type: ignore - Specify add/remove actions

    def execute(self, context):
        settings = context.scene.beamng_jbeam_instance.buttons

        if self.action == 'ADD':
            # Deselect all existing buttons
            for item in settings:
                item.name = ""

            # Add the specified number of buttons
            first_button_index = len(settings)
            for i in range(self.button_amount):
                item = settings.add()
                item.name = ButtonItem.generate_button_name(first_button_index + i)

            # Ensure only the first button added is highlighted
            if self.button_amount > 1:
                for i in range(first_button_index + 1, len(settings)):
                    settings[i].name = ""

        elif self.action == 'REMOVE' and settings:
            # Get indices of highlighted buttons
            highlighted_indices = [i for i, item in enumerate(settings) if item.name]

            if highlighted_indices:
                # Remove highlighted buttons in reverse order
                for index in reversed(highlighted_indices):
                    settings.remove(index)

                # Highlight the next or previous button, if any remain
                if len(settings) > 0:
                    next_highlight_index = min(highlighted_indices[-1], len(settings) - 1)
                    settings[next_highlight_index].name = ButtonItem.generate_button_name(next_highlight_index)
            else:
                self.report({'WARNING'}, "No buttons are highlighted to remove!")

        return {'FINISHED'}
