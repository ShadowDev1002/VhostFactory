#!/bin/bash

set -e

echo "Installing VhostFactory..."

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root"
    exit 1
fi

VENV=/opt/vhostfactory/venv

echo "Installing system dependencies..."
apt-get install -y python3-venv python3-full > /dev/null 2>&1

echo "Creating /opt/vhostfactory directory..."
mkdir -p /opt/vhostfactory
cp -r src/vhostfactory /opt/vhostfactory/
cp -r templates /opt/vhostfactory/

echo "Setting up Python virtualenv..."
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r requirements.txt

echo "Creating /etc/vhostfactory directory..."
mkdir -p /etc/vhostfactory
if [ ! -f /etc/vhostfactory/config.yml ]; then
    cp config.yml.example /etc/vhostfactory/config.yml
    echo "Created default config at /etc/vhostfactory/config.yml"
    echo "Please edit /etc/vhostfactory/config.yml with your settings"
fi

touch /var/log/vhostfactory.log
chmod 644 /var/log/vhostfactory.log

echo "Installing systemd service..."
cp systemd/vhostfactory.service /etc/systemd/system/
cp systemd/vhostfactory-renewal.service /etc/systemd/system/
cp systemd/vhostfactory-renewal.timer /etc/systemd/system/

systemctl daemon-reload

echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit /etc/vhostfactory/config.yml with your settings"
echo "2. Start the service: systemctl start vhostfactory"
echo "3. Enable on boot: systemctl enable vhostfactory"
echo "4. Check status: systemctl status vhostfactory"
