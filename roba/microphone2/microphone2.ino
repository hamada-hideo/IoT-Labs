#include <PDM.h>

// Dichiarazione dell'array con la dimensione corretta di 256 elementi [1]
volatile short sampleBuffer[256];
volatile int samplesRead = 0;

// Variabile per il timer
unsigned long lastPrintTime = 0;

// Variabile per memorizzare il picco massimo nei 3 secondi
int maxPicco = 0; 

void setup() {
  Serial.begin(9600);
  while(!Serial); 
  
  PDM.onReceive(onPDMdata);
  if (!PDM.begin(1, 16000)) {
    Serial.println("Failed to start PDM!");
    while(1);
  }
  Serial.println("Avvio lettura picco massimo ogni 3 secondi...");
}

void loop() {
  // 1. ELABORAZIONE CONTINUA DEL BUFFER
  if (samplesRead) {
    // Scansioniamo tutti i campioni appena letti
    for (int i = 0; i < samplesRead; i++) {
      // Prendiamo il valore assoluto (l'ampiezza dell'onda sonora)
      int valoreAttuale = abs(sampleBuffer[i]);
      
      // Se troviamo un valore più grande di quello memorizzato, lo aggiorniamo
      if (valoreAttuale > maxPicco) {
        maxPicco = valoreAttuale;
      }
    }
    
    // Svuotiamo il contatore dei campioni letti [2]
    samplesRead = 0;
  }

  // 2. TIMER DI STAMPA A 3 SECONDI
  unsigned long currentMillis = millis();
  if (currentMillis - lastPrintTime >= 3000) {
    lastPrintTime = currentMillis; // Resetta il timer

    // Stampa il valore più grande trovato in questi 3 secondi
    Serial.print("Picco massimo (raw) negli ultimi 3s: ");
    Serial.println(maxPicco);
    
    // Azzera la variabile per iniziare a cercare il picco dei successivi 3 secondi
    maxPicco = 0;
  }
}

// ISR del microfono
void onPDMdata() {
  int bytesAvailable = PDM.available();
  PDM.read((void*)sampleBuffer, bytesAvailable);
  samplesRead = bytesAvailable / 2; // 16-bit, 2 bytes per campione [2]
}