import os
import re

from unofficial_jbeam_editor.ui.addon_preferences import MyAddonPreferences as a
from unofficial_jbeam_editor.utils.utils import Utils
from unofficial_jbeam_editor.utils.jbeam.jbeam_models import JbeamLoadItem, PcJson, PcJbeamParts


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
            Utils.log_and_report(f"Failed to parse PC file 📄 {self.pc.filepath}: {e}", None, "ERROR")
            return False

        print(f"Loaded part configurator: {self.pc} ")
        return True

    def get_jbeam_load_items(self, search_subdirs=True, search_common=True):
        d = self.directory
        if not self.pc.part_names:
            print(f"⚠️  No part names defined in 📄 {self.pc.filepath}")
            return None

        print(f"🔎 Search .jbeam files in directory 📁  {d} for jbeam part names {self.pc.part_names}")

        part_name_pattern = re.compile(r'^\s*"([^"]+)"\s*:\s*')
        slot_type_pattern = re.compile(r'"slotType"\s*:\s*"([^"]+)"')
        target_parts = set((v, k) for k, v in self.pc.part_names.items())  # (part_name, slot_type)

        search_dirs = [d]
        if search_common:
            common_dir = os.path.join(os.path.dirname(d), "common")
            if os.path.isdir(common_dir):
                search_dirs.append(common_dir)

        if search_subdirs:
            file_iter = (
                os.path.join(root, f)
                for directory in search_dirs
                for root, _, files in os.walk(directory)
                for f in files if f.endswith('.jbeam')
            )
        else:
            file_iter = (
                os.path.join(directory, f)
                for directory in search_dirs
                for f in os.listdir(directory)
                if f.endswith('.jbeam') and os.path.isfile(os.path.join(directory, f))
            )

        load_items: list[JbeamLoadItem] = []
    
        for file_path in file_iter:
            if not file_path.endswith('.jbeam'):
                continue

            print(f"🔎 Opening and reading file 📄 {file_path} ...")

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

