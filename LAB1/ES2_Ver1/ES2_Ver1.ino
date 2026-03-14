#include <MBED_RPi_Pico_TimerInterrupt.h>
// Costanti per i pin dei LED e i semi-periodi
const int RLED_PIN = 2;
const int GLED_PIN = 3;
const long R_HALF_PERIOD = 1500L;
const long G_HALF_PERIOD = 3500L;
// Variabili di stato dichiarate "volatile" perché utilizzate sia nel loop() che nell'ISR
volatile int redLedState = LOW;
volatile int greenLedState = LOW;
// Inizializzazione del Timer 1
MBED_RPI_PICO_Timer ITimer1(1);
// Interrupt Service Routine per far lampeggiare il LED verde
void blinkGreen(uint alarm_num) {
  TIMER_ISR_START(alarm_num);
  digitalWrite(GLED_PIN, greenLedState);
  greenLedState = !greenLedState;
  TIMER_ISR_END(alarm_num);
}
// Funzione dedicata alla gestione della porta seriale
void serialPrintStatus() {
  // Controlla se ci sono dati in arrivo sulla porta seriale
  if (Serial.available() > 0) {
    int inByte = Serial.read(); // Legge il carattere ricevuto
    // Ignora i caratteri di fine riga che il Serial Monitor potrebbe inviare
    if (inByte == '\n' || inByte == '\r') {
        return; 
    }
    if (inByte == 'R') {
      Serial.print("LED ");
      Serial.print(RLED_PIN);
      Serial.print(" Status: ");
      Serial.println(redLedState);
    } 
    else if (inByte == 'L') {
      Serial.print("LED ");
      Serial.print(GLED_PIN);
      Serial.print(" Status: ");
      Serial.println(greenLedState);
    } 
    else {
      Serial.println("Invalid command");
    }
  }
}
void setup() {
  // Configurazione dei pin come output
  pinMode(RLED_PIN, OUTPUT);
  pinMode(GLED_PIN, OUTPUT);
  // Configurazione della comunicazione Seriale
  Serial.begin(9600);
  // Attende che la connessione seriale sia stabilita prima di avviare il programma
  while (!Serial); 
  Serial.println("Lab 1.2 Starting");
  // Collega l'ISR al Timer, convertendo il tempo in microsecondi
  ITimer1.setInterval(G_HALF_PERIOD * 1000, blinkGreen);
}
void loop() {
  // 1. Controlla e gestisce le richieste in arrivo dalla Seriale
  serialPrintStatus();
  // 2. Gestisce il lampeggio del LED rosso
  digitalWrite(RLED_PIN, redLedState);
  redLedState = !redLedState;
  // 3. Mette in pausa il programma principale
  delay(R_HALF_PERIOD); 
}