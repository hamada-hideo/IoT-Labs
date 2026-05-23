// 1. Definizione del pin analogico per il sensore
// Le specifiche suggeriscono di utilizzare A0
const int TEMP_PIN = A0; 
// Costanti tipiche per il termistore del Grove Temperature Sensor.
// Nota: I documenti indicano di usare la formula del datasheet. 
// I valori B e R0 qui sotto sono lo standard per questo specifico modulo.
const int B = 4275;               // Valore B del termistore
const float R0 = 100000.0;        // R0 = 100k ohm
void setup() {
  // Inizializzazione della comunicazione seriale
  Serial.begin(9600);
  while (!Serial); // Attende l'apertura del Serial Monitor
  // Stampa il messaggio di avvio
  Serial.println("Lab 1.5 starting");
}
void loop() {
  // 1. Legge il valore di tensione del pin (da 0 a 1023)
  int sensorValue = analogRead(TEMP_PIN);
  // 2. Converte il valore analogico in temperatura
  // Il sensore Grove usa una resistenza variabile (termistore)
  float R = 1023.0 / sensorValue - 1.0;
  R = R0 * R;
  // Applica l'equazione per il termistore per ottenere i gradi Celsius
  float temperature = 1.0 / (log(R / R0) / B + 1 / 298.15) - 273.15; 
  // 3. Invia la misurazione della temperatura al PC 
  // formatto l'output
  Serial.print("temperature = ");
  Serial.println(temperature);
  // 4. Attende 10 secondi prima della prossima lettura
  delay(10000);
}