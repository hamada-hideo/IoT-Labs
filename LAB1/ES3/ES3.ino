// Definizione dei pin tramite costanti
const int LED_PIN = 2; // Pin per il LED esterno
const int PIR_PIN = 4; // Pin collegato all'output digitale del sensore PIR
// Variabile dichiarata 'volatile' perché viene modificata nell'ISR 
// e letta all'interno della funzione loop()
volatile int tot_count = 0;
// Interrupt Service Routine (ISR)
void checkPresence() {
  // 1. Legge il valore attuale del sensore PIR
  int pirState = digitalRead(PIR_PIN);
  // 2. Riproduce il valore sul LED (Acceso se HIGH, Spento se LOW)
  digitalWrite(LED_PIN, pirState);
  // 3. Un "evento" è un NUOVO movimento. Poiché l'ISR si attiva sia
  // sul fronte di salita che su quello di discesa (CHANGE),
  // incrementiamo il contatore solo quando il sensore rileva 
  // una nuova presenza (ovvero quando passa allo stato HIGH).
  if (pirState == HIGH) {
    tot_count++;
  }
}
void setup() {
  // Configurazione della comunicazione Seriale
  Serial.begin(9600);
  while (!Serial); // Attende l'apertura del Serial Monitor
  // Stampa il messaggio iniziale
  Serial.println("Lab 1.3 starting");
  // Configurazione dei Pin
  pinMode(LED_PIN, OUTPUT);
  pinMode(PIR_PIN, INPUT);
  // Associazione dell'Interrupt al pin del sensore PIR.
  // Utilizziamo la modalità CHANGE per reagire sia all'inizio (RISING) 
  // che alla fine (FALLING) del movimento.
  attachInterrupt(digitalPinToInterrupt(PIR_PIN), checkPresence, CHANGE);
}
void loop() {
  // Invia il conteggio totale al PC
  Serial.print("Total people count: ");
  Serial.println(tot_count);
  // Attende 30 secondi (30000 millisecondi) prima di stampare nuovamente.
  // Nota: usare delay() qui è corretto perché l'acquisizione dei dati 
  // del sensore è gestita in modo totalmente asincrono dall'Interrupt hardware.
  delay(30000);
}