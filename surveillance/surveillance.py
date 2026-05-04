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
import yaml

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

@app.route('/api/mpv-config', methods=['GET', 'POST'])
def mpv_config():
    if request.method == 'GET':
        return jsonify({"args": cfg.get('mpv', {}).get('default_args', '')})
    
    # POST
    try:
        new_args = request.json.get('args', '')
        if 'mpv' not in cfg:
            cfg['mpv'] = {}
        cfg['mpv']['default_args'] = new_args
        
        # Save to file
        config_path = os.path.join(BASE_DIR, 'etc', 'general.yml')
        with open(config_path, 'w') as f:
            yaml.dump(cfg, f, default_flow_style=False)
        
        return jsonify({"status": "success", "message": "MPV arguments updated"})
    except Exception as e:
        logger.error(f"API: Error saving MPV config: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

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