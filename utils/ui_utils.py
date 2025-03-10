class UiUtils:

    @staticmethod
    def update_ui(context):
        for region in context.area.regions:
            if region.type == "UI":
                region.tag_redraw()

    @staticmethod
    def force_update_ui(context):
        for area in context.screen.areas:
            if area.type in {'PROPERTIES', 'VIEW_3D'}:
                for region in area.regions:
                    if region.type in {'WINDOW', 'UI'}:
                        region.tag_redraw()