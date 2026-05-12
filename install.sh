#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root"
fi

# Ensure we are running from the repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

for required in src/vhostfactory templates config.yml.example systemd; do
    [ -e "$required" ] || error "Required path '$required' not found — run install.sh from the repo root"
done

INSTALL_DIR=/opt/vhostfactory
VENV="$INSTALL_DIR/venv"
CONFIG_DIR=/etc/vhostfactory
CONFIG_FILE="$CONFIG_DIR/config.yml"

info "Updating package lists..."
apt-get update -qq

info "Installing system dependencies..."
apt-get install -y -qq \
    python3-venv \
    python3-full \
    nginx \
    certbot \
    python3-certbot-nginx \
    openssl \
    curl \
    software-properties-common

# PHP detection and installation
PHP_VERSION=$(php -r 'echo PHP_MAJOR_VERSION.".".PHP_MINOR_VERSION;' 2>/dev/null || true)

if [ -z "$PHP_VERSION" ]; then
    info "No PHP found — installing php8.3-fpm..."
    apt-get install -y -qq php8.3-fpm php8.3-cli php8.3-common php8.3-mysql php8.3-zip \
        php8.3-gd php8.3-mbstring php8.3-curl php8.3-xml php8.3-bcmath
    PHP_VERSION="8.3"
else
    info "PHP $PHP_VERSION already installed"
    PKG="php${PHP_VERSION}-fpm"
    if ! dpkg -s "$PKG" &>/dev/null; then
        info "Installing $PKG..."
        apt-get install -y -qq "$PKG"
    fi
fi

PHP_FPM_SOCKET="/run/php/php${PHP_VERSION}-fpm.sock"
info "PHP-FPM socket: $PHP_FPM_SOCKET"

info "Starting and enabling services..."
systemctl enable --now nginx
systemctl enable --now "php${PHP_VERSION}-fpm"

info "Deploying application files..."
mkdir -p "$INSTALL_DIR"
cp -r src/vhostfactory "$INSTALL_DIR/"
cp -r templates "$INSTALL_DIR/"

info "Setting up Python virtualenv..."
python3 -m venv --clear "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r requirements.txt

mkdir -p "$CONFIG_DIR"

if [ ! -f "$CONFIG_FILE" ]; then
    info "Creating default config at $CONFIG_FILE..."
    cp config.yml.example "$CONFIG_FILE"
fi

# Always ensure templates_dir is set correctly
if grep -q "^templates_dir:" "$CONFIG_FILE"; then
    sed -i "s|^templates_dir:.*|templates_dir: $INSTALL_DIR/templates|" "$CONFIG_FILE"
else
    echo "templates_dir: $INSTALL_DIR/templates" >> "$CONFIG_FILE"
fi

# Always update php_fpm_socket to match detected version
if grep -q "^php_fpm_socket:" "$CONFIG_FILE"; then
    sed -i "s|^php_fpm_socket:.*|php_fpm_socket: $PHP_FPM_SOCKET|" "$CONFIG_FILE"
else
    echo "php_fpm_socket: $PHP_FPM_SOCKET" >> "$CONFIG_FILE"
fi

# Warn about placeholder certbot email
CURRENT_EMAIL=$(grep "^certbot_email:" "$CONFIG_FILE" | awk '{print $2}' | tr -d '"')
if [ "$CURRENT_EMAIL" = "admin@example.com" ] || [ -z "$CURRENT_EMAIL" ]; then
    echo ""
    warn "certbot_email is still set to the placeholder value."
    read -rp "Enter your email for Let's Encrypt certificates: " USER_EMAIL
    if [ -n "$USER_EMAIL" ]; then
        sed -i "s|^certbot_email:.*|certbot_email: $USER_EMAIL|" "$CONFIG_FILE"
        info "Email set to $USER_EMAIL"
    else
        warn "No email entered — SSL certificate creation will fail until you set certbot_email in $CONFIG_FILE"
    fi
fi

touch /var/log/vhostfactory.log
chmod 644 /var/log/vhostfactory.log

mkdir -p /var/www
# Only set ownership if /var/www is freshly created (no existing sites)
if [ -z "$(ls -A /var/www 2>/dev/null)" ]; then
    chown www-data:www-data /var/www
fi

# Catch-all HTTPS server block — prevents wrong vhost being served for unmatched domains
CATCHALL=/etc/nginx/sites-available/catch-all-https
if [ ! -f "$CATCHALL" ]; then
    info "Creating catch-all HTTPS server block..."
    mkdir -p /etc/nginx/ssl
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/catch-all.key \
        -out /etc/nginx/ssl/catch-all.crt \
        -subj "/CN=catch-all" 2>/dev/null
    cat > "$CATCHALL" <<'EOF'
# Catch-all for unmatched HTTPS requests
server {
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    server_name _;

    ssl_certificate /etc/nginx/ssl/catch-all.crt;
    ssl_certificate_key /etc/nginx/ssl/catch-all.key;

    return 444;
}
EOF
fi
# Always ensure symlink exists (might be missing after manual deletion)
ln -sf "$CATCHALL" /etc/nginx/sites-enabled/catch-all-https

info "Installing systemd service..."
cp systemd/vhostfactory.service /etc/systemd/system/
cp systemd/vhostfactory-renewal.service /etc/systemd/system/
cp systemd/vhostfactory-renewal.timer /etc/systemd/system/

systemctl daemon-reload
systemctl enable vhostfactory
systemctl enable vhostfactory-renewal.timer

nginx -t && systemctl reload nginx

info "Starting VhostFactory..."
systemctl restart vhostfactory

echo ""
info "Installation complete!"
echo ""
echo "  Config:  $CONFIG_FILE"
echo "  Logs:    journalctl -u vhostfactory -f"
echo "  Status:  systemctl status vhostfactory"
echo ""
