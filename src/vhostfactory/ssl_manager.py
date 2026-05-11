import subprocess
import os
import logging

logger = logging.getLogger("vhostfactory")


class SSLManager:
    def __init__(self, config):
        self.config = config
        self.certbot_email = config.get("certbot_email")
        self.ssl_cert_dir = config.get("ssl_cert_directory")

    def create_certificate(self, domain, web_root):
        try:
            cmd = (
                f"certbot certonly --webroot -w {web_root} -d {domain}"
                f" --email {self.certbot_email} --agree-tos --non-interactive --quiet"
            )
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                logger.info(f"SSL certificate created for {domain}")
                return True
            else:
                logger.error(f"Certbot failed for {domain}: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Failed to create SSL certificate: {e}")
            return False

    def certificate_exists(self, domain):
        cert_path = os.path.join(self.ssl_cert_dir, domain, "fullchain.pem")
        return os.path.exists(cert_path)

    def update_nginx_for_ssl(self, domain, nginx_config_path):
        try:
            with open(nginx_config_path, 'r') as f:
                content = f.read()

            # Remove HTTP listen lines and placeholder comment from existing server block
            content = content.replace("    listen 80;\n", "")
            content = content.replace("    listen [::]:80;\n", "")
            content = content.replace(
                "    # HTTPS redirect (will be updated after SSL creation)\n"
                "    # return 301 https://$server_name$request_uri;\n",
                ""
            )

            # Insert SSL directives right after opening server {
            ssl_lines = (
                f"    listen 443 ssl http2;\n"
                f"    listen [::]:443 ssl http2;\n"
                f"    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;\n"
                f"    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;\n"
                f"    ssl_protocols TLSv1.2 TLSv1.3;\n"
                f"    ssl_ciphers HIGH:!aNULL:!MD5;\n"
                f"    ssl_prefer_server_ciphers on;\n"
            )
            content = content.replace("server {\n", f"server {{\n{ssl_lines}", 1)

            # Append separate HTTP redirect block
            redirect_block = (
                f"\nserver {{\n"
                f"    listen 80;\n"
                f"    listen [::]:80;\n"
                f"    server_name {domain};\n"
                f"    return 301 https://$server_name$request_uri;\n"
                f"}}\n"
            )
            content = content.rstrip() + "\n" + redirect_block

            with open(nginx_config_path, 'w') as f:
                f.write(content)

            logger.info(f"Updated Nginx config with SSL for {domain}")
            return True
        except Exception as e:
            logger.error(f"Failed to update Nginx SSL config: {e}")
            return False

    def delete_certificate(self, domain):
        try:
            cmd = f"certbot delete --cert-name {domain} --non-interactive --quiet"
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info(f"SSL certificate deleted for {domain}")
                return True
            else:
                logger.error(f"Failed to delete certificate for {domain}: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error deleting certificate: {e}")
            return False
