#!/bin/bash

if [ ! "$BASH_VERSION" ] ; then
    echo "ERROR: Please use bash not sh or other shells to run this installer. You can also run this script directly like ./install.sh"
    exit 1
fi

ask_yes_no() {
    local prompt=$1
    local default=$2
    local response
    
    if [ "$default" = "yes" ]; then
        prompt="$prompt [Y/n]: "
    else
        prompt="$prompt [y/N]: "
    fi
    
    read -p "$prompt" response
    response=$(echo "$response" | tr '[:upper:]' '[:lower:]')
    
    if [ -z "$response" ]; then
        echo "$default"
    elif [[ "$response" =~ ^(y|yes)$ ]]; then
        echo "yes"
    else
        echo "no"
    fi
}

show_version() {
    echo "$fullversion_for_installer"
}

configure_lightdm() {
  echo '[Seat:*]
autologin-user=opensurv
#autologin-session=xfce
autologin-session=opensurv
autologin-user-timeout=0' > /etc/lightdm/lightdm.conf
}

set_default_options_mpv() {
  #mpv logging may really fill your disk fast, as a precaution only log fatal errors by default
  echo 'msg-level=all=fatal' > /home/opensurv/.config/mpv/mpv.conf
}

if [ "$(id -u)" -ne 0 ];then echo "ABORT, run this installer as the root user (sudo ./install.sh)"; exit 2; fi

cat << 'EOF'
  ------------------------------------------------------------
       _____                      ____                      
      |_   _|___ ___ _ _ ___ ___|    \ ___ ___ _ _ ___ _ _ 
        | | | . |   | | |_ -| . |  |  | . | -_| | |_ -| | |
        |_| |___|_|_|_  |___|___|____/|___|___|___|___|\_/ 
                    |___|                                   

                T O N Y S   O P E N S U R V
  ------------------------------------------------------------
EOF

BASEPATH="$(cd $(dirname "${BASH_SOURCE[0]}");pwd)"
fullversion_for_installer="Tonys OpenSurv Pro v2.3.0"
AUTO_INSTALL=false
KILL_SERVER=true
for arg in "$@"; do
    if [ "$arg" == "--auto" ]; then AUTO_INSTALL=true; fi
    if [ "$arg" == "--no-kill-server" ]; then KILL_SERVER=false; fi
done

if [ "$AUTO_INSTALL" = false ]; then
    echo "Use this installer on your own risk. Make sure this host does not contain important data and is replacable"
    echo "This installer will configure to boot directly into Opensurv"
    echo
    echo -n "The following version will be installed:"
    show_version
    echo
    echo "Do you want to continue press <Enter>, <Ctrl-C> to cancel"
    read
fi

# --- Step 1: System Preparation ---
echo "Step 1/7: Preparing system and stopping services..."
systemctl stop lightdm > /dev/null 2>&1

if [ "$KILL_SERVER" = true ]; then
    pkill -f surveillance.py 2>/dev/null
fi

# --- Step 2: Dependencies ---
echo "Step 2/7: Installing system and Python dependencies (this may take a minute)..."
apt update > /dev/null 2>&1
apt install --only-upgrade xdotool mpv xfce4 python3-pygame python3-xlib ffmpeg wmctrl unclutter python3-pip -y > /dev/null 2>&1 || \
apt install xdotool mpv xfce4 python3-pygame python3-xlib ffmpeg wmctrl unclutter python3-pip -y > /dev/null 2>&1

pip3 install --upgrade --break-system-packages -r "$BASEPATH/requirements.txt" > /dev/null 2>&1

# --- Step 3: User Configuration ---
echo "Step 3/7: Configuring user permissions and security..."
id -u opensurv > /dev/null 2>&1 || useradd -m opensurv -s /bin/bash
echo "opensurv ALL=(ALL) NOPASSWD: $BASEPATH/install.sh, /usr/bin/nmcli" > /etc/sudoers.d/opensurv
chmod 0440 /etc/sudoers.d/opensurv
configure_lightdm > /dev/null 2>&1

# --- Step 4: Filesystem Initialization ---
echo "Step 4/7: Initializing filesystem and performing backups..."
DESTPATH="/home/opensurv"
mkdir -pv "$DESTPATH"/{etc,lib,logs,bin} > /dev/null 2>&1
echo "$BASEPATH" > "$DESTPATH/lib/.repo_path"

SOURCEDIR="$BASEPATH/surveillance"
CONFDIR="etc"
BACKUPCONFDIR=/tmp/backup_opensurv_config_$(date +%Y%m%d_%s)

if [ -d "$DESTPATH/${CONFDIR}" ];then
   cp -arv "$DESTPATH/${CONFDIR}" "${BACKUPCONFDIR}" > /dev/null 2>&1
fi

# --- Step 5: Application Deployment ---
echo "Step 5/7: Deploying core application files..."
rsync -av --ignore-existing "$SOURCEDIR/images/" "$DESTPATH/lib/images/" > /dev/null 2>&1
rsync -av --ignore-existing "$SOURCEDIR/etc/" "$DESTPATH/etc/" > /dev/null 2>&1
rsync -av "$SOURCEDIR/core" "$DESTPATH/lib/" > /dev/null 2>&1
rsync -av "$SOURCEDIR/web" "$DESTPATH/lib/" > /dev/null 2>&1
rsync -av "$SOURCEDIR/surveillance.py" "$DESTPATH/lib/" > /dev/null 2>&1
rsync -av "$BASEPATH/version.txt" "$DESTPATH/lib/" > /dev/null 2>&1
rsync -av opensurv "$DESTPATH/bin/" > /dev/null 2>&1
rsync -av opensurv.desktop "/usr/share/xsessions/" > /dev/null 2>&1

# --- Step 6: GUI Editor ---
echo "Step 6/7: Installing/Updating Tonys OpenSurv Gui Editor..."
GUI_DEST="/home/opensurv/lib/Tonys-OpenSurv-Gui-Editor"
git config --global --add safe.directory "$GUI_DEST"

if [ ! -d "$GUI_DEST" ]; then
    git clone https://github.com/BigTonyTones/Tonys-OpenSurv-Gui-Editor.git "$GUI_DEST" > /dev/null 2>&1
else
    cd "$GUI_DEST" && git pull > /dev/null 2>&1
fi

# --- Step 7: Finalizing ---
echo "Step 7/7: Finalizing permissions and starting services..."
chown -Rc opensurv:opensurv /home/opensurv > /dev/null 2>&1

if [ ! -L /etc/opensurv ]; then
  ln -fsv "$DESTPATH/$CONFDIR" /etc/opensurv > /dev/null 2>&1
fi

if [ ! -f /home/opensurv/firstinstall_DONE ];then
  apt remove gdm3 -y > /dev/null 2>&1
  touch /home/opensurv/firstinstall_DONE
  echo "First installation complete. System reboot required."
  if [ "$AUTO_INSTALL" = false ]; then
      echo "Press <Enter> to reboot..."
      read
  fi
  reboot
fi

systemctl daemon-reload
systemctl restart lightdm

# Get IP Address for the summary
IP_ADDR=$(hostname -I | awk '{print $1}')
echo ""
echo "------------------------------------------------------------"
echo "  INSTALLATION COMPLETE"
echo "------------------------------------------------------------"
echo "  Web Dashboard: http://$IP_ADDR:5000"
echo "  GUI Editor:    http://$IP_ADDR:6453"
echo "------------------------------------------------------------"
echo ""

if [ "$AUTO_INSTALL" = true ]; then
  echo "Update complete. Rebooting in 5 seconds..."
  sleep 5
  reboot
fi