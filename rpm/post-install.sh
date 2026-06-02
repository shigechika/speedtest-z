#!/bin/sh
# RPM %post — パッケージインストール後に実行
# $1: 1=新規インストール, 2=アップグレード

# Create runtime directories (logs go to logger.log under the working
# directory and to journald, so no separate /var/log dir is needed)
install -d -o speedtest-z -g speedtest-z -m 0755 /var/lib/speedtest-z
install -d -o speedtest-z -g speedtest-z -m 0755 /var/lib/speedtest-z/snapshots

# config.ini の権限設定（トークンを含む可能性があるため）
if [ -f /etc/speedtest-z/config.ini ]; then
    chown root:speedtest-z /etc/speedtest-z/config.ini
    chmod 0640 /etc/speedtest-z/config.ini
fi

# systemd デーモンリロード
systemctl daemon-reload 2>/dev/null || true
