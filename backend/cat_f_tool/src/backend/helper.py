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
    """
    Check if both ports are still present.
    Uses a fast non-blocking port list — no sleep, no retry loop.
    """
    try:
        from serial.tools import list_ports
        available = [p.device for p in list_ports.comports()]

        unavailable_ports = []
        if port1 not in available:
            unavailable_ports.append(port1)
            logger.log(f"Device on port {port1} is disconnected.", level=logging.WARNING)
        if port2 not in available:
            unavailable_ports.append(port2)
            logger.log(f"Device on port {port2} is disconnected.", level=logging.WARNING)

        if unavailable_ports:
            return False, unavailable_ports
        return True, []
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
                        try:
                            error_code = int(parts[8].strip())
                            error = ERROR_CODES.get(error_code, "Unknown error")
                        except Exception:
                            pass
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
    Get call state via AT+CLCC.
    If AT+CLCC is not supported (feature phones often return ERROR),
    returns a minimal IDLE state so the caller can handle fallback logic.
    Does NOT do the 20-second passive listen here — that is done directly
    in perform_call() so the same serial port is not opened twice.
    """
    try:
        clcc_response = send_at_command(at_port, 'AT+CLCC', logger)

        if clcc_response and "ERROR" not in clcc_response.upper():
            clcc_response_decoded = decode_clcc_response(clcc_response, logger)
            logger.log(f"Call state [{at_port}] -> {clcc_response_decoded}")
            return clcc_response_decoded

        # AT+CLCC not supported — return IDLE so caller uses direct RING detection
        logger.log(f"AT+CLCC not supported on {at_port}, returning IDLE for caller to handle.")
        return {'direction': 'NA', 'state': 'IDLE', 'mode': 'NA',
                'number': 'NA', 'type': 'NA', 'error': 'NA'}

    except Exception as e:
        logger.log("Failed to fetch call state", e, logging.ERROR)
        return {'direction': 'NA', 'state': 'IDLE', 'mode': 'NA',
                'number': 'NA', 'type': 'NA', 'error': 'NA'}


def wait_for_ring_on_mt(mt_port, timeout_sec, logger):
    """Backward-compat wrapper: detect RING only (no answer)."""
    ring, _ = wait_for_ring_and_answer(mt_port, timeout_sec, logger, answer=False)
    return ring


def wait_for_ring_and_answer(mt_port, timeout_sec, logger, answer=True):
    """
    Keep the MT serial port open the entire time: detect RING then send ATA
    on the SAME open connection without ever closing it in between.

    This is required for feature phones like the HMD Wonka Touch (Unisoc).
    Closing and reopening the port between ring-detection and ATA resets the
    modem pending-call state on these devices so ATA finds nothing to answer.
    Keeping one persistent connection avoids that race condition entirely.

    Returns: (ring_detected: bool, answered: bool)
    """
    logger.log("Listening for RING on MT port {} (timeout={}s)...".format(mt_port, timeout_sec))
    ring_detected = False
    answered      = False
    try:
        ser = serial.Serial(mt_port, baudrate=115200, timeout=0.5)
        ser.reset_input_buffer()
        deadline = time.time() + timeout_sec

        # Phase 1: wait for RING on the open port
        while time.time() < deadline:
            line = ser.readline().decode(errors="ignore").strip()
            if line:
                logger.log("  MT rx: {}".format(repr(line)))
            if any(kw in line.upper() for kw in
                   ("RING", "+CSYS: 1", "+CLCC:", "INCOMING", "+CRING")):
                logger.log("RING detected on {}: {}".format(mt_port, repr(line)))
                ring_detected = True
                break

        if not ring_detected:
            logger.log("No RING on {} within {}s".format(mt_port, timeout_sec))
            ser.close()
            return False, False

        if not answer:
            ser.close()
            return True, False

        # Phase 2: answer on the SAME open port (no close/reopen)
        # A short pause lets the network finish alerting before we send ATA
        time.sleep(0.3)
        for attempt in range(3):
            try:
                ser.reset_input_buffer()
                ser.write(b"ATA\r\n")
                logger.log("ATA sent (attempt {}) on {}".format(attempt + 1, mt_port))
                # Read for up to 4 s in small chunks
                response    = b""
                ser.timeout = 0.5
                deadline_a  = time.time() + 4
                while time.time() < deadline_a:
                    chunk = ser.read(256)
                    if chunk:
                        response += chunk
                        logger.log("  ATA rx: {}".format(repr(chunk.decode(errors="ignore"))))
                    decoded = response.decode(errors="ignore").upper()
                    if any(kw in decoded for kw in
                           ("OK", "CONNECT", "NO CARRIER", "ERROR")):
                        break
                decoded = response.decode(errors="ignore").upper()
                logger.log("ATA full response attempt {}: {}".format(attempt + 1, repr(decoded)))
                if "OK" in decoded or "CONNECT" in decoded:
                    logger.log("Call answered (OK/CONNECT) on {}".format(mt_port))
                    answered = True
                    break
                if "NO CARRIER" in decoded or "ERROR" in decoded:
                    logger.log("ATA got NO CARRIER/ERROR attempt {}, retrying...".format(attempt + 1))
                    time.sleep(1)
                    continue
                # Silent response -- feature phones often return nothing after ATA
                # but the call IS connected. Trust silence after the 1st attempt.
                if attempt >= 1:
                    logger.log("ATA silent on {} -- assuming call connected".format(mt_port))
                    answered = True
                    break
                time.sleep(1)
            except Exception as e:
                logger.log("ATA attempt {} error on {}".format(attempt + 1, mt_port), e, logging.ERROR)
                time.sleep(1)

        ser.close()
    except Exception as e:
        logger.log("wait_for_ring_and_answer error on {}".format(mt_port), e, logging.ERROR)

    return ring_detected, answered


def check_mo_dialing(mo_port: str, logger: CustomLogger) -> bool:
    """
    Check whether MO has successfully started dialing.

    Strategy:
      1. Try AT+CLCC — if it returns a dialing/alerting state, return True.
      2. If AT+CLCC not supported (ERROR), try AT — if we get OK the port is
         still responsive, which means the dial command was accepted.
         Feature phones that don't support CLCC typically return OK to ATD
         immediately after starting the call setup, so we trust the dial result.
    """
    try:
        clcc_response = send_at_command(mo_port, 'AT+CLCC', logger)
        if clcc_response and "ERROR" not in clcc_response.upper():
            decoded = decode_clcc_response(clcc_response, logger)
            if decoded:
                state = decoded.get('state', '').lower()
                logger.log(f"MO CLCC state: {state}")
                # Accept dialing, alerting, or active
                if any(kw in state for kw in ('dialing', 'alerting', 'active')):
                    return True
            # CLCC returned OK but no active call — not dialing
            return False

        # AT+CLCC not supported — check port is alive and trust the ATD result
        ping = send_at_command(mo_port, 'AT', logger)
        if ping and 'OK' in ping.upper():
            logger.log("AT+CLCC unsupported on MO, port alive — trusting ATD dial result.")
            return True

        return False
    except Exception as e:
        logger.log(f"check_mo_dialing error on {mo_port}", e, logging.ERROR)
        return False


def answer_call_on_mt(mt_port: str, logger: CustomLogger) -> bool:
    """
    Send ATA to the MT device to answer an incoming call.
    Retries once if the first attempt gets no OK.
    """
    for attempt in range(2):
        try:
            ser = serial.Serial(mt_port, baudrate=115200, timeout=3)
            ser.reset_input_buffer()
            ser.write(b'ATA\r\n')
            time.sleep(0.5)
            response = ser.read(256).decode(errors='ignore')
            ser.close()
            logger.log(f"ATA attempt {attempt+1} response: {repr(response)}")
            if 'OK' in response.upper() or 'CONNECT' in response.upper():
                logger.log(f"Call answered on MT port {mt_port}")
                return True
        except Exception as e:
            logger.log(f"ATA attempt {attempt+1} error on {mt_port}", e, logging.ERROR)
        time.sleep(1)

    logger.log(f"Failed to answer call on MT port {mt_port} after 2 attempts")
    return False


def dial_number(serial_port, phone_number, logger: CustomLogger):
    def try_dial(cmd):
        try:
            ser = serial.Serial(serial_port, baudrate=115200, timeout=3)
            ser.reset_input_buffer()
            ser.write(f'{cmd}\r\n'.encode())
            time.sleep(2)
            response = ser.read(256).decode(errors='ignore')
            ser.close()
            logger.log(f"Dial command '{cmd}' response: {repr(response)}")
            # Accept OK, NO CARRIER (call started but MT not yet answering),
            # or empty response (some phones return nothing until call connects)
            if 'OK' in response.upper():
                logger.log(f"Dial OK: {cmd} via {serial_port}")
                return True
            if 'NO CARRIER' in response.upper():
                logger.log(f"NO CARRIER on dial — treating as dial initiated: {cmd}")
                return True
            if 'ERROR' not in response.upper():
                # No explicit error — assume dial accepted (some 2G phones return nothing)
                logger.log(f"No ERROR in dial response — assuming dial accepted: {cmd}")
                return True
            return False
        except Exception as e:
            logger.log(f"Exception during dialing command {cmd}", e, logging.ERROR)
            return False

    # 1. Try with number as-is
    local_cmd = f"ATD{phone_number};"
    if try_dial(local_cmd):
        return True

    # 2. Retry with country code prefix
    intl_number = f"{DeviceInfo.code}{phone_number.lstrip('+')}"
    intl_cmd    = f"ATD{intl_number};"
    if try_dial(intl_cmd):
        return True

    logger.log(f"Both dial attempts failed for {phone_number} on {serial_port}.", level=logging.WARNING)
    return False


def receive_call(serial_port, logger: CustomLogger):
    try:
        ser = serial.Serial(serial_port, baudrate=115200, timeout=2)
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
        ser = serial.Serial(serial_port, baudrate=115200, timeout=2)
        ser.write(b'ATH\r\n')
        time.sleep(0.5)
        response = ser.read(128).decode(errors='ignore')
        ser.close()
        logger.log(f"ATH response on {serial_port}: {repr(response)}")
        return True  # Always return True — ATH is best-effort
    except Exception as e:
        logger.log(f"Failed to end call on {serial_port}.", e, logging.ERROR)
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
        pci_match    = re.search(r'PCI: (\d+)',    response)
        tac_match    = re.search(r'TAC: (\d+)',    response)
        earfcn_match = re.search(r'EARFCN: (\d+)', response)
        band_match   = re.search(r'BAND: (\d+)',   response)
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
        response = ser.read_until(b'OK').decode('utf-8')
        ser.close()
        match = re.search(r'\+CSQ: (\d+),(\d+)', response)
        if match:
            rssi = int(match.group(1))
            ber  = int(match.group(2))
            return {'RSSI': decode_rssi(rssi), 'BER': ber}
        print("No match")
        return None
    except serial.SerialException as se:
        print("Serial port error:", se)
        return None
    except Exception as e:
        print("Error fetching signal quality:", e)
        return None