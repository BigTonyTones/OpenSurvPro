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
    grep fullversion_for_installer "$BASEPATH/surveillance/surveillance.py" | head -n 1 | cut -d"=" -f2
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
fullversion_for_installer="Tonys OpenSurv Pro v2.1.1"

# Check for auto flag
AUTO_INSTALL=false
if [[ "$*" == *"--auto"* ]]; then
    AUTO_INSTALL=true
fi

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

# Stop OpenSurv after user confirms they want to proceed
echo "Stopping OpenSurv and LightDM..."
systemctl stop lightdm
pkill -f surveillance.py 2>/dev/null

#Install needed packages
apt update
apt install --only-upgrade xdotool mpv xfce4 python3-pygame python3-xlib ffmpeg wmctrl unclutter python3-pip -y || apt install xdotool mpv xfce4 python3-pygame python3-xlib ffmpeg wmctrl unclutter python3-pip -y

#Install python dependencies
pip3 install --upgrade --break-system-packages -r "$BASEPATH/requirements.txt"

#Configure user and autologin
useradd -m opensurv -s /bin/bash
configure_lightdm

DESTPATH="/home/opensurv"
mkdir -pv "$DESTPATH"/{etc,lib,logs,bin}

SOURCEDIR="$BASEPATH/surveillance"
CONFDIR="etc"
BACKUPCONFDIR=/tmp/backup_opensurv_config_$(date +%Y%m%d_%s)

if [ -d "$DESTPATH/${CONFDIR}" ];then
   echo
   echo "Existing config dir will be backed up to "${BACKUPCONFDIR}""
   cp -arv "$DESTPATH/${CONFDIR}" "${BACKUPCONFDIR}"
fi

ANSWERSTART="yes"

# Install essential files (ignoring existing ones to protect user data)
rsync -av --ignore-existing "$SOURCEDIR/images/" "$DESTPATH/lib/images/"
rsync -av --ignore-existing "$SOURCEDIR/etc/" "$DESTPATH/etc/"

# Always update core logic
rsync -av "$SOURCEDIR/core" "$DESTPATH/lib/"
rsync -av "$SOURCEDIR/web" "$DESTPATH/lib/"
rsync -av "$SOURCEDIR/surveillance.py" "$DESTPATH/lib/"
rsync -av "$BASEPATH/version.txt" "$DESTPATH/lib/"
rsync -av opensurv "$DESTPATH/bin/"
rsync -av opensurv.desktop "/usr/share/xsessions/"

# Install Tonys OpenSurv Gui Editor
echo "Installing Tonys OpenSurv Gui Editor..."
GUI_DEST="/home/opensurv/lib/Tonys-OpenSurv-Gui-Editor"
git config --global --add safe.directory "$GUI_DEST"

if [ ! -d "$GUI_DEST" ]; then
    git clone https://github.com/BigTonyTones/Tonys-OpenSurv-Gui-Editor.git "$GUI_DEST"
else
    cd "$GUI_DEST" && git pull
fi

# We skip installing requirements.txt for the GUI Editor because it may downgrade 
# Pro dependencies. Pro requirements.txt already covers everything needed.
echo "Syncing dependencies..."
pip install --break-system-packages -r "$BASEPATH/requirements.txt"

chown -Rc opensurv:opensurv /home/opensurv

#Link config file dir into /etc as convenient way to edit
if [ ! -L /etc/opensurv ]; then
  ln -fsv "$DESTPATH/$CONFDIR" /etc/opensurv
fi

if [ ! -f /home/opensurv/firstinstall_DONE ];then
  #We use lightdm, do not let gdm3 be in our way
  apt remove gdm3
  touch /home/opensurv/firstinstall_DONE
  echo "This is first install we need to reboot"
  echo "For reboot press <Enter>"
  read
  reboot
fi

if [ x"$ANSWERSTART" == x"yes" ]; then
    systemctl daemon-reload
    systemctl restart lightdm
fi

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