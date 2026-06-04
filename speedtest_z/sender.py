"""Metric backend management: Zabbix, Grafana, OTel."""

from __future__ import annotations

import configparser
import logging

from zappix.sender import Sender, SenderData

logger = logging.getLogger("speedtest-z")


def _is_plaintext_remote(url: str) -> bool:
    """Return True if *url* sends over plaintext http to a non-local host.

    Local endpoints (a co-located OTLP collector or Prometheus) over http are a
    common, low-risk setup, so they are not flagged.
    """
    if url.startswith("https://"):
        return False
    return not any(host in url for host in ("localhost", "127.0.0.1", "[::1]"))


class SenderManager:
    """Manages all metric backends (Zabbix, Grafana, OTel)."""

    def __init__(
        self,
        config: configparser.ConfigParser,
        host: str,
        dry_run: bool,
    ) -> None:
        """Initialize all configured metric backends.

        Args:
            config: Parsed config.ini.
            host: Default Zabbix host name.
            dry_run: If True, suppress all sends.
        """
        self.dry_run = dry_run

        # Zabbix settings
        self.zabbix_enable = config.getboolean("zabbix", "enable", fallback=False)
        self.zabbix_server = config.get("zabbix", "server", fallback="127.0.0.1")
        self.zabbix_port = config.getint("zabbix", "port", fallback=10051)
        self.zabbix_host = host
        # Optional Zabbix JSON-RPC API (for host tags); separate from the
        # trapper send path above. All three must be set to enable it.
        self.zabbix_api_url = config.get("zabbix", "api_url", fallback="")
        self.zabbix_api_user = config.get("zabbix", "api_user", fallback="")
        self.zabbix_api_password = config.get("zabbix", "api_password", fallback="")

        # Grafana
        self.grafana_sender = None
        if config.has_section("grafana"):
            grafana_enable = config.getboolean("grafana", "enable", fallback=False)
            if grafana_enable:
                try:
                    # cramjam is an optional dependency ([grafana] extra).
                    # GrafanaSender only imports it inside send(), so import it
                    # explicitly here to detect a missing install at startup and
                    # surface the install hint.
                    import cramjam  # noqa: F401

                    from speedtest_z.grafana import GrafanaSender

                    url = config.get("grafana", "remote_write_url")
                    username = config.get("grafana", "username")
                    token = config.get("grafana", "token")
                    if _is_plaintext_remote(url):
                        logger.warning(
                            "[grafana] remote_write_url is not https; "
                            "credentials would be sent over plaintext"
                        )
                    self.grafana_sender = GrafanaSender(url, username, token)
                except ImportError:
                    logger.error("cramjam not installed. Run: pip install speedtest-z[grafana]")
                except configparser.NoOptionError as e:
                    logger.error(f"[grafana] config incomplete: {e}")

        # OTel
        self.otel_sender = None
        if config.has_section("otel"):
            otel_enable = config.getboolean("otel", "enable", fallback=False)
            if otel_enable:
                try:
                    from speedtest_z.otel import OtelSender

                    endpoint = config.get("otel", "endpoint")
                    if _is_plaintext_remote(endpoint):
                        logger.warning(
                            "[otel] endpoint is not https; "
                            "headers (e.g. auth) would be sent over plaintext"
                        )
                    headers_str = config.get("otel", "headers", fallback="")
                    # "Key1=Val1,Key2=Val2" -> dict
                    headers: dict[str, str] = {}
                    for pair in headers_str.split(","):
                        pair = pair.strip()
                        if "=" in pair:
                            k, v = pair.split("=", 1)
                            headers[k.strip()] = v.strip()
                    self.otel_sender = OtelSender(endpoint, headers, self.zabbix_host)
                except ImportError:
                    logger.error("opentelemetry not installed. Run: pip install speedtest-z[otel]")
                except configparser.NoOptionError as e:
                    logger.error(f"[otel] config incomplete: {e}")

    def send(self, data_list: list[dict[str, str]]) -> None:
        """Send measurement results to all enabled backends."""
        if not data_list:
            return

        # Drop empty values. Zabbix would accept an empty value as-is while
        # Grafana/OTel silently skip it on float() failure; filtering here keeps
        # what is sent consistent across all backends.
        data_list = [item for item in data_list if str(item.get("value", "")).strip()]
        if not data_list:
            logger.debug("No non-empty metrics to send.")
            return

        packet = []
        for item in data_list:
            hostname = item.get("host", self.zabbix_host)
            metric = SenderData(hostname, item["key"], item["value"])
            packet.append(metric)

        if self.dry_run:
            target_host = data_list[0].get("host", "unknown")
            logger.debug(f"Buffered for {target_host}: {data_list}")
            logger.debug("Dryrun: True - Data not sent.")
            return

        # Zabbix
        if self.zabbix_enable:
            try:
                sender = Sender(self.zabbix_server, self.zabbix_port)
                res = sender.send_bulk(packet)
                logger.info(f"Zabbix Response: {res}")
            except Exception:
                logger.exception("Failed to send to Zabbix")

        # Grafana
        if self.grafana_sender:
            try:
                self.grafana_sender.send(data_list)
            except Exception:
                logger.exception("Failed to send to Grafana")

        # OTel
        if self.otel_sender:
            try:
                self.otel_sender.send(data_list)
            except Exception:
                logger.exception("Failed to send to OTel")

    def set_version_tag(self, version: str) -> None:
        """Stamp the running speedtest-z version onto the Zabbix host as a tag.

        Sets the host tag ``speedtest-z=<version>`` via the Zabbix JSON-RPC API
        (separate from the trapper send path). No-op in dry-run, when Zabbix is
        disabled, or when the API is not configured. Requires the optional
        ``zapi-mcp`` package; a missing install or an API failure is logged,
        not fatal.
        """
        if self.dry_run or not self.zabbix_enable:
            return
        if not (self.zabbix_api_url and self.zabbix_api_user and self.zabbix_api_password):
            logger.debug("[zabbix] API not configured; skipping version host tag")
            return
        try:
            from zapi_mcp.client import ZapiClient
        except ImportError:
            logger.warning(
                "zapi-mcp not installed; cannot set the version host tag. "
                "Install zapi-mcp to enable it."
            )
            return
        try:
            with ZapiClient(
                self.zabbix_api_url, self.zabbix_api_user, self.zabbix_api_password
            ) as client:
                client.set_host_tag(self.zabbix_host, "speedtest-z", version)
            logger.info(f"Zabbix host tag set: speedtest-z={version} on {self.zabbix_host}")
        except Exception:
            logger.exception("Failed to set the Zabbix version host tag")

    def close(self) -> None:
        """Shut down backends that need cleanup."""
        if self.otel_sender:
            self.otel_sender.shutdown()
