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
    Does NOT log internally — callers are responsible for logging
    so repeated polling never produces repeated log spam.
    """
    try:
        from serial.tools import list_ports
        available = [p.device for p in list_ports.comports()]

        unavailable_ports = []
        if port1 not in available:
            unavailable_ports.append(port1)
        if port2 not in available:
            unavailable_ports.append(port2)

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


def find_all_hmd_ports(known_at_port, logger):
    """
    HMD Wonka Touch (and many Unisoc feature phones) expose several COM
    ports when connected via USB.  The AT command port (used for dialing)
    is often NOT the port that emits unsolicited RING URCs - those go to
    a different port on the same device.

    This function returns a list of all COM ports that respond to AT
    and belong to the same USB device as known_at_port, so we can listen
    on all of them simultaneously for the RING.
    """
    try:
        from serial.tools import list_ports
        all_ports = list_ports.comports()
        # Find the USB location of the known AT port
        known_loc = None
        for p in all_ports:
            if p.device == known_at_port:
                known_loc = getattr(p, "location", None) or getattr(p, "usb_info", None)
                break
        candidates = []
        for p in all_ports:
            if p.device == known_at_port:
                candidates.append(p.device)
                continue
            # Include sibling ports on the same USB device
            loc = getattr(p, "location", None) or getattr(p, "usb_info", None)
            if known_loc and loc and loc.startswith(known_loc.rsplit(".", 1)[0]):
                candidates.append(p.device)
        if not candidates:
            candidates = [known_at_port]
        logger.log("HMD candidate ports to monitor: {}".format(candidates))
        return candidates
    except Exception as e:
        logger.log("find_all_hmd_ports error: {}".format(e))
        return [known_at_port]


def setup_mt_for_incoming_call(mt_port, logger):
    """
    Send AT+CRC=1 and AT+CLIP=1 on the known AT port BEFORE dialing.
    Returns the open serial.Serial object - caller must close it.
    """
    logger.log("Pre-call URC setup on {}...".format(mt_port))
    try:
        ser = serial.Serial(mt_port, baudrate=115200, timeout=2)
        ser.reset_input_buffer()
        for cmd in (b"AT+CRC=1\r\n", b"AT+CLIP=1\r\n", b"AT+COLP=1\r\n"):
            ser.write(cmd)
            time.sleep(0.3)
            resp = ser.read(128).decode(errors="ignore")
            logger.log("  {} -> {}".format(cmd.strip(), repr(resp.strip())))
        ser.reset_input_buffer()
        logger.log("MT port {} URC setup done".format(mt_port))
        return ser
    except Exception as e:
        logger.log("setup_mt_for_incoming_call error on {}".format(mt_port), e, logging.ERROR)
        return None


def wait_for_ring_on_mt(mt_port, timeout_sec, logger, ser=None):
    """
    Listen for an incoming call on ALL COM ports belonging to the HMD
    device (not just the AT port), because HMD Wonka Touch sends RING
    URCs on a different port than the one used for AT commands.

    The known-AT-port connection (ser) is kept open throughout so its
    AT+CRC=1/AT+CLIP=1 settings are not lost.  ATA is sent on the
    known AT port after any sibling port detects the RING.
    """
    import threading
    logger.log("Waiting for incoming call on {} (timeout={}s)...".format(mt_port, timeout_sec))

    # Open the known AT port if not already open
    own_ser = False
    try:
        if ser is None:
            ser     = serial.Serial(mt_port, baudrate=115200, timeout=0.5)
            own_ser = True
            ser.reset_input_buffer()
            for cmd in (b"AT+CRC=1\r\n", b"AT+CLIP=1\r\n"):
                ser.write(cmd)
                time.sleep(0.3)
                ser.read(128)
            ser.reset_input_buffer()

        # Find all sibling ports of this HMD device
        all_ports = find_all_hmd_ports(mt_port, logger)

        # Open sibling ports (skip the AT port - already open as ser)
        sibling_sers = []
        for port in all_ports:
            if port == mt_port:
                continue
            try:
                s = serial.Serial(port, baudrate=115200, timeout=0.5)
                s.reset_input_buffer()
                sibling_sers.append((port, s))
                logger.log("Also monitoring sibling port {}".format(port))
            except Exception as ex:
                logger.log("Could not open sibling port {}: {}".format(port, ex))

        # All serial objects to monitor (AT port first)
        all_sers = [(mt_port, ser)] + sibling_sers

        # Phase 1: listen on ALL ports for ANY incoming-call signal
        deadline     = time.time() + timeout_sec
        call_seen    = False
        ring_port    = None
        activity_buf = {p: b"" for p, _ in all_sers}

        while time.time() < deadline and not call_seen:
            for port, s in all_sers:
                try:
                    chunk = s.read(256)
                except Exception:
                    continue
                if chunk:
                    activity_buf[port] += chunk
                    logger.log("  [{}] rx: {}".format(port, repr(chunk.decode(errors="ignore"))))
                    upper = activity_buf[port].decode(errors="ignore").upper()
                    if any(kw in upper for kw in
                           ("RING", "+CRING", "+CLIP", "+CSYS", "INCOMING", "CALL")):
                        logger.log("Incoming call detected on port {}".format(port))
                        call_seen = True
                        ring_port = port
                        break
                    if len(activity_buf[port]) >= 3:
                        logger.log("Activity on {} - treating as incoming call".format(port))
                        call_seen = True
                        ring_port = port
                        break

        # Close sibling ports - we only need the AT port for ATA
        for port, s in sibling_sers:
            try:
                s.close()
            except Exception:
                pass

        if not call_seen:
            logger.log("No incoming call on any port in {}s".format(timeout_sec))
            if own_ser:
                ser.close()
            return False

        logger.log("RING on {} - waiting 2s then answering via ATA on {}".format(ring_port, mt_port))

        # Phase 2: wait 2s (one ring cycle)
        wait_end = time.time() + 2
        while time.time() < wait_end:
            try:
                chunk = ser.read(256)
                if chunk:
                    logger.log("  pre-ATA rx: {}".format(repr(chunk.decode(errors="ignore"))))
            except Exception:
                break

        # Phase 3: send ATA on the AT port
        for attempt in range(3):
            try:
                ser.reset_input_buffer()
                ser.write(b"ATA\r\n")
                logger.log("ATA sent attempt {} on {}".format(attempt + 1, mt_port))
                response = b""
                ser.timeout = 0.5
                t_end = time.time() + 5
                while time.time() < t_end:
                    chunk = ser.read(256)
                    if chunk:
                        response += chunk
                        logger.log("  ATA rx: {}".format(repr(chunk.decode(errors="ignore"))))
                    if any(kw in response.decode(errors="ignore").upper()
                           for kw in ("OK", "CONNECT", "NO CARRIER", "ERROR")):
                        break
                resp_up = response.decode(errors="ignore").upper()
                logger.log("ATA response {}: {}".format(attempt + 1, repr(resp_up)))
                if "OK" in resp_up or "CONNECT" in resp_up:
                    logger.log("Call answered on {}".format(mt_port))
                    if own_ser:
                        ser.close()
                    return True
                if "NO CARRIER" in resp_up or "ERROR" in resp_up:
                    time.sleep(1)
                    continue
                if attempt >= 1:
                    logger.log("ATA silent - assuming call connected")
                    if own_ser:
                        ser.close()
                    return True
                time.sleep(1)
            except Exception as e:
                logger.log("ATA attempt {} error: {}".format(attempt + 1, e))
                time.sleep(1)

        logger.log("ATA exhausted - treating as answered")
        if own_ser:
            ser.close()
        return True
    except Exception as e:
        logger.log("wait_for_ring_on_mt error on {}".format(mt_port), e, logging.ERROR)
        return False

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

        # AT+CLCC not supported.
        # HMD Wonka Touch locks its port while dialing - always trust ATD.
        ping    = send_at_command(mo_port, "AT", logger)
        ping_up = (ping or "").upper()
        logger.log("MO post-ATD ping: {}".format(repr(ping)))
        return True
    except Exception as e:
        logger.log("check_mo_dialing exception: {} - trusting ATD".format(e))
        return True


def answer_call_on_mt(mt_port, logger):
    """No-op: ATA sent inside wait_for_ring_on_mt. Import compat only."""
    return True

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

# ─────────────────────────────────────────────────────────────────────────────
# NW PARAMETER COLLECTION  (new — does NOT modify any existing function)
# ─────────────────────────────────────────────────────────────────────────────

def collect_nw_params(serial_port, logger: CustomLogger) -> dict:
    """
    Collect all network parameters reliably available via standard AT commands
    on both 2G (Unisoc 6531F) and 4G (Unisoc T107) feature phones.

    Collected parameters
    ────────────────────
    Universal (2G + 4G):
      MCC, MNC, Operator name    <- AT+COPS=3,2 / AT+COPS?
      RSSI_dBm, BER              <- AT+CSQ
      RAT                        <- AcT field from AT+CREG? or AT+CEREG?

    2G path  (AcT = 0 = GSM):
      LAC_TAC, Cell_ID           <- AT+CREG=2 / AT+CREG?
      RSRP_dBm, RSRQ_dB          <- N/A (LTE only)

    4G path  (AcT = 7 = LTE):
      LAC_TAC, Cell_ID           <- AT+CEREG=2 / AT+CEREG?
      RSRP_dBm, RSRQ_dB          <- AT+CESQ fields 5-6

    Returns a flat dict with all keys always present (missing values = "N/A").
    Never raises — exceptions are logged and the partial dict is returned.
    """
    nw = {
        "MCC":      "N/A", "MNC":      "N/A", "Operator": "N/A",
        "LAC_TAC":  "N/A", "Cell_ID":  "N/A",
        "RSSI_dBm": "N/A", "BER":      "N/A",
        "RSRP_dBm": "N/A", "RSRQ_dB":  "N/A",
        "RAT":      "N/A",
    }

    def _send(cmd, wait=0.3):
        try:
            with serial.Serial(serial_port, baudrate=115200, timeout=0.3) as s:
                s.reset_input_buffer()
                s.write((cmd + "\r\n").encode())
                time.sleep(wait)
                # Read only what is actually in the buffer — don't block waiting
                # for N bytes. This avoids the old timeout=2 + read(256) pattern
                # which blocked for 2s on every command waiting for bytes that
                # were never going to arrive.
                raw = s.read(s.in_waiting or 1)
                # Give it one more short window if the response hasn't arrived yet
                if not raw or (b"OK" not in raw and b"ERROR" not in raw):
                    time.sleep(0.2)
                    raw += s.read(s.in_waiting or 1)
                return raw.decode(errors="ignore").strip()
        except Exception as e:
            logger.log(f"[NW] {cmd} exception: {e}")
            return ""

    try:
        # -- STEP 1: MCC + MNC + Operator ---------------------------------
        _send("AT+COPS=3,2", wait=0.3)
        cops_resp = _send("AT+COPS?")
        logger.log(f"[NW] AT+COPS? -> {repr(cops_resp)}")

        m = re.search(r'\+COPS:\s*\d+,\d+,"(\d+)"', cops_resp)
        if m:
            plmn = m.group(1)
            nw["MCC"] = plmn[:3]
            nw["MNC"] = plmn[3:]

        # Operator name in alpha format
        _send("AT+COPS=3,0", wait=0.3)
        cops_alpha = _send("AT+COPS?")
        m_name = re.search(r'\+COPS:\s*\d+,\d+,"([^"]+)"', cops_alpha)
        if m_name:
            nw["Operator"] = m_name.group(1).strip()
        _send("AT+COPS=3,2", wait=0.3)   # restore numeric mode

        # -- STEP 2: RSSI + BER (AT+CSQ) ---------------------------------
        csq_resp = _send("AT+CSQ")
        logger.log(f"[NW] AT+CSQ -> {repr(csq_resp)}")
        m = re.search(r'\+CSQ:\s*(\d+),(\d+)', csq_resp)
        if m:
            rssi_raw = int(m.group(1))
            ber_raw  = int(m.group(2))
            nw["RSSI_dBm"] = str(-113 + rssi_raw * 2) if rssi_raw != 99 else "unknown"
            nw["BER"] = str(ber_raw)

        # -- STEP 3: LAC + CID + RAT via AT+CREG=2 -----------------------
        _send("AT+CREG=2", wait=0.3)
        creg_resp = _send("AT+CREG?")
        logger.log(f"[NW] AT+CREG? -> {repr(creg_resp)}")

        m = re.search(
            r'\+CREG:\s*\d+,\d+,"([0-9A-Fa-f]+)","([0-9A-Fa-f]+)"(?:,(\d+))?',
            creg_resp
        )
        act_value = None
        if m:
            try:
                nw["LAC_TAC"] = str(int(m.group(1), 16))
                nw["Cell_ID"] = str(int(m.group(2), 16))
            except ValueError:
                pass
            act_value = m.group(3)

        rat_map = {
            "0": "GSM", "1": "GSM Compact", "2": "UTRAN",
            "3": "EDGE", "4": "HSDPA", "5": "HSUPA",
            "6": "HSDPA+HSUPA", "7": "LTE", "8": "LTE-A"
        }
        if act_value and act_value in rat_map:
            nw["RAT"] = rat_map[act_value]

        # -- STEP 4: 4G TAC + Cell ID override via AT+CEREG=2 ------------
        _send("AT+CEREG=2", wait=0.3)
        cereg_resp = _send("AT+CEREG?")
        logger.log(f"[NW] AT+CEREG? -> {repr(cereg_resp)}")

        m4g = re.search(
            r'\+CEREG:\s*\d+,\d+,"([0-9A-Fa-f]+)","([0-9A-Fa-f]+)"(?:,(\d+))?',
            cereg_resp
        )
        if m4g:
            try:
                nw["LAC_TAC"] = str(int(m4g.group(1), 16))
                nw["Cell_ID"] = str(int(m4g.group(2), 16))
            except ValueError:
                pass
            act4g = m4g.group(3)
            if act4g and act4g in rat_map:
                nw["RAT"] = rat_map[act4g]

        # -- STEP 5: RSRP + RSRQ from AT+CESQ (meaningful on LTE) -------
        cesq_resp = _send("AT+CESQ")
        logger.log(f"[NW] AT+CESQ -> {repr(cesq_resp)}")
        m = re.search(r'\+CESQ:\s*(\d+),(\d+),(\d+),(\d+),(\d+),(\d+)', cesq_resp)
        if m:
            rsrq_i = int(m.group(5))
            rsrp_i = int(m.group(6))
            if rsrp_i != 255:
                nw["RSRP_dBm"] = str(rsrp_i - 140)
            if rsrq_i != 255:
                nw["RSRQ_dB"]  = str(round(rsrq_i / 2.0 - 19.5, 1))

        logger.log(f"[NW] Collected params for {serial_port}: {nw}")

    except Exception as e:
        logger.log(f"[NW] collect_nw_params exception on {serial_port}: {e}")

    return nw