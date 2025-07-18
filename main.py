import logging
import logging.config
from pathlib import Path

import yaml

# Load the logging configuration
LOGGING_CONFIG = {}
with open(Path(__file__).parent / "logger_config.yaml", "r") as f:
    LOGGING_CONFIG = yaml.safe_load(f)
    logging.config.dictConfig(LOGGING_CONFIG)



if __name__ == "__main__":
    print("main.py")

