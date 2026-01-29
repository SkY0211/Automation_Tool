import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import time
import os
import subprocess
import sys
import threading
import time
import tkinter as tk 
from tkinter.font import Font
import tkinter.ttk as ttk
from tkinter import PhotoImage 
import re
from typing import List, Dict
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import seaborn as sns
from frontend.utils import play_alert_sound 
from backend.cat_a_wrapper import run_cat_a_tool
from backend.cat_a_tool.logger import CustomLogger
from frontend.data.constants import *
from queue import Queue, Empty
import queue
import threading
import queue
import time
import threading
from frontend.data.constants import *
import time


from backend.cat_a_wrapper import run_cat_a_tool
  
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMainWindow, QPushButton, QLabel,
    QVBoxLayout, QHBoxLayout, QGridLayout, QSizePolicy, 
    QDialog, QTextEdit, QSpacerItem
)
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import QStackedLayout, QComboBox
from PyQt6.QtWidgets import (
    QStackedLayout,
    QComboBox,
    QGroupBox,
    QFormLayout,
    QSpinBox,
    QProgressBar,
    QLineEdit,
)


"""
Automation Tool - Integration Dashboard (Desktop)
Single-file PyQt6 application.

Run:
    python automation_desktop.py
"""

# ------------------------------------------------
# Styling (QSS)
# ------------------------------------------------

APP_STYLES = """
QMainWindow, QWidget {
  background: #ffffff;
  color: #1f2937;
  font-family: "Segoe UI", Roboto, Arial, sans-serif;
}

/* Header */
#header {
  background: #ffffff;
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
}

/* Title */
#titleLabel {
  font-weight: 700;
  font-size: 20px;
  color: #111827;
}

/* Subtitle */
#subtitleLabel {
  color: #4b5563;
  font-size: 14px;
}

/* Cards */
.CardButton {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 18px;
  min-height: 120px;
  max-height: 150px;
}

.CardButton:hover {
  border: 1px solid #2563eb;
  background: #f9fafb;
}

/* Footer */
#footerLabel {
  color: #6b7280;
  font-size: 12px;
}

/* Back button */
QPushButton#backBtn {
  color: #2563eb;
  border: 1px solid #2563eb;
  border-radius: 8px;
  padding: 8px 12px;
  background: transparent;
}
"""

# ------------------------------------------------
# Placeholder Dialog
# ------------------------------------------------

class PlaceholderDialog(QDialog):
    def __init__(self, parent, title, description):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(480, 300)

        layout = QVBoxLayout(self)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(title_label)

        desc = QTextEdit()
        desc.setReadOnly(True)
        desc.setText(description)
        layout.addWidget(desc)

        back_btn = QPushButton("← Back to Dashboard")
        back_btn.setObjectName("backBtn")
        back_btn.clicked.connect(self.close)
        layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignRight)

# ------------------------------------------------
# CAT-A Landing Page (Step-by-step flow)
# ------------------------------------------------

class CATAWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CAT-A — Calling Automation Tool")
        self.setMinimumSize(1000, 600)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # ---------- HEADER ----------
        header = QLabel("Calling Automation Tool (Android)")
        header.setStyleSheet(
            "background:#4ec9a6; color:#5b1365; font-size:26px; "
            "font-weight:700; padding:16px;"
        )
        main_layout.addWidget(header)

        # ---------- STACK ----------
        self.stack = QStackedLayout()
        main_layout.addLayout(self.stack)

        self.stack.addWidget(self.step_1())  # index 0
        self.stack.addWidget(self.step_2())  # index 1
        self.stack.addWidget(self.step_3())  # index 2

    def step_1(self):
        w = QWidget()
        layout = QVBoxLayout(w)

        title = QLabel("CAT-A — Calling Automation Tool")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))

        self.status = QLabel("Status: Idle")
        self.status.setStyleSheet("color: gray;")

        start_btn = QPushButton("Start CAT-A Test")
        start_btn.setFixedWidth(220)

        def start_backend():
            self.status.setText("Status: Running...")
            self.status.setStyleSheet("color: blue;")

            def worker():
                try:
                    print("🔥 REAL CAT-A BACKEND STARTED 🔥")

                    result = run_cat_a_tool({
                        "simulate": False,
                        "device_count": 0,  # auto-detect ADB devices
                    })

                    QTimer.singleShot(0, lambda: (
                        self.status.setText("Status: Completed"),
                        self.status.setStyleSheet("color: green;")
                    ))

                    print("Backend result:", result)

                except Exception as e:
                    QTimer.singleShot(0, lambda: (
                        self.status.setText("Status: Failed"),
                        self.status.setStyleSheet("color: red;")
                    ))
                    print("CAT-A error:", e)

            threading.Thread(target=worker, daemon=True).start()

        start_btn.clicked.connect(start_backend)

        layout.addWidget(title)
        layout.addWidget(start_btn)
        layout.addWidget(self.status)
        layout.addStretch()

        return w


    def step_2(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("CAT-A Step 2 (Placeholder)"))
        return w

    def step_3(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel("CAT-A Step 3 (Placeholder)"))
        return w

class CATAWorker(QThread):
    status = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        self.status.emit("Running CAT-A backend...")
        try:
            result = run_cat_a_tool(self.config)
            self.finished.emit(result)
        except Exception as e:
            print("CAT-A ERROR:", e)
            self.finished.emit(False)


class ReconnectWindow(tk.Toplevel):
    def __init__(self, home, device, *args, **kwargs):
        super().__init__(home, *args, **kwargs)
        self.overrideredirect(True)  # Remove the title bar
        # Get the screen width and height
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Calculate the x and y coordinates to center the window
        x = (screen_width - 500) // 2
        y = (screen_height - 300) // 2

        self.geometry(f'550x250+{x}+{y}')
        self.configure(bg=LIGHT_RED)
        self.title("Device Connection Error!")

        FONT = Font(family="Georgia", size=14, weight="bold")
        FONT2 = Font(family="Georgia", size=12, weight="bold")

        text1 = f"Device Disconnected!\n\nPlease check the USB connection of {device}. "
        text2 = "Make sure all devices are properly connected \nbefore clicking the Resume button."

        tk.Label(self, text=text1, font=FONT, fg=RED, bg=LIGHT_RED).pack(pady=10)
        tk.Label(self, text=text2, font=FONT2, fg=BLACK, bg=LIGHT_RED).pack(pady=10)

        self.resume_clicked = False

        resume_button = tk.Button(self, text="Resume", command=self.resume, fg=BLACK, bg=BLUE, font=FONT2)
        resume_button.pack(pady=20)

        play_alert_sound()

        self.transient(None)  # Not a child of the Home window
        self.wm_attributes("-topmost", 1)  # Keep it always on top

    def resume(self):
        self.resume_clicked = True
        self.destroy()


