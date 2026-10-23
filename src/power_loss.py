"""The setting for OpenNept4une's power-loss recovery (img-config/plr/plr.py).

Recovery is off while DISABLED_FILE exists, which plr.py checks when the power
fails.
"""

import logging
import os

DISABLED_FILE = os.path.expanduser("~/printer_data/plr/disabled")

logger = logging.getLogger(__name__)


def recovery_enabled():
    return not os.path.exists(DISABLED_FILE)


def toggle_recovery():
    """Turn recovery on or off. Returns whether it's now on."""
    try:
        if os.path.exists(DISABLED_FILE):
            os.remove(DISABLED_FILE)
        else:
            os.makedirs(os.path.dirname(DISABLED_FILE), exist_ok=True)
            open(DISABLED_FILE, "w").close()
    except OSError as e:
        logger.error(f"Can't change the power-loss recovery setting: {e}")
    return recovery_enabled()
