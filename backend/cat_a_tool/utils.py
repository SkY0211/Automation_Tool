import json
import os
import re
import subprocess
import sys
from datetime import datetime

import pandas
import screeninfo
import winsound

from .exception import CallException
from .data.constants import COLUMNS


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
        subprocess.run(f"adb -s {udid} reboot", shell=False)
        custom_logger.log(f"Restarting device : {udid}")
    except Exception as e:
        custom_logger.log("Failed to restart", e)


def toggle_data(device, state: 0 or 1, custom_logger):
    try:
        custom_logger.log(f"Mobile Data turned(ON/OFF): {state}")
        if state == 1:
            subprocess.run(f'adb -s {device} shell "svc data enable"', shell=False)
        if state == 0:
            subprocess.run(f'adb -s {device} shell "svc data disable"', shell=False)
    except Exception as e:
        custom_logger.log("Failed to toggle Mobile Data", e)
        CallException(e, sys)


def toggle_wifi(device, state: 0 or 1, custom_logger):
    try:
        custom_logger.log(f"Wi-Fi turned(ON/OFF): {state}")
        if state == 1:
            subprocess.run(f'adb -s {device} shell "svc wifi enable"', shell=False)
        if state == 0:
            subprocess.run(f'adb -s {device} shell "svc wifi disable"', shell=False)
    except Exception as e:
        custom_logger.log("Failed to toggle Wi-Fi.", e)
        CallException(e, sys)


def stats(df: pandas.DataFrame, custom_logger):
    try:
        total = df["Iteration"].nunique()
        pass_count = df.Status[df.Status == 'PASS'].count()
        fail_count = df.Status[df.Status == 'FAILED'].count()
        call_drop_count = df.Status[df.Status == 'CALL_DROPPED'].count()
        row = ["Pass Count = ", f"{pass_count} out of {total}", None,
               "Fail Count = ", f"{fail_count} out of {total}", None,
               "Call Drop Count = ", f"{call_drop_count} out of {total}", None] + [""] * (len(COLUMNS) - 9)
        df.loc[len(df)] = row
    except Exception as e:
        CallException(e, sys)
        custom_logger.log("Failed to Calculate Pass-Fail %", e)
    return df


def get_service_state(udid, custom_logger):
    try:
        custom_logger.log(f"Fetching mServiceState from {udid}")
        # Run the adb shell command and capture the output
        adb_command = ["adb", '-s', udid, "shell", "dumpsys", "telephony.registry"]
        completed_process = subprocess.run(adb_command, capture_output=True, text=True)
        output = completed_process.stdout

        # Search for lines starting with "mServiceState"
        mservice_lines = [line for line in output.splitlines() if line.strip().startswith("mServiceState")]

        voice_reg_states = []
        data_reg_states = []

        # Iterate through each mservice line and extract the desired portion
        for line in mservice_lines:
            pattern = r'mVoiceRegState=\d+\((.*?)\), mDataRegState=\d+\((.*?)\)'
            match = re.search(pattern, line)
            if match:
                voice_reg_states.append(match.group(1))
                data_reg_states.append(match.group(2))

        if voice_reg_states:
            return voice_reg_states
        else:
            custom_logger.log("Failed to find the mServiceState")
            return []
    except Exception as e:
        custom_logger.log("Error in mServiceState: ", e)
        return []