def reconnect(home, device, timeout=15):
    reconnect_window = ReconnectWindow(home, device)
    # Wait for the reconnect window to be closed or timeout to occur
    end_time = time.time() + timeout
    while not reconnect_window.resume_clicked and time.time() < end_time:
        home.update()  # Process events to keep the UI responsive
        time.sleep(0.1)  # Small delay to avoid busy-waiting
    reconnect_window.destroy()
    return reconnect_window.resume_clicked


class MainPage(tk.Tk):
    def __init__(self):
        super().__init__()

        # Variables to store test credentials
        self.content_frame = None
        self.test_type = None
        self.test_type_var = None
        self.canvas = None
        self.scroll_frame = None
        self.buttons_frame = None
        self.user_input_frame = None
        self.input_frame = None
        self.start_time = None
        self.start_test_button = None
        self.reset_button = None
        self.next_button = None
        self.retest_button = None
        self.device_count: int = 0
        self.iterations: int = 0
        self.call_duration: int = 0
        self.call_delay: int = 0
        self.udids: List[str] = []
        self.all_device_info: Dict[str, str] = {}
        self.phone_numbers = []
        self.pair_widgets = []  # To store widgets for each pair of devices
        self.progress_bars = []
        # Get the path of the script and the directory containing the script
        script_path = os.path.abspath(__file__)
        script_directory = os.path.dirname(script_path)

        # Construct the path to the image using the script_directory
        image_path = os.path.join(script_directory, "..", "data", "logo.png")
        self.logo_image = PhotoImage(file=image_path)

        # self.configure(bg=WHITE)
        self.title("Call Automation Tool")
        self.state('zoomed')  # Open the window in full-screen mode
        self.protocol("WM_DELETE_WINDOW", self.on_close)  # Bind custom closing action
        # logo_label = tk.Label(self, image=self.logo_image)
        # logo_label.pack(anchor="ne", padx=10, pady=10)
        self.heading_font = Font(family="Helvetica", size=18, weight="bold")  # Customize the font here
        self.heading_font2 = Font(family="Cooper Black", size=30, weight="bold")
        self.body_font = Font(family="Georgia", size=12)
        self.body_font2 = Font(family="Georgia", size=14, weight="bold")
        self.button_font = Font(family="Ariel", size=12, weight="bold")

        self.num_devices_entry = None
        self.call_delay_entry = None
        self.call_duration_entry = None
        self.num_iterations_entry = None
        self.current_device = None

        # Animation of the welcome message
        welcome_frame = tk.Frame(self, bg=SPRING_GREEN, height=1, relief='raised', bd=3)
        welcome_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
        welcome_label = tk.Label(welcome_frame, text="", font=self.heading_font2, bg=SPRING_GREEN, fg=VIOLET)
        welcome_label.grid(row=1, column=0, sticky='w', padx=(5, 0),
                           pady=(20, 0))  # pack(side=tk.LEFT, expand=True, pady=10)
        self.animate_text(welcome_label, "Calling Automation Tool (Android)")
        logo_label = tk.Label(welcome_frame, image=self.logo_image, bg=SPRING_GREEN)
        logo_label.grid(row=1, column=1, sticky="e", padx=(0, 5), pady=(10, 0))  # pack(anchor="ne", padx=10, pady=10)
        version_label = tk.Label(welcome_frame, text=f"Version -> {VERSION}", font=self.body_font2, bg=SPRING_GREEN)
        version_label.grid(row=2, column=1, sticky='e', padx=(0, 5))
        # Configure column weights to make the logo_label move to the extreme right
        welcome_frame.grid_columnconfigure(0, weight=1)  # welcome_label column
        welcome_frame.grid_columnconfigure(1, weight=1)  # logo_label column

        # Create required folders
        create_folders()
        self.logger = CustomLogger("frontend")
        self.home_window()
        self.logger.log(f"Application Started || Version - {VERSION}")
        self.create_scrollable_frame()

    def create_scrollable_frame(self):
        if self.scroll_frame is not None:
            self.scroll_frame.destroy()  # Destroy the previous scroll frame if it exists

        # Scrollable frame for all content
        self.scroll_frame = tk.Frame(self)
        self.scroll_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.scroll_frame)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(self.scroll_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.configure(yscrollcommand=scrollbar.set)

        # Bind the on_canvas_configure method to the <Configure> event of content_frame
        self.content_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.content_frame, anchor=tk.NW)
        self.content_frame.bind("<Configure>", self.on_canvas_configure)

    def home_window(self):

        # Frame for the input box and "Next" button
        self.input_frame = tk.Frame(self)
        self.input_frame.pack(pady=10)

        # test type: (i) Short Calls, (ii) Long Calls
        # Display test type options
        test_type_label = tk.Label(self.input_frame, text="Select Test Type:", font=self.body_font2)
        test_type_label.pack(side=tk.LEFT, padx=10)

        self.test_type_var = tk.StringVar(self)
        self.test_type_var.set("None")  # Default value

        test_type_options = ["None", "Short calls", "Long calls"]
        test_type_menu = ttk.OptionMenu(self.input_frame, self.test_type_var, *test_type_options)
        test_type_menu.pack(side=tk.LEFT, padx=(10, 80))

        # User input label and entry widget
        input_label = tk.Label(self.input_frame, text="How many devices do you want to test?", font=self.body_font2)
        input_label.pack(side=tk.LEFT)

        self.num_devices_entry = tk.Entry(self.input_frame, font=self.body_font)
        self.num_devices_entry.pack(side=tk.LEFT, padx=10)

        # Next button
        self.next_button = tk.Button(self.input_frame, text="Next", font=self.button_font,
                                     command=self.save_num_devices,
                                     bg=BLUE,
                                     fg=WHITE)
        self.next_button.pack(side=tk.LEFT, padx=10)

    def animate_text(self, label, text):
        for char in text:
            label.config(text=label.cget("text") + char)
            self.update()
            time.sleep(0.05)

    def save_num_devices(self):
        self.logger.log("Next Button clicked")
        if not self.test_type_var.get() or self.test_type_var.get() == "None":
            messagebox.showerror("Invalid Input", "Please select a 'Test type' from the given options.")
            self.next_button.config(state=tk.NORMAL)
            return
        else:
            self.test_type = self.test_type_var.get()
        
        num_devices = self.num_devices_entry.get()

        try:
            num_devices = int(num_devices)
            if num_devices < 1 or num_devices % 2 != 0:
                raise ValueError("Please enter a valid number of devices (Non-zero Even Integer).")
        except ValueError as e:
            # Display an error message for invalid input
            messagebox.showerror("Invalid Input", str(e))
            return

        # Save the input in the data module
        self.device_count = num_devices

        # Create sections for each pair of devices
        self.create_pair_sections(num_devices)

    def create_pair_sections(self, num_devices):
        self.next_button.configure(state=tk.DISABLED)
        # Clear existing pair sections
        for widget in self.pair_widgets:
            widget.destroy()
        self.pair_widgets.clear()

        for i in range(1, num_devices // 2 + 1):
            self.logger.log(f"Creating Pair-frame {i}")
            pair_frame = tk.Frame(self.content_frame)
            pair_frame.pack(pady=20)
            self.pair_widgets.append(pair_frame)
            # show the MO-MT pair count
            pair_label = tk.Label(pair_frame, text=f"MO-MT Pair {i}:", font=self.body_font2)
            pair_label.grid(row=0, column=0, padx=20, pady=5)

            # MO configuration
            self.current_device = f"MO{i}"
            # self.config_mo(pair_frame, i)
            config_mo_button = tk.Button(pair_frame, text=f"Configuring MO{i}...", font=self.body_font,
                                         bg=BLUE, fg=WHITE)
            config_mo_button.grid(row=0, column=1, padx=20, pady=5)

            # open the config device window
            pair_frame.update()
            self.wait(1)
            self.config_devices()

            # change the button color and text
            config_mo_button.destroy()
            mo_status = tk.Button(pair_frame, text=f"MO{i} Connected", font=self.button_font, bg=GREEN, fg=WHITE)
            mo_status.grid(row=0, column=1, padx=20, pady=5)

            # MT configuration
            self.current_device = f"MT{i}"
            config_mt_button = tk.Button(pair_frame, text=f"Configuring MT{i}...", font=self.body_font,
                                         bg=BLUE, fg=WHITE)
            config_mt_button.grid(row=0, column=2, padx=20, pady=5)

            # open the config device window
            pair_frame.update()
            self.wait(1)
            self.config_devices()

            # change the button color and text
            config_mt_button.destroy()
            mt_status = tk.Button(pair_frame, text=f"MT{i} Connected", font=self.button_font,
                                  bg=GREEN, fg=WHITE)
            mt_status.grid(row=0, column=2, padx=20, pady=5)

            # Input box for MT ph number
            self.wait(1)
            self.create_phone_number_input(pair_frame)

        # Frame for user inputs and buttons
        self.user_input_frame = tk.Frame(self)
        self.user_input_frame.pack(pady=15)

        # User input labels and entry widgets
        tk.Label(self.user_input_frame, text="No of Iterations:", font=self.button_font).pack(side=tk.LEFT, padx=10)
        self.num_iterations_entry = tk.Entry(self.user_input_frame, font=("Helvetica", 16))
        self.num_iterations_entry.pack(side=tk.LEFT, padx=10)

        if self.test_type == 'Short calls':
            call_duration_label = "Call Duration (in sec):"
        else:
            call_duration_label = "Call Duration (in min):"

        tk.Label(self.user_input_frame, text=call_duration_label, font=self.button_font).pack(side=tk.LEFT,
                                                                                                    padx=10)
        self.call_duration_entry = tk.Entry(self.user_input_frame, font=("Helvetica", 16))
        self.call_duration_entry.pack(side=tk.LEFT, padx=10)

        tk.Label(self.user_input_frame, text="Call Delay (in sec):", font=self.button_font).pack(side=tk.LEFT, padx=10)
        self.call_delay_entry = tk.Entry(self.user_input_frame, font=("Helvetica", 16))
        self.call_delay_entry.pack(side=tk.LEFT, padx=10)

        # Add "Reset" and "Start Test" buttons at the bottom of the page
        self.buttons_frame = tk.Frame(self)
        self.buttons_frame.pack(side=tk.BOTTOM, pady=10)

        self.reset_button = tk.Button(self.buttons_frame, text="Reset", font=self.button_font, command=self.refresh_app,
                                      bg=ORANGE, fg=WHITE)
        self.reset_button.pack(side=tk.LEFT, padx=30, pady=10)

        self.start_test_button = tk.Button(self.buttons_frame, text="Start Test", font=self.button_font,
                                           command=self.start_test, bg=GREEN, fg=WHITE)
        self.start_test_button.pack(side=tk.RIGHT, padx=30, pady=10)

        self.retest_button = tk.Button(self.buttons_frame, text="Retest", font=self.button_font,
                                       command=self.retest, bg=BLUE, fg=WHITE, state=tk.DISABLED)
        self.retest_button.pack(side=tk.RIGHT, padx=30, pady=10)

    def config_devices(self, ):
        self.logger.log("Configuring Devices...")
        # Create a new Toplevel window
        config_window = tk.Toplevel(self)
        config_window.title("Configure Devices")
        config_window.geometry("500x400+100+100")
        config_window.transient(self)

        # Function to fetch device info using ADB command
        def fetch_current_device_info():
            self.logger.log("Collecting Device Info...")
            device_info = {}
            try:
                # Collect udid, device name and Android Version for current device
                completed_process = subprocess.run(["adb", "devices"], capture_output=True, text=True)
                output = completed_process.stdout
                lines = re.findall(r"(\S+)\s+device", output)[1:]
                if len(self.udids):
                    line = next((line for line in lines if not any(udid in line for udid in self.udids)),
                                "NotFound")
                else:
                    line = lines[0]
            except subprocess.CalledProcessError as e:
                self.logger.log("adb command failure: ", str(e))
                line = "NotFound"
            except Exception as e:
                self.logger.log("An error occurred: ", str(e))
                line = "NotFound"

            udid = line.split()[0]
            self.udids.append(udid)
            device_name = get_device_name(udid, self.logger)
            android_version = get_android_version(udid, self.logger)
            device_info["udid"] = udid
            device_info["android_version"] = android_version
            device_info["device_name"] = device_name

            return device_info

        # Function to show device info and get confirmation
        def show_device_info():
            proceed_button.configure(state=tk.DISABLED)
            device_info = fetch_current_device_info()
            # if device Not Found
            if device_info["udid"] == "NotFound":
                messagebox.showerror("No Device Found", "Connect the device properly and try again")
                proceed_button.configure(state=tk.NORMAL)
            else:
                # Create a label to display device info
                info_label = tk.Label(config_window, text="Device Info:", font=self.body_font2)
                info_label.pack(pady=10)

                for key, value in device_info.items():
                    info_text = f"{key}: {value}"
                    tk.Label(config_window, text=info_text, font=self.body_font).pack()

                # Create a label for Sim preference options
                sim_pref_label = tk.Label(config_window, text="SIM preference:", font=self.body_font2)
                sim_pref_label.pack(pady=10)

                # Sim preference options
                sim_pref_var = tk.IntVar(value=None)
                sim_text_options = ["SIM1", "SIM2"]
                for option in sim_text_options:
                    tk.Radiobutton(config_window, text=option, font=self.body_font, variable=sim_pref_var,
                                   value=sim_text_options.index(option)).pack()

                self.wait_variable(sim_pref_var)

                # Create a confirmation button
                confirm_button = tk.Button(config_window, text="Confirm", font=self.button_font,
                                           command=lambda: save_device_info(device_info, sim_pref_var.get()),
                                           bg=GREEN, fg=WHITE,
                                           state=tk.NORMAL)
                confirm_button.pack(pady=10)

        # Function to save device info in a dictionary and destroy the window
        def save_device_info(device_info, sim_pref):
            self.logger.log("Saving device info...")
            device_info["Sim_Preference"] = sim_pref
            # Here, you can save the device_info dictionary or perform any other actions needed
            self.all_device_info[self.current_device] = device_info
            config_window.destroy()

        # self.wait(3)
        # Show instructions and create Proceed button
        tk.Label(config_window, text=f"Connect the {self.current_device} and click 'Proceed' button",
                 font=self.body_font).pack(padx=10, pady=10)
        proceed_button = tk.Button(config_window, text="Proceed", font=self.button_font,
                                   command=show_device_info, bg=ORANGE, fg=WHITE)
        proceed_button.pack(pady=10, padx=10)
        self.wait_window(config_window)

    def create_phone_number_input(self, pair_frame, ):
        self.logger.log("Collecting MT phone number")

        def save_phone_number():
            phone_number = phone_number_entry.get()
            # if verify_phone_number(phone_number):
            self.phone_numbers.append(phone_number)
            phone_number_label.destroy()
            phone_number_entry.destroy()
            save_button.destroy()
            # else:
            #     messagebox.showerror("Invalid Number", "Please enter a valid 10-digit phone number.")
            #     phone_number_entry.delete(0, tk.END)

        phone_number_label = tk.Label(pair_frame, text="Enter MT Phone Number:", font=self.body_font)
        phone_number_label.grid(row=0, column=3, padx=10, pady=5)
        phone_number_entry = tk.Entry(pair_frame, font=self.body_font, )
        phone_number_entry.grid(row=0, column=4, padx=10, pady=5)
        save_button = tk.Button(pair_frame, text="Save", font=self.button_font, command=save_phone_number, bg=BLUE,
                                fg=WHITE)
        save_button.grid(row=0, column=5, padx=10, pady=5)
        self.wait_window(save_button)

    def show_test_report(self, ):
        self.logger.log("Displaying Latest Test Report")
        latest_dir = get_latest_dir(os.path.join(get_parent_dir(), 'reports'))
        test_report = tk.Toplevel(self)
        test_report.wm_attributes("-topmost", 1)  # Keep the window on top

        test_report.title("Test Report Summary")
        test_report.geometry("1200x400+50+50")

        # Get the list of CSV files in the latest directory
        csv_list = os.listdir(latest_dir)
        x = int(len(csv_list) / 2)

        # Create a figure with subplots for each dataframe
        figure = Figure(figsize=(15, 300 / 80), dpi=80)

        colors = ['#4CAF50', '#F44336', '#FF9800']

        for i, csv_file in enumerate(csv_list[:x]):
            # Read the CSV file
            df = pd.read_csv(os.path.join(latest_dir, csv_file))

            # Calculate pass/fail/call drop counts
            pass_count = df['Status'].eq('PASS').sum()
            fail_count = df['Status'].eq('FAILED').sum()
            call_drop_count = df['Status'].eq('CALL_DROPPED').sum()

            # Create a subplot for the current dataframe
            subplot = figure.add_subplot(1, 3, i + 1)

            # Plot pass/fail/call drop counts as a bar plot using Seaborn
            data = pd.DataFrame({'Count': [pass_count, fail_count, call_drop_count],
                                 'Status': ['Pass', 'Fail', 'Call Drop']})
            sns.barplot(x='Count', y='Status', data=data, ax=subplot, errorbar=None, palette=colors)
            subplot.set_title(csv_file.split('.')[0], fontweight='bold', fontsize=12, pad=10)
            subplot.set_xlabel('')
            subplot.set_ylabel('')

            # Remove y-axis scale
            subplot.get_xaxis().set_visible(False)

            # Adjust the bar width
            for patch in subplot.patches:
                width = patch.get_width()
                patch.set_width(width * 0.9)

                # Add count labels to the bars
                x = patch.get_x() + width / 2
                y = patch.get_y() + patch.get_height() / 2
                subplot.text(x, y, int(width), ha='center', va='center', color=WHITE, fontweight='bold')

        # Adjust spacing between subplots
        figure.tight_layout()

        # Create canvas for displaying the figure
        canvas = FigureCanvasTkAgg(figure, master=test_report)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        close_button_frame = tk.Frame(test_report)
        close_button_frame.pack(side=tk.BOTTOM, pady=10)
        close_button = tk.Button(close_button_frame, text="Close", command=test_report.destroy, font=self.button_font,
                                 bg=RED, fg=WHITE)
        close_button.pack(side=tk.BOTTOM, pady=10)

    def device_setup_reminder(self):
        def reminder_confirmation():
            reminder.destroy()
            self.start_test_button.configure(state=tk.DISABLED)
            self.start_calling()

        self.logger.log("Device setup related reminder shown")
        checklist_items = [
            "Configure the default calling SIM if any MO device has two SIM cards.",
            "Location service in all devices must be enabled.",
            "In USB preferences, 'Photo and Video transfer mode' must be selected.",
            "In developer options, 'Stay awake' mode must be enabled."
        ]
        reminder = tk.Toplevel(self)
        # reminder.transient(self)  # Set the main window as the transient parent
        reminder.wm_attributes("-topmost", 1)  # Keep the window on top
        reminder.overrideredirect(True)

        # Get the screen width and height
        screen_width = reminder.winfo_screenwidth()
        screen_height = reminder.winfo_screenheight()

        # Calculate the x and y coordinates to center the window
        x = (screen_width - 850) // 2
        y = (screen_height - 330) // 2

        reminder.geometry(f'850x330+{x}+{y}')
        reminder.configure(bg=LIGHT_RED)

        tk.Label(reminder, text="Please Recheck and Confirm", bg=LIGHT_RED, fg=RED, font=self.body_font2).pack(pady=20,
                                                                                                               padx=10)

        for i, item in enumerate(checklist_items, start=1):
            tk.Label(reminder, text=f"{i}. {item}", font=self.body_font2, bg=LIGHT_RED).pack(padx=10, pady=10)

        tk.Button(reminder, text="Confirm", command=reminder_confirmation, bg=GREEN, fg=WHITE,
                  font=self.button_font).pack(pady=10, side=tk.BOTTOM)

    def start_test(self, ):
        self.logger.log("Start button clicked")
        if self.validate_user_inputs():
            self.device_setup_reminder()

    def start_calling(self):
        self.reset_button.configure(state=tk.DISABLED)
        self.logger.log("User Inputs :")
        self.logger.log(f"Test type -> {self.test_type}\n"
                        f"No of devices -> {self.device_count}\n"
                        f"Iterations -> {self.iterations}\n"
                        f"Call Duration -> {self.call_duration}\n"
                        f"Call Delay -> {self.call_delay}\n"
                        f"Device Info -> {self.all_device_info}")

        self.logger.log("----------------Starting Call test-------------")
        self.start_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.logger.log(f"Starting time : {self.start_time}")

        # Build configuration dict for backend
        config = {
            "source": "CAT-A UI",
            "simulate": False,
            "device_count": 2,          # minimum 2 devices
            "iterations": 5,
            "call_duration": 30,
            "call_delay": 5
    }



        # Call backend to run the actual automation
        def run_backend():
            try:
                result = run_cat_a_tool(config)
                self.logger.log("Backend automation completed")
                
                # Calculate the time taken
                end = time.strftime("%Y-%m-%d %H:%M:%S")
                self.logger.log(f"Ending time: {end}")
                start_timestamp = time.mktime(time.strptime(self.start_time, "%Y-%m-%d %H:%M:%S"))
                end_timestamp = time.mktime(time.strptime(end, "%Y-%m-%d %H:%M:%S"))
                duration = round((end_timestamp - start_timestamp) / 60, 3)
                self.logger.log(f"Duration = {duration} minutes")
                self.logger.log("-------------Call Test Completed!--------------")
                
                self.show_test_report()
                self.start_test_button.destroy()
                self.retest_button.configure(state=tk.NORMAL)
                self.reset_button.configure(state=tk.NORMAL)
            except Exception as e:
                self.logger.log(f"Backend error: {e}")
                import traceback
                traceback.print_exc()
                self.reset_button.configure(state=tk.NORMAL)

        # Run backend in a separate thread so the UI remains responsive
        threading.Thread(target=run_backend, daemon=True).start()



    def on_canvas_configure(self, event):
        self.logger.log("Resting the Application")
        self.input_frame.destroy()
        self.buttons_frame.destroy()
        self.user_input_frame.destroy()
        self.scroll_frame.destroy()
        for widget in self.pair_widgets:
            widget.destroy()
        self.pair_widgets.clear()
        # Re initiate Variables to store test credentials
        self.content_frame = None
        self.test_type = None
        self.test_type_var = None
        self.canvas = None
        self.scroll_frame = None
        self.buttons_frame = None
        self.user_input_frame = None
        self.input_frame = None
        self.start_time = None
        self.start_test_button = None
        self.reset_button = None
        self.next_button = None
        self.retest_button = None
        self.device_count: int = 0
        self.iterations: int = 0
        self.call_duration: int = 0
        self.call_delay: int = 0
        self.udids: List[str] = []
        self.all_device_info: Dict[str, str] = {}
        self.phone_numbers = []
        self.progress_bars = []

        self.logger = None
        create_folders()
        self.logger = CustomLogger("frontend")
        self.logger.log("Application Re-initiated")
        self.home_window()
        self.create_scrollable_frame()

    def retest(self):
        if self.validate_user_inputs():
            create_folders()
            self.logger = None
            self.logger = CustomLogger("frontend")
            self.logger.log("Retest initiated...")
            self.retest_button.configure(state=tk.DISABLED)
            self.start_calling()

    def on_canvas_configure(self, event):
        # Update the canvas scrolling region when the content changes
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_close(self):
        # Customize the closing action here (e.g., save data, confirm exit, etc.)
        self.logger.log("Application terminated")
        self.destroy()

    def validate_user_inputs(self):
        # Get user input for the number of iterations, call duration, and call delay
        if self.validate_positive_integer(self.num_iterations_entry.get()) and \
                self.validate_positive_integer(self.call_duration_entry.get()) and \
                self.validate_positive_integer(self.call_delay_entry.get()):

            # All entries are valid positive integers greater than zero
            self.iterations = int(self.num_iterations_entry.get())
            call_duration_var = int(self.call_duration_entry.get())
            self.call_duration = call_duration_var if self.test_type == 'Short calls' else (call_duration_var * 60)
            self.call_delay = int(self.call_delay_entry.get())
            self.logger.log("All inputs are valid.")
            return True
        else:
            self.logger.log("Invalid inputs provided")
            # At least one entry is not a valid positive integer
            # Show an error message or handle the invalid input accordingly
            messagebox.showerror("Invalid Input", "Please enter valid positive integers greater than zero.")
            # Clear the input box with invalid input
            if not self.validate_positive_integer(self.num_iterations_entry.get()):
                self.num_iterations_entry.delete(0, tk.END)
            if not self.validate_positive_integer(self.call_duration_entry.get()):
                self.call_duration_entry.delete(0, tk.END)
            if not self.validate_positive_integer(self.call_delay_entry.get()):
                self.call_delay_entry.delete(0, tk.END)
            return False

    @staticmethod
    def wait(duration):
        for _ in range(duration):
            time.sleep(1)

    @staticmethod
    def validate_positive_integer(value):
        try:
            num = int(value)
            if num > 0:
                return True
            else:
                return False
        except ValueError:
            return False




class TestProgress:
    def __init__(self, pair_frame, iterations):
        self.pair_frame = pair_frame
        self.current_iteration = 0
        self.iterations = iterations
        self.body_font = Font(family="Georgia", size=12)
        # Clear the location where the progress label and progress bar will be shown
        for i in range(4, 6):
            child = self.pair_frame.grid_slaves(row=0, column=i)
            if isinstance(child, tk.Widget):
                child.destroy()

        self.progress_label = tk.Label(self.pair_frame, text="Test Started...", font=self.body_font)
        self.progress_label.grid(row=0, column=4, padx=10, pady=5)
        self.progress_bar = tk.ttk.Progressbar(self.pair_frame, orient=tk.HORIZONTAL, length=400, mode='determinate', maximum=self.iterations)
        self.progress_bar.grid(row=0, column=5, columnspan=2, padx=20, pady=5)
        # self.pair_frame.update()
        # self.pair_frame.update_idletasks()

    def update_progress(self,):
        self.current_iteration = self.current_iteration+1
        self.progress_bar['value'] = self.current_iteration
        self.progress_label.config(text=f'Iteration {self.current_iteration} of {self.iterations}')
        # self.pair_frame.update()
        # self.pair_frame.update_idletasks()


class OOSZoneWindow(tk.Toplevel):
    def __init__(self, home, oos_device, *args, **kwargs):
        super().__init__(home, *args, **kwargs)
        devices_name = '\n'.join(oos_device)
        self.overrideredirect(True)  # Remove the title bar
        # Get the screen width and height
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Calculate the x and y coordinates to center the window
        x = (screen_width - 500) // 2
        y = (screen_height - 300) // 2

        self.geometry(f'550x250+{x}+{y}')
        self.configure(bg=LIGHT_RED)
        self.title("OOS Zone Error!")

        FONT = Font(family="Georgia", size=14, weight="bold")
        FONT2 = Font(family="Georgia", size=12, weight="bold")

        text1 = f"Device in OOS Zone"
        text2 = f"Following device(s) in OOS Zone:\n{devices_name}"
        text3 = "Will retry after 10 sec"

        tk.Label(self, text=text1, font=FONT, fg=RED, bg=LIGHT_RED).pack(pady=10)
        tk.Label(self, text=text2, font=FONT2, fg=BLACK, bg=LIGHT_RED).pack(pady=10)
        tk.Label(self, text=text3, font=FONT2, fg=BLACK, bg=LIGHT_RED).pack(pady=10)

        play_alert_sound(duration=500, times=1)

        self.transient(None)
        self.wm_attributes("-topmost", 1)

    # def resume(self):
    #     self.resume_clicked = True
    #     self.destroy()


def ooszone(home, oos_device):
    oos_window = OOSZoneWindow(home, oos_device)
    time.sleep(10)
    oos_window.destroy()


#   if __name__ == '__main__':
#   Create the main window
#   root = tk.Tk()
#   root.title("Main Window")
#   print(reconnect(root, "Device Name"))
#   root.destroy()
#   Run the main loop
# root.mainloop()

# ------------------------------------------------
# Card Builder
# ------------------------------------------------

def make_card(title, description, callback):
    btn = QPushButton()
    btn.setProperty("class", "CardButton")
    btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    btn.clicked.connect(callback)

    layout = QVBoxLayout(btn)
    layout.setSpacing(6)

    t = QLabel(title)
    t.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))

    d = QLabel(description)
    d.setWordWrap(True)
    d.setStyleSheet("color:#9aa3b2; font-size:13px;")

    layout.addWidget(t)
    layout.addWidget(d)

    return btn

