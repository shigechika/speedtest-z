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

    # ロケールに応じて日本語版/英語版を選択
    readme = "README.ja.md" if _LANG_JA else "README.md"

    text = None

    # 1. importlib.resources でパッケージ内から読み込み (pip install 時)
    with contextlib.suppress(FileNotFoundError, TypeError):
        text = files("speedtest_z").joinpath(readme).read_text(encoding="utf-8")

    # 2. フォールバック: リポジトリルートの README (開発時)
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

    # --man は Chrome 不要で応答
    if args.man:
        _show_manual()
        return

    # --list-sites は Chrome 不要で応答
    if args.list_sites:
        print("Available test sites:")
        for site in AVAILABLE_SITES:
            print(f"  {site}")
        return

    # --check は Chrome 不要で応答
    if args.check:
        from speedtest_z.healthcheck import check_sites

        sys.exit(check_sites(args.sites or None))

    # logging 設定（--debug 対応）
    # json/csv 出力時は stdout を占有するため、ログを stderr に出す
    output_fmt = getattr(args, "output", "zabbix")
    log_stream = "stderr" if output_fmt in ("json", "csv") else "stdout"
    _setup_logging(debug=args.debug, stream=log_stream)

    # config.ini の存在チェック（必須）
    config_path = _find_config("config.ini", args.config)
    if config_path is None:
        logger.error(_msg("config_not_found"))
        sys.exit(1)
    args.config = config_path  # 見つかったパスで上書き

    # TTY 実行時の確認プロンプト（--yes とは無関係に常に確認）
    if sys.stdin.isatty():
        sites = args.sites if args.sites else AVAILABLE_SITES
        site_list = ", ".join(sites)
        print(_msg("confirm_prompt", count=len(sites), sites=site_list))
        answer = input(_msg("confirm_input")).strip().lower()
        if answer not in ("y", "yes"):
            print(_msg("confirm_abort"))
            return

    logger.info("speedtest-z: START")

    from speedtest_z.runner import SpeedtestZ

    app = SpeedtestZ(args)

    # json/csv モードでは send_results を OutputCollector に差し替え
    collector = None
    output_fmt = getattr(args, "output", "zabbix")
    if output_fmt in ("json", "csv"):
        from speedtest_z.output import OutputCollector

        collector = OutputCollector(output_fmt)
        app._original_send_results = app.send_results
        app.send_results = collector.add

    try:
        sites = args.sites if args.sites else AVAILABLE_SITES
        site_runners = get_site_runners()
        for site in sites:
            runner = site_runners.get(site)
            if runner:
                runner(app)
            else:
                logger.warning(f"Unknown site: {site}")
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal Error: {e}")
    finally:
        if collector:
            collector.flush()
        app.close()

    logger.info("speedtest-z: FINISH")
