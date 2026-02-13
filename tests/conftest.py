"""speedtest-z テスト用共通フィクスチャ"""

import argparse
import configparser

import pytest


@pytest.fixture
def mock_args():
    """CLI 引数のモック"""
    return argparse.Namespace(
        config=None,
        dry_run=False,
        headless=None,
        timeout=None,
        list_sites=False,
        debug=False,
        sites=[],
    )


@pytest.fixture
def mock_config():
    """ConfigParser のモック（config.ini-sample 相当）"""
    config = configparser.ConfigParser()
    config.read_dict(
        {
            "general": {
                "dryrun": "true",
                "headless": "true",
                "timeout": "30",
            },
            "zabbix": {
                "server": "127.0.0.1",
                "port": "10051",
                "host": "speedtest-agent",
            },
            "snapshot": {
                "enable": "false",
                "save_dir": "./snapshots",
            },
            "frequency": {
                "cloudflare": "100",
                "netflix": "100",
                "google": "100",
                "ookla": "50",
                "boxtest": "50",
                "mlab": "10",
                "usen": "50",
                "inonius": "50",
            },
        }
    )
    return config


@pytest.fixture
def sample_config_ini(tmp_path):
    """tmp_path に config.ini を作成して返す"""
    ini = tmp_path / "config.ini"
    ini.write_text(
        "[general]\n"
        "dryrun = true\n"
        "headless = true\n"
        "timeout = 30\n"
        "\n"
        "[zabbix]\n"
        "server = 127.0.0.1\n"
        "port = 10051\n"
        "host = speedtest-agent\n"
        "\n"
        "[frequency]\n"
        "cloudflare = 100\n"
        "ookla = 50\n"
    )
    return ini