# ------------------------------------------------
# CAT-F Landing Page (Step-by-step flow)
# ------------------------------------------------


    def start_test(self):
        # Minimal UI -> backend bridge. This calls a safe stub in backend.cat_a_tool.runner.
        from PyQt6.QtWidgets import QMessageBox
        try:
            from backend.cat_a_tool.runner import start_test_stub
            start_test_stub()
            QMessageBox.information(self, "CAT-A", "Backend runner started (stub).")
        except Exception as e:
            QMessageBox.critical(self, "CAT-A", f"Failed to start backend runner:\n{e}")

class CATFWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CAT-F — Calling Automation Tool")
        self.setMinimumSize(900, 520)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(16)

        # Header
        header = QLabel("Calling Automation Tool (Feature Phones)")
        header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        main_layout.addWidget(header)

        # Step container
        self.stack = QStackedLayout()
        main_layout.addLayout(self.stack)

        # Steps
        self.stack.addWidget(self.step_country())                        # index 0
        self.stack.addWidget(self.step_device("Configure 1st Device", 2)) # index 1 → 2
        self.stack.addWidget(self.step_device("Configure 2nd Device", 3)) # index 2 → 3
        self.stack.addWidget(self.step_test_configuration())

    # ---------------- STEP 1 ----------------
    def step_country(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        label = QLabel("Select Country & Country Code")
        label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))

        self.country_combo = QComboBox()
        self.country_combo.addItems([
            "Select Country & Code",
            "India (+91)",
            "USA (+1)",
            "UK (+44)",
            "Germany (+49)"
        ])

        next_btn = QPushButton("Next")
        next_btn.setFixedWidth(120)
        next_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        layout.addWidget(label)
        layout.addWidget(self.country_combo)
        layout.addWidget(next_btn, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addStretch()

        return widget

    # ---------------- STEP 2 & 3 ----------------
    def step_device(self, title_text, next_index):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        title = QLabel(title_text)
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))

        info = QLabel(
            "Software Version: Not found\n"
            "IMEI: Not found\n"
            "Phone Number: Not found\n"
            "AT Port: COMxx"
        )
        info.setStyleSheet("color:#374151;")

        btn_next = QPushButton("Next")
        btn_next.setFixedWidth(140)
        btn_next.clicked.connect(
        lambda: self.stack.setCurrentIndex(next_index)
        )

        layout.addWidget(title)
        layout.addWidget(info)
        layout.addWidget(btn_next, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addStretch()

        return widget


    def step_test_configuration(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)


    # ---------- DEVICE SUMMARY ----------
        device_box = QGroupBox("Configured Devices")
        device_layout = QHBoxLayout(device_box)

        dev1 = QLabel(
            "<b>1st Device</b><br>"
            "Software Version: Not found<br>"
            "IMEI: Not found<br>"
            "Phone: +91xxxxxxxxxx<br>"
            "AT Port: COM11"
    )

        dev2 = QLabel(
            "<b>2nd Device</b><br>"
            "Software Version: 0.2408.11.01<br>"
            "IMEI: 3549xxxxxxxxxx<br>"
            "Phone: +9170xxxxxxxx<br>"
            "AT Port: COM14"
    )

        device_layout.addWidget(dev1)
        device_layout.addWidget(dev2)

    # ---------- TEST TYPE ----------
        test_type_box = QGroupBox("Select Test Type")
        test_type_layout = QHBoxLayout(test_type_box)

        call_length = QComboBox()
        call_length.addItems(["Short calls", "Long calls"])

        call_mode = QComboBox()
        call_mode.addItems(["MO calls", "MT calls", "MO-MT calls"])

        test_type_layout.addWidget(QLabel("Call Length:"))
        test_type_layout.addWidget(call_length)
        test_type_layout.addSpacing(20)
        test_type_layout.addWidget(QLabel("Call Mode:"))
        test_type_layout.addWidget(call_mode)

    # ---------- TEST PARAMETERS ----------
        params_box = QGroupBox("Test Parameters")
        params_layout = QFormLayout(params_box)

        iterations = QSpinBox()
        iterations.setRange(1, 10000)
        iterations.setValue(10)

        hh = QSpinBox(); hh.setRange(0, 23)
        mm = QSpinBox(); mm.setRange(0, 59)
        ss = QSpinBox(); ss.setRange(0, 59); ss.setValue(30)

        duration_layout = QHBoxLayout()
        duration_layout.addWidget(hh)
        duration_layout.addWidget(QLabel("hr"))
        duration_layout.addWidget(mm)
        duration_layout.addWidget(QLabel("min"))
        duration_layout.addWidget(ss)
        duration_layout.addWidget(QLabel("sec"))

        delay = QSpinBox()
        delay.setRange(0, 600)

        params_layout.addRow("No of Iterations:", iterations)
        params_layout.addRow("Call Duration:", duration_layout)
        params_layout.addRow("Call Delay (sec):", delay)

    # ---------- CONTROL BUTTONS ----------
        btn_layout = QHBoxLayout()

        for text, color in [
           ("Reset", "#f59e0b"),
           ("Start Test", "#22c55e"),
           ("Pause", "#fb923c"),
           ("Resume", "#4ade80"),
           ("End Test", "#ef4444"),
        ]:
           b = QPushButton(text)
           b.setStyleSheet(f"background:{color}; padding:8px;")
           btn_layout.addWidget(b)

    # ---------- ASSEMBLE ----------
        layout.addWidget(device_box)
        layout.addWidget(test_type_box)
        layout.addWidget(params_box)
        layout.addLayout(btn_layout)
        layout.addStretch()

        return widget

class TATWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TAT — Tput Automation Testing")
        self.setMinimumSize(1200, 700)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)

        self.stack = QStackedLayout()
        main_layout.addLayout(self.stack)

        self.stack.addWidget(self.step_credentials())   # index 0
        self.stack.addWidget(self.step_device_config()) # index 1
        self.stack.addWidget(self.step_speedtest())     # index 2

    # ---------------- STEP 1 ----------------
    def step_credentials(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        self.measured_by = QComboBox()
        self.measured_by.addItems(["iPerf3 apk binary", "SpeedtestApp"])

        proceed = QPushButton("Proceed")
        proceed.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        layout.addRow("Measured by:", self.measured_by)
        layout.addRow("Number of Devices:", QSpinBox())
        layout.addRow("Iterations:", QSpinBox())
        layout.addRow("Delay (sec):", QSpinBox())
        layout.addRow(proceed)

        return widget

    # ---------------- STEP 2 ----------------
    def step_device_config(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)

        layout.addWidget(QGroupBox("Device - 1"))
        layout.addWidget(QGroupBox("Device - 2"))
        layout.addWidget(QLabel("Preview / Logs"))

        next_btn = QPushButton("Next")
        next_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2))

        v = QVBoxLayout()
        v.addLayout(layout)
        v.addWidget(next_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        container = QWidget()
        container.setLayout(v)
        return container

    # ---------------- STEP 3 ----------------
    def step_speedtest(self):
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setSpacing(12)

        top_layout = QHBoxLayout()

        def device_panel(title):
            box = QGroupBox(title)
            grid = QGridLayout(box)
            grid.setSpacing(6)

            fields = [
                "UDID", "Device Name", "Android Version",
                "SIM Slot", "Operator",
                "VRT", "DRT",
                "PCI", "EARFCN",
                "Band", "Bandwidth",
                "rsrp", "rsrq", "rssi",
                "snr", "CQI"
            ]

            for i, field in enumerate(fields):
                label = QLabel(f"<b>{field}:</b> None")
                label.setStyleSheet(
                    "padding:4px; border:1px solid #d1d5db; border-radius:6px;"
                )
                grid.addWidget(label, i // 2, i % 2)

            return box

        dev1 = device_panel("Device - 1")
        dev2 = device_panel("Device - 2")

        black_panel = QLabel()
        black_panel.setMinimumSize(350, 350)
        black_panel.setStyleSheet("background:black; border-radius:6px;")

        top_layout.addWidget(dev1, 2)
        top_layout.addWidget(dev2, 2)
        top_layout.addWidget(black_panel, 3)

        progress_label = QLabel("Test Progress:  Click 'Start' button")
        progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        progress_bar = QProgressBar()
        progress_bar.setValue(0)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        buttons = [
            ("Reset", "#60a5fa"),
            ("Start", "#22c55e"),
            ("Pause", "#e11d48"),
            ("Resume", "#10b981"),
            ("Stop", "#fb7185"),
            ("Retest", "#9333ea"),
        ]

        for text, color in buttons:
            b = QPushButton(text)
            b.setStyleSheet(
                f"""
                QPushButton {{
                    background:{color};
                    color:white;
                    padding:10px;
                    font-weight:600;
                    border-radius:8px;
                }}
                """
            )
            btn_layout.addWidget(b)

        main_layout.addLayout(top_layout)
        main_layout.addWidget(progress_label)
        main_layout.addWidget(progress_bar)
        main_layout.addLayout(btn_layout)

        return widget




# ------------------------------------------------
# Main Window
# ------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Automation Tool – Integration Dashboard")
        self.setMinimumSize(900, 520)

        # -------- CENTRAL + MAIN LAYOUT --------
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # ---------------- HEADER ----------------
        header = QWidget()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_box = QVBoxLayout()

        title = QLabel("Automation Tool — Integration Dashboard")
        title.setObjectName("titleLabel")

        subtitle = QLabel(
            "Choose a category to explore integration features and automation workflows."
        )
        subtitle.setObjectName("subtitleLabel")
        subtitle.setWordWrap(True)

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header_layout.addLayout(title_box)
        header_layout.addStretch()

        # ---------------- LOGO ----------------
        logo = QLabel()
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(BASE_DIR, "images", "logo.png")

        pix = QPixmap(logo_path)
        if not pix.isNull():
            pix = pix.scaled(
                490, 170,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo.setPixmap(pix)
            logo.setFixedSize(pix.size())
        else:
            logo.setText("Company")

        header_layout.addWidget(
            logo,
            alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        main_layout.addWidget(header)

        # -------- STACK (CENTER AREA) --------
        self.page_stack = QStackedLayout()
        main_layout.addLayout(self.page_stack, 1)

        # ---------------- DASHBOARD PAGE ----------------
        dashboard_page = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_page)

        grid_widget = QWidget()
        self.grid = QGridLayout(grid_widget)
        self.grid.setSpacing(16)

        self.cards = [
            make_card("CAT-A", "Automation Tool for Android Phone.", self.open_cata),
            make_card("CAT-F", "Automation Tool for Feature Phone.", self.open_catf),
            make_card("TAT", "Automation Speedtest Tool.", self.open_tat),
        ]

        for i, card in enumerate(self.cards):
            self.grid.addWidget(card, 0, i)

        # 🔥 IMPORTANT: stretch so cards are visible
        self.grid.setRowStretch(0, 1)
        for c in range(3):
            self.grid.setColumnStretch(c, 1)

        dashboard_layout.addWidget(grid_widget, 1)
        dashboard_layout.addStretch()

        footer = QLabel("© 2025 Automation Tool — Integration Dashboard")
        footer.setObjectName("footerLabel")
        dashboard_layout.addWidget(
            footer, alignment=Qt.AlignmentFlag.AlignCenter
        )

        # ---------------- TOOL PAGE WRAPPER ----------------
        def wrap_with_back_button(widget):
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(8)

            back_btn = QPushButton("← Back to Dashboard")
            back_btn.setObjectName("backBtn")
            back_btn.setFixedWidth(180)
            back_btn.clicked.connect(self.back_to_dashboard)

            layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignLeft)
            layout.addWidget(widget, 1)

            return container

        # ---------------- TOOL PAGES ----------------
        # keep full window instances so their internal state (e.g. .stack) persists
        self.cata_window = CATAWindow()
        self.catf_window = CATFWindow()
        self.tat_window  = TATWindow()

        self.cata_page = wrap_with_back_button(self.cata_window.centralWidget())
        self.catf_page = wrap_with_back_button(self.catf_window.centralWidget())
        self.tat_page  = wrap_with_back_button(self.tat_window.centralWidget())

        # ---------------- ADD TO STACK ----------------
        self.page_stack.addWidget(dashboard_page)  # index 0
        self.page_stack.addWidget(self.cata_page)  # index 1
        self.page_stack.addWidget(self.catf_page)  # index 2
        self.page_stack.addWidget(self.tat_page)   # index 3

        self.page_stack.setCurrentIndex(0)

        self.setStyleSheet(APP_STYLES)

    # ---------------- NAVIGATION ----------------
    def back_to_dashboard(self):
        self.page_stack.setCurrentIndex(0)

    def open_cata(self):
        try:
            self.cata_window.stack.setCurrentIndex(0)
        except Exception:
            pass
        self.page_stack.setCurrentIndex(1)

    def open_catf(self):
        try:
            self.catf_window.stack.setCurrentIndex(0)
        except Exception:
            pass
        self.page_stack.setCurrentIndex(2)

    def open_tat(self):
        try:
            self.tat_window.stack.setCurrentIndex(0)
        except Exception:
            pass
        self.page_stack.setCurrentIndex(3)


# ------------------------------------------------
# Entry Point
# ------------------------------------------------
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
