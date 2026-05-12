import os
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from vhostfactory.stack_detector import StackDetector
from vhostfactory.nginx_manager import NginxManager
from vhostfactory.ssl_manager import SSLManager

logger = logging.getLogger("vhostfactory")


class VhostEventHandler(FileSystemEventHandler):
    def __init__(self, config):
        self.config = config
        self.watch_dir = config.get("watch_directory")
        self.nginx_manager = NginxManager(config)
        self.ssl_manager = SSLManager(config)
        self.processing = set()

    def on_created(self, event):
        if event.is_directory:
            parent = os.path.dirname(event.src_path)
            if os.path.abspath(parent) == os.path.abspath(self.watch_dir):
                self._handle_new_domain(event.src_path)
        else:
            filename = os.path.basename(event.src_path)
            if filename in ("index.php", "package.json"):
                domain_dir = os.path.dirname(event.src_path)
                parent = os.path.dirname(domain_dir)
                if os.path.abspath(parent) == os.path.abspath(self.watch_dir):
                    self._handle_stack_change(domain_dir)

    def on_deleted(self, event):
        if event.is_directory:
            parent = os.path.dirname(event.src_path)
            if os.path.abspath(parent) == os.path.abspath(self.watch_dir):
                self._handle_deleted_domain(event.src_path)

    def _handle_new_domain(self, dir_path):
        domain = os.path.basename(dir_path)

        if domain in self.processing:
            return

        self.processing.add(domain)

        try:
            logger.info(f"Processing new domain: {domain}")

            stack_type = StackDetector.detect(dir_path)

            config_content = self.nginx_manager.generate_config(
                domain=domain,
                stack_type=stack_type,
                root_path=dir_path
            )

            if not config_content:
                logger.error(f"Failed to generate Nginx config for {domain}")
                return

            config_path = self.nginx_manager.write_config(domain, config_content)
            if not config_path:
                return

            if not self.nginx_manager.enable_config(domain):
                return

            if self.ssl_manager.certificate_exists(domain):
                logger.info(f"SSL certificate already exists for {domain}, reusing")
                self.ssl_manager.update_nginx_for_ssl(domain, config_path)
            elif self.ssl_manager.create_certificate(domain, dir_path):
                self.ssl_manager.update_nginx_for_ssl(domain, config_path)
            else:
                logger.warning(f"SSL creation failed for {domain}, continuing with HTTP only")

            self.nginx_manager.reload_nginx()

            logger.info(f"Successfully processed domain: {domain}")
        except Exception as e:
            logger.error(f"Error processing domain {domain}: {e}")
        finally:
            self.processing.discard(domain)

    def _handle_stack_change(self, dir_path):
        domain = os.path.basename(dir_path)
        new_stack = StackDetector.detect(dir_path)

        if not self.nginx_manager.is_auto_generated(domain):
            return

        sites_available = self.nginx_manager.sites_available
        config_path = os.path.join(sites_available, domain)
        try:
            with open(config_path, 'r') as f:
                current = f.read()
        except Exception:
            return

        # Only regenerate if stack has changed
        if f"# stack: {new_stack}" in current:
            return

        logger.info(f"Stack changed for {domain}, regenerating config as {new_stack}")

        self.nginx_manager.delete_config(domain)
        self.ssl_manager.delete_certificate(domain)
        self._handle_new_domain(dir_path)

    def _handle_deleted_domain(self, dir_path):
        domain = os.path.basename(dir_path)

        try:
            logger.info(f"Processing deleted domain: {domain}")

            if not self.nginx_manager.delete_config(domain):
                logger.warning(f"Nginx config for {domain} is not auto-generated or doesn't exist")

            if not self.ssl_manager.delete_certificate(domain):
                logger.warning(f"SSL certificate for {domain} not found or deletion failed")

            self.nginx_manager.reload_nginx()

            logger.info(f"Successfully processed deletion of domain: {domain}")
        except Exception as e:
            logger.error(f"Error processing deletion of domain {domain}: {e}")


class VhostWatcher:
    def __init__(self, config):
        self.config = config
        self.watch_dir = config.get("watch_directory")
        self.observer = Observer()
        self.event_handler = VhostEventHandler(config)

    def start(self):
        try:
            os.makedirs(self.watch_dir, exist_ok=True)
            self.observer.schedule(self.event_handler, self.watch_dir, recursive=True)
            self.observer.start()
            logger.info(f"Started watching directory: {self.watch_dir}")
        except Exception as e:
            logger.error(f"Failed to start watcher: {e}")
            raise

    def stop(self):
        self.observer.stop()
        self.observer.join()
        logger.info("Watcher stopped")
