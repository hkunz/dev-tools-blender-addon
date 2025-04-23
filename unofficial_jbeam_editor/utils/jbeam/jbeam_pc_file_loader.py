import json
import logging

from pathlib import Path

from unofficial_jbeam_editor.ui.addon_preferences import MyAddonPreferences as a
from unofficial_jbeam_editor.utils.jbeam.jbeam_loader import JbeamLoaderBase
from unofficial_jbeam_editor.utils.jbeam.jbeam_models import PcJson


class JbeamPcFileLoader(JbeamLoaderBase):
    def __init__(self, filepath: str, operator=None):
        super().__init__(filepath, operator)
        self.model_file_path: Path | None = None

    def _load_main(self, filepath: str) -> PcJson:
        self.is_jbeam = False
        with open(filepath, "r", encoding="utf-8") as f:
            raw_json: PcJson = json.load(f)
        self.json_str = json.dumps(raw_json)
        return raw_json

    def _validate_content(self, json_data: dict) -> PcJson:
        required_keys = {"format", "model", "parts"}

        # Case 1: fully valid .pc structure
        if required_keys.issubset(json_data):
            if not isinstance(json_data["parts"], dict) or not json_data["parts"]:
                model = json_data["model"]
                self.model_file_path = Path(self.directory) / f"{model}.jbeam"
                if self.model_file_path.exists():
                    return json_data
                raise ValueError("❌ Invalid .pc file: 'parts' must be a non-empty object.")
            return json_data

        # Case 2: modern .pc structure missing optional keys
        if "parts" in json_data:
            parts = json_data["parts"]
            if not isinstance(parts, dict) or not parts:
                raise ValueError("❌ Invalid .pc file: 'parts' must be a non-empty object.")

            missing_keys = []
            if "format" not in json_data:
                json_data["format"] = 2
                missing_keys.append("format")
            if "model" not in json_data:
                json_data["model"] = "undefined"
                missing_keys.append("model")

            if missing_keys:
                logging.debug(f"⚠️  Warning: .pc file was missing {missing_keys}; defaults have been inserted.")
            return json_data

        # Case 3: legacy-style wrapped structure
        if len(json_data) == 1:
            main_key = next(iter(json_data))
            inner = json_data[main_key]

            if not isinstance(inner, dict):
                raise ValueError(f"❌ Expected dict under key '{main_key}', got {type(inner).__name__}")

            parts = inner.get("parts")
            if isinstance(parts, dict) and parts:
                missing_keys = []
                if "format" not in inner:
                    inner["format"] = 2
                    missing_keys.append("format")
                if "model" not in inner:
                    inner["model"] = "undefined"
                    missing_keys.append("model")

                if missing_keys:
                    logging.debug(f"⚠️  Legacy .pc file under '{main_key}' was missing {missing_keys}; defaults have been inserted.")
                return inner
            else:
                raise ValueError(f"❌ Invalid .pc file: 'parts' under '{main_key}' must be a non-empty object.")

        # Case 4: completely invalid or ambiguous structure
        raise ValueError("❌ Invalid .pc file: missing 'parts' section and no legacy structure detected.")




