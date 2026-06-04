#!/usr/bin/env bash
# Install/update systemd units and daily cleanup timer for frontend ops.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SYSTEMD_SRC="$ROOT/deploy/systemd"
SYSTEMD_DST="/etc/systemd/system"

units=(
  marketplace-frontend.service
  marketplace-frontend-cleanup.service
  marketplace-frontend-cleanup.timer
)

for u in "${units[@]}"; do
  install -m 0644 "${SYSTEMD_SRC}/${u}" "${SYSTEMD_DST}/${u}"
done

chmod +x "${ROOT}/scripts/cleanup-frontend-artifacts.sh"
chmod +x "${ROOT}/scripts/deploy-frontend.sh"

systemctl daemon-reload
systemctl enable marketplace-frontend-cleanup.timer
systemctl start marketplace-frontend-cleanup.timer

echo "Installed:"
systemctl list-unit-files 'marketplace-frontend*' --no-pager
echo ""
echo "Production VPS (nginx static UI): disable optional preview to save RAM:"
echo "  sudo systemctl disable --now marketplace-frontend.service"
