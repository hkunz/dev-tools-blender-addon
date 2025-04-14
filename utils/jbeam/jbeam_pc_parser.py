import json
import os
import re

from dev_tools.ui.addon_preferences import MyAddonPreferences as a # type: ignore
from dev_tools.utils.json_cleanup import json_cleanup  # type: ignore
from dev_tools.utils.utils import Utils  # type: ignore


class PartConfig:

    def __init__(self):
        self.directory: str = ""
        self.filepath: str = ""
        self.format: int = 0
        self.model: str = ""
        self.part_names: dict[str, str] = {}  # key (slot type) value (part name)

    def __repr__(self):
        return f"{self.__class__.__name__}(format={self.format}, model={self.model}, parts={self.part_names})"


class JbeamLoadItem:
    def __init__(self, part_name: str, slot_type: str, file_path: str):
        self.part_name = part_name
        self.slot_type = slot_type
        self.file_path = file_path

    def __repr__(self):
        return f"{self.__class__.__name__}(part_name={self.part_name}, slot_type={self.slot_type}, file_path={self.file_path})"

class JbeamPcParser:

    def __init__(self):
        self.pc = PartConfig()
        self.json_str: str = ""

    def load_pc_file(self, filepath):
        import os

        self.pc.filepath = filepath
        self.pc.directory = os.path.dirname(filepath)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                raw_json = json.load(f)
                self.json_str = raw_json

            if "format" in raw_json and "model" in raw_json and "parts" in raw_json:
                data = raw_json
            else:
                main_key = next(iter(raw_json))
                data = raw_json[main_key]

            self._on_pc_data_load(data)

        except Exception as e:
            print(f"Failed to parse PC file {filepath}: {e}")
            Utils.log_and_raise(f"Failed to parse PC file {filepath}: {e}", ValueError, e)

    def _on_pc_data_load(self, data):
        self.pc.format = data.get("format")
        self.pc.model = data.get("model")
        self.pc.part_names = data.get("parts", {})

        print(f"Loaded part configurator: {self.pc} ")
        print(f"Part Configurator Loaded from File: {self.pc.filepath}")

    def load_pc_file_from_string(self, text):
        """Load and clean JBeam file from string."""
        try:
            self.json_str = json_cleanup(text)
            data = json.loads(self.json_str)
            self._on_pc_data_load(data)
            print("Loaded pc file data successfully from fixed string")
        except json.JSONDecodeError as e:
            Utils.log_and_raise(f"Error decoding JSON from JBeam string: {e}", ValueError, e)

    def get_json_str(self) -> str:
        return self.json_str

    def get_jbeam_load_items(self):
        load_items: list[JbeamLoadItem] = []
        d = self.pc.directory
        print(f"🔎📁 Search .jbeam files in directory {d} for jbeam part names {self.pc.part_names}")
        part_name_pattern = r'^\s*"([^"]+)"\s*:\s*'  # r'^\s*"([^"]+)"\s*:\s*{'

        for filename in os.listdir(d):
            if not filename.endswith('.jbeam'):
                continue
            file_path = os.path.join(d, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                print(f"🔎📄 Opening and reading file {file_path} ...")
                lines = f.readlines()

            depth = 0
            curr_part_name = None

            for slot_type, part_name in self.pc.part_names.items():
                # print(f"🔎 Scanning for part name '{part_name}' with slotType '{slot_type}'")
                for i, line in enumerate(lines):
                    if depth == 1:  # Match only if we're at the top level (depth 1)
                        match = re.match(part_name_pattern, line)
                        if match:
                            curr_part_name = match.group(1)
                            #print(f"Found part name: {current_part}")
                    depth += line.count("{") - line.count("}")  # Track curly brace depth to avoid matching nested "information"
                    if not curr_part_name or '"slotType"' not in line:
                        continue
                    slot_match = re.search(r'"slotType"\s*:\s*"([^"]+)"', line)
                    if not slot_match:
                        continue
                    found_slot_type = slot_match.group(1)
                    if found_slot_type != slot_type or curr_part_name != part_name:
                        continue
                    print(f"===> Part Match 🎯 on line {i+1}: '{curr_part_name}' matches slotType '{found_slot_type}'")
                    load_items.append(JbeamLoadItem(curr_part_name, found_slot_type, file_path))
                    curr_part_name = None  # reset after checking
        return load_items
