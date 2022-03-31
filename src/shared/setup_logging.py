import logging
import logging.config

from yaml import safe_load


def setup_logging():
    config_path = "etc/logging.yml"

    with open(config_path, "r") as f:
        config = safe_load(f)
        logging.config.dictConfig(config)
