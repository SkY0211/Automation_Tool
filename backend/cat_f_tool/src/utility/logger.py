import os
import logging
import sys
from datetime import datetime

from backend.cat_f_tool.src.utility.exceptions import FPAException


class CustomLogger:
    def __init__(self, instance_name, latest_log_dir):
        self.instance_id = instance_name
        self.log_folder  = latest_log_dir
        self.log_text    = self.configure_logger()

    def configure_logger(self):
        config_logger = logging.getLogger(f"CatF_Instance_{self.instance_id}")
        config_logger.setLevel(logging.DEBUG)

        for handler in config_logger.handlers:
            config_logger.removeHandler(handler)

        log_file     = os.path.join(self.log_folder, f"{self.instance_id}.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        config_logger.addHandler(file_handler)

        return config_logger

    def log(self, message, error=None, level=logging.DEBUG):
        self.log_text.log(level, message)
        if error:
            self.log_text.log(logging.ERROR, FPAException(error, sys))