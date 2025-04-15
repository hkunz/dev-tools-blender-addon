import json
import os
import re

from dev_tools.ui.addon_preferences import MyAddonPreferences as a # type: ignore
from dev_tools.utils.utils import Utils  # type: ignore
from dev_tools.utils.jbeam.jbeam_models import JbeamLoadItem, PcJson, PcJbeamParts  # type: ignore


class PartConfig:

    def __init__(self):
        self.directory: str = ""
        self.filepath: str = ""
        self.format: int = 0
        self.model: str = ""
        self.part_names: PcJbeamParts = {}  # key (slot type) value (part name)

    def __repr__(self):
        return f"{self.__class__.__name__}(format={self.format}, model={self.model}, parts={self.part_names})"

class JbeamPcParser:

    def __init__(self, directory):
        self.pc = PartConfig()
        self.directory = directory

    def parse(self, data: PcJson):
        try:
            self.pc.directory = self.directory
            self.pc.format = data.get("format")
            self.pc.model = data.get("model")
            self.pc.part_names = data.get("parts", {})
        except Exception as e:
            Utils.log_and_report(f"Failed to parse PC file {self.pc.filepath}: {e}", None, "ERROR")
            return

        print(f"Loaded part configurator: {self.pc} ")
        print(f"Part Configurator Loaded from File: {self.pc.filepath}")

    def get_jbeam_load_items(self):
        load_items: list[JbeamLoadItem] = []
        d = self.directory
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
                    load_items.append(JbeamLoadItem(file_path, curr_part_name, found_slot_type))
                    curr_part_name = None  # reset after checking
        return load_items
