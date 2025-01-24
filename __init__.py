# "Dev Tools"
# Author: Harry McKenzie
#
# ##### BEGIN LICENSE BLOCK #####
#
# Dev Tools
# Copyright (c) 2024 Harry McKenzie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# ##### END LICENSE BLOCK #####

bl_info = {
    "name": "Dev Tools",
    "description": "Dev Tools description here",
    "author" : "Harry McKenzie",
    "version": (0, 0, 0),
    "blender": (2, 93, 0),
    "location": "N-Panel > Dev Tools",
    "warning": "",
    "doc_url": "https://blendermarket.com/products/dev_tools/docs",
    "wiki_url": "https://blendermarket.com/products/dev_tools/docs",
    "tracker_url": "https://blendermarket.com/products/dev_tools/docs",
    "support": "COMMUNITY",
    "category": "Import-Export",
}

import bpy
import stat

from pathlib import Path
from typing import Union
from bpy.app.handlers import persistent

from dev_tools.ui.addon_preferences import register as register_preferences, unregister as unregister_preferences # type: ignore
from dev_tools.utils.file_utils import FileUtils # type: ignore
from dev_tools.utils.temp_file_manager import TempFileManager # type: ignore
from dev_tools.utils.icons_manager import IconsManager # type: ignore
from dev_tools.translation.translations import register as register_translations, unregister as unregister_translations # type: ignore
from dev_tools.ui.sidebar_menu import register as register_sidebar_menu, unregister as unregister_sidebar_menu # type: ignore
from dev_tools.operators.common.operator_generic_popup import register as register_generic_popup, unregister as unregister_generic_popup # type: ignore

def add_executable_permission(exe: Union[str, Path]) -> Path: #https://blender.stackexchange.com/questions/310144/mac-executable-binary-within-addon-zip-loses-execute-permission-when-addon-zip
    app = Path(f"{exe}")
    print("Using voxconvert:", app, f"({FileUtils.get_file_size(app)})")
    app.chmod(app.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return app

@persistent
def on_application_load(a, b):
    print("Application load post handler ==============>", a, b)
    #check_addon_compatibility() # check compatibility of addon and its settings if opened in another blender version

def register() -> None:
    print("Addon Registration Begin ==============>")
    #add_executable_permission(FileUtils.get_executable_filepath())
    register_preferences()
    register_translations()
    register_sidebar_menu()
    register_generic_popup()
    TempFileManager().init()
    IconsManager().init()
    bpy.app.handlers.load_post.append(on_application_load)
    print("Addon Registration Complete <==========\n")

def unregister() -> None:
    print("Addon Unregistration Begin ============>")
    unregister_preferences()
    unregister_translations()
    unregister_sidebar_menu()
    unregister_generic_popup()
    TempFileManager().cleanup()
    IconsManager().cleanup()
    bpy.app.handlers.load_post.clear()
    print("Addon Unregistration Complete <========\n")
