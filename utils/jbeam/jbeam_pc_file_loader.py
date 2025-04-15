import json
import os

from dev_tools.ui.addon_preferences import MyAddonPreferences as a # type: ignore
from dev_tools.utils.temp_file_manager import TempFileManager  # type: ignore
from dev_tools.utils.json_cleanup import json_cleanup  # type: ignore
from dev_tools.utils.utils import Utils  # type: ignore
from dev_tools.utils.jbeam.jbeam_helper import JbeamFileHelper  # type: ignore

class JbeamPcFileLoader:
    def __init__(self, filepath: str, operator=None):
        self.filepath = filepath
        self.directory = os.path.dirname(self.filepath)
        self.filename = os.path.basename(self.filepath)
        self.operator = operator
        self.json_str = ""

    def load(self):
        try:
            print(f"\n🔄 Loading {self.filepath}")
            with open(self.filepath, 'r', encoding='utf-8') as f:
                raw_json = json.load(f)
                self.json_str = raw_json

            if "format" in raw_json and "model" in raw_json and "parts" in raw_json:
                data = raw_json
            else:
                main_key = next(iter(raw_json))
                data = raw_json[main_key]
        except Exception as e:
            Utils.log_and_report(f"⚠️  Initial load failed with '{e}'. Attempting auto-fix...", None, "WARNING")
            pc_fixed_str = self._get_fixed_string(e)
            data = self._load_fixed_string(pc_fixed_str)
        return data

    def _load_fixed_string(self, pc_json):
        tmp_dir = TempFileManager().create_temp_dir()
        os.makedirs(tmp_dir, exist_ok=True)
        file_path1 = os.path.join(tmp_dir, self.filename)
        file_path2 = os.path.join(tmp_dir, f"{self.filename}.json")
        data: dict = {}
        try:
            data = self._load_pc_file_from_string(pc_json)
            print(f"Auto-Fix and Load Success {self.filename}")
        except Exception as e2:
            error_text = JbeamFileHelper.extract_json_error_snippet(e2, pc_json)
            print(f"Failed to fix and load file: '{e2}' Error Text: {error_text}\nWrote attempted fix file to: {file_path1}")

        try:
            with open(file_path1, 'w') as f:
                f.write(pc_json)
            with open(file_path2, 'w') as f:
                f.write(self.json_str)
        except Exception as write_error:
            Utils.log_and_report(f"Failed to write the attempted fix file: {write_error}", None, "ERROR")

        return data

    def _load_pc_file_from_string(self, text):
        """Load and clean JBeam file from string."""
        try:
            self.json_str = json_cleanup(text)
            data: dict = json.loads(self.json_str)
            print("Loaded pc file data successfully from fixed string")
        except json.JSONDecodeError as e:
            Utils.log_and_raise(f"Error decoding JSON from JBeam string: {e}", ValueError, e)
        return data

    def _get_fixed_string(self, e):
        error_text = JbeamFileHelper.extract_json_error_snippet(e, self.json_str)
        show_warning = a.is_warnings_enabled()
        print(f"⚠️  Init load failed with '{e}' Error Text: {error_text}. Trying to auto-fix commas and attempt reload...")
        with open(self.filepath, "r", encoding="utf-8") as f:
            raw = f.read()
        return JbeamFileHelper.attempt_fix_jbeam_commas(raw, False)
