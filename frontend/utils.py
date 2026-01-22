import os
import winsound

def get_device_name():
    ...

def get_android_version():
    ...

def verify_phone_number(phone):
    ...

def get_latest_dir(path):
    ...

def get_parent_dir(path):
    ...

def create_folders(base_path):
    ...

def play_alert_sound(frequency=800, duration=400, times=2):
    for _ in range(times):
        winsound.Beep(frequency, duration)
