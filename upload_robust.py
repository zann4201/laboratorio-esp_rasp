import paramiko

IPS = ["192.168.1.17", "192.168.0.12"]
USER = "alex"
PASSWORD = "motas177"
LOCAL_FILE = "raspberry_uart.py"
REMOTE_FILE = "/home/alex/raspberry_uart.py"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

connected = False
for host in IPS:
    try:
        print(f"[+] Intentando conectar a {host}...")
        ssh.connect(host, username=USER, password=PASSWORD, timeout=5)
        print(f"[OK] Conectado exitosamente a {host}!")
        connected = True
        break
    except Exception as e:
        print(f"[-] Fallo conexion a {host}: {e}")

if connected:
    try:
        print(f"[+] Subiendo archivo robusto con auto-reconexion...")
        sftp = ssh.open_sftp()
        sftp.put(LOCAL_FILE, REMOTE_FILE)
        sftp.close()
        
        # Dar permisos de ejecucion
        ssh.exec_command(f"chmod +x {REMOTE_FILE}")
        print("[OK] ¡Archivo robusto actualizado exitosamente en la Raspberry Pi!")
    except Exception as e:
        print(f"[ERROR] Error al subir archivo: {e}")
    finally:
        ssh.close()
else:
    print("[ERROR] No se pudo conectar a la Raspberry Pi en ninguna de las IPs.")
