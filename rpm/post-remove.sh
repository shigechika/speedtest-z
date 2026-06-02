#!/bin/sh
# RPM %postun — run after package removal
# $1: 0=final removal, 1=upgrade

if [ "$1" -eq 0 ]; then
    rm -rf /opt/venvs/speedtest-z
    rm -rf /etc/speedtest-z
    rm -rf /var/lib/speedtest-z
    userdel speedtest-z 2>/dev/null || true
fi

systemctl daemon-reload 2>/dev/null || true
