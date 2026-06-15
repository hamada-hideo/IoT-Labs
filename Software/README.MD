
# Istruzioni di Avvio - Ecosistema IoT Gruppo 12

## 1. Configurazione Python
Per installare le dipendenze Python esterne necessarie per il Controller, i WebServer e il Catalogo, aprire il terminale ed eseguire:
pip install -r requirements.txt
Per tirare su un servizio:

- Copiare il file `network_config_template.json` in un nuovo file `network_config.json`
- Modificare l'indirizzo ip nel file `network_config.json` con il proprio indirizzo ip ed eventualmente gli altri valori, lasciando intatta la struttura
- Tirare su il servizio
## 2. Configurazione Hardware (Arduino)
Prima di compilare lo sketch `ES14.ino`, assicurarsi di aver installato le seguenti librerie tramite il Gestore Librerie dell'IDE Arduino:
- WiFiNINA
- ArduinoHttpClient
- PubSubClient
- ArduinoJson
- Arduino_LSM6DSOX (per la temperatura)
- PDM (per il microfono)
- LiquidCrystal_PCF8574 (per il display I2C)

ATTENZIONE: Aprire il file `arduino_secrets.h` e inserire le credenziali Wi-Fi e l'indirizzo IP locale del PC che ospita il server REST del Catalogo prima del flash.

