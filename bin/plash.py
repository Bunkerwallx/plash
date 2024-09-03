import os
import subprocess
import platform

# Ruta al script que debe ser persistente
script_path = r"C:\path\to\your\bot_script.py" if platform.system() == "Windows" else "/path/to/your/bot_script.py"

### PERSISTENCIA EN WINDOWS ###
def create_scheduled_task():
    task_name = "PersistentBotTask"
    command = f'schtasks /create /tn {task_name} /tr "python {script_path}" /sc onlogon /ru SYSTEM'
    
    try:
        subprocess.run(command, shell=True, check=True)
        print(f"Tarea programada '{task_name}' creada exitosamente.")
    except subprocess.CalledProcessError:
        print("Error al crear la tarea programada.")

def add_registry_persistence():
    try:
        import winreg as reg
        key = reg.HKEY_CURRENT_USER
        sub_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        reg_key = reg.OpenKey(key, sub_key, 0, reg.KEY_SET_VALUE)
        reg.SetValueEx(reg_key, "PersistentBot", 0, reg.REG_SZ, f'python {script_path}')
        reg.CloseKey(reg_key)
        print("Persistencia agregada al registro.")
    except ImportError:
        print("El módulo winreg no está disponible.")
    except WindowsError as e:
        print(f"Error al agregar persistencia al registro: {e}")

### PERSISTENCIA EN LINUX ###
def create_systemd_service():
    service_file = f"""
    [Unit]
    Description=Persistent Bot Script

    [Service]
    ExecStart=/usr/bin/python3 {script_path}
    Restart=always

    [Install]
    WantedBy=multi-user.target
    """
    with open("/etc/systemd/system/bot_service.service", "w") as service:
        service.write(service_file)
    try:
        subprocess.run(["systemctl", "enable", "bot_service.service"], check=True)
        subprocess.run(["systemctl", "start", "bot_service.service"], check=True)
        print("Servicio systemd creado y activado.")
    except subprocess.CalledProcessError:
        print("Error al crear o activar el servicio systemd.")

def add_cron_job():
    cron_command = f"@reboot /usr/bin/python3 {script_path}"
    try:
        subprocess.run(f'(crontab -l; echo "{cron_command}") | crontab -', shell=True, check=True)
        print("Cron job agregado para persistencia.")
    except subprocess.CalledProcessError:
        print("Error al agregar cron job.")

### SELECCIÓN DEL MÉTODO DE PERSISTENCIA SEGÚN EL SISTEMA OPERATIVO ###
def setup_persistence():
    if platform.system() == "Windows":
        create_scheduled_task()
        add_registry_persistence()
    elif platform.system() == "Linux":
        create_systemd_service()
        add_cron_job()
    else:
        print("Sistema operativo no soportado.")

# Ejecutar la configuración de persistencia
setup_persistence()
