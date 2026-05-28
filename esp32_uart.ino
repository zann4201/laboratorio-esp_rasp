/*
  ESP32 Multi-Sensor UART Simulator sketch (Versión ultra-compatible)
  
  Conexión física:
  -------------------------------------------------------------
  ESP32 Pin                    | Raspberry Pi 3 Pin
  -------------------------------------------------------------
  GND                          | GND (Pin físico 6, 9, 14, 20, 25, etc.)
  TX2 (GPIO 17)                | RXD (Pin físico 10 / GPIO 15)
  RX2 (GPIO 16)                | TXD (Pin físico 8  / GPIO 14)
  -------------------------------------------------------------
*/

#include <Arduino.h>

#define RXD2 16
#define TXD2 17

// Instanciamos de forma explícita la clase HardwareSerial para evitar
// incompatibilidades de compilación con algunas versiones del Core de ESP32.
HardwareSerial MySerial(2); 

unsigned long ultimoEnvio = 0;
const unsigned long intervaloEnvio = 1500; // Enviar datos cada 1.5 segundos

void setup() {
  // Serial USB para depuración en PC
  Serial.begin(115200);
  
  // Inicializamos nuestro puerto UART2 configurando pines dinámicos
  MySerial.begin(115200, SERIAL_8N1, RXD2, TXD2);
  
  Serial.println("[ESP32] Simulador Multi-Sensor UART Iniciado.");
  Serial.println("[ESP32] Enviando datos en formato JSON a 115200 baudios...");
}

void loop() {
  unsigned long tiempoActual = millis();
  
  // 1. Simulación y envío de múltiples sensores en formato JSON
  if (tiempoActual - ultimoEnvio >= intervaloEnvio) {
    ultimoEnvio = tiempoActual;
    
    // Simulación de Sensor de Temperatura (LM35/DHT22) -> Oscilación entre 22°C y 28°C
    float temp = 25.0 + 3.0 * sin(tiempoActual / 20000.0) + (random(-2, 2) / 10.0);
    
    // Simulación de Sensor de Humedad (DHT22) -> Oscilación entre 50% y 70%
    float hum = 60.0 + 8.0 * cos(tiempoActual / 30000.0) + (random(-5, 5) / 10.0);
    
    // Simulación de Sensor de Luz (LDR con ADC de 12 bits) -> Rango 0 - 4095
    int light = 2048 + 1500 * sin(tiempoActual / 40000.0) + random(-50, 50);
    if (light < 0) light = 0;
    if (light > 4095) light = 4095;
    
    // Construcción manual y súper ligera de la cadena JSON sin librerías externas
    String json = "{\"t\":" + String(temp, 2) + 
                  ",\"h\":" + String(hum, 1) + 
                  ",\"l\":" + String(light) + "}";
    
    // Enviar por el canal UART físico hacia la Raspberry Pi
    MySerial.println(json);
    
    // Mostrar en el puerto serial de la PC para depuración
    Serial.println("[TX] -> RPi: " + json);
  }
  
  // 2. Escuchar la respuesta de eco de la Raspberry Pi
  if (MySerial.available() > 0) {
    String respuesta = MySerial.readStringUntil('\n');
    respuesta.trim();
    Serial.println("[RX] <- RPi: " + respuesta);
  }
}
