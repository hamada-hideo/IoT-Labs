# Laboratori di IoT 

## 1. Configurazione Python

Per installare le dipendenze Python esterne necessarie per il Controller, i WebServer e il Catalogo, aprire il terminale ed eseguire:

```
pip install -r requirements.txt
```

Per lanciare il sistema in modalità distribuita è necessario modificare il file di configurazione di ogni elemento software, impostando l'IP del dispositivo su cui verrà eseguita.

Di default tali file contengono l'indirizzo `127.0.0.1`, quindi per lanciare il sistema su un solo PC non è necessaria alcuna modifica.

## 2. Configurazione Hardware (Arduino)

Librerie necessarie per eseguire gli sketch:

- WiFiNINA
- ArduinoHttpClient
- PubSubClient
- ArduinoJson
- Arduino_LSM6DSOX
- PDM
- LiquidCrystal_PCF8574

Per gli sketch che richiedono di interagire con un PC tramite le API REST è necessario creare un file `arduino_secrets.h` e inserire le credenziali Wi-Fi e l'indirizzo IP locale del PC.
