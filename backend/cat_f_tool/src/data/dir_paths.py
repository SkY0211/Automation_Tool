from dataclasses import dataclass


@dataclass
class Paths:
    latest_log_dir_path:       str = ""
    latest_report_dir_path:    str = ""
    latest_user_info_dir_path: str = ""