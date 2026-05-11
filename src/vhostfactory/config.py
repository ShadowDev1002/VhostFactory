import yaml
import os


class Config:
    def __init__(self, config_file="/etc/vhostfactory/config.yml"):
        self.config_file = config_file
        self.data = self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Config file not found: {self.config_file}")

        with open(self.config_file, 'r') as f:
            return yaml.safe_load(f)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def __getattr__(self, key):
        if key.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")
        return self.data.get(key)
