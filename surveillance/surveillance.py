#!/usr/bin/env python3
# Tonys OpenSurv Pro
# A modernization and fork of the original OpenSurv project (github.com/OpenSurv/OpenSurv)
# Licensed under GNU GPL v2.0
import os
import signal
import sys
import time
import threading
import platform
import psutil
import socket
import logging
import threading
import requests
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import Xlib.display

from core.util.config import cfg
from core.util.setuplogging import setup_logging
from core.ScreenManager import ScreenManager

# Version Info
fullversion_for_installer="Tonys OpenSurv Pro v2.1.0"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TonysOpenSurvPro")

# Get absolute path for the web directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, 'web')

# Initialize Flask App
app = Flask(__name__, 
            static_folder=os.path.join(WEB_DIR, 'static'), 
            template_folder=os.path.join(WEB_DIR, 'templates'))
CORS(app)

screenmanagers = []
monitors = []

def get_monitors():
    try:
        display = Xlib.display.Display()
        root = display.screen().root

        monitor_list = []
        for i, m in enumerate(root.xrandr_get_monitors().monitors):
            connector = display.get_atom_name(m.name)
            monitor_dict = {
                "xdisplay_id": ":0.0",
                "monitor_id": connector,
                "monitor_number": i,
                "resolution": {
                    "width": m.width_in_pixels,
                    "height": m.height_in_pixels
                },
                "x_offset": m.x,
                "y_offset": m.y
            }
            monitor_list.append(monitor_dict)
        return monitor_list
    except Exception as e:
        print(f"Error detecting monitors: {e}")
        return [{
            "xdisplay_id": ":0.0",
            "monitor_id": "DEFAULT",
            "monitor_number": 0,
            "resolution": {"width": 1920, "height": 1080},
            "x_offset": 0,
            "y_offset": 0
        }]

def get_system_info():
    """Gathers technical specs of the host system"""
    try:
        # Get Network IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()

        # Get RPi Model if available
        model = "Unknown Hardware"
        model_paths = ["/proc/device-tree/model", "/sys/firmware/devicetree/base/model"]
        for path in model_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r") as f:
                        model = f.read().strip('\0').strip()
                        break
                except Exception:
                    continue

        return {
            "os": f"{platform.system()} {platform.release()}",
            "hardware": model,
            "cpu_usage": f"{psutil.cpu_percent()}%",
            "memory": f"{psutil.virtual_memory().percent}%",
            "uptime": int(time.time() - psutil.boot_time()),
            "ip_address": ip,
            "hostname": socket.gethostname(),
            "python_version": platform.python_version()
        }
    except Exception as e:
        logger.error(f"Error gathering system info: {e}")
        return {}

