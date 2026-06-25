"""
<plugin key="TPLinkRouter" name="TP-Link Router" author="4D" version="1.0.0"
        wikilink="https://github.com/YOUR_USERNAME/Domoticz-TPLinkRouter"
        externallink="https://github.com/YOUR_USERNAME/Domoticz-TPLinkRouter">
    <description>
        <h2>TP-Link Router</h2><br/>
        Controls and monitors TP-Link compatible routers using tplinkrouterc6u.
    </description>
    <params>
        <param field="Address" label="Router IP / Host" width="200px" required="true" default="192.168.0.1"/>
        <param field="Username" label="Username" width="120px" required="true" default="admin"/>
        <param field="Password" label="Password" width="200px" required="true" password="true"/>
        <param field="Mode1" label="Poll interval (seconds)" width="80px" required="true" default="180"/>
        <param field="Mode2" label="Scheme" width="120px">
            <options>
                <option label="HTTPS" value="https" default="true"/>
                <option label="HTTP" value="http"/>
            </options>
        </param>
        <param field="Mode3" label="Verify SSL" width="120px">
            <options>
                <option label="False" value="false" default="true"/>
                <option label="True" value="true"/>
            </options>
        </param>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="Normal" value="Normal" default="true"/>
                <option label="Debug" value="Debug"/>
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz
import traceback
import warnings
import os
import sys
import glob
import time
import threading
import queue

warnings.filterwarnings("ignore")

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_SITE_PACKAGES = glob.glob(
    os.path.join(PLUGIN_DIR, "venv", "lib", "python*", "site-packages")
)

for path in VENV_SITE_PACKAGES:
    if path not in sys.path:
        sys.path.insert(0, path)

import urllib3
urllib3.disable_warnings()

from tplinkrouterc6u import TplinkRouterProvider, Connection

# Units
UNIT_WIFI_24 = 1
UNIT_WIFI_5 = 2
UNIT_INTERNET = 3
UNIT_CLIENTS = 4
UNIT_WIFI_CLIENTS = 5
UNIT_WIRED_CLIENTS = 6
UNIT_GUEST_CLIENTS = 7
UNIT_GUEST_WIFI_24 = 8
UNIT_GUEST_WIFI_5 = 9

CONTROL_UNIT_CONNECTIONS = {
    UNIT_WIFI_24: Connection.HOST_2G,
    UNIT_WIFI_5: Connection.HOST_5G,
    UNIT_GUEST_WIFI_24: Connection.GUEST_2G,
    UNIT_GUEST_WIFI_5: Connection.GUEST_5G,
}


class BasePlugin:
    def __init__(self):
        self.poll_interval = 180
        self.heartbeat_interval = 10
        self.heartbeat_counter = 0

        self.busy = False
        self.command_queue = queue.Queue()
        self.command_worker = None
        self.worker_stop = threading.Event()
        self.lock = threading.Lock()
        self.last_worker_error = None

    def log(self, msg):
        Domoticz.Log(f"TPLinkRouter: {msg}")

    def debug(self, msg):
        if Parameters["Mode6"] == "Debug":
            Domoticz.Debug(f"TPLinkRouter: {msg}")

    def error(self, msg):
        Domoticz.Error(f"TPLinkRouter: {msg}")

    def router_url(self):
        scheme = Parameters["Mode2"] if Parameters["Mode2"] else "https"
        host = Parameters["Address"].strip()
        if host.startswith("http://") or host.startswith("https://"):
            return host
        return f"{scheme}://{host}"

    def verify_ssl(self):
        return str(Parameters["Mode3"]).lower() == "true"

    def get_client(self):
        return TplinkRouterProvider.get_client(
            self.router_url(),
            Parameters["Password"],
            Parameters["Username"],
            verify_ssl=self.verify_ssl()
        )

    def ensure_switch(self, unit, name):
        if unit not in Devices:
            Domoticz.Device(
                Name=name,
                Unit=unit,
                Type=244,
                Subtype=73,
                Switchtype=0,
                Used=1
            ).Create()

    def ensure_counter(self, unit, name):
        if unit not in Devices:
            Domoticz.Device(
                Name=name,
                Unit=unit,
                Type=243,
                Subtype=31,
                Switchtype=0,
                Options={"Custom": "1;Count"},
                Used=1
            ).Create()

    def ensure_devices(self):
        self.ensure_switch(UNIT_WIFI_24, "WiFi 2.4G")
        self.ensure_switch(UNIT_WIFI_5, "WiFi 5G")
        self.ensure_switch(UNIT_INTERNET, "Internet")
        self.ensure_counter(UNIT_CLIENTS, "Connected Clients")
        self.ensure_counter(UNIT_WIFI_CLIENTS, "WiFi Clients")
        self.ensure_counter(UNIT_WIRED_CLIENTS, "Wired Clients")
        self.ensure_counter(UNIT_GUEST_CLIENTS, "Guest Clients")
        self.ensure_switch(UNIT_GUEST_WIFI_24, "Guest WiFi 2.4G")
        self.ensure_switch(UNIT_GUEST_WIFI_5, "Guest WiFi 5G")

    def update_switch(self, unit, is_on):
        nValue = 1 if is_on else 0
        sValue = "On" if is_on else "Off"

        if unit in Devices:
            dev = Devices[unit]
            if dev.nValue != nValue or dev.sValue != sValue:
                self.debug(f"Updating unit {unit} => {sValue}")
                dev.Update(nValue=nValue, sValue=sValue)

    def update_counter(self, unit, value):
        if unit in Devices:
            dev = Devices[unit]
            value_str = str(value)
            if dev.sValue != value_str:
                dev.Update(nValue=0, sValue=value_str)

    def update_from_status(self, status):
        self.update_switch(UNIT_WIFI_24, bool(status.wifi_2g_enable))
        self.update_switch(UNIT_WIFI_5, bool(status.wifi_5g_enable))
        self.update_switch(
            UNIT_GUEST_WIFI_24,
            bool(getattr(status, "guest_2g_enable", False))
        )
        self.update_switch(
            UNIT_GUEST_WIFI_5,
            bool(getattr(status, "guest_5g_enable", False))
        )

        self.update_counter(UNIT_CLIENTS, int(status.clients_total))
        self.update_counter(UNIT_WIFI_CLIENTS, int(status.wifi_clients_total))
        self.update_counter(UNIT_WIRED_CLIENTS, int(status.wired_total))
        self.update_counter(UNIT_GUEST_CLIENTS, int(status.guest_clients_total))

        wan_ip = getattr(status, "wan_ipv4_addr", None)
        online = wan_ip not in (None, "", "0.0.0.0")
        self.update_switch(UNIT_INTERNET, online)

    def get_status_with_retry(self, router, attempts=2, delay=2):
        last_error = None

        for attempt in range(attempts):
            try:
                return router.get_status()
            except Exception as e:
                last_error = e
                if attempt < attempts - 1:
                    time.sleep(delay)

        raise last_error

    def poll_status(self):
        self.debug("Polling router status")
        router = self.get_client()

        try:
            router.authorize()
            status = self.get_status_with_retry(router)
            self.update_from_status(status)
        finally:
            try:
                router.logout()
            except Exception:
                pass

    def send_router_command(self, unit, enable):
        connection = CONTROL_UNIT_CONNECTIONS.get(unit)
        if connection is None:
            self.debug(f"Unit {unit} is not controllable")
            return

        router = self.get_client()
        try:
            router.authorize()
            router.set_wifi(connection, enable)
        finally:
            try:
                router.logout()
            except Exception:
                pass

    def command_worker_loop(self):
        self.debug("Command worker started")

        while not self.worker_stop.is_set():
            try:
                unit, enable = self.command_queue.get(timeout=1)
            except queue.Empty:
                continue

            try:
                self.debug(f"Processing command unit={unit}, enable={enable}")
                self.send_router_command(unit, enable)
            except Exception as e:
                with self.lock:
                    self.last_worker_error = (
                        f"Command failed for unit {unit}: {e}\n{traceback.format_exc()}"
                    )
            finally:
                self.command_queue.task_done()

        self.debug("Command worker stopped")

    def start_worker(self):
        if self.command_worker is not None and self.command_worker.is_alive():
            return

        self.worker_stop.clear()
        self.command_worker = threading.Thread(
            target=self.command_worker_loop,
            daemon=True
        )
        self.command_worker.start()

    def enqueue_wifi_command(self, unit, command):
        if unit not in CONTROL_UNIT_CONNECTIONS:
            self.log(f"Ignoring command for non-controllable unit {unit}")
            return

        enable = str(command).strip().lower() == "on"

        # Instant visual update in Domoticz.
        # If router state differs, normal polling will correct it later.
        self.update_switch(unit, enable)

        # Keep only latest command for the same unit as much as possible.
        self.command_queue.put((unit, enable))

    def onStart(self):
        self.log("TP-Link Router Plugin v1.0.0")
        self.log(f"Python {sys.version.split()[0]}")
        self.log("Library: tplinkrouterc6u")

        Domoticz.Heartbeat(self.heartbeat_interval)

        if Parameters["Mode6"] == "Debug":
            Domoticz.Debugging(1)

        self.ensure_devices()
        self.start_worker()

        try:
            self.poll_interval = max(30, int(Parameters["Mode1"]))
        except Exception:
            self.poll_interval = 180

        self.log(
            f"Started. Router={self.router_url()}, Poll={self.poll_interval}s, VerifySSL={self.verify_ssl()}"
        )

        try:
            self.busy = True
            self.poll_status()
        except Exception as e:
            self.error(f"Initial poll failed: {e}")
            self.error(traceback.format_exc())
        finally:
            self.busy = False

    def onStop(self):
        self.worker_stop.set()
    
        if self.command_worker is not None:
            self.command_worker.join(timeout=2)
    
        self.log("Stopped.")


    def onCommand(self, Unit, Command, Level, Hue):
        self.debug(f"onCommand Unit={Unit}, Command={Command}, Level={Level}, Hue={Hue}")

        # Return quickly: UI updates immediately, router work is queued.
        self.enqueue_wifi_command(Unit, Command)

    def onHeartbeat(self):
        with self.lock:
            worker_error = self.last_worker_error
            self.last_worker_error = None

        if worker_error:
            self.error(worker_error)

        if self.busy:
            self.debug("Heartbeat skipped: plugin busy")
            return

        self.heartbeat_counter += 1
        elapsed = self.heartbeat_counter * self.heartbeat_interval

        if elapsed < self.poll_interval:
            return

        self.heartbeat_counter = 0

        try:
            self.busy = True
            self.poll_status()
        except Exception as e:
            self.error(f"Polling failed: {e}")
            self.error(traceback.format_exc())
        finally:
            self.busy = False


global _plugin
_plugin = BasePlugin()


def onStart():
    _plugin.onStart()


def onStop():
    _plugin.onStop()


def onCommand(Unit, Command, Level, Hue):
    _plugin.onCommand(Unit, Command, Level, Hue)


def onHeartbeat():
    _plugin.onHeartbeat()
