"""Internationalization support for speedtest-z."""

from __future__ import annotations

import locale
import os

# ロケール判定（ja_JP 等で始まれば日本語）
_LANG_JA: bool = (locale.getlocale()[0] or os.environ.get("LANG", "")).startswith("ja")

# ユーザ向けメッセージ辞書 (日本語, 英語)
_MESSAGES: dict[str, tuple[str, str]] = {
    "config_not_found_cli": (
        "{path} が見つかりません",
        "{path} not found",
    ),
    "config_not_found": (
        "config.ini が見つかりません。\n"
        "  config.ini-sample を以下のいずれかにコピーしてください:\n"
        "    ./config.ini\n"
        "    ~/.config/speedtest-z/config.ini\n"
        "  config.ini-sample:\n"
        "    https://github.com/shigechika/speedtest-z/blob/main/config.ini-sample",
        "config.ini not found.\n"
        "  Copy config.ini-sample to one of the following locations:\n"
        "    ./config.ini\n"
        "    ~/.config/speedtest-z/config.ini\n"
        "  config.ini-sample:\n"
        "    https://github.com/shigechika/speedtest-z/blob/main/config.ini-sample",
    ),
    "config_not_found_fallback": (
        "config.ini が見つかりません。デフォルト設定で動作します。\n"
        "  config.ini-sample を以下のいずれかにコピーしてください:\n"
        "    ./config.ini\n"
        "    ~/.config/speedtest-z/config.ini\n"
        "  config.ini-sample:\n"
        "    https://github.com/shigechika/speedtest-z/blob/main/config.ini-sample",
        "config.ini not found. Using default settings.\n"
        "  Copy config.ini-sample to one of the following locations:\n"
        "    ./config.ini\n"
        "    ~/.config/speedtest-z/config.ini\n"
        "  config.ini-sample:\n"
        "    https://github.com/shigechika/speedtest-z/blob/main/config.ini-sample",
    ),
    "chrome_init_failed": (
        "Chrome WebDriver の初期化に失敗しました: {error}\n"
        "  Google Chrome がインストールされているか確認してください。\n"
        "  https://www.google.com/chrome/",
        "Failed to initialize Chrome WebDriver: {error}\n"
        "  Please make sure Google Chrome is installed.\n"
        "  https://www.google.com/chrome/",
    ),
    "confirm_prompt": (
        "speedtest-z: {count} サイトに接続します ({sites})",
        "speedtest-z: connecting to {count} site(s) ({sites})",
    ),
    "confirm_input": (
        "続行しますか？ [y/N]: ",
        "Continue? [y/N]: ",
    ),
    "confirm_abort": (
        "中止しました。",
        "Aborted.",
    ),
    "manual_not_found": (
        "マニュアルが見つかりません。",
        "Manual not found.",
    ),
}


def _msg(key: str, **kwargs: str | int) -> str:
    """Return a localized message string."""
    ja, en = _MESSAGES[key]
    text = ja if _LANG_JA else en
    return text.format(**kwargs) if kwargs else text
