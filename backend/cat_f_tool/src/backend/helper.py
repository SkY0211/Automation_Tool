import logging
import time
import re

from backend.cat_f_tool.src.data.device_info  import DeviceInfo
from backend.cat_f_tool.src.data.constants    import ERROR_CODES
from backend.cat_f_tool.src.utility.logger    import CustomLogger
from backend.cat_f_tool.src.utility.utils     import send_at_command, list_serial_ports, create_folders

import serial


def check_network_registration_status(at_port):
    try:
        with serial.Serial(at_port, baudrate=115200, timeout=1) as ser:
            ser.write(b'AT+CREG?\r\n')
            time.sleep(0.1)
            response = ser.readlines()
            for line in response:
                if b'+CREG:' in line:
                    parts = line.split(b',')
                    if len(parts) > 1:
                        registration_status = int(parts[1])
                        return registration_status in (1, 5)
            return False
    except Exception as e:
        print(f"Error checking network registration status: {e}")
        return False


def check_device_disconnection(port1, port2, logger: CustomLogger):
    try:
        avl_ports         = list_serial_ports(logger)
        unavailable_ports = []

        if port1 not in avl_ports:
            unavailable_ports.append(port1)
            logger.log(f"Device connected to port {port1} is disconnected.", level=logging.WARNING)

        if port2 not in avl_ports:
            unavailable_ports.append(port2)
            logger.log(f"Device connected to port {port2} is disconnected.", level=logging.WARNING)

        if unavailable_ports:
            return False, unavailable_ports
        else:
            return True, unavailable_ports
    except Exception as e:
        logger.log("Failed to check device disconnection.", e, logging.ERROR)
        return False, []


def decode_clcc_response(response, logger: CustomLogger):
    try:
        lines = response.split('\n')
        decoded_calls = {
            'direction': 'NA',
            'state':     'IDLE',
            'mode':      'NA',
            'number':    'NA',
            'type':      'NA',
            'error':     'NA'
        }

        for line in lines:
            if line.startswith('+CLCC:'):
                parts = line.split(',')
                if len(parts) >= 7:
                    direction = "MO" if int(parts[1]) == 0 else "MT"
                    state = {
                        0: "Active",
                        1: "Held",
                        2: "Dialing (MO call)",
                        3: "Alerting (MO call)",
                        4: "Incoming (MT call)",
                        5: "Waiting (MT call)"
                    }.get(int(parts[2]), "Unknown")
                    mode = {
                        0: "Voice",
                        1: "Data",
                        2: "FAX"
                    }.get(int(parts[3]), "Unknown")
                    number = parts[5].strip('"')
                    type_ = {
                        129: "Unknown type",
                        145: "International type (contains the character '+')",
                        161: "National type"
                    }.get(int(parts[6]), "Unknown")
                    error = None
                    if len(parts) > 7:
                        error_code = int(parts[8].strip())
                        error = ERROR_CODES.get(error_code, "Unknown error")
                    decoded_calls = {
                        'direction': direction,
                        'state':     state,
                        'mode':      mode,
                        'number':    number,
                        'type':      type_,
                        'error':     error
                    }
        return decoded_calls
    except Exception as e:
        logger.log("Error decoding CLCC response.", e, logging.ERROR)
        return None


def get_call_state(at_port: str, logger: CustomLogger):
    """
    Retrieves the current call state of a device connected via the specified AT port.

    First attempts AT+CLCC. If unsupported (returns ERROR), falls back to passive
    listening for RING or +CSYS: 1 — common on Unisoc 2G feature phones.
    """
    try:
        clcc_response = send_at_command(at_port, 'AT+CLCC', logger)

        if clcc_response and "ERROR" not in clcc_response.upper():
            clcc_response_decoded = decode_clcc_response(clcc_response, logger)
            logger.log(f"Call state [{at_port} Port] -> {clcc_response_decoded}")
            return clcc_response_decoded

        # Fallback: listen for RING on port for 20 seconds
        logger.log(f"AT+CLCC unsupported on {at_port}, listening via RING or +CSYS...")
        ring_detected = False
        fallback_state = {
            'direction': 'MT',
            'state':     'RING',
            'mode':      'Voice',
            'number':    'NA',
            'type':      'Unknown type',
            'error':     'NA'
        }

        with serial.Serial(at_port, baudrate=115200, timeout=1) as ser:
            start_time = time.time()
            while time.time() - start_time < 20:
                if ser.in_waiting:
                    line = ser.readline().decode(errors='ignore').strip()
                    if "RING" in line or "+CSYS: 1" in line:
                        ring_detected = True
                        break

        if ring_detected:
            logger.log(f"Incoming call detected via fallback on port {at_port}")
            return fallback_state
        else:
            logger.log(f"No incoming call detected within timeout on {at_port}")
            fallback_state['state'] = 'IDLE'
            return fallback_state

    except Exception as e:
        logger.log("Failed to fetch call state", e, logging.ERROR)
        return None


