import os
import socket
import subprocess
import logging
import psutil
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("TonysOpenSurvPro")

def get_network_details():
    """Gathers current IP, Ethernet, and WiFi network telemetry"""
    details = {
        "hostname": socket.gethostname(),
        "model": "Raspberry Pi",
        "eth_ip": None,
        "wifi_ip": None,
        "wifi_ssid": None,
        "primary_ip": "127.0.0.1"
    }

    # Model info
    for path in ["/proc/device-tree/model", "/sys/firmware/devicetree/base/model"]:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    details["model"] = f.read().strip('\0').strip()
                    break
            except Exception:
                pass

    # Primary routing IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 1))
        details["primary_ip"] = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    # Inspect all network interfaces
    try:
        addrs = psutil.net_if_addrs()
        for iface, addr_list in addrs.items():
            for a in addr_list:
                if a.family == socket.AF_INET and not a.address.startswith("127."):
                    if iface.startswith(("eth", "en")):
                        details["eth_ip"] = a.address
                    elif iface.startswith("wl"):
                        details["wifi_ip"] = a.address
    except Exception as e:
        logger.debug(f"Splash: Error reading interface addrs: {e}")

    # Detect WiFi SSID
    try:
        res = subprocess.run(["iwgetid", "-r"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip():
            details["wifi_ssid"] = res.stdout.strip()
    except Exception:
        pass

    if not details["wifi_ssid"]:
        try:
            res = subprocess.run(["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if line.startswith("yes:"):
                        details["wifi_ssid"] = line.split("yes:", 1)[1].strip()
                        break
        except Exception:
            pass

    return details


def generate_splash_image(output_path, version="v2.7.0", width=1920, height=1080):
    """Generates a high-resolution dark mode startup splash image showing system & network telemetry"""
    try:
        net = get_network_details()

        # Create base canvas with a modern dark gradient
        img = Image.new("RGB", (width, height), color=(15, 17, 26))
        draw = ImageDraw.Draw(img)

        # Draw subtle vertical gradient background
        for y in range(height):
            r = int(13 + (24 - 13) * (y / height))
            g = int(16 + (30 - 16) * (y / height))
            b = int(27 + (48 - 27) * (y / height))
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Fonts - load default or truetype if available
        try:
            font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 46)
            font_subtitle = ImageFont.truetype("DejaVuSans.ttf", 24)
            font_section = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
            font_label = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
            font_val = ImageFont.truetype("DejaVuSans.ttf", 22)
            font_footer = ImageFont.truetype("DejaVuSans.ttf", 20)
        except Exception:
            try:
                font_title = ImageFont.truetype("arialbd.ttf", 46)
                font_subtitle = ImageFont.truetype("arial.ttf", 24)
                font_section = ImageFont.truetype("arialbd.ttf", 26)
                font_label = ImageFont.truetype("arialbd.ttf", 22)
                font_val = ImageFont.truetype("arial.ttf", 22)
                font_footer = ImageFont.truetype("arial.ttf", 20)
            except Exception:
                font_title = ImageFont.load_default()
                font_subtitle = font_title
                font_section = font_title
                font_label = font_title
                font_val = font_title
                font_footer = font_title

        # Main Central Card Geometry
        card_w = min(1100, int(width * 0.75))
        card_h = min(620, int(height * 0.65))
        card_x = (width - card_w) // 2
        card_y = (height - card_h) // 2

        # Draw outer card background & border
        draw.rounded_rectangle(
            [card_x, card_y, card_x + card_w, card_y + card_h],
            radius=20,
            fill=(22, 27, 42),
            outline=(60, 75, 110),
            width=2
        )

        # Header Bar inside Card
        draw.text((card_x + 40, card_y + 40), "⚡ TONYS OPENSURV PRO", fill=(96, 165, 250), font=font_title)
        draw.text((card_x + card_w - 180, card_y + 45), version, fill=(148, 163, 184), font=font_subtitle)
        draw.line(
            [(card_x + 40, card_y + 105), (card_x + card_w - 40, card_y + 105)],
            fill=(45, 55, 80),
            width=2
        )

        # Left Column: System & Hardware
        col1_x = card_x + 45
        y_cursor = card_y + 130
        draw.text((col1_x, y_cursor), "SYSTEM & DEVICE", fill=(190, 205, 230), font=font_section)
        
        y_cursor += 45
        draw.text((col1_x, y_cursor), "Device Name:", fill=(148, 163, 184), font=font_label)
        draw.text((col1_x + 160, y_cursor), net["hostname"], fill=(255, 255, 255), font=font_val)

        y_cursor += 38
        draw.text((col1_x, y_cursor), "Hardware:", fill=(148, 163, 184), font=font_label)
        draw.text((col1_x + 160, y_cursor), net["model"], fill=(226, 232, 240), font=font_val)

        y_cursor += 50
        draw.text((col1_x, y_cursor), "NETWORK TELEMETRY", fill=(190, 205, 230), font=font_section)

        y_cursor += 45
        draw.text((col1_x, y_cursor), "Ethernet:", fill=(148, 163, 184), font=font_label)
        eth_text = net["eth_ip"] if net["eth_ip"] else "Disconnected"
        eth_color = (74, 222, 128) if net["eth_ip"] else (148, 163, 184)
        draw.text((col1_x + 160, y_cursor), eth_text, fill=eth_color, font=font_val)

        y_cursor += 38
        draw.text((col1_x, y_cursor), "Wi-Fi (WLAN):", fill=(148, 163, 184), font=font_label)
        wifi_ssid_str = f" ({net['wifi_ssid']})" if net["wifi_ssid"] else ""
        wifi_text = f"{net['wifi_ip']}{wifi_ssid_str}" if net["wifi_ip"] else "Disconnected"
        wifi_color = (74, 222, 128) if net["wifi_ip"] else (148, 163, 184)
        draw.text((col1_x + 160, y_cursor), wifi_text, fill=wifi_color, font=font_val)

        # Right Column: Web Access Portal
        col2_x = card_x + (card_w // 2) + 20
        y_cursor2 = card_y + 130
        draw.text((col2_x, y_cursor2), "MANAGEMENT ACCESS", fill=(190, 205, 230), font=font_section)

        primary_ip = net["eth_ip"] or net["wifi_ip"] or net["primary_ip"]

        y_cursor2 += 45
        draw.text((col2_x, y_cursor2), "Web Dashboard:", fill=(148, 163, 184), font=font_label)
        y_cursor2 += 30
        draw.text((col2_x, y_cursor2), f"http://{primary_ip}:5000", fill=(56, 189, 248), font=font_val)

        y_cursor2 += 50
        draw.text((col2_x, y_cursor2), "GUI Layout Editor:", fill=(148, 163, 184), font=font_label)
        y_cursor2 += 30
        draw.text((col2_x, y_cursor2), f"http://{primary_ip}:6453", fill=(167, 139, 250), font=font_val)

        # Footer Status
        footer_y = card_y + card_h - 60
        draw.line(
            [(card_x + 40, footer_y - 15), (card_x + card_w - 40, footer_y - 15)],
            fill=(45, 55, 80),
            width=1
        )
        draw.text(
            (card_x + 40, footer_y),
            "● Connecting camera streams and preparing displays...",
            fill=(251, 191, 36),
            font=font_footer
        )

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        img.save(output_path)
        logger.info(f"Splash: Startup telemetry image generated at {output_path}")
        return True
    except Exception as e:
        logger.error(f"Splash: Error generating startup splash: {e}")
        return False
