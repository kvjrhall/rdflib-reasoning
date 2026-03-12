#! /usr/bin/env bash
set -o errexit -o nounset -o pipefail -o noclobber
# shellcheck source=../../../.script-helpers.sh
source "$(git rev-parse --show-toplevel)/.script-helpers.sh"
# -----------------------------------------------------------------------------

# Directory of this script (SCRIPT_DIR is set by helpers to the helpers' dir)
JENA_SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly JENA_SCRIPT_DIR
readonly JENA_DOCS="${JENA_SCRIPT_DIR}/jena-docs"
readonly JENA_SOURCE="${JENA_SCRIPT_DIR}/jena-source"
readonly JENA_INFERENCE_URL="https://jena.apache.org/documentation/inference/"
readonly JENA_REPO_URL="https://github.com/apache/jena.git"
readonly JENA_ETC_PATH="jena-core/src/main/resources/etc"

mkdir -p "${JENA_DOCS}"
loginfo "Fetching Jena inference documentation into ${JENA_DOCS}"
curl -sS -o "${JENA_DOCS}/inference.html" "${JENA_INFERENCE_URL}"

loginfo "Sparse shallow clone of ${JENA_ETC_PATH} into ${JENA_SOURCE}"
rm -rf "${JENA_SOURCE}"
git clone --depth 1 --filter=blob:none --sparse "${JENA_REPO_URL}" "${JENA_SOURCE}"
# Use --no-cone so only the exact path is included; cone mode would also pull in
# sibling files in parent directories and root.
git -C "${JENA_SOURCE}" sparse-checkout set --no-cone "${JENA_ETC_PATH}"

# Verify: only .git and the exact subdirectory (and its path components) must exist.
unexpected="$(
  cd "${JENA_SOURCE}" && find . -mindepth 1 \
    ! -path './.git' ! -path './.git/*' \
    ! -path './jena-core' ! -path './jena-core/src' ! -path './jena-core/src/main' \
    ! -path './jena-core/src/main/resources' \
    ! -path './jena-core/src/main/resources/etc' ! -path './jena-core/src/main/resources/etc/*' \
    -print
)"
if [[ -n "${unexpected}" ]]; then
  logfail "Sparse checkout included unexpected paths (only .git and ${JENA_ETC_PATH} are allowed):"
  echo "${unexpected}"
  exit 1
fi
logdebug "Sparse checkout verified: only .git and ${JENA_ETC_PATH} present"

logdebug "Removing git directory metadata from ${JENA_SOURCE}"
rm -rf "${JENA_SOURCE}"/.*

trap - EXIT
