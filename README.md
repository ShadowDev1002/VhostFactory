# VhostFactory

Erstellt automatisch Nginx-Konfigurationen und SSL-Zertifikate, sobald ein neuer Ordner in `/var/www` angelegt wird.

## Voraussetzungen

- Ubuntu 20.04+
- Python 3.9+
- Nginx
- Certbot: `apt install certbot python3-certbot-nginx`

## Installation

```bash
git clone https://github.com/ShadowDev1002/VhostFactory.git
cd VhostFactory
sudo ./install.sh
```

Danach die Konfiguration anpassen:

```bash
nano /etc/vhostfactory/config.yml
```

## Benutzung

Ordner erstellen → fertig.

```bash
mkdir /var/www/example.com
```

VhostFactory erkennt automatisch den Stack und konfiguriert alles:

| Datei im Ordner | Stack |
|---|---|
| `index.php` | PHP + FPM |
| `package.json` | Node.js (Reverse Proxy auf Port 3000) |
| *(keine)* | Statische Website |

Ordner löschen → Nginx-Config und SSL-Zertifikat werden automatisch entfernt.

## Service

```bash
systemctl start vhostfactory      # starten
systemctl enable vhostfactory     # autostart aktivieren
systemctl status vhostfactory     # status prüfen
journalctl -u vhostfactory -f     # logs live
```

## Lizenz

MIT
