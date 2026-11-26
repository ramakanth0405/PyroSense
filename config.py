import tomllib

import tomli_w

CONFIG_PATH = "config.toml"


def load_config() -> dict:
    with open(CONFIG_PATH, "rb") as file:
        return tomllib.load(file)


def save_config(config: dict):
    with open(CONFIG_PATH, "wb") as file:
        tomli_w.dump(config, file)
