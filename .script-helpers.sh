#! /usr/bin/env bash

# NOTE: this should be sourced, not executed. Use the following template.
# -----------------------------------------------------------------------------
##! /usr/bin/env bash
#set -o errexit -o nounset -o pipefail -o noclobber
## shellcheck source=../../.script-helpers.sh
#source "$(git rev-parse --show-toplevel)/.script-helpers.sh"
# -----------------------------------------------------------------------------

shopt -s inherit_errexit

readonly DEBUG=${DEBUG:-0}
export DEBUG

SOURCE=${BASH_SOURCE[0]}
while [ -L "$SOURCE" ]; do
	DIR=$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)
	SOURCE=$(readlink "$SOURCE")
	[[ $SOURCE != /* ]] && SOURCE=$DIR/$SOURCE
done
SCRIPT_DIR=$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)
export SCRIPT_DIR

# Converts a name (typically filename) to logger-name format
# function log_slug() { basename "$1" .sh | sed 's/^\.//'; }

# Converts an array of names (typically filenames) to logger-name format
# example: LOGGER=$(log_path "${BASH_SOURCE[@]}")
# function log_path {
# 	local -a names
# 	local -a slugs
# 	names=$(
# 		printf '%s\n' "${@}" | tac | tr '\n' ' '
# 		echo
# 	)
# 	for name in $names; do
# 		slugs+=("$(log_slug "$name")")
# 	done
# 	join_by '.' "${slugs[@]}"
# }

# Joins a bash array or the sequence of arguments by the given delimiter string
# example: join_by ')|(' a b c #a)|(b)|(c
# example: join_by , "${FOO[@]}" #a,b,c
# see: https://stackoverflow.com/a/17841619
function join_by {
	local d=${1-} f=${2-}
	if shift 2; then
		printf %s "$f" "${@/#/$d}"
	fi
}

function trim_string() {
	local var="$*"
	# remove leading whitespace characters
	var="${var#"${var%%[![:space:]]*}"}"
	# remove trailing whitespace characters
	var="${var%"${var##*[![:space:]]}"}"
	printf '%s' "$var"
}

function stack_frame() {
	local depth=$(("$1" + 1))
	shift 1
	local format="${*}"

	local funcName="${FUNCNAME[$depth]}"
	local lineNumber="${BASH_LINENO[$((depth - 1))]}"
	local sourceFile="${SCRIPT_DIR}/${BASH_SOURCE[$depth]}"
	sourceFile=$(readlink -f "${sourceFile}")
	sourceFile=$(realpath --relative-to="${SCRIPT_DIR}" "${sourceFile}")

	local sourceCode=""
	if [[ "${format}" = "table" ]]; then
		sourceCode=$(sed "${lineNumber}q;d" "$(readlink -f "${SCRIPT_DIR}/$sourceFile")")
		sourceCode=$(echo -e "${sourceCode}" | head -n 1)
		sourceCode=$(trim_string "${sourceCode}")
		sourceCode="=${sourceCode}"
	fi
	echo "$funcName($sourceFile:$lineNumber)${sourceCode}"
}

function get_stack() {
	local start=${1:-1}
	local indent=''
	local stack=""
	for ((i = start; i < ${#FUNCNAME[@]}; i++)); do
		local newline
		if [[ $i -eq $start ]]; then newline=''; else newline=$'\n'; fi
		stack+="${newline}${indent}$(stack_frame $i "${2:-}")"
	done
	echo -e "$stack" | column --table-columns-limit 2 --separator "=" --table

	# local frame=0 lineNumber funcName fileName
	# while read lineNumber funcName fileName < <(caller $frame); do
	#     printf '  %s @ %s:%s' "${funcName}" "${fileName}" "${lineNumber}"
	#     ((frame++))
	# done
	#
	# local i lineNumber funcName fileName
	# for (( i=0; i<${#FUNCNAME[@]}; i++ )); do
	#     read lineNumber funcName fileName < <(caller $i)
	#     printf '  %s @ %s:%s' "${funcName}\n" "${fileName}" "${lineNumber}"
	# done
}

# Print an iso-8601 timestamp (converting UTC offsets to Z)
# pass additional arguments for `date` as arguments to this function
# see also: `timestamp_utc` for a
function timestamp() {
	date "${@}" "+%Y-%m-%dT%H:%M:%SZ"
}

# shellcheck disable=SC2120
function timestamp_utc() {
	timestamp -u "${@}"
}

export -f join_by get_stack timestamp timestamp_utc

# -----------------------------------------------------------------------------
declare -a LOGGER
LOGGER+=("$(basename "${BASH_SOURCE[0]}")")

function push_logger() {
	LOGGER+=("$(basename "${BASH_SOURCE[1]}")")
}
function pop_logger() {
	unset "LOGGER[${#LOGGER[@]}-1]"
}

normal=$(tput sgr 0)
bold=$(tput bold)
faint="${normal}$(tput dim)"
magenta=$(tput setaf 5)
yellow=$(tput setaf 11)
red=$(tput setaf 9)
white=$(tput setaf 15)
# shellcheck disable=SC2034
readonly normal bold faint magenta yellow red white

readonly LOG_TEMPLATE="${faint}%s ${normal}[%s${normal}] ${magenta}$$${faint} --- ${normal}[%s] %s${normal}\n"

function _logany() {
	local level
	local message
	case $1 in
	'DEBUG')
		level=$(printf "${faint}%-5s" "$1")
		message="${faint}$(echo -e "$2")"
		;;
	'INFO')
		level=$(printf "${normal}%-5s" "$1")
		message="${normal}$(echo -e "$2")"
		;;
	'WARN')
		level=$(printf "${yellow}%-5s" "$1")
		message="${yellow}$(echo -e "$2")"
		;;
	'FAIL')
		level=$(printf "${red}${bold}%-5s" "$1")
		message="${red}$(echo -e "$2")"
		;;
	*)
		echo "[INTERNAL ERROR] _logany 1=$1, 2=$2" >&2
		exit 1
		;;

	esac
	readonly level
	readonly message

	local call_site
	call_site=$(printf "%20s:%-3s" "${LOGGER[${#LOGGER[@]} - 1]}" "${BASH_LINENO[1]}")
	readonly call_site

	# shellcheck disable=SC2059
	printf "${LOG_TEMPLATE}" "$(timestamp_utc)" "$level" "$call_site" "$message" >&2
}

# -----------------------------------------------------------------------------
function logdebug() {
	if [[ $DEBUG -ne 0 ]]; then
		_logany "DEBUG" "${@}"
	fi
}

function loginfo() { _logany "INFO" "${@}"; }
function logwarn() { _logany "WARN" "${@}"; }
function logfail() { _logany "FAIL" "${@}"; }

# -----------------------------------------------------------------------------
function errexit() {
	local code=$?
	push_logger
	logfail "script terminating unexpectedly with code=${code}\n$(get_stack 1)"
}
trap errexit EXIT

function onerr() {
	local code=$?
	push_logger
	logfail "command exited with error; code=${code}\n$(get_stack 1 'table')"
}
trap onerr ERR

function assert() {
	local message="$1"
	shift 1
	if test "${@}"; then
		return 0
	else
		logfail "assertion failed (${*}): $message\n$(get_stack 2)"
		exit 1
	fi
}

# =============================================================================
WORKSPACE_DIR="$(git rev-parse --show-toplevel)"
export WORKSPACE_DIR
readonly WORKSPACE_DIR

# assert "missing bin directory: ${PROJECT_BIN}" -d "${PROJECT_BIN}"
logdebug "WORKSPACE_DIR=${WORKSPACE_DIR}"

# =============================================================================
if [[ ${#BASH_SOURCE[@]} -gt 1 ]]; then
	LOGGER+=("$(basename "${BASH_SOURCE[1]}")")
fi
