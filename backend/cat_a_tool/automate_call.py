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

        self.current_dir_path = get_latest_dir(
            os.path.join(get_parent_dir(), 'reports')
        )

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

        self.workbook_file_path = os.path.join(
            self.current_dir_path, f"temp_report_{self.instance_id}.xlsx"
        )
        
        self.workbook = openpyxl.Workbook()
        self.mo_sheet = self.workbook.active
        self.mo_sheet.title = "MO Report"
        self.mt_sheet = self.workbook.create_sheet("MT Report")

        self.mo_sheet.append(self.columns)
        self.mt_sheet.append(self.columns)
        self.workbook.save(self.workbook_file_path)

    # --------------------------------------------------
    # ALL EXISTING METHODS BELOW ARE UNCHANGED
    # --------------------------------------------------

    # all_devices_connected()
    # initiate_call()
    # receive_call()
    # end_call()
    # oos_checking()
    # device_setting()
    # check_status()
    # run_test()


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
                                # Disconnect the call on MT device if not already ended
                                status_mo = self.get_call_state(self.mo)
                                status_mt = self.get_call_state(self.mt)
                                if "mCallState=2" not in status_mo:
                                    if not self.all_devices_connected():
                                        raise Exception("Device Not Found!")
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
                                    time.sleep(4)
                                    time_now = datetime.now().time().strftime("%H:%M:%S")
                                    if "mCallState=2" in status_mo and "mCallState=2" in status_mt:
                                        status = "Ongoing"
                                        comment = None
                                        mo_cell_info = get_cell_info(self.mo, self.mo_sim_pref, self.logger)
                                        mo_gps = get_location(self.mo, self.logger)
                                        mt_cell_info = get_cell_info(self.mt, self.mt_sim_pref, self.logger)
                                        mt_gps = get_location(self.mt, self.logger)

                                        # report preparation
                                        mo_report = [current_itr, date, time_now, None, None, status,
                                                     comment] + mo_cell_info + mo_gps
                                        mt_report = [current_itr, date, time_now, None, None, status,
                                                     comment] + mt_cell_info + mt_gps

                                        # temp report generation
                                        self.mo_sheet.append(mo_report)
                                        self.mt_sheet.append(mt_report)
                                        self.workbook.save(self.workbook_file_path)

                                        # add a report to respective DataFrames
                                        self.logger.log("Submitting Call report.")
                                        self.mo_df.loc[len(self.mo_df)] = mo_report
                                        self.mt_df.loc[len(self.mt_df)] = mt_report

                            self.logger.log("Success : PASS", )
                            return "PASS", None, start_time, end_time, call_duration
                        else:
                            wait2 -= 1

                    # If no calls received on MT
                    if not self.all_devices_connected():
                        raise Exception("Device Not Found!")
                    self.get_mt_cell_info()
                    self.end_call(self.mo)
                    end_time = datetime.now().time().strftime("%H:%M:%S")
                    self.logger.log("No call received on MT : FAILED", )
                    return "FAILED", "No call received on MT", start_time, end_time, call_duration
                else:
                    wait1 -= 1
                time.sleep(1)

            # If call not established properly by MO
            self.logger.log("Call not established : FAILED", )
            if not self.all_devices_connected():
                raise Exception("Device Not Found!")
            self.get_mt_cell_info()
            end_time = datetime.now().time().strftime("%H:%M:%S")
            return "FAILED", "MO call was not established properly.", start_time, end_time, call_duration

        except (Exception, subprocess.CalledProcessError) as e:
            self.logger.log("Unable to complete", e)

            if not self.all_devices_connected():
                raise Exception("Device Not Found!")
            # Get the cell info of MT
            self.mt_cell_info = get_cell_info(self.mt, self.mt_sim_pref, self.logger)
            # Get the current location
            self.mt_gps = get_location(self.mt, self.logger)
            end_time = datetime.now().time().strftime("%H:%M:%S")
            return "FAILED", "System Error", start_time, end_time, call_duration

    def device_setting(self):
        try:
            # #restart the device
            # restart_device(self.mo, self.logger)
            # restart_device(self.mt, self.logger)
            #
            # time.sleep(90)

            # Turn Off Wi-Fi
            toggle_wifi(self.mo, 0, self.logger)
            toggle_wifi(self.mt, 0, self.logger)

            # Turn ON mobile Data in MO & MT
            toggle_data(self.mo, 1, self.logger)
            toggle_data(self.mt, 1, self.logger)

        except Exception as e:
            if self.all_devices_connected():
                # error not related to device connection
                self.logger.log("Error :", e)
            else:
                # device connection error
                while True:
                    device = f"MO-MT pair - {self.mo_label[-1]}"
                    reconnect_status = reconnect(self.home, device)
                    if reconnect_status and self.all_devices_connected():
                        break
                # redo device setting
                self.device_setting()

    def oos_checking(self):
        mo_flag = True
        mt_flag = True

        while mo_flag or mt_flag:
            if not self.all_devices_connected():
                raise Exception("Device Not Found!")
            oos_devices = []

            # if mo_flag:
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
                ooszone(self.home, oos_devices)
                self.logger.log("Again checking if the device(s) are back IN SERVICE")
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

        progress_data["total"] = self.itr
        progress_data["current"] = 0
        progress_data["percent"] = 0
        progress_data["running"] = True


        i = 1
        while i <= self.itr:
            try:
                self.logger.log("#" * 50)

                if not self.all_devices_connected():
                     raise Exception("Device Not Found!")

                self.oos_checking()

                if not self.all_devices_connected():
                    raise Exception("Device Not Found!")

                self.logger.log(f"Iteration {i} ---")

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
                self.mo_sheet.append(mo_report)
                self.mt_sheet.append(mt_report)
                self.workbook.save(self.workbook_file_path)

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
