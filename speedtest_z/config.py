"""Configuration file discovery and logging setup for speedtest-z."""

from __future__ import annotations

import logging
import logging.config
import os
import sys

from speedtest_z.i18n import _msg

logger = logging.getLogger("speedtest-z")


def _find_config(name: str, cli_path: str | None = None) -> str | None:
    """Search for a configuration file in standard locations.

    Lookup order:
        1. Path specified via CLI (``-c`` / ``--config``)
        2. Current working directory
        3. ``~/.config/speedtest-z/`` (XDG_CONFIG_HOME)
    """
    if cli_path:
        if os.path.isfile(cli_path):
            return cli_path
        logger.warning(_msg("config_not_found_cli", path=cli_path))
        return None

    if os.path.isfile(name):
        return name

    xdg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    xdg_path = os.path.join(xdg, "speedtest-z", name)
    if os.path.isfile(xdg_path):
        return xdg_path

    return None


def _setup_logging(debug: bool = False) -> None:
    """Initialize logging configuration."""
    logging_ini = _find_config("logging.ini")
    if logging_ini:
        logging.config.fileConfig(logging_ini, disable_existing_loggers=False)
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )
