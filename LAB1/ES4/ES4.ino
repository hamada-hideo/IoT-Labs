// Definizione del pin di controllo della ventola. 
// Deve essere un pin che supporta il PWM
const int FAN_PIN = 5; 
// Variabile per tenere traccia della velocità corrente. 
// Le slide suggeriscono l'uso di un float
float current_speed = 0;
// Definizione del numero di step (10 step come richiesto dalle specifiche)
// Valore massimo PWM è 255. Incremento = 255.0 / 10 = 25.5
const float step_size = 25.5;
void setup() {
  // Inizializzazione della comunicazione seriale
  Serial.begin(9600);
  while (!Serial); // Attende l'apertura del Serial Monitor
  // Configura il pin della ventola come OUTPUT
  pinMode(FAN_PIN, OUTPUT);
  // Imposta la velocità iniziale a 0 (Duty cycle = 0%)
  // La variabile float viene castata a int
  analogWrite(FAN_PIN, (int)current_speed);
  Serial.println("Lab 1.4 Starting - Motor Control");
}
void loop() {
  // Controlla se ci sono caratteri in ingresso sulla porta seriale
  if (Serial.available() > 0) {
    char command = Serial.read();
    // Ignora i caratteri di a capo invisibili (carriage return e line feed)
    if (command == '\n' || command == '\r') {
      return;
    }
    // Aumenta la velocità se riceve '+'
    if (command == '+') {
      if (current_speed >= 255.0) {
        Serial.println("Already at max speed"); // Raggiunto il limite massimo
      } else {
        current_speed += step_size;
        if (current_speed > 255.0) current_speed = 255.0; // Previene lo sforamento
        analogWrite(FAN_PIN, (int)current_speed);
        Serial.print("Increasing speed: ");
        Serial.println(current_speed);
      }
    } 
    // Diminuisce la velocità se riceve '-'
    else if (command == '-') {
      if (current_speed <= 0.0) {
        Serial.println("Already at min speed"); // Raggiunto il limite minimo
      } else {
        current_speed -= step_size;
        if (current_speed < 0.0) current_speed = 0.0; // Previene lo sforamento
        analogWrite(FAN_PIN, (int)current_speed); [2]
        Serial.print("Decreasing speed: ");
        Serial.println(current_speed);
      }
    } 
    // Qualsiasi altro carattere genera un messaggio di errore
    else {
      Serial.println("Error: Invalid command");
    }
  }
}