import json

from dev_tools.ui.addon_preferences import MyAddonPreferences as a # type: ignore
from dev_tools.utils.temp_file_manager import TempFileManager  # type: ignore
from dev_tools.utils.json_cleanup import json_cleanup  # type: ignore
from dev_tools.utils.utils import Utils  # type: ignore
from dev_tools.utils.jbeam.jbeam_helper import JbeamFileHelper  # type: ignore
from dev_tools.utils.jbeam.jbeam_loader import JbeamLoaderBase  # type: ignore


class JbeamPcFileLoader(JbeamLoaderBase):
    def _load_main(self, filepath: str) -> dict:
        with open(filepath, "r", encoding="utf-8") as f:
            raw_json = json.load(f)
        self.json_str = json.dumps(raw_json)

        if "format" in raw_json and "model" in raw_json and "parts" in raw_json:
            return raw_json
        else:
            main_key = next(iter(raw_json))
            return raw_json[main_key]

    def _load_from_string(self, text: str) -> dict:
        self.json_str = json_cleanup(text)
        data = json.loads(self.json_str)
        print("✅ Loaded .pc file data from fixed string")
        if "format" in data and "model" in data and "parts" in data:
            return data
        else:
            return data[next(iter(data))]

    def _attempt_fix(self, path: str, error: Exception) -> str:
        raw = super()._attempt_fix(path, error)
        return JbeamFileHelper.attempt_fix_jbeam_commas(raw, False)
