#!/usr/bin/python3
import os
import signal
import sys
import time
import threading
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import Xlib.display

from core.util.config import cfg
from core.util.setuplogging import setup_logging
from core.ScreenManager import ScreenManager

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

# --- API Endpoints ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def status():
    return jsonify({
        "status": "online",
        "version": "2.0-PRO",
        "monitors": monitors,
        "screenmanagers": [sm.get_status() for sm in screenmanagers]
    })

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