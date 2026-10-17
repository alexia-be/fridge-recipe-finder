# logging_setup.py - writes a log file so problems can be diagnosed later
import logging
from pathlib import Path

LOG_DIR = Path(__file__).parent / "logs"


def setup_logging():
    """Create a logger that writes to logs/app.log and to the terminal."""
    LOG_DIR.mkdir(exist_ok=True)  # make the logs/ folder if it's missing

    logger = logging.getLogger("fridge")
    logger.setLevel(logging.INFO)

    # Only add handlers once (Flask can load this file twice when it restarts)
    if not logger.handlers:
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

        file_handler = logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()  # also show logs in the terminal
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger