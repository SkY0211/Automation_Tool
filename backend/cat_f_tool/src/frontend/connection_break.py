"""
connection_break.py  —  Tkinter-free stub
==========================================
The original CAT-F app showed a blocking Tkinter popup when a device
disconnected. In the Flask/web context that dialog is replaced by the
disconnect modal in the browser UI. This stub keeps the import alive
so CallTester.run_test() never crashes, and simply returns True so the
reconnect loop exits and the test resumes normally once the device is
back (the service layer handles the actual state update).
"""


def reconnect(home, disconnected_ports, timeout_seconds=20):
    """
    No-op stub — always returns True.
    The browser UI polls /api/cat-f/status and shows its own modal.
    """
    return True