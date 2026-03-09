import threading
import time
from typing import List
import subprocess
import re
import os
from datetime import datetime

import openpyxl
import pandas as pd

from backend.cat_a_tool.logger import CustomLogger
from backend.cat_a_tool.utils import *
from backend.cat_a_tool.data.constants import *
from frontend.connection_break import reconnect


class CallTester:
    def __init__(
        self,
        home,
        cred_mo,
        cred_mt,
        test_type,
        iterations,
        call_duration,
        call_delay,
        ph_no,
        frame,
        mo_label,
        mt_label,
        barriers: List[threading.Barrier],
        no_of_devices
    ):
        self.home = home
        self.mo = cred_mo['udid']
        self.mt = cred_mt['udid']

        self.mo_sim_pref = int(cred_mo["Sim_Preference"])
        self.mt_sim_pref = int(cred_mt["Sim_Preference"])

        self.mo_label = mo_label
        self.mt_label = mt_label
        self.phone_number = ph_no

        self.test_type = test_type
        self.itr = iterations
        self.DURATION = call_duration
        self.delay = call_delay
        self.no_of_devices = no_of_devices

        self.dial_barrier = barriers[0]
        self.rcv_barrier = barriers[1]
        self.end_barrier = barriers[2]

        # ✅ Get reports folder from logger (same session as logs)
        from backend.cat_a_tool.logger import get_reports_folder
        reports_folder = get_reports_folder()
        
        # Use reports folder for all file paths
        self.current_dir_path = reports_folder

        self.mo_file_name = f"{self.mo_label}-{self.mo}.csv"
        self.mt_file_name = f"{self.mt_label}-{self.mt}.csv"

        self.mo_file_path = os.path.join(self.current_dir_path, self.mo_file_name)
        self.mt_file_path = os.path.join(self.current_dir_path, self.mt_file_name)

        self.columns = COLUMNS
        self.frame = frame

        self.mo_df = pd.DataFrame(columns=COLUMNS)
        self.mt_df = pd.DataFrame(columns=COLUMNS)

        self.instance_id = f"{self.mo_label}_to_{self.mt_label}"
        self.logger = CustomLogger(self.instance_id)
        
        # ✅ Save Excel files with device serial numbers
        self.mo_excel_path = os.path.join(reports_folder, f"MO1-{self.mo}.xlsx")
        self.mt_excel_path = os.path.join(reports_folder, f"MT1-{self.mt}.xlsx")
        self.combined_excel_path = os.path.join(reports_folder, f"temp_report_{self.instance_id}.xlsx")

        # ✅ Create Excel workbook with headers
        self.workbook = openpyxl.Workbook()
        self.mo_sheet = self.workbook.active
        self.mo_sheet.title = "MO Report"
        self.mt_sheet = self.workbook.create_sheet("MT Report")

        self.mo_sheet.append(self.columns)
        self.mt_sheet.append(self.columns)
        self.workbook.save(self.combined_excel_path)

    # --------------------------------------------------
    # ALL EXISTING METHODS BELOW ARE UNCHANGED
    # --------------------------------------------------

    def all_devices_connected(self):
        no_of_connected_devices, found = count_connected_devices(self.logger)
        if no_of_connected_devices == self.no_of_devices:
            return True
        else:
            if (self.mo in found) and (self.mt in found):
                return True
            else:
                return False

    def get_call_state(self, udid):
        self.logger.log(f"Checking mCallState <{udid}>", )
        # Execute the adb command to get the telephony registry information
        output = subprocess.check_output(["adb", "-s", udid, "shell", "dumpsys", "telephony.registry"], text=True)

        # Use regular expression to find the lines containing "mCallState" and its value
        call_state_lines = re.findall(r'mCallState=\d', output)

        call_state = '\n'.join(call_state_lines)

        # Return the extracted call state lines
        return call_state

    def initiate_call(self, ):
        self.dial_barrier.wait()
        self.logger.log("Dialing Number ...", )
        cmd_start_call = f"adb -s {self.mo} shell am start -a android.intent.action.CALL -d 'tel:{self.phone_number}'"
        subprocess.run(cmd_start_call, shell=False, check=True)

    def receive_call(self, ):
        self.rcv_barrier.wait()
        self.logger.log("Receiving Call...", )
        subprocess.run(
            f"adb -s {self.mt} shell input keyevent {KEYCODE_CALL}",
            shell=False, check=True)

    def end_call(self, udid):
        self.logger.log("Ending Call...", )
        cmd_end_call = f"adb -s {udid} shell input keyevent {KEYCODE_ENDCALL}"
        subprocess.run(cmd_end_call, shell=False, check=True)

    def get_mt_cell_info(self):
        # Get the cell info of MT
        self.mt_cell_info = get_cell_info(self.mt, self.mt_sim_pref, self.logger)
        # Get the current location
        self.mt_gps = get_location(self.mt, self.logger)

    def check_status(self, current_itr, date):
        start_time = datetime.now().time().strftime("%H:%M:%S")
        end_time = "00:00:00"
        call_duration = "0"
        try:
            # Check if MO call is properly established
            wait1 = 30
            while wait1:
                if not self.all_devices_connected():
                    raise Exception("Device Not Found!")
                output_mo = self.get_call_state(self.mo)
                if "mCallState=2" in output_mo:
                    start_time = datetime.now().time().strftime("%H:%M:%S")
                    # Check if MT device is receiving any calls
                    wait2 = 20
                    while wait2:
                        time.sleep(1)
                        if not self.all_devices_connected():
                            raise Exception("Device Not Found!")
                        if "mCallState=1" in self.get_call_state(self.mt):
                            time.sleep(2)
                            # Receive the call on MT device
                            if not self.all_devices_connected():
                                raise Exception("Device Not Found!")
                            self.receive_call()
                            call_rcv_time = datetime.now()
        
                            if not self.all_devices_connected():
                                raise Exception("Device Not Found!")
                            self.get_mt_cell_info()
 
                            while True:
                                if not self.all_devices_connected():
                                    raise Exception("Device Not Found!")
                                
                                # ✅ CHECK FOR PAUSE DURING ACTIVE CALL
                                from backend.cat_a_tool.service import cat_a_state
                                if cat_a_state.get("cut_call_on_pause", False):
                                    self.logger.log("⏸️ PAUSE DETECTED - Cutting call immediately")
                                    call_duration = (datetime.now() - call_rcv_time).total_seconds()
                                    end_time = datetime.now().time().strftime("%H:%M:%S")
                                    try:
                                        self.end_call(self.mo)
                                        self.end_call(self.mt)
                                    except Exception as e:
                                        self.logger.log(f"Error cutting call: {e}")
                                    cat_a_state["cut_call_on_pause"] = False
                                    return ("PAUSED", "Call cut on pause", start_time, end_time, call_duration)
                                
                                # ✅ CHECK FOR OOS DURING ACTIVE CALL
                                mo_service = get_service_state(self.mo, self.logger)
                                mt_service = get_service_state(self.mt, self.logger)
                                mo_in_service = "IN_SERVICE" in mo_service[self.mo_sim_pref]
                                mt_in_service = "IN_SERVICE" in mt_service[self.mt_sim_pref]
                                
                                if not mo_in_service or not mt_in_service:
                                    # CRITICAL: Check if this is actually OOS or device disconnect
                                    if not self.all_devices_connected():
                                        # Device disconnected - NOT OOS! Raise exception
                                        self.logger.log("⚠️ Device disconnected (NOT OOS) - raising exception")
                                        raise Exception("Device Not Found!")
                                    
                                    # OOS detected during call - this is NOT a dropped call
                                    oos_devices = []
                                    if not mo_in_service:
                                        oos_devices.append(f"{self.mo_label} -> SIM{self.mo_sim_pref + 1}")
                                    if not mt_in_service:
                                        oos_devices.append(f"{self.mt_label} -> SIM{self.mt_sim_pref + 1}")
                                    
                                    self.logger.log(f"⚠️ OOS DURING CALL: {oos_devices} - Aborting iteration {current_itr}")
                                    self.logger.log("📍 This is NOT a dropped call - waiting for devices to come back online")
                                    
                                    # End the call gracefully
                                    try:
                                        self.end_call(self.mo)
                                        self.end_call(self.mt)
                                    except:
                                        pass
                                    
                                    # Wait for devices to come back
                                    from backend.cat_a_tool.service import cat_a_state
                                    my_test_id = getattr(self, 'my_test_id', None)
                                    
                                    cat_a_state["oos_detected"] = True
                                    cat_a_state["oos_devices"] = oos_devices
                                    
                                    self.logger.log("⏳ Waiting for devices to return to IN_SERVICE...")
                                    
                                    while True:
                                        time.sleep(5)
                                        
                                        # Check for test stop/new test
                                        current_test_id = cat_a_state.get("test_id", None)
                                        if my_test_id is not None and current_test_id != my_test_id:
                                            self.logger.log(f"⚠️ New test started - exiting OOS wait")
                                            return "OOS_ABORT", "New test started during OOS", start_time, end_time, 0
                                        
                                        if cat_a_state.get("stop_requested", False):
                                            self.logger.log("⏹️ Test stopped during OOS wait")
                                            return "OOS_ABORT", "Test stopped during OOS", start_time, end_time, 0
                                        
                                        # Check if back online
                                        re_mo = get_service_state(self.mo, self.logger)
                                        re_mt = get_service_state(self.mt, self.logger)
                                        mo_ok = "IN_SERVICE" in re_mo[self.mo_sim_pref]
                                        mt_ok = "IN_SERVICE" in re_mt[self.mt_sim_pref]
                                        
                                        if mo_ok and mt_ok:
                                            self.logger.log("✅ Devices back online - will retry this iteration")
                                            cat_a_state["oos_detected"] = False
                                            cat_a_state["oos_devices"] = []
                                            # Return special status so iteration is retried
                                            return "OOS_RETRY", "OOS during call - retrying iteration", start_time, end_time, 0
                                        else:
                                            still_oos = []
                                            if not mo_ok:
                                                still_oos.append(self.mo_label)
                                            if not mt_ok:
                                                still_oos.append(self.mt_label)
                                            self.logger.log(f"⏳ Still OOS: {', '.join(still_oos)}")
                                
                                # Disconnect the call on MT device if not already ended
                                status_mo = self.get_call_state(self.mo)
                                status_mt = self.get_call_state(self.mt)
                                if "mCallState=2" not in status_mo:
                                    if not self.all_devices_connected():
                                        raise Exception("Device Not Found!")
                                    
                                    # ✅ Before saying CALL DROPPED, check if it's due to OOS
                                    mo_service_check = get_service_state(self.mo, self.logger)
                                    mt_service_check = get_service_state(self.mt, self.logger)
                                    mo_in_svc = "IN_SERVICE" in mo_service_check[self.mo_sim_pref]
                                    mt_in_svc = "IN_SERVICE" in mt_service_check[self.mt_sim_pref]
                                    
                                    if not mo_in_svc or not mt_in_svc:
                                        # This is OOS, not a dropped call!
                                        oos_list = []
                                        if not mo_in_svc:
                                            oos_list.append(f"{self.mo_label} -> SIM{self.mo_sim_pref + 1}")
                                        if not mt_in_svc:
                                            oos_list.append(f"{self.mt_label} -> SIM{self.mo_sim_pref + 1}")
                                        
                                        self.logger.log(f"⚠️ OOS DETECTED: {oos_list} - WAITING for devices to come back IN SERVICE")
                                        
                                        # End call gracefully
                                        try:
                                            self.end_call(self.mo)
                                            self.end_call(self.mt)
                                        except:
                                            pass
                                        
                                        # Set OOS state
                                        from backend.cat_a_tool.service import cat_a_state
                                        cat_a_state["oos_detected"] = True
                                        cat_a_state["oos_devices"] = oos_list
                                        my_test_id = getattr(self, 'my_test_id', None)
                                        
                                        # Wait for devices to come back
                                        self.logger.log("⏳ Waiting for devices to return to IN_SERVICE...")
                                        while True:
                                            time.sleep(5)
                                            
                                            # Check for test stop
                                            if cat_a_state.get("stop_requested", False):
                                                self.logger.log("⏹️ Test stopped during OOS wait")
                                                return "OOS_ABORT", "Test stopped during OOS", start_time, end_time, 0
                                            
                                            # Check if new test started
                                            current_test_id = cat_a_state.get("test_id", None)
                                            if my_test_id is not None and current_test_id != my_test_id:
                                                self.logger.log(f"⚠️ New test started - exiting OOS wait")
                                                return "OOS_ABORT", "New test started during OOS", start_time, end_time, 0
                                            
                                            # Check if back online
                                            re_mo = get_service_state(self.mo, self.logger)
                                            re_mt = get_service_state(self.mt, self.logger)
                                            mo_back = "IN_SERVICE" in re_mo[self.mo_sim_pref]
                                            mt_back = "IN_SERVICE" in re_mt[self.mt_sim_pref]
                                            
                                            if mo_back and mt_back:
                                                self.logger.log("✅ Devices back online - will retry this iteration")
                                                cat_a_state["oos_detected"] = False
                                                cat_a_state["oos_devices"] = []
                                                return "OOS_RETRY", "OOS during call - retrying iteration", start_time, end_time, 0
                                            else:
                                                still_oos_list = []
                                                if not mo_back:
                                                    still_oos_list.append(self.mo_label)
                                                if not mt_back:
                                                    still_oos_list.append(self.mt_label)
                                                self.logger.log(f"⏳ Still OOS: {', '.join(still_oos_list)}")
                                    
                                    # Not OOS - actual dropped call
                                    call_duration = (datetime.now() - call_rcv_time).total_seconds()
                                    end_time = datetime.now().time().strftime("%H:%M:%S")
                                    self.logger.log("Call ended before given time : CALL DROPPED", )
                                    return "CALL_DROPPED", "Call ended before given time", start_time, end_time, call_duration
                                if (datetime.now() - call_rcv_time).total_seconds() > self.DURATION:
                                    call_duration = (datetime.now() - call_rcv_time).total_seconds()
                                    end_time = datetime.now().time().strftime("%H:%M:%S")
                                    time.sleep(0.4)
                                    if not self.all_devices_connected():
                                        raise Exception("Device Not Found!")
                                    if self.test_type == "Long calls":
                                        self.get_mt_cell_info()
                                    self.end_call(self.mo)
                                    break

                                if self.test_type == "Long calls":
                                    time.sleep(30)
                                else:
                                    time.sleep(1)

                            self.logger.log("Call ended successfully : PASS", )
                            return "PASS", "", start_time, end_time, call_duration

                        wait2 -= 1

                    # If MT device is not receiving any calls
                    self.logger.log("MT device is not receiving any calls : FAILED", )
                    end_time = datetime.now().time().strftime("%H:%M:%S")
                    return "FAILED", "MT device is not receiving any calls", start_time, end_time, call_duration

                time.sleep(1)
                wait1 -= 1

            # If MO call is not properly established
            self.logger.log("MO call is not properly established : FAILED", )
            end_time = datetime.now().time().strftime("%H:%M:%S")
            return "FAILED", "MO call is not properly established", start_time, end_time, call_duration

        except Exception as e:
            self.logger.log(f"Error in check_status: {e}", )
            end_time = datetime.now().time().strftime("%H:%M:%S")
            return "FAILED", str(e), start_time, end_time, call_duration

    def device_setting(self):
        self.logger.log(f"Setting up device <{self.mo}>")
        toggle_wifi(self.mo, 0, self.logger)
        toggle_data(self.mo, 0, self.logger)
        toggle_data(self.mo, 1, self.logger)

        self.logger.log(f"Setting up device <{self.mt}>")
        toggle_wifi(self.mt, 0, self.logger)
        toggle_data(self.mt, 0, self.logger)
        toggle_data(self.mt, 1, self.logger)

    def oos_checking(self):
        mo_flag = False
        mt_flag = False
        oos_devices = []

        mo_service_state = get_service_state(self.mo, self.logger)
        if "IN_SERVICE" in mo_service_state[self.mo_sim_pref]:
            mo_flag = False
        else:
            oos_devices.append(f"{self.mo_label} -> SIM{self.mo_sim_pref + 1}")
            mo_flag = True
            mo_lat, mo_long = get_location(self.mo, self.logger)
            self.logger.log(
                f"OOS Zone ({mo_service_state}) found in {self.mo_label} at Location (lat, long) -> {mo_lat, mo_long}")

        # if mt_flag:
        mt_service_state = get_service_state(self.mt, self.logger)
        if "IN_SERVICE" in mt_service_state[self.mt_sim_pref]:
            mt_flag = False
        else:
            oos_devices.append(f"{self.mt_label} -> SIM{self.mt_sim_pref + 1}")
            mt_flag = True
            mt_lat, mt_long = get_location(self.mt, self.logger)
            self.logger.log(
                f"OOS Zone ({mt_service_state}) found in {self.mt_label} at Location (lat, long) -> {mt_lat, mt_long}")

        if mo_flag or mt_flag:
            # CRITICAL: Check if this is actually OOS or device disconnect
            if not self.all_devices_connected():
                # Device disconnected - NOT OOS! Raise exception
                self.logger.log("⚠️ Device disconnected (NOT OOS) - raising exception")
                raise Exception("Device Not Found!")
            
            # ✅ OOS DETECTED: Auto-wait for devices to come back IN_SERVICE
            from backend.cat_a_tool.service import cat_a_state
            
            my_test_id = getattr(self, 'my_test_id', None)
            
            # Set OOS flag but DO NOT pause (no user intervention)
            cat_a_state["oos_detected"] = True
            cat_a_state["oos_devices"] = oos_devices
            
            self.logger.log(f"⚠️ OOS DETECTED: {oos_devices} - WAITING for devices to come back IN SERVICE")
            self.logger.log(f"📍 Current iteration will PAUSE and RESUME automatically when back online")
            print(f"⚠️ OOS DETECTED - test_id={my_test_id}, auto-waiting for IN_SERVICE")

            # ✅ AUTO-WAIT loop: continuously check until devices are back IN_SERVICE
            while True:
                time.sleep(5)  # Check every 5 seconds
                
                # Check if a NEW test has started (stale thread detection)
                current_test_id = cat_a_state.get("test_id", None)
                if my_test_id is not None and current_test_id != my_test_id:
                    self.logger.log(f"⚠️ New test started (id={current_test_id}), stopping stale OOS thread (id={my_test_id})")
                    print(f"⚠️ STALE THREAD: my_test_id={my_test_id}, current={current_test_id} - exiting")
                    return

                # Check if user manually stopped test
                if cat_a_state.get("stop_requested", False):
                    self.logger.log("⏹️ Test stopped by user during OOS wait")
                    print(f"⏹️ OOS loop: stop_requested=True, exiting")
                    return

                # Check if devices are back IN SERVICE
                re_mo = get_service_state(self.mo, self.logger)
                re_mt = get_service_state(self.mt, self.logger)

                mo_ok = "IN_SERVICE" in re_mo[self.mo_sim_pref]
                mt_ok = "IN_SERVICE" in re_mt[self.mt_sim_pref]

                if mo_ok and mt_ok:
                    # ✅ AUTO-RESUME: Devices are back online
                    self.logger.log("✅ Both devices back IN SERVICE - AUTO-RESUMING test from same iteration")
                    cat_a_state["oos_detected"] = False
                    cat_a_state["oos_devices"] = []
                    cat_a_state["device_disconnected"] = False
                    cat_a_state["disconnected_device"] = None
                    print(f"✅ OOS CLEARED - continuing iteration")
                    break
                else:
                    # Still OOS - keep waiting
                    still_oos = []
                    if not mo_ok:
                        still_oos.append(self.mo_label)
                    if not mt_ok:
                        still_oos.append(self.mt_label)
                    self.logger.log(f"⏳ Still OOS: {', '.join(still_oos)} - waiting...")
                    print(f"  OOS wait: {', '.join(still_oos)} still out of service")
        else:
            self.logger.log(f"Both {self.mo_label} and {self.mt_label} are IN SERVICE")

    def run_test(self, queue):
        # ---- ENTRY LOG ----
        self.logger.log("run_test ENTERED")

        try:
            self.device_setting()
        except Exception as e:
            self.logger.log(f"Device setting failed: {e}")
            return

        # initiating progress tracking
        self.logger.log("Progress tracking started")

        from backend.cat_a_tool.progress_state import progress_data
        from backend.cat_a_tool.service import cat_a_state

        progress_data["total"] = self.itr
        progress_data["current"] = 0
        progress_data["percent"] = 0
        progress_data["running"] = True

        i = 1
        while i <= self.itr:
            try:
                # ✅ NEW: Check for pause
                while cat_a_state.get("paused", False):
                    self.logger.log("⏸️ Test paused, waiting...")
                    time.sleep(1)
                    
                    # Check if stop was requested during pause
                    if cat_a_state.get("stop_requested", False):
                        self.logger.log("⏹️ Test stopped during pause")
                        progress_data["running"] = False
                        return

                # ✅ NEW: Check for stop request
                if cat_a_state.get("stop_requested", False):
                    self.logger.log("⏹️ Test stopped by user")
                    progress_data["running"] = False
                    return

                # ✅ NEW: Check for device disconnection
                if cat_a_state.get("device_disconnected", False):
                    self.logger.log(f"⚠️ Device disconnected: {cat_a_state.get('disconnected_device')}")
                    # Don't automatically continue - wait for user action
                    progress_data["running"] = False
                    cat_a_state["state"] = "FAILED"
                    cat_a_state["message"] = f"Device {cat_a_state.get('disconnected_device')} disconnected"
                    return

                self.logger.log("#" * 50)

                if not self.all_devices_connected():
                    raise Exception("Device Not Found!")

                self.oos_checking()

                if not self.all_devices_connected():
                    raise Exception("Device Not Found!")

                self.logger.log(f"Iteration {i} ---")

                # Update current iteration in cat_a_state
                cat_a_state["current_iteration"] = i

                start_time = time.strftime("%Y-%m-%d %H:%M:%S")
                start_time_datetime = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                date = start_time_datetime.date()

                # ---- INITIATE CALL ----
                self.initiate_call()

                mo_cell_info = get_cell_info(self.mo, self.mo_sim_pref, self.logger)
                mo_gps = get_location(self.mo, self.logger)

                if not self.all_devices_connected():
                    raise Exception("Device Not Found!")

                status, comment, s_time, e_time, c_duration = self.check_status(i, date)

                # ✅ HANDLE PAUSED: Call was cut, restart same iteration
                if status == "PAUSED":
                    self.logger.log(f"⏸️ Call cut on iteration {i} - will restart this iteration after resume")
                    # Wait for resume
                    while cat_a_state.get("paused", False):
                        time.sleep(1)
                        if cat_a_state.get("stop_requested", False):
                            progress_data["running"] = False
                            return
                    # After resume, continue to restart same iteration
                    self.logger.log(f"▶️ Resuming - restarting iteration {i}")
                    continue

                # ✅ HANDLE OOS_RETRY: Don't save report, retry same iteration
                if status == "OOS_RETRY":
                    self.logger.log(f"🔄 OOS detected during iteration {i} - will retry this iteration")
                    # Don't increment i, don't save report, just continue to retry
                    time.sleep(5)  # Brief delay before retry
                    continue
                
                # ✅ HANDLE OOS_ABORT: Test was stopped/changed during OOS wait
                if status == "OOS_ABORT":
                    self.logger.log(f"⚠️ OOS abort: {comment}")
                    progress_data["running"] = False
                    return

                # --------------------------------------------------
                # FORCE END CALL AFTER DURATION (CRITICAL FIX)
                # --------------------------------------------------
                self.logger.log("Ending call after duration")

                try:
                    self.end_call(self.mo)
                    self.end_call(self.mt)
                except Exception as e:
                    self.logger.log(f"Call end error: {e}")
                    
                # --------------------------------------------------
                # Delay BEFORE NEXT ITERATION
                # --------------------------------------------------
                self.logger.log(f"Waiting call_delay = {self.delay} seconds")

                time.sleep(3)

                mo_report = [
                    i, date, s_time, e_time, int(c_duration), status, comment
                ] + mo_cell_info + mo_gps

                mt_report = [
                    i, date, s_time, e_time, int(c_duration), status, comment
                ] + self.mt_cell_info + self.mt_gps

                # ---- SAVE REPORTS ----
                # ✅ Save to combined workbook
                self.mo_sheet.append(mo_report)
                self.mt_sheet.append(mt_report)
                self.workbook.save(self.combined_excel_path)
                
                # ✅ Save individual device Excel files (real-time)
                # MO Excel file
                if not os.path.exists(self.mo_excel_path):
                    mo_wb = openpyxl.Workbook()
                    mo_ws = mo_wb.active
                    mo_ws.append(self.columns)
                    mo_ws.append(mo_report)
                    mo_wb.save(self.mo_excel_path)
                else:
                    mo_wb = openpyxl.load_workbook(self.mo_excel_path)
                    mo_ws = mo_wb.active
                    mo_ws.append(mo_report)
                    mo_wb.save(self.mo_excel_path)
                
                # MT Excel file
                if not os.path.exists(self.mt_excel_path):
                    mt_wb = openpyxl.Workbook()
                    mt_ws = mt_wb.active
                    mt_ws.append(self.columns)
                    mt_ws.append(mt_report)
                    mt_wb.save(self.mt_excel_path)
                else:
                    mt_wb = openpyxl.load_workbook(self.mt_excel_path)
                    mt_ws = mt_wb.active
                    mt_ws.append(mt_report)
                    mt_wb.save(self.mt_excel_path)

                self.logger.log("Submitting Call report")

                self.mo_df.loc[len(self.mo_df)] = mo_report
                self.mt_df.loc[len(self.mt_df)] = mt_report

                time.sleep(self.delay)

                # ---- TIME CALCULATION ----
                end_time = time.strftime("%Y-%m-%d %H:%M:%S")
                start_timestamp = time.mktime(time.strptime(start_time, "%Y-%m-%d %H:%M:%S"))
                end_timestamp = time.mktime(time.strptime(end_time, "%Y-%m-%d %H:%M:%S"))
                time_taken_seconds = end_timestamp - start_timestamp

                self.logger.log(f"Time taken for Iteration {i}: {time_taken_seconds} seconds")

                # ---- BARRIER (SAFE) ----
                try:
                    self.end_barrier.wait(timeout=10)
                except Exception as b_err:
                    self.logger.log(f"Barrier skipped: {b_err}")

                # ---- QUEUE UPDATE ----
                try:
                    queue.put(int(self.mo_label[-1]))
                except Exception as q_err:
                    self.logger.log(f"Queue update skipped: {q_err}")

                # ---- PROGRESS UPDATE ----
                progress_data["current"] = i
                progress_data["percent"] = int((i / self.itr) * 100)

                i += 1

            except Exception as e:
                if self.all_devices_connected():
                    self.logger.log(f"Error: {e}")
                else:
                    device = f"MO-MT pair - {self.mo_label[-1]}"
                    self.logger.log(f"Device disconnected in {device}")
                    self.logger.log("Terminating ongoing calls")

                    _, devices_still_connected = count_connected_devices(self.logger)
                    if self.mo in devices_still_connected:
                        self.end_call(self.mo)
                    if self.mt in devices_still_connected:
                        self.end_call(self.mt)

                    while True:
                        self.logger.log("UI Warning: Device Not Found!")
                        reconnect_status = reconnect(self.home, device, 20)
                        if reconnect_status and self.all_devices_connected():
                            self.logger.log("Device reconnected")
                            break

        # ---- FINAL STATS ----
        try:
            mo_df_final = stats(self.mo_df, self.logger)
            mt_df_final = stats(self.mt_df, self.logger)

            mo_df_final.to_csv(self.mo_file_path, index=False)
            mt_df_final.to_csv(self.mt_file_path, index=False)

            self.logger.log("CAT-A EXECUTION FINISHED")
        except Exception as f_err:
            self.logger.log(f"Finalization error: {f_err}")

        progress_data["current"] = self.itr
        progress_data["percent"] = 100
        progress_data["running"] = False

        self.logger.log("CAT-A EXECUTION FINISHED")


def run_single_test(test: CallTester, queue):
    test.run_test(queue)

def run_automation(config: dict):
    """
    Adapter for WebUI → legacy CAT-A logic
    NO logic rewrite
    """

    tester = CallTester(
        home=config.get("home"),
        cred_mo=config.get("cred_mo"),
        cred_mt=config.get("cred_mt"),
        ph_no=config.get("mt_number"),
        frame=None,              # no UI
        mo_label="MO",
        mt_label="MT"
    )

    tester.itr = config.get("iterations")
    tester.run_test(queue=None)


if __name__ == "__main__":
    print(get_latest_dir(os.path.join(get_parent_dir(), 'reports')))