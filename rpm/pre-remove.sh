#!/bin/sh
# RPM %preun — run before package removal
# $1: 0=final removal, 1=upgrade

if [ "$1" -eq 0 ]; then
    systemctl stop speedtest-z.timer speedtest-z.service 2>/dev/null || true
    systemctl disable speedtest-z.timer speedtest-z.service 2>/dev/null || true
fi
