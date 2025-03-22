import bpy

class MySettings(bpy.types.PropertyGroup):
    option_1: bpy.props.BoolProperty(name="Option 1")  # type: ignore
    option_2: bpy.props.BoolProperty(name="Option 2")  # type: ignore
    option_3: bpy.props.BoolProperty(name="Option 3")  # type: ignore

class ToggleOptionOperator(bpy.types.Operator):
    """Toggle Options with Shift+Click for Multi-Select"""
    bl_idname = "wm.toggle_option"
    bl_label = "Toggle Option"

    option: bpy.props.StringProperty()  # type: ignore

    def invoke(self, context, event):
        settings = context.scene.my_settings
        is_shift = event.shift
        current_value = getattr(settings, self.option)

        if is_shift:
            # Toggle the current option
            setattr(settings, self.option, not current_value)
        else:
            # Disable all other options and select only this one
            for prop in ['option_1', 'option_2', 'option_3']:
                setattr(settings, prop, False)
            setattr(settings, self.option, True)

        return {'FINISHED'}

class MyPanel(bpy.types.Panel):
    bl_label = "Button-Style Multi-Select"
    bl_idname = "PT_MY_BUTTON_PANEL"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Example'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.my_settings

        row = layout.row(align=True)

        # Create button-style toggles
        row.operator("wm.toggle_option", text="Option 1", depress=settings.option_1).option = "option_1"
        row.operator("wm.toggle_option", text="Option 2", depress=settings.option_2).option = "option_2"
        row.operator("wm.toggle_option", text="Option 3", depress=settings.option_3).option = "option_3"

        # Display selected options
        selected = []
        for prop in ['option_1', 'option_2', 'option_3']:
            if getattr(settings, prop):
                selected.append(prop.replace('_', ' ').title())
        layout.label(text=f"Selected: {', '.join(selected)}")

# Registration
classes = [MySettings, ToggleOptionOperator, MyPanel]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.my_settings = bpy.props.PointerProperty(type=MySettings)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.my_settings

if __name__ == "__main__":
    register()
