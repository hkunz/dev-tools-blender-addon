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

    def get_jbeam_load_items(self):
        load_items: list[JbeamLoadItem] = []
        d = self.directory
        print(f"🔎📁 Search .jbeam files in directory {d} for jbeam part names {self.pc.part_names}")
        part_name_pattern = re.compile(r'^\s*"([^"]+)"\s*:\s*')
        slot_type_pattern = re.compile(r'"slotType"\s*:\s*"([^"]+)"')
        target_parts = set((v, k) for k, v in self.pc.part_names.items())  # (part_name, slot_type)

        for filename in os.listdir(d):
            if not filename.endswith('.jbeam'):
                continue

            file_path = os.path.join(d, filename)
            print(f"🔎📄 Opening and reading file {file_path} ...")
            with open(file_path, 'r', encoding='utf-8') as f:
                depth = 0
                curr_part_name = None

                for i, line in enumerate(f):
                    if depth == 1:
                        match = part_name_pattern.match(line)
                        if match:
                            curr_part_name = match.group(1)

                    depth += line.count("{") - line.count("}")

                    if not curr_part_name or '"slotType"' not in line:
                        continue

                    slot_match = slot_type_pattern.search(line)
                    if not slot_match:
                        continue

                    found_slot_type = slot_match.group(1)
                    if (curr_part_name, found_slot_type) in target_parts:
                        print(f"===> Part Match 🎯 on line {i+1}: '{curr_part_name}' matches slotType '{found_slot_type}'")
                        load_items.append(JbeamLoadItem(file_path, curr_part_name, found_slot_type))
                        curr_part_name = None  # Reset after match

        return load_items

