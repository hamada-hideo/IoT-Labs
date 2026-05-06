# 🚀 Guida all'avvio: Rete IoT Distribuita (Tailscale)

Poiché il nostro ecosistema IoT (Sensori, Attuatori, Logger e futuri Client) deve girare su computer diversi in città diverse, utilizziamo **Tailscale** per creare una Virtual Private Network (VPN) Mesh. 

## 1. Installazione e Accesso
Per poter parlare con i server del progetto, devi prima entrare nella nostra rete virtuale:

1. Vai su [tailscale.com/download](https://tailscale.com/download) e installa il client per il tuo sistema operativo.
2. Apri l'applicazione e clicca sull'icona di Tailscale (in basso a destra vicino all'orologio) e seleziona **"Log in"**.
4. Si aprirà una pagina nel browser. Fai l'accesso con **[INSERIRE QUI EMAIL/LINK INVITO]**.
5. **ATTENZIONE:** Dopo il login nel browser, assicurati di cliccare sul pulsante blu **"Connect"** (o "Autorizza") che appare sulla pagina web. Se il browser ti chiede di aprire l'app Tailscale, accetta. 
6. Quando l'icona sul tuo PC ha un pallino verde, sei dentro! Il sistema ti assegnerà un indirizzo IP privato che inizia per `100.x.x.x`.

## 2. Configurazione del Progetto (`Globals.py`)
Prima di avviare il codice, dobbiamo dire ai nostri script a quali IP di Tailscale devono puntare.

1. Apri Tailscale per vedere il tuo IP `100.x.x.x` (o guarda la dashboard web per vedere gli IP degli altri colleghi).
2. Apri il file `Globals.py`.
3. Assicurati che gli IP corrispondano ai computer che attualmente fanno girare i servizi. Ad esempio:

# Sostituire con l'IP Tailscale del PC che esegue main.py (Sensori/Attuatori)
SENSOR_READING_ACTUATOR_CONTROL_WEBSERVER_IP = "100.x.y.z" 
SENSOR_READING_ACTUATOR_CONTROL_WEBSERVER_PORT = 8080

# Sostituire con l'IP Tailscale del PC che esegue main.py (Logger)
LOGGER_WEBSERVICE_IP = "100.a.b.c" 
LOGGER_WEBSERVICE_PORT = 8081

3. ⚠️ REGOLE FONDAMENTALI PER I SERVER ⚠️

1. Host Globale: Nel codice di CherryPy, l'host deve essere impostato su '0.0.0.0' (non su 127.0.0.1 o sull'IP di Tailscale). 
Questo dice a Python di ascoltare anche sulla rete VPN.
# Esempio: cherrypy.config.update({'server.socket_host': '0.0.0.0'})
2. Il Firewall di Windows (**FONDAMENTALE**): 
La prima volta che avvii il file main.py, Windows aprirà una finestra blu del Windows Defender Firewall. Devi assolutamente spuntare le caselle "Reti Private" e "Reti Pubbliche" e cliccare su "Consenti Accesso". 
Se la chiudi per sbaglio o non metti le spunte, le richieste degli altri colleghi verranno bloccate e andranno in Timeout!
