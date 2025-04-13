import os

from dev_tools.utils.jbeam.jbeam_parser import JbeamParser  # type: ignore
from dev_tools.utils.temp_file_manager import TempFileManager  # type: ignore
from dev_tools.utils.jbeam.jbeam_helper import JbeamFileHelper  # type: ignore
from dev_tools.ui.addon_preferences import MyAddonPreferences as a  # type: ignore
from dev_tools.utils.utils import Utils  # type: ignore


class JbeamFileLoader:

    def __init__(self, filename: str, operator=None):
        self.filename = filename
        self.operator = operator
        self.parser = JbeamParser()

    def load(self, path: str) -> JbeamParser:
        try:
            self.parser.load_jbeam(path)
        except Exception as e:
            jbeam_fixed_str = self._attempt_fix_and_log(path, e)
            self._load_fixed_string(jbeam_fixed_str)
            self._write_debug_files(jbeam_fixed_str)
        return self.parser

    def _attempt_fix_and_log(self, path: str, error: Exception) -> str:
        json_str = self.parser.get_json_str()
        error_text = JbeamFileHelper.extract_json_error_snippet(error, json_str)
        show_warning = a.is_addon_option_enabled("show_import_warnings")
        Utils.log_and_report(f"Initial load failed with '{error}'. Error Snippet: {error_text}. Attempting auto-fix...", self.operator if show_warning else None, "WARNING")
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        return JbeamFileHelper.attempt_fix_jbeam_commas(raw)

    def _load_fixed_string(self, jbeam_str: str):
        try:
            self.parser.load_jbeam_from_string(jbeam_str)
            print(f"Auto-fix and load success: {self.filename}")
        except Exception as e:
            error_text = JbeamFileHelper.extract_json_error_snippet(e, jbeam_str)
            Utils.log_and_report(f"Failed to fix and load file: '{e}'. Error Text: {error_text}", self.operator, "ERROR")
            raise e

    def _write_debug_files(self, jbeam_str: str):
        try:
            tmp_dir = TempFileManager().create_temp_dir()
            os.makedirs(tmp_dir, exist_ok=True)
            file_path1 = os.path.join(tmp_dir, self.filename)
            file_path2 = os.path.join(tmp_dir, f"{self.filename}.json")

            with open(file_path1, 'w', encoding='utf-8') as f:
                f.write(jbeam_str)
            with open(file_path2, 'w', encoding='utf-8') as f:
                f.write(self.parser.get_json_str())
        except Exception as write_error:
            Utils.log_and_report(f"Failed to write debug files: {write_error}", self.operator, "ERROR")
