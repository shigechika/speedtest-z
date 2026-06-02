#!/bin/sh
# RPM %post — run after package installation
# $1: 1=new install, 2=upgrade

# Create runtime directories (logs go to logger.log under the working
# directory and to journald, so no separate /var/log dir is needed)
install -d -o speedtest-z -g speedtest-z -m 0755 /var/lib/speedtest-z
install -d -o speedtest-z -g speedtest-z -m 0755 /var/lib/speedtest-z/snapshots

# Set config.ini permissions (it may contain tokens)
if [ -f /etc/speedtest-z/config.ini ]; then
    chown root:speedtest-z /etc/speedtest-z/config.ini
    chmod 0640 /etc/speedtest-z/config.ini
fi

# Reload systemd daemon
systemctl daemon-reload 2>/dev/null || true
