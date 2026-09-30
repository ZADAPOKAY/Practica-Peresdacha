import os
import yaml


class ConfigError(Exception):
    pass


def load_config(path=None):
    path = path or os.environ.get("APP_CONFIG", "config.yaml")
    try:
        with open(path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    except FileNotFoundError:
        raise ConfigError(f"Файл настроек не найден: {path}")
    except yaml.YAMLError as e:
        raise ConfigError(f"Ошибка в файле настроек {path}: {e}")
    try:
        for section, keys in {"database": ["host", "port", "user", "password", "name"],
                              "logs": ["dir", "mask"],
                              "web": ["host", "port", "secret_key"]}.items():
            for k in keys:
                cfg[section][k]
    except (KeyError, TypeError):
        raise ConfigError(f"В {path} не хватает параметра в секции '{section}': {k}")
    cfg.setdefault("errors_log", "./parse_errors.log")
    return cfg
