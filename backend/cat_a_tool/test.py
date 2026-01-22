import time

import pandas as pd
import requests

from .logger import CustomLogger
from .utils import get_cell_info, get_location

# # Replace 'YOUR_AZURE_MAPS_SUBSCRIPTION_KEY' with your actual Azure Maps subscription key
# api_key = 'AvKuHSR0h-ndVjyUlhLQTfWNRxsShy_ShsMfb7FFW7YAYlKW0KhzuQfQdvi4fMJX'
#
# # Load latitude and longitude values from the Excel sheet
# file = r"D:\MQT\AutoTool MQT\Application\v2.64\SourceCode\temp_reportMO1_to_MT1.xlsx"
# df = pd.read_excel(file)  # Update with your file path
#
# # Remove duplicate pairs where both latitude and longitude are the same
# df.drop_duplicates(subset=['latitude', 'longitude'], inplace=True)
#
# # Reset the index after dropping duplicates
# df.reset_index(drop=True, inplace=True)
#
# # Construct the request URL for Static Maps API
# url = "https://atlas.microsoft.com/map/static/png?"
# url += f"subscription-key={api_key}"
# url += "&api-version=1.0"
# url += "&layer=basic"
# url += "&zoom=10"
# url += "&format=png"

# # Add waypoints to the URL to generate route polyline
# for i, (lat, lon) in enumerate(zip(df['latitude'], df['longitude'])):
#     url += f"&center={lat},{lon}"
#
# # Send the request to Azure Maps Static API
# response = requests.get(url)
#
# # Check if the request was successful
# if response.status_code == 200:
#     # Save the image to a file
#     with open("route_map.png", "wb") as f:
#         f.write(response.content)
#     print("Route map image saved as route_map.png")
# else:
#     print("Error:", response.status_code, response.text)


if __name__ == "__main__":

    udid = "NFOE1K0145"
    cus_log = CustomLogger("test cell info")
    param_names = ['operator', 'mcc', 'mnc', 'bw', 'cell_id', 'band', 'VRT', 'pci', 'tac',
                   'earfcn', 'rsrp', 'rsrq']
    while True:
        param_values = get_cell_info(udid, 0, cus_log)
        for name, value in zip(param_names, param_values):
            print(f"{name}: {value}", end='|')
        time.sleep(1)
        print('\n')
