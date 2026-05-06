SENSOR_READING_ACTUATOR_CONTROL_WEBSERVER_IP = "127.0.0.1"
SENSOR_READING_ACTUATOR_CONTROL_WEBSERVER_PORT = 8080
LOGGER_WEBSERVICE_IP = "127.0.0.1"
LOGGER_WEBSERVICE_PORT = 8081

# Elenco delle stanze disponibili nella Smart Home
ROOMS = ["living_room", "kitchen", "bedroom"]

# Tipi di sensori supportati e relative unità di misura SenML (Esercizi 01 e 02)
SENSOR_TYPES = {
    "temperature": "Cel", 
    "humidity": "%RH", 
    "motion": "bool"
}

# Struttura iniziale degli attuatori in ogni stanza (Esercizio 03)
# Modellati come richiesto: termostato in °C, luci come booleano, e tapparelle in %
INITIAL_ACTUATORS_STATE = {
    "living_room": {
        "thermostat": {"v": 20.0, "u": "Cel", "t": 0},
        "lights": {"v": False, "u": "bool", "t": 0},
        "blinds": {"v": 0, "u": "%", "t": 0}
    },
    "kitchen": {
        "thermostat": {"v": 20.0, "u": "Cel", "t": 0},
        "lights": {"v": False, "u": "bool", "t": 0},
        "blinds": {"v": 0, "u": "%", "t": 0}
    },
    "bedroom": {
        "thermostat": {"v": 20.0, "u": "Cel", "t": 0},
        "lights": {"v": False, "u": "bool", "t": 0},
        "blinds": {"v": 0, "u": "%", "t": 0}
    }
}

ACTUATOR_RULES = {
    "thermostat": {
        "unit": "Cel",
        "low": 10,
        "high": 30,
        "type": (float, int)
    },
    "lights": {
        "unit": "bool",
        "low": None,
        "high": None,
        "type": bool
    },
    "blinds": {
        "unit": "%",
        "low": 0,
        "high": 100,
        "type": (float, int)
    }
}

SENSOR_RULES = {
    "temperature": {
        "unit": "Cel",
        "low": 15,
        "high": 30,
        "type": (float, int)
    },
    "humidity": {
        "unit": "%RH",
        "low": 30,
        "high": 70,
        "type": (float, int)
    },
    "motion": {
        "unit": "bool",
        "low": None,
        "high": None,
        "type": bool
    }
}