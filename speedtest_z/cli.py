"""CLI entry point for speedtest-z."""

from __future__ import annotations

import argparse
import contextlib
import logging
import os
import sys

from speedtest_z import __version__
from speedtest_z.config import _find_config, _setup_logging
from speedtest_z.i18n import _LANG_JA, _msg
from speedtest_z.sites import AVAILABLE_SITES, get_site_runners

logger = logging.getLogger("speedtest-z")


def _show_manual() -> None:
    """Display the manual (README) using a pager."""
    import pydoc
    from importlib.resources import files

    # Select the Japanese/English version based on locale
    readme = "README.ja.md" if _LANG_JA else "README.md"

    text = None

    # 1. Read from inside the package via importlib.resources (pip install)
    with contextlib.suppress(FileNotFoundError, TypeError):
        text = files("speedtest_z").joinpath(readme).read_text(encoding="utf-8")

    # 2. Fallback: README at the repository root (development)
    if not text:
        dev_path = os.path.normpath(os.path.join(os.path.dirname(__file__), os.pardir, readme))
        if os.path.isfile(dev_path):
            with open(dev_path, encoding="utf-8") as f:
                text = f.read()

    if not text:
        print(_msg("manual_not_found"), file=sys.stderr)
        sys.exit(1)

    pydoc.pager(text)


def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser."""
    parser = argparse.ArgumentParser(
        prog="speedtest-z",
        description="Automated multi-site speed test runner with Zabbix integration",
        epilog="https://github.com/shigechika/speedtest-z",
    )
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-m", "--man", action="store_true", help="show manual and exit")
    parser.add_argument(
        "-c",
        "--config",
        metavar="CONFIG",
        help="config file path (default: ./config.ini or ~/.config/speedtest-z/config.ini)",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="test run (do not send data to Zabbix)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=None,
        dest="headless",
        help="run Chrome in headless mode",
    )
    parser.add_argument(
        "--no-headless",
        "--headed",
        action="store_false",
        dest="headless",
        help="run Chrome with GUI (non-headless)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        metavar="SECONDS",
        help="timeout in seconds for each test",
    )
    parser.add_argument(
        "--list-sites",
        action="store_true",
        help="list available test sites and exit",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="check site URL reachability and exit (no Chrome needed)",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-o",
        "--output",
        choices=["zabbix", "json", "csv"],
        default="zabbix",
        metavar="FORMAT",
        help="output format: zabbix (default), json, csv",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="enable debug output",
    )
    parser.add_argument(
        "sites",
        nargs="*",
        metavar="site",
        choices=AVAILABLE_SITES + [[]],
        help=f"test sites to run (default: all). choices: {', '.join(AVAILABLE_SITES)}",
    )
    return parser


def _init_logging(args: argparse.Namespace) -> None:
    """Configure logging based on CLI arguments.

    Redirect logs to stderr when output format is json/csv
    (stdout is reserved for structured output).
    """
    output_fmt = getattr(args, "output", "zabbix")
    log_stream = "stderr" if output_fmt in ("json", "csv") else "stdout"
    _setup_logging(debug=args.debug, stream=log_stream)


def _confirm_execution(args: argparse.Namespace, sites: list[str]) -> bool:
    """Show confirmation prompt on TTY and return True to continue.

    Returns True without prompting when stdin is not a TTY (pipe/cron) or
    when --yes was given (-y answers every prompt, matching the usual CLI
    convention). Otherwise prompts and returns False if the user declines.
    """
    if not sys.stdin.isatty() or getattr(args, "yes", False):
        return True

    site_list = ", ".join(sites)
    print(_msg("confirm_prompt", count=len(sites), sites=site_list))
    answer = input(_msg("confirm_input")).strip().lower()
    if answer not in ("y", "yes"):
        print(_msg("confirm_abort"))
        return False
    return True


def main() -> None:
    """CLI entry point."""
    parser = _build_parser()

    # Tab completion (requires: pip install speedtest-z[completion])
    try:
        import argcomplete

        argcomplete.autocomplete(parser)
    except ImportError:
        pass

    args = parser.parse_args()

    # --man responds without needing Chrome
    if args.man:
        _show_manual()
        return

    # --list-sites responds without needing Chrome
    if args.list_sites:
        print("Available test sites:")
        for site in AVAILABLE_SITES:
            print(f"  {site}")
        return

    # --check responds without needing Chrome
    if args.check:
        from speedtest_z.healthcheck import check_sites

        sys.exit(check_sites(args.sites or None))

    _init_logging(args)

    # Check that config.ini exists (required)
    config_path = _find_config("config.ini", args.config)
    if config_path is None:
        logger.error(_msg("config_not_found"))
        sys.exit(1)
    args.config = config_path  # overwrite with the resolved path

    sites = args.sites if args.sites else AVAILABLE_SITES
    if not _confirm_execution(args, sites):
        return

    logger.info("speedtest-z: START")

    from speedtest_z.runner import SpeedtestZ

    app = SpeedtestZ(args)

    # In json/csv mode, use OutputCollector instead of SenderManager
    output_fmt = getattr(args, "output", "zabbix")
    if output_fmt in ("json", "csv"):
        from speedtest_z.output import OutputCollector

        # Release the SenderManager's backends (e.g. the OTel exporter thread)
        # before replacing it, so they do not leak for the rest of the run.
        app.sender.close()
        app.sender = OutputCollector(output_fmt)

    interrupted = False
    try:
        site_runners = get_site_runners()
        for site in sites:
            runner = site_runners.get(site)
            if runner:
                runner(app)
            else:
                logger.warning(f"Unknown site: {site}")
        # Stamp the running version onto the Zabbix host (no-op in dry-run,
        # when the API is unconfigured, or for json/csv output).
        app.stamp_version()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        interrupted = True
    except Exception:
        # Surface a non-zero exit code so systemd/cron can detect the failure.
        logger.exception("Fatal Error")
        sys.exit(1)
    finally:
        app.close()

    if interrupted:
        # 128 + SIGINT, the conventional exit code for Ctrl-C. Also skips the
        # FINISH log line, which would misleadingly suggest a complete run.
        sys.exit(130)

    logger.info("speedtest-z: FINISH")
