from dataclasses import dataclass


@dataclass
class DeviceInfo:
    country: str = ""
    code: str    = "+91"
    dev1: dict   = None
    dev2: dict   = None