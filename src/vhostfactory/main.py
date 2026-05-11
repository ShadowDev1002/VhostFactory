import sys
import signal
import logging

from vhostfactory.config import Config
from vhostfactory.logger import setup_logger
from vhostfactory.watcher import VhostWatcher


def main():
    try:
        config = Config("/etc/vhostfactory/config.yml")

        log_file = config.get("log_file", "/var/log/vhostfactory.log")
        log_level_str = config.get("log_level", "INFO")
        log_level = getattr(logging, log_level_str, logging.INFO)

        logger = setup_logger(log_file, log_level)
        logger.info("VhostFactory daemon starting...")

        watcher = VhostWatcher(config)
        watcher.start()

        logger.info("VhostFactory daemon is running. Press Ctrl+C to stop.")

        def signal_handler(sig, frame):
            logger.info("Received shutdown signal")
            watcher.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        signal.pause()

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please ensure /etc/vhostfactory/config.yml exists")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
