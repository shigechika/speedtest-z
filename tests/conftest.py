"""Shared fixtures for speedtest-z tests."""

import argparse
import configparser
from unittest.mock import MagicMock, patch

import pytest

from speedtest_z.runner import SpeedtestZ
from speedtest_z.sender import SenderManager


@pytest.fixture
def mock_args():
    """Mock of the CLI arguments."""
    return argparse.Namespace(
        config=None,
        dry_run=False,
        headless=None,
        timeout=None,
        list_sites=False,
        debug=False,
        yes=False,
        sites=[],
    )


@pytest.fixture
def mock_config():
    """Mock ConfigParser (equivalent to config.ini-sample)."""
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
    """Create a config.ini under tmp_path and return it."""
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


@pytest.fixture
def mock_driver():
    """Mock of the Selenium WebDriver."""
    driver = MagicMock()
    driver.page_source = "<html></html>"
    return driver


@pytest.fixture
def mock_app(mock_config, mock_driver):
    """Mock SpeedtestZ instance (WebDriver bypassed)."""
    with patch.object(SpeedtestZ, "__init__", lambda self, *a, **kw: None):
        app = SpeedtestZ.__new__(SpeedtestZ)
        app.config = mock_config
        app.driver = mock_driver
        app.wait = MagicMock()
        app.action_chains = MagicMock()
        app.dryrun = True
        app.headless = True
        app.timeout = 30
        app.zabbix_enable = False
        app.zabbix_host = "speedtest-agent"
        app.zabbix_server = "127.0.0.1"
        app.zabbix_port = 10051
        app.grafana_sender = None
        app.otel_sender = None
        app.snapshot_enable = False
        app.snapshot_dir = "./snapshots"
        app.explicit_sites = False
        app.auto_consent = False
        app.ookla_server = None
        app.chrome_profile_dir = "/tmp/chrome-profile"
        # SenderManager mock
        sender = MagicMock(spec=SenderManager)
        sender.otel_sender = None
        app.sender = sender
    return app
