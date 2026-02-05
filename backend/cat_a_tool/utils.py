import json
import os
import re
import subprocess
import sys
from datetime import datetime

import pandas
import screeninfo
import winsound

from backend.cat_a_tool.exception import CallException
from backend.cat_a_tool.data.constants import COLUMNS



# from backend.logger import CustomLogger


def generate_window_locations(n):
    monitor_info = screeninfo.get_monitors()[0]
    screen_width = monitor_info.width
    screen_height = monitor_info.height

    max_windows_per_column = 3
    window_width = 40
    window_height = 20
    horizontal_padding = 50
    vertical_padding = 50

    if n <= max_windows_per_column:
        # Generate locations for a single column
        window_locations = [(horizontal_padding, vertical_padding + i * (window_height + vertical_padding))
                            for i in range(n)]
    else:
        # Generate locations for two columns
        windows_per_column = (n + 1) // 2  # Round up to the nearest integer
        column_width = window_width + horizontal_padding
        column_padding = (screen_width - 2 * column_width) // 3  # Padding between the columns

        window_locations = []
        for i in range(n):
            if i < windows_per_column:
                # First column
                x = column_padding + i * column_width
                y = vertical_padding + i * (window_height + vertical_padding)
            else:
                # Second column
                x = 2 * column_padding + window_width + (i - windows_per_column) * column_width
                y = vertical_padding + (i - windows_per_column) * (window_height + vertical_padding)
            window_locations.append((x, y))

    return window_locations


# def get_desired_caps(udid: str, android_version: str, device_name: str) -> dict:
#     desired_caps["appium:udid"] = udid
#     desired_caps["appium:platformVersion"] = android_version
#     desired_caps["appium:deviceName"] = device_name
# 
#     return desired_caps

def restart_device(udid, custom_logger):
    try:
        subprocess.run(
            ["adb", "-s", udid, "reboot"],
            timeout=10
        )
        custom_logger.log(f"Restarting device: {udid}")
    except Exception as e:
        custom_logger.log("Failed to restart device", e)


def toggle_data(device, state: int, custom_logger):
    try:
        custom_logger.log(f"Mobile Data set to {state} for {device}")
        cmd = [
            "adb", "-s", device, "shell",
            "svc", "data", "enable" if state == 1 else "disable"
        ]
        subprocess.run(cmd, check=True, timeout=10)
    except Exception as e:
        custom_logger.log("Failed to toggle Mobile Data", e)
        CallException(e, sys)


def toggle_wifi(device, state: int, custom_logger):
    try:
        custom_logger.log(f"Wi-Fi set to {state} for {device}")
        cmd = [
            "adb", "-s", device, "shell",
            "svc", "wifi", "enable" if state == 1 else "disable"
        ]
        subprocess.run(cmd, check=True, timeout=10)
    except Exception as e:
        custom_logger.log("Failed to toggle Wi-Fi", e)
        CallException(e, sys)


# -------------------- STATS --------------------

def stats(df: pandas.DataFrame, custom_logger):
    try:
        total = df["Iteration"].nunique()
        pass_count = df.Status[df.Status == 'PASS'].count()
        fail_count = df.Status[df.Status == 'FAILED'].count()
        call_drop_count = df.Status[df.Status == 'CALL_DROPPED'].count()

        row = [
            "Pass Count", f"{pass_count}/{total}", None,
            "Fail Count", f"{fail_count}/{total}", None,
            "Call Drop", f"{call_drop_count}/{total}", None
        ] + [""] * (len(COLUMNS) - 9)

        df.loc[len(df)] = row
    except Exception as e:
        custom_logger.log("Failed to calculate stats", e)
        CallException(e, sys)
    return df


# -------------------- TELEPHONY --------------------

