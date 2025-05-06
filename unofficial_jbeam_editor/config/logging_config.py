import logging
import os
import re

from unofficial_jbeam_editor.utils.file_utils import FileUtils

class AnsiFilter(logging.Filter):
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

    def filter(self, record):
        record.msg = self.ansi_escape.sub('', str(record.msg))
        return True

def configure_logging(enable=True):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if enable else logging.CRITICAL)
    
    if logger.hasHandlers():
        return

    stream_handler = logging.StreamHandler()  # Console handler

    applog_path = os.path.normpath(os.path.join(FileUtils.get_addon_root_dir(), "app.log"))
    file_handler = logging.FileHandler(applog_path, mode='w')  # overwrite instead of append
    file_handler.addFilter(AnsiFilter())

    formatter = logging.Formatter('%(levelname)s: %(message)s')
    stream_handler.setFormatter(formatter)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    logger.setLevel(logging.DEBUG)
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
