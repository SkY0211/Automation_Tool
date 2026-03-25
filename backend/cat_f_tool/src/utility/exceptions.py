import sys
import traceback


class FPAException(Exception):

    def __init__(self, error_msg, error_detail: sys):
        exc_type, exc_value, exc_traceback = error_detail.exc_info()
        error_message  = f"\nError type: {exc_type}\n"
        error_message += f"Error detail: \n{error_msg}\n"
        tb_str         = "".join(traceback.format_tb(exc_traceback))
        error_message += f"Traceback:\n{tb_str}"
        self.error_message = error_message

    def __str__(self):
        return self.error_message