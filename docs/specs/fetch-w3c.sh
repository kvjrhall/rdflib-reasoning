#! /usr/bin/env bash
set -o errexit -o nounset -o pipefail -o noclobber
# shellcheck source=../../.script-helpers.sh
source "$(git rev-parse --show-toplevel)/.script-helpers.sh"
# -----------------------------------------------------------------------------


readonly specs_dir="${WORKSPACE_DIR}/docs/specs"

declare -A my_array=(
    ["owl2-conformance"]="https://www.w3.org/TR/owl2-conformance/"
    ["owl2-mapping-to-rdf"]="https://www.w3.org/TR/owl2-mapping-to-rdf/"
    ["owl2-overview"]="https://www.w3.org/TR/owl2-overview/"
    ["owl2-reasoning-profiles"]="https://www.w3.org/TR/owl2-profiles/"
    ["owl2-semantics-direct"]="https://www.w3.org/TR/owl2-direct-semantics/"
    ["owl2-semantics-rdf"]="https://www.w3.org/TR/owl2-rdf-based-semantics/"
    ["owl2-structure-syntax"]="https://www.w3.org/TR/owl2-syntax/"
    ["rdf11-concepts-syntax"]="https://www.w3.org/TR/rdf11-concepts/"
    ["rdf11-datasets"]="https://www.w3.org/TR/rdf11-datasets/"
    ["rdf11-primer"]="https://www.w3.org/TR/rdf11-primer/"
    ["rdf11-schema"]="https://www.w3.org/TR/rdf11-schema/"
    ["rdf11-semantics"]="https://www.w3.org/TR/rdf11-mt/"
)

for key in "${!my_array[@]}"; do
    spec_dir="${specs_dir}/${key}"
    spec_url="${my_array[$key]}"
    spec_raw="${spec_dir}/raw.html"
    spec_opt="${spec_dir}/optimized.html"

    if [[ -f "${spec_opt}" ]]; then
        loginfo "Found optimized spec: ${key}"
    else
        logdebug "Optimized spec not found: ${spec_opt}"
        if [[ -f "${spec_raw}" ]]; then
            logdebug "Raw spec found: ${spec_raw}"
        else
            loginfo "Downloading latest: ${key}"
            mkdir -p "${spec_dir}"
            curl -s -o "${spec_raw}" "${spec_url}"
        fi
    fi
done

for key in "${!my_array[@]}"; do
    spec_raw="${specs_dir}/${key}/raw.html"
    spec_opt="${specs_dir}/${key}/optimized.html"
    if [[ -f "${spec_raw}" ]]; then
        loginfo "Normalizing: ${key}"
        python "${WORKSPACE_DIR}/docs/specs/w3c-normalize.py" "${spec_raw}" -o "${spec_opt}"
    fi
done

trap - EXIT
