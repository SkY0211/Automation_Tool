import os
import logging
import sys
from datetime import datetime
from .exception import CallException
from .utils import get_latest_dir, get_parent_dir


class CustomLogger:
    def __init__(self, instance_name):
        self.instance_id = instance_name
        self.log_folder = self.get_latest_log_folder()
        self.log_text = self.configure_logger()  # Create a new logger instance

    @staticmethod
    def get_latest_log_folder():
        logs_dir = os.path.join(get_parent_dir(), "logs")
        existing_folder = get_latest_dir(logs_dir)
        if existing_folder:
            return existing_folder
        else:
            # If no folders found, create a new one with the current timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_folder = os.path.join(logs_dir, timestamp)
            os.makedirs(new_folder, exist_ok=True)
            return new_folder

    def configure_logger(self):

        config_logger = logging.getLogger(f"Instance_{self.instance_id}")
        config_logger.setLevel(logging.DEBUG)  # Set the log level to DEBUG for all messages

        # Remove any existing handlers from the logger
        for handler in config_logger.handlers:
            config_logger.removeHandler(handler)

        # Create a file handler and set the log level to DEBUG
        log_file = os.path.join(self.log_folder, f"{self.instance_id}.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Create a formatter and attach it to the file handler
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)

        # Add the file handler to the logger
        config_logger.addHandler(file_handler)

        return config_logger

    def log(self, message, error=None, level=logging.DEBUG):  # Set the default log level to DEBUG
        self.log_text.log(level, message)

        if error:
            self.log_text.log(logging.ERROR, CallException(error, sys))


if __name__ == "__main__":
    # Example usage:
    # instance_id = "example_instance"
    # logger = CustomLogger(instance_id)
    # logger.log(
    #     "This log will be saved in a folder with timestamp in 'logs' directory with DEBUG level")  # DEBUG level by default
    log = CustomLogger("test")