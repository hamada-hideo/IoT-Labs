import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from DeviceMQTTClient.mqtt_client import *

if __name__ == "__main__":
    device = DeviceMQTTClient()
    device.run()
