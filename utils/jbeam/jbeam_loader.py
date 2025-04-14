import os

from dev_tools.utils.jbeam.jbeam_models import JbeamLoadItem  # type: ignore
from dev_tools.utils.jbeam.jbeam_parser import JbeamParser  # type: ignore
from dev_tools.utils.temp_file_manager import TempFileManager  # type: ignore
from dev_tools.utils.jbeam.jbeam_helper import JbeamFileHelper  # type: ignore
from dev_tools.ui.addon_preferences import MyAddonPreferences as a  # type: ignore
from dev_tools.utils.utils import Utils  # type: ignore


class JbeamFileLoader:

    def __init__(self, load_item:JbeamLoadItem, operator=None):
        self.load_item  = load_item
        self.filename = os.path.basename(load_item.file_path)
        self.operator = operator
        self.parser = JbeamParser()

    def load(self) -> JbeamParser:
        try:
            path = self.load_item.file_path
            print(f"🔄 Loading {path}")
            self.parser.load_jbeam(path)
        except Exception as e:
            jbeam_fixed_str = self._attempt_fix_and_log(path, e)
            success =self._load_fixed_string(jbeam_fixed_str)
            self._write_debug_files(jbeam_fixed_str)
            if not success:
                raise e
        return self.parser

    def show_warnings(self):
        return a.is_addon_option_enabled("show_import_warnings")

    def _attempt_fix_and_log(self, path: str, error: Exception) -> str:
        json_str = self.parser.get_json_str()
        error_text = JbeamFileHelper.extract_json_error_snippet(error, json_str)
        
        Utils.log_and_report(f"⚠️  Initial load failed with '{error}'. Error Snippet: {error_text}. Attempting auto-fix...", self.operator if self.show_warnings() else None, "WARNING")
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        return JbeamFileHelper.attempt_fix_jbeam_commas(raw)

    def _load_fixed_string(self, jbeam_str: str):
        try:
            self.parser.load_jbeam_from_string(jbeam_str)
            print(f"✅ Auto-fix and load success: {self.filename}")
            return True
        except Exception as e:
            error_text = JbeamFileHelper.extract_json_error_snippet(e, jbeam_str)
            Utils.log_and_report(f"🚫 Failed to fix and load file: {self.load_item.file_path} with error '{e}'. Error Text: {error_text}", self.operator, "ERROR")
        return False

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
            Utils.log_and_report(f"Attempted fix of .jbeam syntax written to: {file_path1}", self.operator if self.show_warnings() else None, "INFO")
        except Exception as write_error:
            Utils.log_and_report(f"Failed to write debug files: {write_error}", self.operator, "ERROR")
