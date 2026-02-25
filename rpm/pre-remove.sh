#!/bin/sh
# RPM %preun — パッケージ削除前に実行
# $1: 0=最終削除, 1=アップグレード

if [ $1 -eq 0 ]; then
    systemctl stop speedtest-z.timer speedtest-z.service 2>/dev/null || true
    systemctl disable speedtest-z.timer speedtest-z.service 2>/dev/null || true
fi
