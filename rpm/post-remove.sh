#!/bin/sh
# RPM %postun — パッケージ削除後に実行
# $1: 0=最終削除, 1=アップグレード

if [ "$1" -eq 0 ]; then
    rm -rf /opt/venvs/speedtest-z
    rm -rf /etc/speedtest-z
    rm -rf /var/lib/speedtest-z
    userdel speedtest-z 2>/dev/null || true
fi

systemctl daemon-reload 2>/dev/null || true
