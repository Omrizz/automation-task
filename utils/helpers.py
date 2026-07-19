"""Pure helper functions: price parsing, filenames, logging setup."""
from __future__ import annotations

import logging
import re
from datetime import datetime


def parse_price(raw: str) -> float:
    """Parse a single displayed price string (e.g. "$1,234.56") into a float.

    Returns 0.0 for empty/unparsable input (e.g. an empty cart's "$0.00" or
    a listing with no visible price).
    """
    if not raw:
        return 0.0
    if " to " in raw or "-" in raw.replace("--", ""):
        return parse_price_range(raw)
    match = re.search(r"[\d,]+\.?\d*", raw)
    if not match:
        return 0.0
    return float(match.group(0).replace(",", ""))


def parse_price_range(raw: str) -> float:
    """Parse a price range (e.g. "$50.00 to $80.00") and return the lower bound."""
    numbers = re.findall(r"[\d,]+\.?\d*", raw)
    if not numbers:
        return 0.0
    return float(numbers[0].replace(",", ""))


def timestamped_filename(prefix: str, ext: str = "png") -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"{prefix}_{stamp}.{ext}"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
