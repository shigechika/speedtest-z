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
        4. ``/etc/speedtest-z/``
    """
    if cli_path:
        if os.path.isfile(cli_path):
            return cli_path
        logger.warning(_msg("config_not_found_cli", path=cli_path))
        return None

    if os.path.isfile(name):
        return name

    # Use `or` so an empty XDG_CONFIG_HOME falls back to ~/.config (os.environ.get
    # returns "" when the variable is set but empty, which would yield a relative path).
    xdg = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    xdg_path = os.path.join(xdg, "speedtest-z", name)
    if os.path.isfile(xdg_path):
        return xdg_path

    # System-wide configuration (for the deb/rpm packages).
    etc_path = os.path.join("/etc/speedtest-z", name)
    if os.path.isfile(etc_path):
        return etc_path

    return None


def _redirect_console_logging_to_stderr() -> None:
    """Point any stdout-bound StreamHandler at stderr.

    Used in json/csv output mode so log records never mix into the structured
    stdout payload, even when a logging.ini routes the console handler to stdout.
    FileHandler is a StreamHandler subclass, but its stream is a file, so the
    identity check against sys.stdout naturally leaves file handlers alone.
    """
    seen: set[int] = set()
    loggers = [logging.getLogger()]
    loggers += [logging.getLogger(name) for name in logging.root.manager.loggerDict]
    for lg in loggers:
        for handler in getattr(lg, "handlers", []):
            if id(handler) in seen:
                continue
            seen.add(id(handler))
            if isinstance(handler, logging.StreamHandler) and handler.stream is sys.stdout:
                handler.setStream(sys.stderr)


def _setup_logging(debug: bool = False, stream: str = "stdout") -> None:
    """Initialize logging configuration.

    When *stream* is ``"stderr"`` (json/csv output mode), guarantee that no log
    records reach stdout — even if a logging.ini routes the console handler
    there — so the structured stdout payload stays clean.
    """
    logging_ini = _find_config("logging.ini")
    if logging_ini:
        logging.config.fileConfig(logging_ini, disable_existing_loggers=False)
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
        if stream == "stderr":
            _redirect_console_logging_to_stderr()
    else:
        out = sys.stderr if stream == "stderr" else sys.stdout
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler(out)],
            force=True,
        )
