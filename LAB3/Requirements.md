# Sensor Class

Simula le misure prese da un sensore.

Possibili tipi di misura:
- temperature
- humidity
- movement

Esporre un metodo `simulate()` che restitusca un array di misure in formato SenML.

# Actuator Class

Attuatori da modellare (uno di ogni tipo per ogni stanza):
- thermostat
- lights
- blinds

Esporre un metodo `send_command()` che riceva un comando in formato SenML.

Esporre un metodo `get_state()` che restituisca lo stato attuale in formato SenML.

# Sensor Reader / Actuator Control Web Server

Entrambi gli endpoint in due versioni:
- query driven
- path drven

## Sensor Reader Endpoint

Mantiene una struttura dati con tutti i sensori registrati.

Parsa la richiesta e chiama il metodo `simulate()` del sensore corretto.

## Actuator Control Endpoint

Mantiene una struttura dati con tutti gli attuatori registrati.

Accetta richieste per:
- inviare comandi a un attuatore -> chiama il metodo `simulate()` dell'attuatore corretto
- leggere lo stato di uno o più attuatori -> chiama il metodo `simulate()` dell'attuatore

# Event Log Web Server

Mantiene una struttura dati con tutti gli eventi registrati.

Accetta richeste per:
- Aggiungere eventi
- Leggere gli eventi loggati
- Eliminare eventi vecchi