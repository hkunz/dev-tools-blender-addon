import os

from dev_tools.ui.addon_preferences import MyAddonPreferences as a # type: ignore
from dev_tools.utils.temp_file_manager import TempFileManager  # type: ignore
from dev_tools.utils.utils import Utils  # type: ignore
from dev_tools.utils.jbeam.jbeam_pc_parser import JbeamPcParser  # type: ignore
from dev_tools.utils.jbeam.jbeam_helper import JbeamFileHelper  # type: ignore

class JbeamPcFileLoader:
    def __init__(self, filepath: str, filename: str, parser: JbeamPcParser):
        self.filepath = filepath
        self.filename = filename
        self.parser = parser

    def try_load(self):
        try:
            print(f"\n🔄 Loading {self.filepath}")
            self.parser.load_pc_file(self.filepath)
            return True
        except Exception as e:
            pc_fixed_str = self._get_fixed_string(e)
            return self._try_load_fixed_string(pc_fixed_str)

    def _try_load_fixed_string(self, pc_json):
        success = True
        tmp_dir = TempFileManager().create_temp_dir()
        os.makedirs(tmp_dir, exist_ok=True)
        file_path1 = os.path.join(tmp_dir, self.filename)
        file_path2 = os.path.join(tmp_dir, f"{self.filename}.json")

        try:
            self.parser.load_pc_file_from_string(pc_json)
            print(f"Auto-Fix and Load Success {self.filename}")
        except Exception as e2:
            error_text = JbeamFileHelper.extract_json_error_snippet(e2, pc_json)
            print(f"Failed to fix and load file: '{e2}' Error Text: {error_text}\nWrote attempted fix file to: {file_path1}")
            success = False

        try:
            json_str = self.parser.get_json_str()
            with open(file_path1, 'w') as f:
                f.write(pc_json)
            with open(file_path2, 'w') as f:
                f.write(json_str)
        except Exception as write_error:
            Utils.log_and_report(f"Failed to write the attempted fix file: {write_error}", None, "ERROR")

        return success

    def _get_fixed_string(self, e):
        json_str = self.parser.get_json_str()
        error_text = JbeamFileHelper.extract_json_error_snippet(e, json_str)
        show_warning = a.is_addon_option_enabled("show_import_warnings")
        print(f"⚠️  Init load failed with '{e}' Error Text: {error_text}. Trying to auto-fix commas and attempt reload...")
        with open(self.filepath, "r", encoding="utf-8") as f:
            raw = f.read()
        return JbeamFileHelper.attempt_fix_jbeam_commas(raw, False)
