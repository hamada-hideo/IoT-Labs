import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from MQTTActuatorCommandPublisher.ActuatorCommandPublisher import *

if __name__ == "__main__":
    publisher = ActuatorCommandPublisher()
    publisher.run()
