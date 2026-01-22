import threading
import time
from typing import List
from queue import Queue

import openpyxl
import pandas as pd
from .logger import CustomLogger
from .utils import *
from .data.constants import *


class CallTester:
    def __init__(self, home, cred_mo, cred_mt, test_type, iterations, call_duration, call_delay,
                 ph_no, frame, mo_label, mt_label, barriers: List[threading.Barrier], no_of_devices):
        self.home = home
        self.mt_gps = None
        self.mt_cell_info = None
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
        self.current_dir_path = get_latest_dir(os.path.join(get_parent_dir(), 'reports'))
        self.mo_file_name = f"{self.mo_label}-{self.mo}.csv"
        self.mt_file_name = f"{self.mt_label}-{self.mt}.csv"
        self.mo_file_path = os.path.join(self.current_dir_path, self.mo_file_name)
        self.mt_file_path = os.path.join(self.current_dir_path, self.mt_file_name)
        self.columns = COLUMNS
        self.frame = frame
        self.dial_barrier = barriers[0]
        self.rcv_barrier = barriers[1]
        self.end_barrier = barriers[2]
        self.no_of_devices = no_of_devices
        # Create DataFrames for MO & MT
        self.mo_df = pd.DataFrame(columns=COLUMNS)
        self.mt_df = pd.DataFrame(columns=COLUMNS)

        # Configure logging for the instance
        self.instance_id = f"{self.mo_label}_to_{self.mt_label}"
        self.logger = CustomLogger(self.instance_id)

        self.workbook_file_path = os.path.join(self.current_dir_path, f"temp_report{self.instance_id}.xlsx")
        self.workbook = openpyxl.Workbook()

        # Get the active sheet (default is the first sheet)
        self.mo_sheet = self.workbook.active
        self.mo_sheet.title = "MO Report"
        self.mt_sheet = self.workbook.create_sheet("MT report")
        # Add column names to the first row
        self.mo_sheet.append(self.columns)
        self.mt_sheet.append(self.columns)
        self.workbook.save(self.workbook_file_path)

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
        self.device_setting()
        
        # Headless-safe: only create GUI progress if a tkinter frame was provided
        gui_progress = None
        try:
            if self.frame is not None:
                # TestProgress may not be available in headless contexts; guard against NameError
                gui_progress = TestProgress(self.frame, self.itr)  # type: ignore
                self.logger.log("Progress Bar Created")
        except Exception:
            gui_progress = None

        i = 1
        while i <= self.itr:
            try:
                self.logger.log("#" * 50)
                if not self.all_devices_connected():
                    raise Exception("Device Not Found!")

                self.oos_checking()

                if not self.all_devices_connected():
                    raise Exception("Device Not Found!")

                # self.barrier.wait()
                self.logger.log(f"Iteration {i} ---", )

                start_time = time.strftime("%Y-%m-%d %H:%M:%S")
                # Parse the time string using strptime
                start_time_datetime = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")

                # Extract date and time components
                date = start_time_datetime.date()

                # Disable Wi-Fi if found enabled
                # toggle_wifi(self.mo, 0, self.logger)
                # toggle_wifi(self.mt, 0, self.logger)

                # Initiate call
                self.initiate_call()
                # Get cell info of MO
                mo_cell_info = get_cell_info(self.mo, self.mo_sim_pref, self.logger)
                # get current GPS location
                mo_gps = get_location(self.mo, self.logger)

                if not self.all_devices_connected():
                    raise Exception("Device Not Found!")

                # Complete the call & Check status
                status, comment, s_time, e_time, c_duration = self.check_status(i, date)

                # report preparation
                mo_report = [i, date, s_time, e_time, int(c_duration), status, comment] + mo_cell_info + mo_gps
                mt_report = [i, date, s_time, e_time, int(c_duration), status,
                             comment] + self.mt_cell_info + self.mt_gps

                # temp report generation
                self.mo_sheet.append(mo_report)
                self.mt_sheet.append(mt_report)
                self.workbook.save(self.workbook_file_path)

                # add report to respective DataFrames
                self.logger.log("Submitting Call report.")
                self.mo_df.loc[len(self.mo_df)] = mo_report
                self.mt_df.loc[len(self.mt_df)] = mt_report

                time.sleep(self.delay)

                # Calculate the time taken
                end_time = time.strftime("%Y-%m-%d %H:%M:%S")
                start_timestamp = time.mktime(time.strptime(start_time, "%Y-%m-%d %H:%M:%S"))
                end_timestamp = time.mktime(time.strptime(end_time, "%Y-%m-%d %H:%M:%S"))
                time_taken_seconds = end_timestamp - start_timestamp

                self.logger.log(f"Time taken for Iteration {i}: {time_taken_seconds} seconds", )

                self.end_barrier.wait()

                # progress update (GUI or headless log)
                if gui_progress is not None:
                    try:
                        gui_progress.update_progress()
                    except Exception:
                        pass
                else:
                    self.logger.log(f"Iteration {i} completed for {self.instance_id}")
                queue.put(int(self.mo_label[-1]))
                i += 1
            except Exception as e:
                if self.all_devices_connected():
                    self.logger.log("Error :", e)
                else:
                    device = f"MO-MT pair - {self.mo_label[-1]}"
                    self.logger.log(f"Device disconnected! in {device}")
                    # terminate ongoing calls
                    self.logger.log("Terminating ongoing calls")
                    _, devices_still_connected = count_connected_devices(self.logger)
                    if self.mo in devices_still_connected:
                        self.end_call(self.mo)
                    if self.mt in devices_still_connected:
                        self.end_call(self.mt)
                    # device connection error
                    while True:
                        self.logger.log("UI Warning: Device Not Found!")
                        reconnect_status = reconnect(self.home, device, 20)
                        if reconnect_status and self.all_devices_connected():
                            self.logger.log("Device reconnected")
                            break

        # calculate pass-fail %
        mo_df_final = stats(self.mo_df, self.logger)
        mt_df_final = stats(self.mt_df, self.logger)

        # save the DataFrames as .csf files
        mo_df_final.to_csv(self.mo_file_path, index=False)
        mt_df_final.to_csv(self.mt_file_path, index=False)