def get_cell_info(udid:str, sim_slot: int, custom_logger):
    custom_logger.log(f"Collecting Cell Info <{udid}>...")
    try:
        cell_infos = []
        service_states = []
        cell_info_line = None
        service_state_line = None
        # Run the command and capture the output
        op_name_output = subprocess.check_output(["adb", "-s", f"{udid}", "shell", "getprop", "gsm.operator.alpha"],
                                                 shell=False)
        operator_name = op_name_output.decode("utf-8").strip()[:-1]
        # Execute the adb command to get the telephony registry information
        output = subprocess.check_output(["adb", "-s", udid, "shell", "dumpsys", "telephony.registry"], text=True)

        # Search for "mCellInfo" and "mServiceState" in the output
        cell_infos = [line for line in output.splitlines() if line.strip().startswith("mCellInfo")]
        service_states = [line for line in output.splitlines() if line.strip().startswith("mServiceState")]

        # Fetch Cell info & service state of target sim slot
        cell_info_line = cell_infos[sim_slot]
        service_state_line = service_states[sim_slot]
        custom_logger.log(f"Cellinfo -> {cell_info_line}\nServiceState-> {service_state_line}")

        # Extract the desired information using regex
        plmn_match = re.search(r"mMcc\s*=\s*(\d+)\s+mMnc\s*=\s*(\d+)", cell_info_line)
        bandwidth_match = re.search(r"mBandwidth\s*=\s*(\d+)", cell_info_line)
        if not bandwidth_match:
            bandwidth_match = re.search(r"mCellBandwidths\s*=\s*\[(\d+)\]", service_state_line)
        cell_id_match = re.search(r"m(Ci|Nci)\s*=\s*(\d+)", cell_info_line)
        band_match = re.search(r"mBands\s*=\s*\[(\d+)\]", cell_info_line)
        radio = re.search(r"getRilVoiceRadioTechnology\s*=\s*(\d+)\((\w+)\)", service_state_line)
        pci_match = re.search(r"mPci\s*=\s*(\d+)", cell_info_line)
        tac_match = re.search(r"mTac\s*=\s*(\d+)", cell_info_line)
        earfcn_match = re.search(r"m(Earfcn|NrArfcn)\s*=\s*(\d+)", cell_info_line)
        rsrp_match = re.search(r"(?i)\b(ss)?Rsrp\s*=\s*(-?\d+)", cell_info_line)
        rsrq_match = re.search(r"(?i)\b(ss)?Rsrq\s*=\s*(-?\d+)", cell_info_line)

        # Extracted values
        plmn_mcc = plmn_match.group(1) if plmn_match else None
        plmn_mnc = plmn_match.group(2) if plmn_match else None
        bandwidth = bandwidth_match.group(1) if bandwidth_match else None
        cell_id = cell_id_match.group(2) if cell_id_match else None
        band = band_match.group(1) if band_match else None
        VRT = radio.group(2) if radio else None
        pci = pci_match.group(1) if pci_match else None
        tac = tac_match.group(1) if tac_match else None
        earfcn = earfcn_match.group(2) if earfcn_match else None
        rsrp = rsrp_match.group(2) if rsrp_match else None
        rsrq = rsrq_match.group(2) if rsrq_match else None

        # Create a list with all the extracted variable values
        info = [operator_name, plmn_mcc, plmn_mnc, bandwidth, cell_id, band, VRT, pci, tac, earfcn, rsrp, rsrq]
        return info
    except Exception as e:
        custom_logger.log("Failed to collect Cell Info", e)
        CallException(e, sys)
        return ["NA" * 12]


def get_location(udid, custom_logger):
    # initiate default values
    latitude = None
    longitude = None
    custom_logger.log(f"Getting GPS location (lat-long) for {udid}")
    try:
        # Run the ADB command to get the location information
        adb_command = f'adb -s {udid} shell dumpsys location'
        result = subprocess.run(adb_command, capture_output=True, text=True, shell=False)

        # Parse the output to extract latitude and longitude
        output_lines = result.stdout.split('\n')

        for line in output_lines:
            if line.startswith('      last location=Location'):
                # Extract latitude and longitude from the line
                line = line.strip()
                custom_logger.log(f"Locaion : {line}")
                match = re.search(r'Location\[[a-zA-Z]+\s+(-?[\d.]+),\s*(-?[\d.]+)', line)
                if match:
                    latitude = float(match.group(1))
                    longitude = float(match.group(2))
                break
    except Exception as e:
        custom_logger.log(f"Failed to detect location because", e)
        CallException(e, sys)

    return [latitude, longitude]


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
