#!/usr/bin/env python3
import serial
import time
import threading
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# CONFIGURACIÓN
PORT_UART = '/dev/serial0'
BAUDRATE = 115200
PORT_HTTP = 8080

# ESTADO MULTI-SENSOR EN TIEMPO REAL
system_state = {
    "connected": False,
    "temp": 0.0,
    "hum": 0.0,
    "light": 0,
    "last_update": "Esperando datos...",
    "history_temp": [],
    "history_hum": [],
    "history_light": []
}

state_lock = threading.Lock()

# SERVIDOR WEB HTTP (Dashboard Multi-Sensor)
class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Omitir logs HTTP en consola

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(self.get_html_template().encode('utf-8'))
        elif self.path == '/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with state_lock:
                response_data = json.dumps(system_state)
            self.wfile.write(response_data.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def get_html_template(self):
        return """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Multisensores IoT - ESP32 & Raspberry Pi</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: 'Outfit', sans-serif;
            background: radial-gradient(circle at top, #0f172a, #020617);
            color: #f8fafc;
            min-height: 100vh;
        }
        .glass-card {
            background: rgba(30, 41, 59, 0.45);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }
        .glow-green { box-shadow: 0 0 15px rgba(34, 197, 94, 0.5); }
        .glow-red { box-shadow: 0 0 15px rgba(239, 68, 68, 0.5); }
        .glow-temp { box-shadow: 0 0 20px rgba(99, 102, 241, 0.15); }
        .glow-hum { box-shadow: 0 0 20px rgba(6, 182, 212, 0.15); }
        .glow-light { box-shadow: 0 0 20px rgba(245, 158, 11, 0.15); }
    </style>
</head>
<body class="p-4 md:p-8 flex flex-col items-center">
    <div class="max-w-6xl w-full flex flex-col gap-6">
        
        <!-- Header -->
        <header class="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-card p-6 rounded-2xl">
            <div>
                <h1 class="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-blue-400 via-cyan-300 to-indigo-400 bg-clip-text text-transparent">
                    Telemetría IoT Multisensores
                </h1>
                <p class="text-slate-400 text-sm mt-1">UART UART2 (ESP32) &rarr; UART0 (Raspberry Pi 3) | Formato JSON</p>
            </div>
            
            <div class="flex items-center gap-3">
                <span class="text-slate-400 text-sm font-semibold">Estado de Enlace:</span>
                <div id="status-badge" class="flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-bold bg-red-500/20 text-red-400 border border-red-500/30 transition-all duration-300 glow-red">
                    <span class="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse"></span>
                    <span id="status-text">DESCONECTADO</span>
                </div>
            </div>
        </header>

        <!-- Metrics Grid -->
        <section class="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            <!-- Sensor 1: Temperatura -->
            <div class="glass-card p-6 rounded-2xl glow-temp flex flex-col justify-between relative overflow-hidden group">
                <div class="absolute -right-8 -top-8 w-24 h-24 bg-indigo-500/10 rounded-full blur-xl group-hover:bg-indigo-500/20 transition-all duration-500"></div>
                <div>
                    <div class="flex justify-between items-center mb-4">
                        <h2 class="text-indigo-400 text-sm font-bold uppercase tracking-wider">Temperatura</h2>
                        <span class="text-xl">🌡️</span>
                    </div>
                    <div class="flex items-baseline gap-2">
                        <span id="temp-val" class="text-5xl font-black tracking-tight text-white">0.0</span>
                        <span class="text-2xl font-bold text-slate-400">°C</span>
                    </div>
                </div>
                <div class="mt-6 border-t border-slate-700/50 pt-3 flex justify-between items-center text-xs text-slate-400">
                    <span>Sensor LM35 / DHT22</span>
                    <span class="font-mono text-indigo-300">Rango: -40 a 80°C</span>
                </div>
            </div>

            <!-- Sensor 2: Humedad -->
            <div class="glass-card p-6 rounded-2xl glow-hum flex flex-col justify-between relative overflow-hidden group">
                <div class="absolute -right-8 -top-8 w-24 h-24 bg-cyan-500/10 rounded-full blur-xl group-hover:bg-cyan-500/20 transition-all duration-500"></div>
                <div>
                    <div class="flex justify-between items-center mb-4">
                        <h2 class="text-cyan-400 text-sm font-bold uppercase tracking-wider">Humedad Relativa</h2>
                        <span class="text-xl">💧</span>
                    </div>
                    <div class="flex items-baseline gap-2">
                        <span id="hum-val" class="text-5xl font-black tracking-tight text-white">0.0</span>
                        <span class="text-2xl font-bold text-slate-400">%</span>
                    </div>
                </div>
                <div class="mt-6 border-t border-slate-700/50 pt-3 flex justify-between items-center text-xs text-slate-400">
                    <span>Sensor de Humedad DHT22</span>
                    <span class="font-mono text-cyan-300">Rango: 0 a 100%</span>
                </div>
            </div>

            <!-- Sensor 3: Luz -->
            <div class="glass-card p-6 rounded-2xl glow-light flex flex-col justify-between relative overflow-hidden group">
                <div class="absolute -right-8 -top-8 w-24 h-24 bg-amber-500/10 rounded-full blur-xl group-hover:bg-amber-500/20 transition-all duration-500"></div>
                <div>
                    <div class="flex justify-between items-center mb-4">
                        <h2 class="text-amber-400 text-sm font-bold uppercase tracking-wider">Luminosidad</h2>
                        <span class="text-xl">☀️</span>
                    </div>
                    <div class="flex items-baseline gap-2">
                        <span id="light-pct" class="text-5xl font-black tracking-tight text-white">0</span>
                        <span class="text-2xl font-bold text-slate-400">%</span>
                    </div>
                </div>
                <div class="mt-6 border-t border-slate-700/50 pt-3 flex justify-between items-center text-xs text-slate-400">
                    <span>LDR + ADC 12-bits</span>
                    <span id="light-raw" class="font-mono text-amber-300">Raw: 0 / 4095</span>
                </div>
            </div>

        </section>

        <!-- Chart and Details Section -->
        <main class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            <!-- Historical Line Chart -->
            <section class="glass-card p-6 rounded-2xl lg:col-span-2 flex flex-col">
                <h2 class="text-slate-400 text-sm font-semibold uppercase tracking-wider mb-4">Gráfico Histórico de Variables</h2>
                <div class="relative w-full h-80">
                    <canvas id="telemetryChart"></canvas>
                </div>
            </section>

            <!-- Technical details / payload JSON -->
            <section class="glass-card p-6 rounded-2xl flex flex-col justify-between">
                <div>
                    <h2 class="text-slate-400 text-sm font-semibold uppercase tracking-wider mb-4">Estructura del Payload</h2>
                    <p class="text-xs text-slate-400 mb-4 leading-relaxed">
                        Trama JSON en tiempo real transmitida por UART físico a 115200 baudios:
                    </p>
                    
                    <!-- Code block for payload -->
                    <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-4 font-mono text-xs text-indigo-300 shadow-inner">
                        <pre id="json-payload" class="overflow-x-auto">{"t": 0.0, "h": 0.0, "l": 0}</pre>
                    </div>
                    
                    <div class="mt-6 flex flex-col gap-3">
                        <div class="flex justify-between items-center text-xs border-b border-slate-700/50 pb-2">
                            <span class="text-slate-500">Último paquete:</span>
                            <span id="last-update-time" class="font-semibold text-slate-300 font-mono">Esperando...</span>
                        </div>
                        <div class="flex justify-between items-center text-xs border-b border-slate-700/50 pb-2">
                            <span class="text-slate-500">Formato del canal:</span>
                            <span class="font-mono text-slate-300">8 Bits, Sin paridad, 1 Stop</span>
                        </div>
                    </div>
                </div>

                <div class="bg-blue-950/20 border border-blue-500/20 rounded-xl p-4 mt-6">
                    <p class="text-xs text-blue-300 leading-relaxed font-semibold">
                        ℹ️ El script decodifica automáticamente la cadena JSON. Si ocurre una desconexión en el cableado, el sistema entra en modo de auto-recuperación sin interrupción.
                    </p>
                </div>
            </section>

        </main>

        <footer class="text-center text-xs text-slate-500 py-4">
            Laboratorio Especial ESP32 - Raspberry Pi &bull; Universidad Nacional de Colombia
        </footer>
    </div>

    <script>
        // Configuración de Chart.js
        const ctx = document.getElementById('telemetryChart').getContext('2d');
        const telemetryChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array.from({length: 30}, (_, i) => ''),
                datasets: [
                    {
                        label: 'Temp (°C)',
                        data: Array(30).fill(null),
                        borderColor: '#6366f1',
                        borderWidth: 3,
                        pointRadius: 0,
                        tension: 0.35,
                        fill: false
                    },
                    {
                        label: 'Hum (%)',
                        data: Array(30).fill(null),
                        borderColor: '#06b6d4',
                        borderWidth: 3,
                        pointRadius: 0,
                        tension: 0.35,
                        fill: false
                    },
                    {
                        label: 'Luz (%)',
                        data: Array(30).fill(null),
                        borderColor: '#f59e0b',
                        borderWidth: 3,
                        pointRadius: 0,
                        tension: 0.35,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#e2e8f0',
                            font: { family: 'Outfit', weight: 'bold' }
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false } },
                    y: { 
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#94a3b8' },
                        min: 0,
                        max: 100
                    }
                }
            }
        });

        // Actualizar datos del dashboard periódicamente
        async function updateDashboard() {
            try {
                const response = await fetch('/data');
                const data = await response.json();

                // 1. Actualizar Badge de Conexión
                const badge = document.getElementById('status-badge');
                const text = document.getElementById('status-text');
                
                if (data.connected) {
                    badge.className = "flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-bold bg-green-500/20 text-green-400 border border-green-500/30 transition-all duration-300 glow-green";
                    text.innerText = "CONECTADO";
                } else {
                    badge.className = "flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-bold bg-red-500/20 text-red-400 border border-red-500/30 transition-all duration-300 glow-red";
                    text.innerText = "DESCONECTADO";
                }

                // 2. Actualizar displays numéricos
                document.getElementById('temp-val').innerText = data.temp.toFixed(1);
                document.getElementById('hum-val').innerText = data.hum.toFixed(1);
                
                // Conversión de luz ADC (0-4095) a porcentaje (0-100%)
                const lightPct = Math.round((data.light / 4095.0) * 100);
                document.getElementById('light-pct').innerText = lightPct;
                document.getElementById('light-raw').innerText = `Raw: ${data.light} / 4095`;
                
                document.getElementById('last-update-time').innerText = data.last_update;

                // 4. Actualizar formato del payload simulado para inspección
                document.getElementById('json-payload').innerText = JSON.stringify({
                    "t": parseFloat(data.temp.toFixed(2)),
                    "h": parseFloat(data.hum.toFixed(1)),
                    "l": data.light
                }, null, 2);

                // 5. Actualizar Gráfico
                if (data.history_temp && data.history_temp.length > 0) {
                    const maxLen = 30;
                    
                    // Rellenar con nulos al inicio si hay menos de 30 elementos
                    const padding = Array(Math.max(0, maxLen - data.history_temp.length)).fill(null);
                    
                    const padAndSlice = (history) => padding.concat(history.slice(-maxLen));
                    
                    telemetryChart.data.datasets[0].data = padAndSlice(data.history_temp);
                    telemetryChart.data.datasets[1].data = padAndSlice(data.history_hum);
                    
                    // Convertir historial de luz a porcentaje para el gráfico
                    const lightHistPct = data.history_light.map(l => (l / 4095.0) * 100);
                    telemetryChart.data.datasets[2].data = padAndSlice(lightHistPct);
                    
                    telemetryChart.update('none'); // Actualización rápida y suave sin retrasos
                }
            } catch (error) {
                console.error("Error cargando datos del backend:", error);
            }
        }

        updateDashboard();
        setInterval(updateDashboard, 500);
    </script>
</body>
</html>
"""

# HILO DEL SERVIDOR WEB HTTP
def run_web_server():
    server = ThreadingHTTPServer(('0.0.0.0', PORT_HTTP), DashboardHandler)
    print(f"[HTTP] Dashboard disponible en: http://localhost:{PORT_HTTP}")
    try:
        server.serve_forever()
    except Exception as e:
        print(f"[HTTP ERROR] {e}")

# HILO PRINCIPAL DE LECTURA UART (Procesador de trama JSON con auto-reconexión)
def main():
    # Lanzar el servidor web HTTP en segundo plano
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    print(f"[-] UART Multi-Sensor iniciado ({PORT_UART} @ {BAUDRATE}). Ctrl+C para salir.")

    while True:
        uart = None
        try:
            # Establecer comunicación UART con la ESP32
            uart = serial.Serial(port=PORT_UART, baudrate=BAUDRATE, timeout=1)
            uart.reset_input_buffer()
            uart.reset_output_buffer()
            
            with state_lock:
                system_state["connected"] = True
            print(f"[OK] UART Conectado con la ESP32.")
            
            while True:
                if uart.in_waiting > 0:
                    datos = uart.readline()
                    texto = datos.decode('utf-8', errors='ignore').strip()
                    
                    if texto:
                        try:
                            # Intentar deserializar trama JSON
                            payload = json.loads(texto)
                            temp = float(payload.get("t", 0.0))
                            hum = float(payload.get("h", 0.0))
                            light = int(payload.get("l", 0))
                            hora_actual = time.strftime("%H:%M:%S")
                            
                            # Actualizar estado compartido
                            with state_lock:
                                system_state["connected"] = True
                                system_state["temp"] = temp
                                system_state["hum"] = hum
                                system_state["light"] = light
                                system_state["last_update"] = hora_actual
                                
                                # Guardar historiales limitados a 30 elementos
                                system_state["history_temp"].append(temp)
                                system_state["history_hum"].append(hum)
                                system_state["history_light"].append(light)
                                
                                for key in ["history_temp", "history_hum", "history_light"]:
                                    if len(system_state[key]) > 30:
                                        system_state[key].pop(0)
                                        
                            print(f"[RX] JSON: T={temp}°C | H={hum}% | L={light}")
                            
                            # Enviar respuesta de eco de vuelta a la ESP32
                            respuesta = f"Eco RPi OK\n"
                            uart.write(respuesta.encode('utf-8'))
                            
                        except (json.JSONDecodeError, ValueError) as e:
                            # En caso de ruido eléctrico o tramas no formateadas, registrar pero no detener
                            print(f"[RUIDO/TEXTO RAW] Recibido: '{texto}'")
                            
                time.sleep(0.05)

        except (serial.SerialException, OSError) as e:
            # Desconexión física en curso
            with state_lock:
                system_state["connected"] = False
                system_state["temp"] = 0.0
                system_state["hum"] = 0.0
                system_state["light"] = 0
            print(f"[ERROR] UART Desconectado: {e}")
            
            if uart is not None:
                try:
                    uart.close()
                except Exception:
                    pass
            
            print("[+] Reintentando conexion UART en 2s...")
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\n[-] Finalizando servicios...")
            if uart is not None:
                try:
                    uart.close()
                except Exception:
                    pass
            break

if __name__ == "__main__":
    main()
