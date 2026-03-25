"""
progress_check.py  —  Tkinter-free stub
=========================================
The original CAT-F app updated a Tkinter progress bar widget.
In the Flask/web context progress is reported via the cat_f_state dict
that the /api/cat-f/status endpoint reads every second.
This stub keeps the import alive without any Tkinter dependency.
"""


class TestProgress:
    """No-op progress reporter — progress is tracked in cat_f_state instead."""

    def __init__(self, progress_frame, total_iterations: int):
        self.total   = total_iterations
        self.current = 0

    def update_progress(self):
        self.current += 1