import json
import os

from dev_tools.utils.jbeam.jbeam_models import JbeamLoadItem, JbeamJson  # type: ignore
from dev_tools.utils.temp_file_manager import TempFileManager  # type: ignore
from dev_tools.utils.jbeam.jbeam_helper import JbeamFileHelper  # type: ignore
from dev_tools.utils.json_cleanup import json_cleanup  # type: ignore
from dev_tools.ui.addon_preferences import MyAddonPreferences as a  # type: ignore
from dev_tools.utils.utils import Utils  # type: ignore

'''
class JbeamLoader:
    def __init__(self, filepath, operator=None):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.operator = operator
        self.json_str = ""

class JbeamFileLoader(JbeamLoader):

    def __init__(self, load_item:JbeamLoadItem, operator=None):
        super().__init__(load_item.file_path, operator)
        self.load_item  = load_item
'''

import os
import json
from abc import ABC, abstractmethod
from dev_tools.utils.temp_file_manager import TempFileManager  # type: ignore
from dev_tools.utils.json_cleanup import json_cleanup  # type: ignore
from dev_tools.utils.utils import Utils  # type: ignore
from dev_tools.utils.jbeam.jbeam_helper import JbeamFileHelper  # type: ignore
from dev_tools.ui.addon_preferences import MyAddonPreferences as a  # type: ignore

class JbeamLoaderBase(ABC):
    def __init__(self, filepath: str, operator=None):
        self.filepath = filepath
        self.directory = os.path.dirname(filepath)
        self.filename = os.path.basename(filepath)
        self.operator = operator
        self.json_str = ""

    def load(self):
        print(f"\n🔄 Loading {self.filepath}")
        data = None
        try:
            return self._load_main(self.filepath)
        except Exception as e:
            Utils.log_and_report(f"⚠️  Initial load failed with '{e}'. Attempting auto-fix...", self.operator if a.is_warnings_enabled() else None, "WARNING")
            fixed_str = self._attempt_fix(self.filepath, e)
            try:
                data = self._load_from_string(fixed_str)
            except json.JSONDecodeError as e:
                Utils.log_and_report(f"JSON decode error: {e}", self.operator, "ERROR")
            except UnicodeDecodeError as e:
                Utils.log_and_report(f"Unicode decode error in fixed file: {e}", self.operator, "ERROR")
            except TypeError as e:
                Utils.log_and_report(f"Type error (maybe fixed_str is None?): {e}", self.operator, "ERROR")
            except Exception as e:
                Utils.log_and_report(f"Unexpected error: {e}", self.operator, "ERROR")
            self._write_debug_files(fixed_str)
            if not data:
                Utils.log_and_report(f"❌ Failed to fix and parse file {self.filepath}", self.operator, "ERROR")
            return data

    def _attempt_fix(self, path: str, error: Exception) -> str:
        snippet = JbeamFileHelper.extract_json_error_snippet(error, self.json_str)
        print(f"Fix attempt due to: {error}. Snippet: {snippet}")
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        return raw  # override method and return JbeamFileHelper.attempt_fix_jbeam_commas(raw, False)

    def _write_debug_files(self, fixed_str: str):
        try:
            tmp_dir = TempFileManager().create_temp_dir()
            fix_path = os.path.join(tmp_dir, self.filename)
            os.makedirs(tmp_dir, exist_ok=True)
            with open(fix_path, 'w', encoding='utf-8') as f:
                f.write(fixed_str)
            with open(os.path.join(tmp_dir, f"{self.filename}.json"), 'w', encoding='utf-8') as f:
                f.write(self.json_str)
            Utils.log_and_report(f"📄 Attempted fix written to: {fix_path}", self.operator, "INFO")
        except Exception as write_error:
            Utils.log_and_report(f"❌ Failed to write debug files: {write_error}", self.operator, "ERROR")

    @abstractmethod
    def _load_main(self, filepath: str):
        pass

    @abstractmethod
    def _load_from_string(self, text: str):
        pass


class JbeamFileLoader(JbeamLoaderBase):
    def __init__(self, load_item: JbeamLoadItem, operator=None):
        super().__init__(load_item.file_path, operator)
        self.load_item = load_item

    def _load_main(self, filepath: str) -> JbeamJson:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            raw_text = f.read()
        self.json_str = json_cleanup(raw_text)
        return json.loads(self.json_str)

    def _load_from_string(self, text: str) -> JbeamJson:
        self.json_str = json_cleanup(text)
        print("✅ Loaded .jbeam from fixed string")
        return json.loads(self.json_str)

    def _attempt_fix(self, path: str, error: Exception) -> str:
        raw = super()._attempt_fix(path, error)
        return JbeamFileHelper.attempt_fix_jbeam_commas(raw)
