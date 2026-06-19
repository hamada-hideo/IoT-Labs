import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from SmartHomeController.smart_home_controller import *

if __name__ == "__main__":
    controller = SmartHomeController()
    controller.start()
