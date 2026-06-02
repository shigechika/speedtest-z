#!/bin/sh
# RPM %pre — run before package installation
# $1: 1=new install, 2=upgrade

if ! getent passwd speedtest-z >/dev/null 2>&1; then
    useradd -r -s /sbin/nologin -d /var/lib/speedtest-z speedtest-z
fi