def run_automation(config: dict):
    """
    Main CAT-A execution entry point.
    
    Args:
        config (dict): Test configuration containing:
            - home: tkinter window (for UI updates)
            - all_device_info: dict of device credentials (MO1, MT1, etc.)
            - phone_numbers: list of phone numbers for each pair
            - pair_widgets: list of tkinter frames for progress display
            - test_type: 'Short calls' or 'Long calls'
            - iterations: number of iterations
            - call_duration: duration in seconds
            - call_delay: delay between calls in seconds
            - device_count: total number of devices
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print("Running CAT-A backend logic with config...")
        
        home = config.get('home')
        all_device_info = config.get('all_device_info', {})
        phone_numbers = config.get('phone_numbers', [])
        pair_widgets = config.get('pair_widgets', [])
        test_type = config.get('test_type', 'Short calls')
        iterations = config.get('iterations', 1)
        call_duration = config.get('call_duration', 30)
        call_delay = config.get('call_delay', 5)
        device_count = config.get('device_count', 0)
        simulate = False

        print("DEBUG simulate =", simulate)
        print("DEBUG device_count =", device_count)
        print("DEBUG all_device_info =", bool(all_device_info))


        # If simulate mode requested, perform a dry-run that generates sample reports
        if simulate:
            try:
                create_folders()
            except Exception:
                pass
            reports_dir = get_latest_dir(os.path.join(get_parent_dir(), 'reports'))
            if reports_dir is None:
                reports_dir = os.path.join(get_parent_dir(), 'reports')
                os.makedirs(reports_dir, exist_ok=True)

            num_pairs = max(1, device_count // 2) if device_count else 1
            print(f"SIMULATION: creating sample reports for {num_pairs} pair(s) in {reports_dir}")
            for idx in range(1, num_pairs + 1):
                # create a simple DataFrame matching COLUMNS with `iterations` rows
                rows = []
                for itr in range(1, max(1, iterations) + 1):
                    status = 'PASS' if (itr % 2 == 1) else 'FAILED'
                    row = [itr, datetime.now().date(), '00:00:00', '00:00:01', 1, status, None]
                    # pad the rest of columns with empty or NA
                    if len(row) < len(COLUMNS):
                        row += ['NA'] * (len(COLUMNS) - len(row))
                    rows.append(row)
                df = pd.DataFrame(rows, columns=COLUMNS)
                fname = os.path.join(reports_dir, f"SIM_MO{idx}-MO{idx}.csv")
                df.to_csv(fname, index=False)
                print(f"SIMULATION: wrote {fname}")

            print("SIMULATION: run_automation completed")
            return True
        print("Auto-detecting devices via ADB...")


        # If frontend didn't provide device info, attempt to auto-detect connected devices
        if (not all_device_info) or (device_count == 0):
            # Ensure required folders exist for logging/reports
            try:
                create_folders()
            except Exception:
                pass
            logger = CustomLogger("backend_auto_detect")
            logger.log("No device info provided by frontend — attempting to auto-detect connected devices.")
            
            cnt, devices = count_connected_devices(logger)
            
            if cnt is None or cnt < 2:
                logger.log("Not enough devices connected to run CAT-A (need at least 2).")
                return False

            # Pair devices sequentially (MO1->devices[0], MT1->devices[1], MO2->devices[2], ...)
            all_device_info = {}
            phone_numbers = []
            for i in range(0, len(devices) - (len(devices) % 2), 2):
                mo_udid = devices[i]
                mt_udid = devices[i + 1]
                pair_index = (i // 2) + 1
                # Default Sim preference to 0
                all_device_info[f'MO{pair_index}'] = {
                    'udid': mo_udid,
                    'Sim_Preference': 0,
                    'device_name': get_device_name(mo_udid, logger),
                    'android_version': get_android_version(mo_udid, logger)
                }
                all_device_info[f'MT{pair_index}'] = {
                    'udid': mt_udid,
                    'Sim_Preference': 0,
                    'device_name': get_device_name(mt_udid, logger),
                    'android_version': get_android_version(mt_udid, logger)
                }
                phone_numbers.append("")

            pair_widgets = []
            device_count = len(devices)
        
        # Create threading barriers for synchronization
        num_pairs = max(1, device_count // 2)
        queue_list = []
        dial_barrier = threading.Barrier(num_pairs)
        rcv_barrier = threading.Barrier(num_pairs)
        end_barrier = threading.Barrier(num_pairs)
        barriers = [dial_barrier, rcv_barrier, end_barrier]
        
        # Create CallTester instances for each MO-MT pair
        tests = []
        for idx in range(1, num_pairs + 1):
            test = CallTester(
                home=home,
                cred_mo=all_device_info.get(f'MO{idx}', {}),
                cred_mt=all_device_info.get(f'MT{idx}', {}),
                test_type=test_type,
                iterations=iterations,
                call_duration=call_duration,
                call_delay=call_delay,
                ph_no=phone_numbers[idx - 1] if idx - 1 < len(phone_numbers) else "",
                frame=pair_widgets[idx - 1] if idx - 1 < len(pair_widgets) else None,
                mo_label=f'MO{idx}',
                mt_label=f'MT{idx}',
                barriers=barriers,
                no_of_devices=device_count
            )
            tests.append(test)
        
        # Run tests in parallel threads
        queue = Queue()
        threads = []
        for test in tests:
            thread = threading.Thread(target=run_single_test, args=(test, queue))
            threads.append(thread)
            thread.start()
        
        print("CAT-A backend automation completed successfully")
        
        
    except Exception as e:
        print(f"Error in run_automation: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    if home:
        try:
            home.after(0, lambda: print("CAT-A backend threads started"))
        except Exception:
            pass



def run_single_test(test: CallTester, queue):
    test.run_test(queue)
    print(f"🚀 Starting CallTester for {test.mo_label} → {test.mt_label}")



