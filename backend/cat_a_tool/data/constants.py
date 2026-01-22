import os

VERSION = "v2.66"
# No of cores the application can use
NO_OF_CORES = os.cpu_count()

# parent dir
MAIN_DIR = os.getcwd()[:-4]

# Blue shades
BLUE = "#02C2F2"
LIGHT_BLUE = "#ADD8E6"
PALE_BLUE = "#87CEFA"
SKY_BLUE = "#87CEEB"
POWDER_BLUE = "#B0DFE6"

# Green shades
GREEN = "#04BF55"
LIGHT_GREEN = "#90EE90"
PALE_GREEN = "#98FB98"
MINT_GREEN = "#00FA9A"
SPRING_GREEN = "#50C7A3"

# Orange shades
ORANGE = "#EB902F"
LIGHT_ORANGE = "#FFDAB9"
PEACH = "#FFE5B4"
SALMON = "#FA8072"
CORAL = "#FF7F50"

# Red shades
RED = "#D90902"
LIGHT_RED = "#FFC0CB"
PINK = "#FFB6C1"
SALMON_RED = "#FFA07A"
LIGHT_SALMON = "#FFA07A"

# White and Black
WHITE = "#FFFFFF"
LIGHT_GRAY = "#D3D3D3"
GRAY = "#808080"
DARK_GRAY = "#A9A9A9"
BLACK = "#000000"

VIOLET = "#5C1163"
PALE_VIOLET = "#DAD1FF"
LIGHT_YELLOW = "#FFE19C"

COLUMNS = [
    "Iteration", "Date", "Start Time", "End Time", "Duration", "Status", "Comment",
    "Operator_name", "PLMN_mcc", "PLMN_mnc", "Bandwidth",
    "Cell_ID", "Band", "VRT", "PCI", "TAC", "EARFCN", "rsrp", "rsrq",
    "latitude", "longitude"
]

# ADB keycodes in use
KEYCODE_CALL = 5
KEYCODE_ENDCALL = 6
