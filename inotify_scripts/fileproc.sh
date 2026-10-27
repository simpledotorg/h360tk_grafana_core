#!/bin/bash

# $1 --> timestamp
# $2 --> watched file/directory path
# $3 --> event name(s)
# $4 --> filename (if a directory is monitored)

echo $1 $2 $3 $4

FULL_PATH="${2}${4}"

if [ ! -f "$FULL_PATH" ]; then
    echo "Info: '$FULL_PATH' is not a regular file or does not exist. Exiting."
    exit 0
fi

# One upload fires a MODIFY event per write, and those events queue up while a
# file is being processed. CLOSE_WRITE would be cleaner, but Docker Desktop
# (macOS) does not deliver it across containers. So: wait until the file stops
# changing, then skip any event for a size/mtime that was already processed.
file_signature() { stat -c '%s %Y' "$1" 2>/dev/null; }

SIGNATURE="$(file_signature "$FULL_PATH")"
while sleep 5; do
    CURRENT="$(file_signature "$FULL_PATH")"
    if [ -z "$CURRENT" ]; then
        echo "Info: '$FULL_PATH' disappeared before upload finished. Exiting."
        exit 0
    fi
    [ "$CURRENT" = "$SIGNATURE" ] && break
    SIGNATURE="$CURRENT"
done

STATE_DIR=/tmp/h360tk_processed
mkdir -p "$STATE_DIR"
STATE_FILE="$STATE_DIR/$(printf '%s' "$FULL_PATH" | md5sum | cut -d' ' -f1)"

if [ "$(cat "$STATE_FILE" 2>/dev/null)" = "$SIGNATURE" ]; then
    echo "Info: '$FULL_PATH' already processed. Skipping duplicate event."
    exit 0
fi
echo "$SIGNATURE" > "$STATE_FILE"

echo "We got a file !! $FULL_PATH"

python3 "${H360TK_DATA_LOAD_SCRIPT}" "$FULL_PATH"
