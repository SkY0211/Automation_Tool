import logging
import os
import time
from datetime import datetime

try:
    import winsound
except ImportError:
    winsound = None  # Non-Windows platform — winsound not available

from backend.cat_f_tool.src.data.device_info import DeviceInfo
from backend.cat_f_tool.src.utility.logger   import CustomLogger
from backend.cat_f_tool.src.data.dir_paths   import Paths

import serial
from serial.tools import list_ports


def get_parent_dir():
    return os.getcwd()


def create_folders():
    """
    Create a new folder with date-time stamp as the name in both
    'logs', 'reports' and 'user_info' folders under artifacts/.
    Returns: log_path, reports_path, user_info_path
    """
    try:
        name           = f"{datetime.now().strftime('%m%d%Y__%H%M%S')}"
        base_dir       = os.path.join(get_parent_dir(), 'artifacts')
        log_path       = os.path.join(base_dir, 'logs',      name)
        reports_path   = os.path.join(base_dir, 'reports',   name)
        user_info_path = os.path.join(base_dir, 'user_info', name)

        os.makedirs(log_path,       exist_ok=True)
        os.makedirs(reports_path,   exist_ok=True)
        os.makedirs(user_info_path, exist_ok=True)

        Paths.latest_log_dir_path       = log_path
        Paths.latest_report_dir_path    = reports_path
        Paths.latest_user_info_dir_path = user_info_path

        return log_path, reports_path, user_info_path
    except Exception as e:
        print(f"Error occurred while creating folders: {e}")
        return None, None, None


def send_at_command(serial_port, command, logger: CustomLogger):
    """Send an AT command and return the response."""
    try:
        ser      = serial.Serial(serial_port, baudrate=115200, timeout=2)
        ser.write(command.encode('utf-8') + b'\r\n')
        response = ser.read_until(b'OK').decode('utf-8').strip()
        ser.close()
    except Exception as e:
        logger.log(f"Failed to execute AT command <{command}>", e, logging.ERROR)
        response = None
    return response


def list_serial_ports(logger: CustomLogger):
    """
    List available serial ports.
    Fast, non-blocking — returns immediately with whatever ports are present.
    Used only for find_at_port during device configuration setup.
    """
    try:
        ports     = list_ports.comports()
        com_ports = [port.device for port in ports]
        logger.log(f"COM ports found -> {com_ports}")
        return com_ports if com_ports else None
    except Exception as e:
        logger.log(f"Failed to list serial ports: {e}", level=logging.ERROR)
        return None


def find_at_port(checked_ports, logger: CustomLogger):
    """
    Find an AT-responsive COM port that hasn't been checked yet.
    Used during device configuration — retries up to 3 times with a short delay.
    """
    logger.log("Searching for AT port", level=logging.INFO)

    for attempt in range(3):
        ports = list_ports.comports()
        com_ports = [p.device for p in ports]
        logger.log(f"Attempt {attempt+1}: ports found -> {com_ports}")

        for port in com_ports:
            if port in checked_ports:
                continue
            try:
                checked_ports.append(port)
                ser = serial.Serial(port, baudrate=115200, timeout=1)
                ser.write(b'AT\r\n')
                response = ser.read_until(b'OK')
                ser.close()
                if b'OK' in response:
                    logger.log(f"AT port found: {port}", level=logging.INFO)
                    return port
            except serial.SerialException as e:
                logger.log(f"Failed to open serial port {port}", e, logging.ERROR)

        if attempt < 2:
            logger.log("No AT port found yet, waiting 2s before retry...")
            time.sleep(2)

    logger.log("No AT port found after 3 attempts", level=logging.INFO)
    return None


def extract_device_info(serial_port, logger: CustomLogger) -> dict:
    """Extract device information from AT command responses."""
    cgmr_response = send_at_command(serial_port, 'AT+CGMR', logger)
    cgsn_response = send_at_command(serial_port, 'AT+CGSN', logger)
    cnum_response = send_at_command(serial_port, 'AT+CNUM', logger)

    logger.log(
        f"Extracting device info...\nAT command responses:\n"
        f"AT+CGMR >>\n{cgmr_response}\nAT+CGSN >>\n{cgsn_response}\nAT+CNUM >>\n{cnum_response}"
    )

    device_info = {
        "Software Version": "Not found",
        "IMEI":             "Not found",
        "Phone Number":     "Not found",
        "AT Port":          serial_port,
    }

    try:
        if cgmr_response and 'Software Version:' in cgmr_response:
            software_version = cgmr_response.split('Software Version: ')[1].split('\r')[0].strip()
            device_info["Software Version"] = software_version

        if cgsn_response and '\n' in cgsn_response:
            imei = cgsn_response.split('\n')[0].strip()
            device_info["IMEI"] = imei

        if cnum_response and ',' in cnum_response:
            phone_number = cnum_response.split(',')[1].strip()
            if phone_number.startswith('"') and phone_number.endswith('"'):
                device_info["Phone Number"] = DeviceInfo.code + phone_number[-11:-1]
            else:
                device_info["Phone Number"] = DeviceInfo.code + phone_number[-10:]

        logger.log(
            f"Device information extracted successfully.\nDevice Info : {device_info}",
            level=logging.INFO
        )
    except Exception as e:
        logger.log("Failed to extract device information", e, logging.ERROR)

    return device_info


def play_alert_sound(frequency=800, duration=400, times=2):
    """Play a beep sound (Windows only — silently skipped on other platforms)."""
    if winsound is not None:
        for _ in range(times):
            winsound.Beep(frequency, duration)