#!/bin/bash
# wait-for-it.sh - Wait for a service to be available
# Usage: ./wait-for-it.sh host:port [-t timeout] [-- command args]

WAITFORIT_TIMEOUT=60
WAITFORIT_HOST="localhost"
WAITFORIT_PORT=5432

while [[ $# -gt 0 ]]; do
    case "$1" in
        *:* )
            WAITFORIT_HOST=${1/:*/}
            WAITFORIT_PORT=${1/*:/}
            shift
            ;;
        -t)
            WAITFORIT_TIMEOUT="$2"
            shift 2
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "Usage: $0 host:port [-t timeout] [-- command args]"
            exit 1
            ;;
    esac
done

WAITFORIT_START_TS=$(date +%s)
while :; do
    if nc -z "$WAITFORIT_HOST" "$WAITFORIT_PORT" >/dev/null 2>&1; then
        WAITFORIT_END_TS=$(date +%s)
        echo "Service at $WAITFORIT_HOST:$WAITFORIT_PORT is available after $((WAITFORIT_END_TS - WAITFORIT_START_TS)) seconds"
        exit 0
    fi
    WAITFORIT_CURRENT_TS=$(date +%s)
    if [ $((WAITFORIT_CURRENT_TS - WAITFORIT_START_TS)) -gt "$WAITFORIT_TIMEOUT" ]; then
        echo "timeout occurred after waiting $WAITFORIT_TIMEOUT seconds for $WAITFORIT_HOST:$WAITFORIT_PORT"
        exit 1
    fi
    sleep 1
done