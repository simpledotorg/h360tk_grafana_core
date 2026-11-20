#!/bin/sh
BRANDING_DIR=/var/lib/grafana/branding
DEFAULT_LOGO=/usr/share/grafana/default_logo.svg
DEFAULT_TITLE="HEARTS360 Dashboard"
LOGO="$DEFAULT_LOGO"
TITLE="$DEFAULT_TITLE"

# Logo: use branding/logo.svg only if it exists, is non-empty and looks like an SVG
if [ -s "$BRANDING_DIR/logo.svg" ] && grep -q "<svg" "$BRANDING_DIR/logo.svg"; then
  LOGO="$BRANDING_DIR/logo.svg"
fi

# Favicon: use branding/favicon.png only if it exists and is a real PNG (magic bytes)
DEFAULT_FAVICON=/usr/share/grafana/default_fav32.png
FAVICON="$DEFAULT_FAVICON"
if [ -s "$BRANDING_DIR/favicon.png" ] && \
   [ "$(head -c 4 "$BRANDING_DIR/favicon.png" | od -An -tx1 | tr -d ' \n')" = "89504e47" ]; then
  FAVICON="$BRANDING_DIR/favicon.png"
fi

# Title: parse LOGIN_TITLE from text.env as plain KEY=VALUE (never "source" it)
if [ -r "$BRANDING_DIR/text.env" ]; then
  VALUE=$(grep 'LOGIN_TITLE=' "$BRANDING_DIR/text.env" | grep -v '^[[:space:]]*#' | tail -n1 | cut -d= -f2- | tr -d '\r')
  VALUE=$(printf '%s' "$VALUE" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' \
                                     -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'\$/\1/")
  VALUE=$(printf '%s' "$VALUE" | tr -d '"'"'"'\\<>`$' | cut -c1-80)
  [ -n "$VALUE" ] && TITLE="$VALUE"
fi

# Apply logo to grafana_icon.svg, grafana_icon_dark.svg and the hashed build copies.
# Runs every start, so removing branding/ restores the default logo.
find /usr/share/grafana/public -name "grafana_icon*.svg" -type f | while read -r f; do
  # cat > (truncate-and-write) instead of cp: busybox cp fails with "File exists" here
  cat "$LOGO" > "$f" || echo "WARNING: could not write logo to $f"
done

# Apply favicon to every fav32.png copy (also resets to default if branding/favicon.png is gone)
find /usr/share/grafana/public -name "fav32*.png" -type f | while read -r f; do
  cat "$FAVICON" > "$f" || echo "WARNING: could not write favicon to $f"
done

# Apply title in place: swap the previously applied title for the new one.
# Only touches the (large) files when the title actually changed; no .tpl copies needed.
# Also resets to default if text.env is gone. Titles shorter than 3 chars are rejected
# (too risky to match inside JS bundles).
APPLIED_FILE=/usr/share/grafana/title_applied
OLD=$(cat "$APPLIED_FILE" 2>/dev/null)
[ "${#TITLE}" -lt 3 ] && TITLE="$DEFAULT_TITLE"
if [ -n "$OLD" ] && [ "$OLD" != "$TITLE" ]; then
  OLD_RE=$(printf '%s' "$OLD" | sed 's/[].*[^$|\\&]/\\&/g')
  NEW_SAFE=$(printf '%s' "$TITLE" | sed 's/[|&\\]/\\&/g')
  while read f; do
    # sed -i needs dir write access (root-owned); edit via /tmp and cat > into the file instead
    sed "s|$OLD_RE|$NEW_SAFE|g" "$f" > /tmp/title.tmp && cat /tmp/title.tmp > "$f" \
      || echo "WARNING: could not write title to $f"
  done < /usr/share/grafana/title_files.txt
  rm -f /tmp/title.tmp
  printf '%s\n' "$TITLE" > "$APPLIED_FILE"
fi

echo "Branding applied: title='$TITLE' logo=$LOGO favicon=$FAVICON"
exec /run.sh "$@"