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
    check_network_registration_status, check_device_disconnection
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
        # Variable initiation
        self.resume_event  = resume_event
        self.pause_event   = pause_event
        self.end_event     = end_test_event
        self.call_duration = None
        self.comment       = None
        self.result        = None
        self.home          = home
        self.progress_frame = progress_frame
        # Create logs file to save the frontend related logs.
        self.logger = CustomLogger("backend", Paths.latest_log_dir_path)
        self.logger.log("Backend code initiated to Start the Call Testing.")
        # Collect required information for Calling
        self.test_type = TestCred.test_type
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

        # Report workbook initiation
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
        """
        If the pause event is set True by pressing Pause button on the UI,
        this function will pause the automation and resume the next iteration only
        if the resume event is set True.
        """
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
            cell       = worksheet.cell(row=row, column=col_idx, value=column_name)
            cell.font  = self.bold_font
            cell.fill  = bg_color
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
        self.logger.log("Put the devices into IDLE state if not already.")
        mo_state = get_call_state(self.mo_port, self.logger)
        if 'idle' not in mo_state['state'].lower() or 'active' in mo_state['state'].lower():
            end_call(self.mo_port, self.logger)
        mt_state = get_call_state(self.mt_port, self.logger)
        if 'idle' not in mt_state['state'].lower() or 'active' in mt_state['state'].lower():
            end_call(self.mt_port, self.logger)

    def perform_call(self, current_itr):
        """
        Performs one iteration of MO-MT call testing.
        Includes fallback for unsupported AT+CLCC using RING detection on MT side.
        """
        from backend.cat_f_tool.src.utility.utils import send_at_command

        date       = datetime.now().strftime("%d/%m/%Y")
        start_time = datetime.now().strftime("%H:%M:%S")
        end_time   = "00:00:00"
        self.call_duration = "00"
        self.logger.log(f"Iteration -> {current_itr}")

        # Step 1: Disconnection check
        status, _ = check_device_disconnection(self.mo_port, self.mt_port, self.logger)
        if not status:
            raise Exception("Device disconnected!")

        self._make_devices_idle()

        # Step 2: Dial from MO with fallback
        dial_success = dial_number(self.mo_port, self.mt_no, self.logger)

        if not dial_success:
            self.logger.log(f"Dial failed for number {self.mt_no} on port {self.mo_port}", level=logging.WARNING)
            self._update_report(current_itr, date, start_time, "NA", "00", "Fail", "MO dial failed")
            return

        time.sleep(3)  # wait before checking call status

        # Step 3: Check MO state
        mo_state = get_call_state(self.mo_port, self.logger)
        if mo_state and mo_state['state'].lower() in ['dialing (mo call)', 'alerting (mo call)']:

            wait_time      = 15
            call_connected = False

            # Step 4: Poll MT for incoming call
            while wait_time:
                mt_state = get_call_state(self.mt_port, self.logger)
                if mt_state and mt_state['state'].lower() == 'ring':
                    self.logger.log("Incoming call detected on MT side. Sending ATA...")
                    send_at_command(self.mt_port, "ATA", self.logger)
                    call_connected = True
                    break
                time.sleep(1)
                wait_time -= 1

            if call_connected:
                # Step 5: Hold call for specified duration
                hold_time = int(self.duration)
                time.sleep(hold_time)
                send_at_command(self.mo_port, "ATH", self.logger)
                end_time           = datetime.now().strftime("%H:%M:%S")
                self.call_duration = self.duration
                self.comment       = ""
                self.result        = "Pass"
                send_at_command(self.mt_port, "ATH", self.logger)
                self.logger.log("Call ended successfully.")
                self._update_report(current_itr, date, start_time, end_time,
                                    self.call_duration, self.result, self.comment)
            else:
                self.logger.log("MT did not answer or detect incoming call.")
                end_time           = "NA"
                self.call_duration = "00"
                self.comment       = "MT did not answer"
                self.result        = "Fail"
                self._update_report(current_itr, date, start_time, end_time,
                                    self.call_duration, self.result, self.comment)

        else:
            self.logger.log("MO device did not establish call state correctly.")
            end_time           = "NA"
            self.call_duration = "00"
            self.comment       = "MO not in dialing/alerting state"
            self.result        = "Fail"
            self._update_report(current_itr, date, start_time, end_time,
                                self.call_duration, self.result, self.comment)

    def run_test(self, queue: Queue):
        self.logger.log("Create Progress bar")
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
                    self.logger.log("Failed to execute. System Error", e, logging.ERROR)

        if self.test_type == "MO-MT calls":
            self._new_sheet_for_mt_calls()
            self.logger.log("Create Progress bar")
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
                        self.logger.log("Failed to execute. System Error", e, logging.ERROR)


def run_call_testing(test: CallTester, queue):
    test.run_test(queue)