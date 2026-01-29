import time
import tkinter as tk
from tkinter.font import Font

from backend.cat_a_tool.utils import play_alert_sound

from backend.cat_a_tool.data.constants import *



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


if __name__ == '__main__':
    # Create the main window
    root = tk.Tk()
    root.title("Main Window")
    print(reconnect(root, "Device Name"))
    # root.destroy()
    # Run the main loop
    root.mainloop()
