from dataclasses import dataclass


@dataclass
class TestCred:
    call_type:    str = "voice"
    test_type:    str = "MO calls"
    country_code: str = "+91"
    iterations:   int = 10
    call_duration: int = 30
    call_delay:   int = 5