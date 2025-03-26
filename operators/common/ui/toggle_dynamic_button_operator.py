import bpy

class ButtonItem(bpy.types.PropertyGroup):
    BUTTON_NAME = "#-Instance"
    name: bpy.props.StringProperty(name="Button Name", default="")  # type: ignore

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
        button_name = self.button_name.replace("#", str(self.index + 1))

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

    button_amount: bpy.props.IntProperty(default=1, min=1)  # type: ignore
    button_name: bpy.props.StringProperty(default="TheButton#")  # type: ignore
    button_name_shortcut1: bpy.props.StringProperty()  # type: ignore
    button_name_shortcut2: bpy.props.StringProperty()  # type: ignore
    action: bpy.props.EnumProperty(
        items=[
            ('ADD', "Add Button", "Add new buttons"),
            ('REMOVE', "Remove Button", "Remove highlighted buttons")
        ],
        name="Action"
    )  # type: ignore

    def execute(self, context):
        settings = context.scene.beamng_jbeam_instance.buttons

        if self.action == 'ADD':
            # Deselect all existing buttons
            for item in settings:
                item.name = ""

            # Add the specified number of buttons
            first_button_index = len(settings)  # Index of the first button to be added
            for i in range(self.button_amount):
                item = settings.add()
                button_name = self.button_name.replace("#", str(len(settings)))
                item.name = button_name

            # Highlight only the first button added
            if self.button_amount > 1:
                for i, item in enumerate(settings):
                    if i == first_button_index:  # Highlight the first button added
                        button_name = self.button_name.replace("#", str(first_button_index + 1))
                        item.name = button_name
                    else:
                        item.name = ""  # Deselect all others

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
                    button_name = self.button_name.replace("#", str(last_index + 1))
                    settings[last_index].name = button_name
                elif len(settings) > 0:
                    # Otherwise, highlight the previous button
                    button_name = self.button_name.replace("#", str(len(settings)))
                    settings[len(settings) - 1].name = button_name
            else:
                self.report({'WARNING'}, "No buttons are highlighted to remove!")

        return {'FINISHED'}
