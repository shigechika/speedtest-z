#!/bin/sh
# RPM %pre — パッケージインストール前に実行
# $1: 1=新規インストール, 2=アップグレード

if ! getent passwd speedtest-z >/dev/null 2>&1; then
    useradd -r -s /sbin/nologin -d /var/lib/speedtest-z speedtest-z
fi
