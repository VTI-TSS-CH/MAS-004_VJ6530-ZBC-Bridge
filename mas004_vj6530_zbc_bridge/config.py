import json
import os
from dataclasses import dataclass

DEFAULT_CFG_PATH = "/etc/mas004_vj6530_zbc_bridge/config.json"


@dataclass
class Settings:
    enabled: bool = True
    simulation: bool = True
    host: str = ""
    port: int = 0
    timeout_s: float = 2.0
    poll_interval_s: float = 2.0

    @classmethod
    def load(cls, path: str = DEFAULT_CFG_PATH) -> "Settings":
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            cfg = cls()
            cfg.save(path)
            return cfg

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}

        cfg = cls()
        for k, v in data.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        return cfg

    def save(self, path: str = DEFAULT_CFG_PATH):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.__dict__, f, indent=2)
