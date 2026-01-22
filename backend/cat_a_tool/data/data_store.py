from dataclasses import dataclass
from typing import List, Dict


@dataclass
class Data:
    device_count: int = 0
    test_type: str = None
    iterations: int = 0
    duration: int = 0
    delay: int = 0
    udids: List[str] = None
    device_info: Dict[str, str] = None

    __instance = None  # Class-level variable to store the singleton instance

    @classmethod
    def get_instance(cls):
        if cls.__instance is None:
            # Create the singleton instance if it doesn't exist
            cls.__instance = cls(udids=[], device_info={})
        return cls.__instance