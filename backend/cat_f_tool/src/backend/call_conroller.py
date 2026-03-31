import logging
import threading
from datetime import datetime
import os.path
import time
from queue import Queue
from typing import List

from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.workbook import Workbook

from backend.cat_f_tool.src.data.device_info      import DeviceInfo
from backend.cat_f_tool.src.data.dir_paths         import Paths
from backend.cat_f_tool.src.data.test_credentials  import TestCred
from backend.cat_f_tool.src.data.constants         import VERSION, COLUMN_NAMES

from backend.cat_f_tool.src.backend.helper import (
    dial_number, receive_call, end_call, get_call_state,
    check_network_registration_status, check_device_disconnection,
    wait_for_ring_on_mt, check_mo_dialing, answer_call_on_mt
)
from backend.cat_f_tool.src.frontend.connection_break import reconnect
from backend.cat_f_tool.src.frontend.progress_check   import TestProgress

from backend.cat_f_tool.src.utility.logger import CustomLogger
from backend.cat_f_tool.src.utility.utils  import create_folders, send_at_command


class CallTester:
    def __init__(self, home, progress_frame,
                 resume_event: threading.Event,
                 pause_event: threading.Event,
                 end_test_event: threading.Event):
        self.resume_event   = resume_event
        self.pause_event    = pause_event
        self.end_event      = end_test_event
        self.call_duration  = None
        self.comment        = None
        self.result         = None
        self.home           = home
        self.progress_frame = progress_frame

        self.logger = CustomLogger("backend", Paths.latest_log_dir_path)
        self.logger.log("Backend code initiated to Start the Call Testing.")

        self.test_type  = TestCred.test_type
        self.iterations = TestCred.iterations
        self.duration   = TestCred.call_duration
        self.delay      = TestCred.call_delay

        # Select MO-MT devices according to Test_type
        if self.test_type == "MO calls" or self.test_type == "MO-MT calls":
            self.mo_sw   = DeviceInfo.dev1["Software Version"]
            self.mo_imei = DeviceInfo.dev1["IMEI"]
            self.mo_port = DeviceInfo.dev1["AT Port"]
            self.mo_no   = DeviceInfo.dev1["Phone Number"]
            self.mt_sw   = DeviceInfo.dev2["Software Version"]
            self.mt_imei = DeviceInfo.dev2["IMEI"]
            self.mt_port = DeviceInfo.dev2["AT Port"]
            self.mt_no   = DeviceInfo.dev2["Phone Number"]
        if self.test_type == "MT calls":
            self.mo_sw   = DeviceInfo.dev2["Software Version"]
            self.mo_imei = DeviceInfo.dev2["IMEI"]
            self.mo_port = DeviceInfo.dev2["AT Port"]
            self.mo_no   = DeviceInfo.dev2["Phone Number"]
            self.mt_sw   = DeviceInfo.dev1["Software Version"]
            self.mt_imei = DeviceInfo.dev1["IMEI"]
            self.mt_port = DeviceInfo.dev1["AT Port"]
            self.mt_no   = DeviceInfo.dev1["Phone Number"]

        # Report workbook
        self.bold_font = Font(bold=True)
        self.report_file_path = os.path.join(
            Paths.latest_report_dir_path,
            f'CAT_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        self.workbook      = Workbook()
        self.current_sheet = self.workbook.active
        self.current_sheet.title = self.test_type if self.test_type != "MO-MT calls" else "MO calls"
        self._write_1st_line()
        self._write_device_info()
        self._write_report_columns_names(self.current_sheet, COLUMN_NAMES, 8)

    def _check_pause(self):
        if self.pause_event.isSet():
            self.pause_event.clear()
            self.logger.log(message="Automation Paused.", level=logging.INFO)
            self.resume_event.wait()
            self.resume_event.clear()
            self.logger.log(message="Automation Resumed.", level=logging.INFO)

    def _write_1st_line(self):
        first_line_text = f"CAT Tool (version- {VERSION}) report"
        self.current_sheet.merge_cells(start_row=1, start_column=2, end_row=1, end_column=5)
        self.current_sheet.cell(row=1, column=2).value = first_line_text
        self.current_sheet.cell(row=1, column=2).font  = self.bold_font
        self._save_workbook()

    def _write_device_info(self):
        self.current_sheet.cell(row=3, column=2).value = "MO"
        self.current_sheet.cell(row=3, column=2).font  = self.bold_font
        self.current_sheet.cell(row=3, column=3).value = "MT"
        self.current_sheet.cell(row=3, column=3).font  = self.bold_font
        self.current_sheet.cell(row=4, column=1).value = "Software Version"
        self.current_sheet.cell(row=4, column=1).font  = self.bold_font
        self.current_sheet.cell(row=4, column=2).value = self.mo_sw
        self.current_sheet.cell(row=4, column=3).value = self.mt_sw
        self.current_sheet.cell(row=5, column=1).value = "IMEI"
        self.current_sheet.cell(row=5, column=1).font  = self.bold_font
        self.current_sheet.cell(row=5, column=2).value = self.mo_imei
        self.current_sheet.cell(row=5, column=3).value = self.mt_imei
        self.current_sheet.cell(row=6, column=1).value = "Phone Number"
        self.current_sheet.cell(row=6, column=1).font  = self.bold_font
        self.current_sheet.cell(row=6, column=2).value = self.mo_no
        self.current_sheet.cell(row=6, column=3).value = self.mt_no
        self._save_workbook()

    def _switch_mo_mt(self):
        self.mo_sw   = DeviceInfo.dev2["Software Version"]
        self.mo_imei = DeviceInfo.dev2["IMEI"]
        self.mo_port = DeviceInfo.dev2["AT Port"]
        self.mo_no   = DeviceInfo.dev2["Phone Number"]
        self.mt_sw   = DeviceInfo.dev1["Software Version"]
        self.mt_imei = DeviceInfo.dev1["IMEI"]
        self.mt_port = DeviceInfo.dev1["AT Port"]
        self.mt_no   = DeviceInfo.dev1["Phone Number"]

    def _write_report_columns_names(self, worksheet, columns: List[str], row: int):
        bg_color = PatternFill(start_color="B0E0E6", end_color="B0E0E6", fill_type="solid")
        for col_idx, column_name in enumerate(columns, 1):
            cell      = worksheet.cell(row=row, column=col_idx, value=column_name)
            cell.font = self.bold_font
            cell.fill = bg_color
        self._save_workbook()

    def _new_sheet_for_mt_calls(self):
        self._switch_mo_mt()
        self.current_sheet       = self.workbook.create_sheet()
        self.current_sheet.title = "MT calls"
        self._write_1st_line()
        self._write_device_info()
        self._write_report_columns_names(self.current_sheet, COLUMN_NAMES, 8)
        self._save_workbook()

    def _save_workbook(self):
        self.workbook.save(self.report_file_path)

    def _update_report(self, itr, date, start_time, end_time, duration, result, comment):
        self.current_sheet.append([itr, date, start_time, end_time, duration, result, comment])
        self._save_workbook()

    def _make_devices_idle(self):
        """Send ATH to both ports to ensure they are in IDLE state."""
        self.logger.log("Putting devices into IDLE state...")
        end_call(self.mo_port, self.logger)
        end_call(self.mt_port, self.logger)
        time.sleep(1)

    def perform_call(self, current_itr):
        """
        Performs one iteration of MO→MT call testing.

        Designed to work correctly with both:
          - Feature phones that support AT+CLCC (standard)
          - 2G/Unisoc feature phones that only emit RING URCs (no AT+CLCC)

        Flow:
          1. Check both ports are connected
          2. Put devices into IDLE
          3. Dial from MO port
          4. Give MO 2s to start the call setup
          5. Check MO is dialing (AT+CLCC if supported; else trust ATD result)
          6. Listen on MT port directly for RING/+CSYS URC (up to 30s)
          7. Answer the call on MT with ATA
          8. Hold call for configured duration
          9. End call on both sides
         10. Write report row
        """
        date       = datetime.now().strftime("%d/%m/%Y")
        start_time = datetime.now().strftime("%H:%M:%S")
        end_time   = "00:00:00"
        self.call_duration = "00"

        self.logger.log(f"{'='*50}")
        self.logger.log(f"Iteration {current_itr} START")
        self.logger.log(f"  MO port: {self.mo_port}  |  MT port: {self.mt_port}")
        self.logger.log(f"  Dialing: {self.mt_no}  |  Duration: {self.duration}s")

        # ── Step 1: Disconnection check ───────────────────────────────────────
        status, _ = check_device_disconnection(self.mo_port, self.mt_port, self.logger)
        if not status:
            raise Exception("Device disconnected!")

        # ── Step 2: Put both devices into IDLE ────────────────────────────────
        self._make_devices_idle()

        # ── Step 3: Dial from MO ──────────────────────────────────────────────
        self.logger.log(f"Dialing {self.mt_no} from MO port {self.mo_port}...")
        dial_success = dial_number(self.mo_port, self.mt_no, self.logger)

        if not dial_success:
            self.logger.log(
                f"Dial failed for {self.mt_no} on {self.mo_port}", level=logging.WARNING)
            self._update_report(current_itr, date, start_time, "NA", "00", "Fail", "MO dial failed")
            return

        # ── Step 4: Brief pause — let the network set up the call ─────────────
        self.logger.log("Dial command accepted. Waiting 2s for call setup...")
        time.sleep(2)

        # ── Step 5: Confirm MO is dialing ─────────────────────────────────────
        # For feature phones without AT+CLCC this returns True if the port is
        # still alive (meaning ATD was accepted and the call setup is underway).
        mo_dialing = check_mo_dialing(self.mo_port, self.logger)
        if not mo_dialing:
            self.logger.log("MO not in dialing state after ATD — marking as Fail.")
            end_call(self.mo_port, self.logger)
            self._update_report(current_itr, date, start_time, "NA", "00",
                                "Fail", "MO failed to establish call")
            return

        self.logger.log("MO confirmed dialing. Listening for RING on MT...")

        # ── Step 6: Listen on MT port for incoming RING ───────────────────────
        # 30 seconds gives plenty of time even on congested networks
        ring_detected = wait_for_ring_on_mt(self.mt_port, timeout_sec=30, logger=self.logger)

        if not ring_detected:
            self.logger.log("MT did not receive incoming call within 30s.")
            end_call(self.mo_port, self.logger)
            end_call(self.mt_port, self.logger)
            self._update_report(current_itr, date, start_time, "NA", "00",
                                "Fail", "MT did not ring")
            return

        # ── Step 7: Answer the call on MT ─────────────────────────────────────
        self.logger.log("RING detected on MT. Answering call...")
        answered = answer_call_on_mt(self.mt_port, self.logger)

        if not answered:
            self.logger.log("MT failed to answer the call.")
            end_call(self.mo_port, self.logger)
            end_call(self.mt_port, self.logger)
            self._update_report(current_itr, date, start_time, "NA", "00",
                                "Fail", "MT failed to answer")
            return

        # ── Step 8: Record call start, hold for configured duration ───────────
        call_start = datetime.now()
        start_time = call_start.strftime("%H:%M:%S")
        hold_secs  = int(self.duration)
        self.logger.log(f"Call connected. Holding for {hold_secs}s...")
        time.sleep(hold_secs)

        # ── Step 9: End call on both sides ────────────────────────────────────
        end_call(self.mo_port, self.logger)
        time.sleep(0.5)
        end_call(self.mt_port, self.logger)

        end_time           = datetime.now().strftime("%H:%M:%S")
        self.call_duration = self.duration
        self.result        = "Pass"
        self.comment       = ""
        self.logger.log(f"Iteration {current_itr} PASS — call held for {hold_secs}s")

        # ── Step 10: Write report ─────────────────────────────────────────────
        self._update_report(current_itr, date, start_time, end_time,
                            self.call_duration, self.result, self.comment)

    def run_test(self, queue: Queue):
        self.logger.log("run_test started")
        progress    = TestProgress(self.progress_frame, self.iterations)
        current_itr = 1

        while current_itr <= self.iterations:
            try:
                self._check_pause()
                status, _ = check_device_disconnection(self.mo_port, self.mt_port, self.logger)
                if not status:
                    raise Exception("Device disconnected!")
                self.perform_call(current_itr)
                time.sleep(self.delay)
                progress.update_progress()
                queue.put(current_itr)
                current_itr += 1
                self._save_workbook()
                if self.end_event.is_set():
                    return
            except Exception as e:
                status, devices = check_device_disconnection(self.mo_port, self.mt_port, self.logger)
                if not status:
                    if self.mo_port not in devices:
                        end_call(self.mo_port, self.logger)
                    elif self.mt_port not in devices:
                        end_call(self.mt_port, self.logger)
                    while True:
                        self.logger.log("UI Warning: Device Not Found!")
                        reconnect_status = reconnect(self.home, devices, 20)
                        status, devices  = check_device_disconnection(self.mo_port, self.mt_port, self.logger)
                        if reconnect_status and status:
                            self.logger.log("Device reconnected")
                            break
                    self._make_devices_idle()
                else:
                    self.logger.log(f"System error in iteration {current_itr}: {e}", level=logging.ERROR)
                    # Continue to next iteration on non-disconnect errors
                    self._update_report(
                        current_itr,
                        datetime.now().strftime("%d/%m/%Y"),
                        datetime.now().strftime("%H:%M:%S"),
                        "NA", "00", "Fail", f"System error: {str(e)[:80]}"
                    )
                    current_itr += 1

        # ── MO-MT calls: second pass with roles swapped ────────────────────
        if self.test_type == "MO-MT calls":
            self._new_sheet_for_mt_calls()
            self.logger.log("Starting MT phase of MO-MT calls test")
            progress    = TestProgress(self.progress_frame, self.iterations)
            current_itr = 1
            while current_itr <= self.iterations:
                try:
                    self._check_pause()
                    status, _ = check_device_disconnection(self.mo_port, self.mt_port, self.logger)
                    if not status:
                        raise Exception("Device disconnected!")
                    self.perform_call(current_itr)
                    time.sleep(self.delay)
                    progress.update_progress()
                    queue.put(current_itr)
                    current_itr += 1
                    self._save_workbook()
                    if self.end_event.is_set():
                        return
                except Exception as e:
                    status, devices = check_device_disconnection(self.mo_port, self.mt_port, self.logger)
                    if not status:
                        if self.mo_port not in devices:
                            end_call(self.mo_port, self.logger)
                        elif self.mt_port not in devices:
                            end_call(self.mt_port, self.logger)
                        while True:
                            self.logger.log("UI Warning: Device Not Found!")
                            reconnect_status = reconnect(self.home, devices, 20)
                            status, devices  = check_device_disconnection(self.mo_port, self.mt_port, self.logger)
                            if reconnect_status and status:
                                self.logger.log("Device reconnected")
                                break
                        self._make_devices_idle()
                    else:
                        self.logger.log(f"System error in MT iteration {current_itr}: {e}", level=logging.ERROR)
                        self._update_report(
                            current_itr,
                            datetime.now().strftime("%d/%m/%Y"),
                            datetime.now().strftime("%H:%M:%S"),
                            "NA", "00", "Fail", f"System error: {str(e)[:80]}"
                        )
                        current_itr += 1


def run_call_testing(test: CallTester, queue):
    test.run_test(queue)