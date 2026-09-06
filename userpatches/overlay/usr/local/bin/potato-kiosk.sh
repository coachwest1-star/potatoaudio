#!/bin/bash
set -e

# Wait for the Potato Audio web service before launching Chromium.
for i in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8080/api/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

# Keep the display awake and launch the Smart Hub full screen.
xset -dpms || true
xset s off || true
xset s noblank || true

exec /usr/bin/chromium \
  --no-sandbox \
  --kiosk \
  --no-first-run \
  --disable-session-crashed-bubble \
  --disable-infobars \
  --disable-translate \
  --autoplay-policy=no-user-gesture-required \
  http://127.0.0.1:8080/hub.html
