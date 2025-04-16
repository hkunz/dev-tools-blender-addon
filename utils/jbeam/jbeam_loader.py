import json
import os

from abc import ABC, abstractmethod

from dev_tools.utils.jbeam.jbeam_models import JbeamLoadItem, JbeamJson  # type: ignore
from dev_tools.utils.temp_file_manager import TempFileManager  # type: ignore
from dev_tools.utils.jbeam.jbeam_helper import JbeamFileHelper  # type: ignore
from dev_tools.utils.json_cleanup import json_cleanup  # type: ignore
from dev_tools.ui.addon_preferences import MyAddonPreferences as a  # type: ignore
from dev_tools.utils.utils import Utils  # type: ignore


class JbeamLoaderBase(ABC):
    def __init__(self, filepath: str, operator=None):
        self.filepath = filepath
        self.directory = os.path.dirname(filepath)
        self.filename = os.path.basename(filepath)
        self.operator = operator
        self.is_jbeam = True
        self.json_str = ""

    def load(self):
        print(f"\n🔄 Loading {self.filepath}")
        data = None
        if not os.path.exists(self.filepath):
            #raise FileNotFoundError(f"❌ File not found: {self.filepath}")
            Utils.log_and_report(f"❌ [FileNotFoundError] {self.filepath}", self.operator, "ERROR")
            return
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
                return None
            print("✅ Loaded data from fixed string")
            return data

    def _attempt_fix(self, path: str, error: Exception) -> str:
        snippet = JbeamFileHelper.extract_json_error_snippet(error, self.json_str)
        print(f"Fix attempt due to: {error}. Snippet: {snippet}")
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        fixed = JbeamFileHelper.attempt_fix_jbeam_commas(raw, self.is_jbeam)
        return fixed

    def json_loads(self, json_string) -> dict:
        self.json_str = json_string
        json_data = json.loads(self.json_str)
        if not isinstance(json_data, dict):
            raise ValueError("❌ Expected a JSON object (dictionary) at the top level")
        main_key = next(iter(json_data), None)
        if main_key is None:
            raise ValueError("❌ Empty JSON structure")
        return json_data

    def _write_debug_files(self, fixed_str: str):
        try:
            tmp_dir = TempFileManager().create_temp_dir()
            fix_path = os.path.join(tmp_dir, self.filename)
            os.makedirs(tmp_dir, exist_ok=True)
            with open(fix_path, 'w', encoding='utf-8') as f:
                f.write(fixed_str)
            with open(os.path.join(tmp_dir, f"{self.filename}.json"), 'w', encoding='utf-8') as f:
                f.write(self.json_str)
            Utils.log_and_report(f"Attempted fix written to: 📄 {fix_path}", self.operator, "INFO")
        except Exception as write_error:
            Utils.log_and_report(f"❌ Failed to write debug files: {write_error}", self.operator, "ERROR")

    def _load_from_string(self, text: str) -> JbeamJson:
        json_data = self.json_loads(json_cleanup(text))
        return self._validate_content(json_data)

    @abstractmethod
    def _validate_content(self, json_data: dict):
        # Check if json data is valid: if not, try to fix the content then return
        pass

    @abstractmethod
    def _load_main(self, filepath: str):
        # Returns: A parsed JSON structure as a specific dictionary type.
        pass


class JbeamFileLoader(JbeamLoaderBase):
    def __init__(self, load_item: JbeamLoadItem, operator=None):
        super().__init__(load_item.file_path, operator)
        self.load_item = load_item

    def _load_main(self, filepath: str) -> JbeamJson:
        with open(filepath, "r", encoding="utf-8") as f:
            raw_text = f.read()
        return self.json_loads(json_cleanup(raw_text))

    def _validate_content(self, json_data: dict):
        # TODO: check content for possible issues
        return json_data
