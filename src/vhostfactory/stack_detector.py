import os
import logging

logger = logging.getLogger("vhostfactory")


class StackDetector:
    STACKS = {
        "php": ["index.php"],
        "node": ["package.json"],
        "static": []
    }

    @staticmethod
    def detect(directory_path):
        if not os.path.isdir(directory_path):
            logger.warning(f"Directory not found: {directory_path}")
            return "static"

        for filename in ["index.php"]:
            if os.path.exists(os.path.join(directory_path, filename)):
                logger.info(f"Detected PHP stack in {directory_path}")
                return "php"

        if os.path.exists(os.path.join(directory_path, "package.json")):
            logger.info(f"Detected Node.js stack in {directory_path}")
            return "node"

        logger.info(f"Detected static stack in {directory_path}")
        return "static"