def dial_number(serial_port, phone_number, logger: CustomLogger):
    def try_dial(cmd):
        try:
            ser = serial.Serial(serial_port, baudrate=115200, timeout=2)
            ser.write(f'{cmd}\r\n'.encode())
            time.sleep(3)
            response = ser.readlines()
            ser.close()
            for line in response:
                if b'OK' in line:
                    logger.log(f"Dialing with command: {cmd} via {serial_port}")
                    return True
                elif b'NO CARRIER' in line:
                    logger.log(f"NO CARRIER received, may still be valid if MT connected. Proceeding...")
                    return True
            return False
        except Exception as e:
            logger.log(f"Exception during dialing command {cmd}", e, logging.ERROR)
            return False

    # 1. Try local number
    local_cmd = f"ATD{phone_number};"
    if try_dial(local_cmd):
        return True

    # 2. Retry with country code
    intl_number = f"{DeviceInfo.code}{phone_number.lstrip('+')}"
    intl_cmd    = f"ATD{intl_number};"
    if try_dial(intl_cmd):
        return True

    logger.log(f"Both attempts to dial {phone_number} failed on port {serial_port}.", level=logging.WARNING)
    return False


def receive_call(serial_port, logger: CustomLogger):
    try:
        ser = serial.Serial(serial_port, baudrate=115200, timeout=1)
        ser.write(b'ATA\r\n')
        time.sleep(1)
        response = ser.readlines()
        ser.close()
        for line in response:
            if b'OK' in line:
                logger.log(f"Call received using {serial_port} port")
                return True
        logger.log(f"Failed to receive call using {serial_port} port")
        return False
    except Exception as e:
        logger.log("Failed to receive call.", e, logging.ERROR)
        return False


def end_call(serial_port, logger: CustomLogger):
    try:
        ser = serial.Serial(serial_port, baudrate=115200, timeout=1)
        ser.write(b'ATH\r\n')
        time.sleep(1)
        response = ser.readlines()
        ser.close()
        for line in response:
            if b'OK' in line:
                logger.log(f"Call ended using {serial_port} port")
                return True
        logger.log(f"Failed to terminate call using {serial_port} port.")
        return False
    except Exception as e:
        logger.log("Failed to end call.", e, logging.ERROR)
        return False


def fetch_cell_information(serial_port):
    try:
        ser = serial.Serial(serial_port, baudrate=115200, timeout=1)
        ser.write(b'AT+COPS?\r\n')
        response = ser.read_all().decode('utf-8')
        mcc_mnc_match = re.search(r'\"(\d+)(\d+)\"', response)
        mcc = mcc_mnc_match.group(1) if mcc_mnc_match else None
        mnc = mcc_mnc_match.group(2) if mcc_mnc_match else None
        ser.write(b'AT+CESQ\r\n')
        response = ser.read_all().decode('utf-8')
        pci_match   = re.search(r'PCI: (\d+)',   response)
        tac_match   = re.search(r'TAC: (\d+)',   response)
        earfcn_match = re.search(r'EARFCN: (\d+)', response)
        band_match  = re.search(r'BAND: (\d+)',  response)
        pci    = pci_match.group(1)    if pci_match    else None
        tac    = tac_match.group(1)    if tac_match    else None
        earfcn = earfcn_match.group(1) if earfcn_match else None
        band   = band_match.group(1)   if band_match   else None
        ser.close()
        return {'MCC': mcc, 'MNC': mnc, 'PCI': pci, 'TAC': tac, 'EARFCN': earfcn, 'Band': band}
    except Exception as e:
        print("Error fetching cell information:", e)
        return None


def decode_rssi(rssi):
    if rssi == 99:
        return "Not known or not detectable"
    elif rssi == 0:
        return "-113 dBm or less"
    elif rssi == 1:
        return "-111 dBm"
    elif 2 <= rssi <= 30:
        return f"{-109 + rssi * 2} dBm"
    elif rssi == 31:
        return "-51 dBm or greater"
    else:
        return "Unknown"


def get_signal_quality_2g3g(serial_port):
    try:
        ser = serial.Serial(serial_port, baudrate=115200, timeout=1)
        ser.write(b'AT+CSQ\r\n')
        response = ser.read_until('OK').decode('utf-8')
        ser.close()
        match = re.search(r'\+CSQ: (\d+),(\d+)', response)
        if match:
            rssi = int(match.group(1))
            ber  = int(match.group(2))
            return {'RSSI': decode_rssi(rssi), 'BER': ber}
        else:
            print("No match")
            return None
    except serial.SerialException as se:
        print("Serial port error:", se)
        return None
    except Exception as e:
        print("Error fetching signal quality:", e)
        return None