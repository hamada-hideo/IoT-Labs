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
        "thermostat": {"v": 20.0, "u": "Cel"},
        "lights": {"v": False, "u": "bool"},
        "blinds": {"v": 0, "u": "%"}
    },
    "kitchen": {
        "thermostat": {"v": 20.0, "u": "Cel"},
        "lights": {"v": False, "u": "bool"},
        "blinds": {"v": 0, "u": "%"}
    },
    "bedroom": {
        "thermostat": {"v": 20.0, "u": "Cel"},
        "lights": {"v": False, "u": "bool"},
        "blinds": {"v": 0, "u": "%"}
    }
}
