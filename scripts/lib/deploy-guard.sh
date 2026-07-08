#!/usr/bin/env bash
# Deploy guard: block production deploy on dirty git tree (allowlisted artifacts exempt).
# Source from deploy scripts: source "$(dirname "$0")/lib/deploy-guard.sh"
set -euo pipefail

_DEPLOY_GUARD_ROOT="${DEPLOY_GUARD_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

# Returns 0 if path matches deploy allowlist (untracked or modified).
_deploy_guard_is_allowed() {
  local path="$1"
  local status="$2"

  case "${path}" in
    frontend/tsconfig*.tsbuildinfo) return 0 ;;
    .coverage|htmlcov/*) return 0 ;;
    .env.bak*|.env.local|.env.integration) return 0 ;;
    tmp_*|reports_investigation*.png|reports_predeploy*.png) return 0 ;;
    frontend/test-results|frontend/test-results/*|frontend/test-results/**) return 0 ;;
    docs/release/screenshots/*|docs/release/screenshots/**) return 0 ;;
  esac

  if [[ "${status}" =~ ^[?]{2} ]]; then
    case "${path}" in
      .coverage|.env.bak*) return 0 ;;
    esac
  fi

  return 1
}

# Returns 0 if clean or forced; 1 if dirty and blocked.
deploy_guard_check() {
  if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
    return 0
  fi
  if [[ "${DEPLOY_FORCE:-0}" == "1" || "${DEPLOY_FORCE_DIRTY:-0}" == "1" ]]; then
    echo "WARNING: deploy guard bypassed (DEPLOY_FORCE or DEPLOY_FORCE_DIRTY)" >&2
    return 0
  fi

  local root="${1:-${_DEPLOY_GUARD_ROOT}}"
  local -a violations=()
  local line path status

  while IFS= read -r line; do
    [[ -z "${line}" ]] && continue
    status="${line:0:2}"
    path="${line:3}"

    if _deploy_guard_is_allowed "${path}" "${status}"; then
      continue
    fi
    violations+=("${line}")
  done < <(cd "${root}" && git status --porcelain -uall)

  if [[ "${#violations[@]}" -gt 0 ]]; then
    echo "DEPLOY GUARD FAIL: git working tree is dirty (${#violations[@]} unallowed paths):" >&2
    for line in "${violations[@]}"; do
      echo "  ${line}" >&2
    done
    echo "Commit changes or set DEPLOY_FORCE_DIRTY=1 for emergency deploy." >&2
    return 1
  fi

  return 0
}

# RAM guard helper (existing deploy-frontend semantics).
deploy_guard_check_ram() {
  local min_mb="${1:-300}"
  if [[ "${DEPLOY_FORCE:-0}" == "1" || "${DEPLOY_FORCE_RAM:-0}" == "1" ]]; then
    echo "WARNING: RAM deploy guard bypassed (DEPLOY_FORCE or DEPLOY_FORCE_RAM)" >&2
    return 0
  fi
  local avail_mb
  avail_mb="$(free -m | awk '/^Mem:/{print $7}')"
  if [[ "${avail_mb}" -lt "${min_mb}" ]]; then
    echo "DEPLOY GUARD FAIL: low memory ${avail_mb}MB < ${min_mb}MB (set DEPLOY_FORCE_RAM=1 to override)" >&2
    return 1
  fi
  return 0
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  deploy_guard_check "${DEPLOY_GUARD_ROOT}"
fi
