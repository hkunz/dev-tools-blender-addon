import bpy
import re
import os
import json

from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper

from dev_tools.ui.addon_preferences import MyAddonPreferences as a # type: ignore
from dev_tools.utils.json_cleanup import json_cleanup  # type: ignore
from dev_tools.utils.utils import Utils  # type: ignore
from dev_tools.utils.temp_file_manager import TempFileManager  # type: ignore
from dev_tools.utils.jbeam.jbeam_parser import JbeamParser  # type: ignore
from dev_tools.utils.jbeam.jbeam_helper import JbeamFileHelper  # type: ignore
from dev_tools.utils.jbeam.jbeam_node_mesh_creator import JbeamNodeMeshCreator  # type: ignore
from dev_tools.utils.jbeam.jbeam_node_mesh_configurator import JbeamNodeMeshConfigurator  # type: ignore

class PartConfig:

    def __init__(self):
        self.filepath: str = ""
        self.format: int = 0
        self.model: str = "",
        self.part_names: dict[str, str] = {}  # key (slot type) value (part name)

    def __repr__(self):
        return f"{self.__class__.__name__}(format={self.format}, model={self.model}, parts={self.part_names})"


class JbeamPcParser:

    def __init__(self):
        self.pc = PartConfig()
        self.json_str: str = ""

    def load_pc_file(self, filepath):
        self.pc.filepath = filepath
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                raw_json = json.load(f)
                self.json_str = raw_json

            if "format" in raw_json and "model" in raw_json and "parts" in raw_json:
                data = raw_json
            else:
                main_key = next(iter(raw_json))
                data = raw_json[main_key]

            self.pc.format = data.get("format")
            self.pc.model = data.get("model")
            self.pc.part_names = data.get("parts", {})

            print(f"Loaded part configurator: {self.pc}")
            print(f"Part Configurator Load Success: {filepath}")

        except Exception as e:
            print(f"Failed to parse PC file {filepath}: {e}")
            Utils.log_and_raise(f"Failed to parse PC file {filepath}: {e}", ValueError, e)

    def load_pc_file_from_string(self, text):
        """Load and clean JBeam file from string."""
        try:
            self.json_str = json_cleanup(text)
            self.jbeam_data = json.loads(self.json_str)
            print("Loaded pc file data successfully from fixed string")
        except json.JSONDecodeError as e:
            Utils.log_and_raise(f"Error decoding JSON from JBeam string: {e}", ValueError, e)

    def get_json_str(self) -> str:
        return self.json_str