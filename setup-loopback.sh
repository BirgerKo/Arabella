#!/usr/bin/env bash
# setup-loopback.sh — add macOS loopback aliases for VentoFanSim containers.
#
# Docker Desktop for Mac does NOT route the bridge subnet (172.28.0.x) to the
# host.  Instead each fan container is port-mapped to a loopback alias so it
# gets its own IP at the standard port 4000.
#
# These aliases are lost on reboot — re-run this script after each restart.
#
# Usage:
#   chmod +x setup-loopback.sh
#   sudo ./setup-loopback.sh          # add aliases for fan1–fan3
#   sudo ./setup-loopback.sh remove   # remove them again

set -euo pipefail

ALIASES=(127.0.0.11 127.0.0.12 127.0.0.13)

case "${1:-add}" in
  add)
    for ip in "${ALIASES[@]}"; do
      if ifconfig lo0 | grep -q "$ip"; then
        echo "  $ip already present — skipping"
      else
        ifconfig lo0 alias "$ip"
        echo "  added $ip"
      fi
    done
    echo "Done.  Loopback aliases:"
    ifconfig lo0 | grep "127\.0\.0\." | awk '{print "  "$2}'
    ;;
  remove)
    for ip in "${ALIASES[@]}"; do
      if ifconfig lo0 | grep -q "$ip"; then
        ifconfig lo0 -alias "$ip"
        echo "  removed $ip"
      else
        echo "  $ip not present — skipping"
      fi
    done
    ;;
  *)
    echo "Usage: sudo $0 [add|remove]"
    exit 1
    ;;
esac
