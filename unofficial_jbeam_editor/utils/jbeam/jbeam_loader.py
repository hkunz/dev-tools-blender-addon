import json
import os

from abc import ABC, abstractmethod

from unofficial_jbeam_editor.utils.jbeam.jbeam_models import JbeamLoadItem, JbeamJson, PcJson
from unofficial_jbeam_editor.utils.temp_file_manager import TempFileManager
from unofficial_jbeam_editor.utils.jbeam.jbeam_helper import JbeamFileHelper
from unofficial_jbeam_editor.utils.json_cleanup import json_cleanup
from unofficial_jbeam_editor.ui.addon_preferences import MyAddonPreferences as a
from unofficial_jbeam_editor.utils.utils import Utils


class JbeamLoaderBase(ABC):
    _cache: dict[str, JbeamJson | PcJson | dict | None] = {}

    def __init__(self, filepath: str, operator=None):
        self.filepath = filepath
        self.directory = os.path.dirname(filepath)
        self.filename = os.path.basename(filepath)
        self.operator = operator
        self.is_jbeam = True
        self.json_str = ""

    def load(self):
        print(f"\n🔄 Loading 📄 {self.filepath}")
        cls = type(self)

        if self.filepath in cls._cache:
            cached = cls._cache[self.filepath]
            if cached is None:
                print(f"⚠️  Cached failure for {self.filepath}, skipping reattempt.")
                return None
            print(f"✅ Loaded from cache: {self.filepath}")
            return cached

        if not os.path.exists(self.filepath):
            Utils.log_and_report(f"❌ [FileNotFoundError] {self.filepath}", self.operator, "ERROR")
            cls._cache[self.filepath] = None
            return None

        try:
            data = self._load_main(self.filepath)
            result = self._validate_content(data)
            cls._cache[self.filepath] = result
            return result
        except Exception as e:
            Utils.log_and_report(f"⚠️  Initial load failed with '{e}'. Attempting auto-fix...", self.operator if a.is_warnings_enabled() else None, "WARNING")
            fixed_str = self._attempt_fix(self.filepath, e)
            try:
                data = self._load_from_string(fixed_str)
                result = self._validate_content(data)
                cls._cache[self.filepath] = result
                self._write_debug_files(fixed_str)
                print(f"✅ Loaded data after fixing malformed content from 📄 {self.filepath}")
                return result
            except Exception as e2:
                self._handle_fix_errors(e2, fixed_str)
                cls._cache[self.filepath] = None
                return None

    def _handle_fix_errors(self, e, fixed_str: str):
        if isinstance(e, json.JSONDecodeError):
            Utils.log_and_report(f"JSON decode error: {e}", self.operator, "ERROR")
        elif isinstance(e, UnicodeDecodeError):
            Utils.log_and_report(f"Unicode decode error in fixed file: {e}", self.operator, "ERROR")
        elif isinstance(e, TypeError):
            Utils.log_and_report(f"Type error (maybe fixed_str is None?): {e}", self.operator, "ERROR")
        elif isinstance(e, ValueError):
            Utils.log_and_report(f"Value error '{e}'", self.operator, "ERROR")
        else:
            Utils.log_and_report(f"Unexpected error: {e}", self.operator, "ERROR")
        self._write_debug_files(fixed_str)
        Utils.log_and_report(f"❌ Failed to fix and parse file {self.filepath}", self.operator, "ERROR")


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
        if not isinstance(json_data, dict):
            raise ValueError("❌ Root of the JBeam file must be a dictionary.")
        for part_name, part_data in json_data.items():
            if not isinstance(part_data, dict):
                raise ValueError(f"❌ Part '{part_name}' must be a dictionary.")
            if not part_data:
                raise ValueError(f"❌ Part '{part_name}' must not be empty.")
        return json_data
