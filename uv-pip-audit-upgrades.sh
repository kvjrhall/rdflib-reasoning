#! /usr/bin/env bash
set -o errexit -o nounset -o pipefail -o noclobber
# shellcheck source=.script-helpers.sh
source "$(git rev-parse --show-toplevel)/.script-helpers.sh"
# -----------------------------------------------------------------------------

# NOTE: this script will fail if `make audit` does not find any vulnerabilities.

if [[ $# -eq 1 && "$1" == "--dry-run" ]]; then
    echo "would run: uv lock $(uv run pip-audit -f json | jq -r '.dependencies[] | select(.vulns | length > 0) | "-P", .name')" >&2
    exit 0
elif [[ $# -ne 0 ]]; then
    logerror "Usage: $0 [--dry-run]"
    exit 1
fi

uv lock "$(uv run pip-audit -f json | jq -r '.dependencies[] | select(.vulns | length > 0) | "-P", .name')"
