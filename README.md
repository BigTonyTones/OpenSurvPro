# Tonys OpenSurv Pro - Advanced Open Source Surveillance v2.1.7

OpenSurv PRO is a major modernization of the original OpenSurv project, designed to transform your Raspberry Pi or compatible Linux device into a professional-grade, high-performance surveillance station. 

OpenSurv PRO focuses on **Premium Aesthetics**, **Remote Management**, and **Low-Latency Performance**.

---

## New PRO Features

### Modern Web Dashboard
Control your entire surveillance station remotely from any device on your network (Desktop, Tablet, or Mobile).
- **Live Status**: Real-time monitoring of all active streams, monitors, and screens.
- **Remote Control**: Switch screens, pause/resume rotation, restart services, or reboot the host machine with a single click.
- **System Telemetry**: Live spec monitoring including OS version, Raspberry Pi hardware model, CPU/Memory usage, and Uptime.
- **Tonys OpenSurv Gui Editor**: Now included by default! A powerful drag-and-drop YAML editor to easily manage your camera layouts and configs.
  
  ![GUI Editor Preview](https://raw.githubusercontent.com/BigTonyTones/Tonys-OpenSurv-Gui-Editor/main/assets/preview_layout_example.png)
- **Integrated Manager**: Quick link access to the GUI Editor and system management at the top of the dashboard.
- **Access**: Available by default at `http://<your-device-ip>:5000` (Dashboard) and `http://<your-device-ip>:6453` (GUI Editor).

### Premium Aesthetics
The entire visual engine has been overhauled for a state-of-the-art look:
- **Deep-Space Gradients**: Replaced solid black backgrounds with dynamic vertical gradients.
- **Glassmorphism UI**: High-fidelity UI elements with alpha-transparency, subtle borders, and modern typography.
- **Smooth Transitions**: Refined screen switching and status overlays.

### Low-Latency Performance
Specifically optimized for high-density monitoring on low-power hardware like the Raspberry Pi:
- **Parallel Startup**: All camera streams launch simultaneously, reducing startup delay from 20+ seconds to just ~3 seconds.
- **Multi-Threaded Probing**: Connectivity checks are performed in parallel, eliminating linear bottlenecks.
- **Optimized Playback**: Pre-configured with low-latency `mpv` profiles, zero-caching, and hardware-accelerated decoding paths.

---

## Standard Features

- **Self-Healing Watchdogs**: Every stream is monitored. If a feed drops, the watchdog automatically restarts it.
- **Auto-Layout**: Coordinates are automatically calculated for any number of streams to perfectly fill your monitor.
- **Autorotation**: Configure multiple screens to cycle automatically or switch them manually via the dashboard or keyboard.
- **Multi-Monitor Support**: Auto-detects dual monitors at boot and manages them independently.
- **Vertical Support**: Easily rotate individual screens 90 degrees for portrait monitors.

---

## One-Line Installation

Run this command on your device to install OpenSurv PRO automatically:
```bash
git clone https://github.com/BigTonyTones/OpenSurvPro.git && cd OpenSurvPro && sudo ./install.sh
```

## Getting Started

### Option 1: One-Liner (Recommended)
Execute the command above in your terminal and follow the prompts.

### Option 2: Manual Steps
1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/BigTonyTones/OpenSurvPro.git
    cd OpenSurvPro
    ```
2.  **Run the Installer**:
    ```bash
    sudo ./install.sh
    ```
3.  **Access the Dashboard**:
    Open your browser to `http://<device-ip>:5000` to begin managing your station.

---

## Configuration

Configuration is managed via YAML files in `/etc/opensurv/`:
- **`general.yml`**: System-wide settings and API configuration.
- **`monitor1.yml`**: Define screens and camera streams for the primary monitor.
- **`monitor2.yml`**: Settings for the secondary monitor (if connected).

---

## Operation & Controls

### Web Interface
- Access `http://<device-ip>:5000` for full remote control.

### Keyboard Shortcuts
- **`n` / `Space`**: Force next screen.
- **`p`**: Pause/Resume autorotation.
- **`q`**: Stop OpenSurv.
- **`F1` - `F12`**: Switch directly to a specific screen index.

---

## Troubleshooting

- **Logs**: Located at `/home/opensurv/logs/main.log`.
- **API Status**: Check `http://<ip>:5000/api/status` for raw system health data.
- **Manual Stop**: `sudo systemctl stop lightdm`
- **Manual Start**: `sudo systemctl start lightdm`

---

## Credits & Attribution
**Tonys OpenSurv Pro** is a community-driven modernization and fork of the original **OpenSurv** project. We would like to thank the original authors and contributors for providing the robust foundation this professional version is built upon.

- **Original Project**: [OpenSurv](https://github.com/OpenSurv/OpenSurv)
- **License**: This project is licensed under the [GNU General Public License v2.0](LICENSE).

---

## License & Community
OpenSurv PRO is based on the original OpenSurv project and is provided as-is for the community.
- **Discussions**: [GitHub Discussions](https://github.com/BigTonyTones/OpenSurvPro/discussions)
- **Issues**: [GitHub Issues](https://github.com/BigTonyTones/OpenSurvPro/issues)