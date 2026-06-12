"""Structured logger for Clavra ProdPilot™."""
import logging, sys
from app.config import settings

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO)
    return logger

logger = get_logger("clavra")