def get_service_state(udid, custom_logger):
    try:
        custom_logger.log(f"Fetching ServiceState for {udid}")
        result = subprocess.run(
            ["adb", "-s", udid, "shell", "dumpsys", "telephony.registry"],
            capture_output=True,
            text=True,
            timeout=10
        )

        output = result.stdout
        lines = [l for l in output.splitlines() if "mServiceState" in l]

        states = []
        for line in lines:
            match = re.search(r"mVoiceRegState=\d+\((.*?)\)", line)
            if match:
                states.append(match.group(1))

        return states
    except Exception as e:
        custom_logger.log("ServiceState error", e)
        return []


def get_cell_info(udid: str, sim_slot: int, custom_logger):
    try:
        custom_logger.log(f"Collecting Cell Info for {udid}")

        operator = subprocess.check_output(
            ["adb", "-s", udid, "shell", "getprop", "gsm.operator.alpha"],
            text=True,
            timeout=10
        ).strip()

        output = subprocess.check_output(
            ["adb", "-s", udid, "shell", "dumpsys", "telephony.registry"],
            text=True,
            timeout=10
        )

        cell_lines = [l for l in output.splitlines() if l.strip().startswith("mCellInfo")]
        service_lines = [l for l in output.splitlines() if l.strip().startswith("mServiceState")]

        cell = cell_lines[sim_slot]
        service = service_lines[sim_slot]

        def rx(p): 
            m = re.search(p, cell + service)
            return m.group(1) if m else None

        return [
            operator,
            rx(r"mMcc=(\d+)"),
            rx(r"mMnc=(\d+)"),
            rx(r"mBandwidth=(\d+)"),
            rx(r"m(Ci|Nci)=(\d+)"),
            rx(r"mBands=\[(\d+)\]"),
            rx(r"getRilVoiceRadioTechnology=\d+\((\w+)\)"),
            rx(r"mPci=(\d+)"),
            rx(r"mTac=(\d+)"),
            rx(r"m(Earfcn|NrArfcn)=(\d+)"),
            rx(r"Rsrp=(-?\d+)"),
            rx(r"Rsrq=(-?\d+)")
        ]
    except Exception as e:
        custom_logger.log("Failed to collect Cell Info", e)
        return ["NA"] * 12


def get_location(udid, custom_logger):
    try:
        custom_logger.log(f"Getting GPS location for {udid}")
        result = subprocess.run(
            ["adb", "-s", udid, "shell", "dumpsys", "location"],
            capture_output=True,
            text=True,
            timeout=10
        )

        for line in result.stdout.splitlines():
            if "last location=Location" in line:
                match = re.search(r"Location\[[^ ]+ (-?\d+\.\d+), (-?\d+\.\d+)", line)
                if match:
                    return [float(match.group(1)), float(match.group(2))]
    except Exception as e:
        custom_logger.log("Location error", e)

    return [None, None]


def print_folder_structure(root_dir, indent='', structure=''):
    for item in os.listdir(root_dir):
        if item.startswith('.') or item.startswith('_') or item == 'venv':
            # Ignore folders starting with '.' or '_'
            continue

        item_path = os.path.join(root_dir, item)
        if os.path.isdir(item_path):
            structure += indent + '|-- ' + item + '/\n'
            structure = print_folder_structure(item_path, indent + '    ', structure)
        else:
            structure += indent + '|-- ' + item + '\n'

    return structure


def validate_input(text):
    if text.isdigit() and text in ['2', '4', '6', '8', '10']:
        return True
    else:
        return False


def get_parent_dir():
    return os.path.dirname(os.getcwd())


def get_latest_dir(root_dir):
    # Get a list of all folders in the reports directory
    folders = [folder for folder in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, folder))]

    # Sort the folders based on the timestamps in descending order
    sorted_folders = sorted(folders, key=lambda x: os.path.getmtime(os.path.join(root_dir, x)), reverse=True)

    # Get the path of the last added folder
    if sorted_folders:
        last_added_folder = sorted_folders[0]
        last_added_folder_path = os.path.join(root_dir, last_added_folder)
        return last_added_folder_path
    else:
        return None


def get_constants_file_path():
    if getattr(sys, 'frozen', False):
        # Running as a bundled .exe (PyInstaller)
        return os.path.join(sys._MEIPASS, "constants.py")
    else:
        # Running as a Python script
        return os.path.join(os.path.dirname(__file__), "constants.py")


def load_from_json(json_file_path):
    with open(json_file_path, "r") as file:
        data = json.load(file)
    return data


def get_android_version(udid, custom_logger):
    command = ['adb', '-s', udid, 'shell', 'getprop', 'ro.build.version.release']
    try:
        output = subprocess.check_output(command, universal_newlines=True)
        return output.strip()
    except subprocess.CalledProcessError as e:
        CallException(e, sys)
        custom_logger.log(f"Error executing adb command:", e)
        return "Unknown"


def get_device_name(udid, custom_logger):
    command = ['adb', '-s', udid, 'shell', 'getprop', 'ro.product.model']
    try:
        output = subprocess.check_output(command, universal_newlines=True)
        return output.strip()
    except subprocess.CalledProcessError as e:
        CallException(e, sys)
        custom_logger.log(f"Error executing adb command:", e)
        return "Unknown"


def verify_phone_number(phone_number):
    # Function to verify the phone number
    if re.match(r'^\d{10}$', phone_number):
        return True
    else:
        return False


def create_folders():
    name = f"{datetime.now().strftime('%m%d%Y__%H%M%S')}"
    log_path = os.path.join(get_parent_dir(), 'logs', name)
    reports_path = os.path.join(get_parent_dir(), 'reports', name)

    os.makedirs(log_path, exist_ok=True)
    os.makedirs(reports_path, exist_ok=True)


def count_connected_devices(custom_logger=None):
    try:
        output = subprocess.check_output(["adb", "devices"]).decode("utf-8")
        lines = output.splitlines()

        # Find the line index where the list of devices starts
        start_index = next((index for index, line in enumerate(lines) if line.startswith("List of devices")), None)

        if start_index is not None:
            devices = [line.split("\t")[0] for line in lines[start_index + 1:] if "\tdevice" in line]
        else:
            devices = []
        count = len(devices)
        return count, devices
    except subprocess.CalledProcessError as e:
        custom_logger.log("Error:", e)
        return 0, None

def update_cat_a_device_state(cat_a_state, custom_logger=None):
    count, devices = count_connected_devices(custom_logger)

    if not devices:
        cat_a_state["devices"] = []
        cat_a_state["pairs"] = []
        cat_a_state["mo_connected"] = False
        cat_a_state["mt_connected"] = False
        return

    cat_a_state["devices"] = devices

    pairs = []
    pair_index = 1

    for i in range(0, len(devices), 2):
        mo = devices[i] if i < len(devices) else None
        mt = devices[i + 1] if i + 1 < len(devices) else None

        pair = {
            "pair_id": pair_index,
            "mo_serial": mo,
            "mt_serial": mt,
            "mo_connected": mo is not None,
            "mt_connected": mt is not None,
        }

        pairs.append(pair)
        pair_index += 1

    cat_a_state["pairs"] = pairs

    # Backward compatibility (Pair 1)
    first = pairs[0] if pairs else {}
    cat_a_state["mo_serial"] = first.get("mo_serial")
    cat_a_state["mt_serial"] = first.get("mt_serial")
    cat_a_state["mo_connected"] = first.get("mo_connected", False)
    cat_a_state["mt_connected"] = first.get("mt_connected", False)


def play_alert_sound(frequency=800, duration=400, times=2):
    # Frequency of the alert sound in Hz
    # Duration of the alert sound in milliseconds
    [winsound.Beep(frequency, duration) for _ in range(times)]


if __name__ == "__main__":
    # l = CustomLogger('test utils')
    #
    # print(get_location("NUNI270102", None))
    # print(get_location("NUNI410102", None))
    play_alert_sound(duration=400, times=1)