# --- API Endpoints ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def status():
    try:
        sm_status = []
        for sm in screenmanagers:
            try:
                sm_status.append(sm.get_status())
            except Exception as e:
                logger.error(f"API: Error getting status for {sm.name}: {e}")
        
        return jsonify({
            "status": "online",
            "version": "2.0-PRO",
            "monitors": monitors,
            "screenmanagers": sm_status,
            "system": get_system_info()
        })
    except Exception as e:
        logger.error(f"API: Global status error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/restart-service', methods=['POST'])
def restart_service():
    """Restarts the OpenSurv process"""
    logger.info("API: Restarting OpenSurv service...")
    def restart():
        time.sleep(1)
        os.execv(sys.executable, ['python3'] + sys.argv)
    
    threading.Thread(target=restart).start()
    return jsonify({"status": "success", "message": "Restarting..."})

@app.route('/api/reboot-host', methods=['POST'])
def reboot_host():
    """Reboots the entire host machine"""
    logger.info("API: Rebooting host machine...")
    def reboot():
        time.sleep(1)
        os.system('sudo reboot')
    
    threading.Thread(target=reboot).start()
    return jsonify({"status": "success", "message": "Rebooting host..."})

# Remote Management APIs
@app.route('/api/check-update')
def check_update():
    try:
        # Load local version
        version_path = os.path.join(BASE_DIR, 'version.txt')
        with open(version_path, 'r') as f:
            local_version = f.read().strip()
        
        # Check GitHub for latest version (with cache busting)
        import time
        repo_url = f"https://raw.githubusercontent.com/BigTonyTones/OpenSurvPro/main/version.txt?t={int(time.time())}"
        response = requests.get(repo_url, timeout=5)
        if response.status_code == 200:
            remote_version = response.text.strip()
            
            # Proper semantic version comparison (only update if remote > local)
            def version_to_tuple(v):
                try:
                    return tuple(map(int, (v.split('.'))))
                except:
                    return (0, 0, 0)
            
            update_available = version_to_tuple(remote_version) > version_to_tuple(local_version)
            
            return jsonify({
                "local": local_version,
                "remote": remote_version,
                "update_available": update_available
            })
    except Exception as e:
        logger.error(f"Error checking for updates: {e}")
    
    return jsonify({"update_available": False, "error": "Could not reach update server"})

@app.route('/api/network-status')
def get_network_status():
    try:
        # Get active connection details
        ip_cmd = "hostname -I | awk '{print $1}'"
        ip_addr = subprocess.check_output(ip_cmd, shell=True).decode().strip()
        
        wifi_cmd = "nmcli -t -f active,ssid dev wifi | grep '^yes' | cut -d: -f2"
        try:
            wifi_ssid = subprocess.check_output(wifi_cmd, shell=True).decode().strip()
        except:
            wifi_ssid = "Not Connected"

        # Scan for nearby networks (limited to 5 for speed)
        scan_cmd = "nmcli -t -f ssid dev wifi list | head -n 5"
        try:
            networks = subprocess.check_output(scan_cmd, shell=True).decode().split('\n')
            networks = [n for n in networks if n]
        except:
            networks = []

        return jsonify({
            "status": "success",
            "ip": ip_addr,
            "ssid": wifi_ssid,
            "available": networks
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/network-configure', methods=['POST'])
def configure_network():
    try:
        data = request.json
        mode = data.get('mode') # 'wifi' or 'static'
        
        if mode == 'wifi':
            ssid = data.get('ssid')
            psk = data.get('password')
            # Use nmcli to connect
            cmd = f"sudo nmcli dev wifi connect '{ssid}' password '{psk}'"
            subprocess.check_call(cmd, shell=True)
            return jsonify({"status": "success", "message": f"Connecting to {ssid}..."})
            
        elif mode == 'static':
            iface = data.get('interface', 'eth0')
            ip = data.get('ip')
            gw = data.get('gateway')
            dns = data.get('dns', '8.8.8.8')
            
            # nmcli commands for static IP
            # We assume a connection already exists, we modify it
            conn_name = subprocess.check_output(f"nmcli -t -f name,device connection show --active | grep {iface} | cut -d: -f1", shell=True).decode().strip()
            if not conn_name:
                return jsonify({"status": "error", "message": f"No active connection found on {iface}"})
            
            subprocess.check_call(f"sudo nmcli connection modify '{conn_name}' ipv4.addresses {ip}/24 ipv4.gateway {gw} ipv4.dns {dns} ipv4.method manual", shell=True)
            subprocess.Popen(f"sudo nmcli connection up '{conn_name}'", shell=True) # Async because we might lose connection
            
            return jsonify({"status": "success", "message": "Static IP applied. Connection may reset."})

    except Exception as e:
        logger.error(f"Network config failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/update-log')
def get_update_log():
    try:
        if os.path.exists('/tmp/opensurv_update.log'):
            with open('/tmp/opensurv_update.log', 'r') as f:
                # Return the last 50 lines to keep it snappy
                lines = f.readlines()
                return jsonify({"status": "success", "log": "".join(lines[-50:])})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    return jsonify({"status": "success", "log": "Waiting for installer to start..."})

@app.route('/api/perform-update', methods=['POST'])
def perform_update():
    try:
        logger.info("Remote update requested. Starting update script in background...")
        # Clear old log
        with open('/tmp/opensurv_update.log', 'w') as f:
            f.write("Starting Tonys OpenSurv Pro Update...\n")
        
        # Determine if we need sudo (not needed if already root)
        sudo_prefix = "sudo " if os.geteuid() != 0 else ""
        
        # Log diagnostic info
        with open('/tmp/opensurv_update.log', 'a') as f:
            f.write(f"App Directory: {BASE_DIR}\n")
        
        # Determine the project path (where the git repo is)
        repo_path_file = os.path.join(BASE_DIR, '.repo_path')
        if os.path.exists(repo_path_file):
            with open(repo_path_file, 'r') as f:
                project_path = f.read().strip()
        else:
            project_path = "/home/tony/OpenSurvPro"
            
        if not os.path.exists(project_path):
             with open('/tmp/opensurv_update.log', 'a') as f:
                f.write(f"ERROR: Project path {project_path} not found!\n")
             return jsonify({"status": "error", "message": "Project path not found"}), 404

        # Disable git prompts to prevent hanging
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        
        update_cmd = f"cd {project_path} && git fetch --all && git reset --hard origin/main && {sudo_prefix}./install.sh --auto --no-kill-server"
        
        # Log diagnostic info
        with open('/tmp/opensurv_update.log', 'a') as f:
            f.write(f"Checking project at: {project_path}\n")
            f.write(f"Executing update command...\n")

        # Use a single string for shell execution and ensure output is flushed
        subprocess.Popen(update_cmd, 
                        shell=True,
                        env=env,
                        stdout=open('/tmp/opensurv_update.log', 'a', buffering=1),
                        stderr=subprocess.STDOUT,
                        start_new_session=True)
        return jsonify({"status": "success", "message": "Update started."})
    except Exception as e:
        logger.error(f"Failed to start update: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/stop-service', methods=['POST'])
def stop_service():
    """Stops the OpenSurv service (and LightDM)"""
    logger.info("API: Stopping OpenSurv service...")
    def stop():
        time.sleep(1)
        os.system('sudo systemctl stop lightdm')
        os.system('pkill -f surveillance.py')
    
    threading.Thread(target=stop).start()
    return jsonify({"status": "success", "message": "Stopping service..."})

@app.route('/api/next', methods=['POST'])
def next_screen():
    for sm in screenmanagers:
        sm.rotate_next()
    return jsonify({"status": "success"})

@app.route('/api/toggle-rotation', methods=['POST'])
def toggle_rotation():
    for sm in screenmanagers:
        sm.disable_autorotation = not sm.disable_autorotation
    return jsonify({"status": "success"})

@app.route('/api/reload', methods=['POST'])
def reload_config():
    # In a real implementation, this would re-initialize everything
    return jsonify({"status": "not_implemented_yet"})

def run_web_server():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

# --- Main Application Logic ---

def handle_input(background_drawinstance):
    event = background_drawinstance.check_input()
    if event is None:
        return

    for sm in screenmanagers:
        if event == "next_event":
            sm.rotate_next()
        elif event == "end_event":
            cleanup_and_exit()
        elif event == "resume_rotation":
            sm.disable_autorotation = False
        elif event == "pause_rotation":
            sm.disable_autorotation = True
        elif isinstance(event, int):
            sm.force_show_screen(event)

def cleanup_and_exit():
    logger.info("MAIN: Shutting down...")
    for sm in screenmanagers:
        sm.destroy()
    sys.exit(0)

def sigterm_handler(_signo, _stack_frame):
    cleanup_and_exit()

if __name__ == '__main__':
    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGINT, sigterm_handler)

    logger = setup_logging()
    VERSION = "2.0-PRO"
    logger.info(f"Starting OpenSurv PRO {VERSION}")

    # Detect monitors
    monitors = get_monitors()
    logger.info(f"Detected {len(monitors)} monitors")

    # Initialize ScreenManagers
    for i, monitor in enumerate(monitors):
        disable_pygame = (i != 0)
        enable_caching = cfg.get('advanced', {}).get('enable_caching_next_screen', True)
        sm = ScreenManager(f'manager_{i}', monitor, enable_caching, disable_pygame)
        screenmanagers.append(sm)

    # Bootstrap
    for sm in screenmanagers:
        sm.bootstrap()

    # Start Web Server in Background
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    logger.info("Web Dashboard started at http://localhost:5000")

    # Main Loop
    interval_check = cfg.get('advanced', {}).get('interval_check_status', 20)
    loop_counter = 0

    while True:
        try:
            loop_counter += 1
            
            # Key Handling
            if screenmanagers:
                handle_input(screenmanagers[0].get_background_drawinstance())

            for sm in screenmanagers:
                # Autorotation logic
                if not sm.get_disable_autorotation():
                    if sm.get_active_screen_run_time() >= sm.get_active_screen_duration():
                        sm.rotate_next()
                        sm.update_active_screen()

                # Health Check / Watchdog (every interval_check seconds)
                if loop_counter % interval_check == 0:
                    sm.update_active_screen()
                    sm.run_watchdogs_active_screen()

                # Refocus for key handling
                sm.focus_background_pygame()

            time.sleep(1)
        except Exception as e:
            logger.error(f"MAIN CRASH: {e}")
            cleanup_and_exit()