#!/bin/bash
set -e

RELEASE="$1"
LINUXFAMILY="$2"
BOARD="$3"
BUILD_DESKTOP="$4"

Main() {
    if [[ "$BOARD" != "lepotato" ]]; then
        echo "Potato Audio image customization skipped: BOARD=$BOARD"
        return 0
    fi

    echo "=== Installing Potato Audio OS ==="

    export DEBIAN_FRONTEND=noninteractive

    apt-get update
    apt-get install -y --no-install-recommends \
        mpd mpc alsa-utils avahi-daemon avahi-utils \
        python3 python3-venv python3-pip \
        cifs-utils curl rsync ca-certificates

    # Appliance identity
    echo "potatoaudio" > /etc/hostname
    if grep -q '^127.0.1.1' /etc/hosts; then
        sed -i 's/^127\.0\.1\.1.*/127.0.1.1\tpotatoaudio/' /etc/hosts
    else
        echo -e "127.0.1.1\tpotatoaudio" >> /etc/hosts
    fi
    echo "1.0.0" > /etc/potato-audio-version

    # Copy our root filesystem overlay.
    cp -a /tmp/overlay/. /

    # Python environment
    python3 -m venv /opt/potato-audio/.venv
    /opt/potato-audio/.venv/bin/pip install --no-cache-dir --upgrade pip
    /opt/potato-audio/.venv/bin/pip install --no-cache-dir \
        -r /opt/potato-audio/server/requirements.txt

    # Dedicated service account
    if ! id potatoaudio >/dev/null 2>&1; then
        useradd --system --home /opt/potato-audio --shell /usr/sbin/nologin potatoaudio
    fi
    usermod -aG audio potatoaudio || true
    usermod -aG audio mpd || true

    # MPD data directories
    install -d -o mpd -g audio -m 0775 /var/lib/mpd/music
    install -d -o mpd -g audio -m 0775 /var/lib/mpd/playlists

    # MPD appliance configuration
    cat > /etc/mpd.conf <<'EOF'
music_directory         "/var/lib/mpd/music"
playlist_directory      "/var/lib/mpd/playlists"
db_file                 "/var/lib/mpd/tag_cache"
log_file                "syslog"
pid_file                "/run/mpd/pid"
state_file              "/var/lib/mpd/state"
sticker_file            "/var/lib/mpd/sticker_file"
user                    "mpd"
group                   "audio"
bind_to_address         "127.0.0.1"
port                    "6600"
auto_update             "yes"
restore_paused          "yes"
metadata_to_use         "artist,album,title,track,name,genre,date,composer,performer,disc"

audio_output {
    type        "alsa"
    name        "Potato Audio"
    device      "default"
    mixer_type  "software"
}

filesystem_charset "UTF-8"
EOF

    # Avahi alias gives us potatoaudio.local even if hostname is later changed.
    cat > /etc/avahi/services/potato-audio.service <<'EOF'
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">Potato Audio on %h</name>
  <service>
    <type>_http._tcp</type>
    <port>8080</port>
  </service>
</service-group>
EOF

    chmod +x /usr/local/bin/potato-audio-diagnose
    chown -R potatoaudio:potatoaudio /opt/potato-audio

    systemctl enable mpd.service
    systemctl enable avahi-daemon.service
    systemctl enable potato-audio.service

    # Friendly console banner
    cat > /etc/update-motd.d/99-potato-audio <<'EOF'
#!/bin/sh
IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo
echo "  Potato Audio OS"
echo "  Web player: http://potatoaudio.local:8080"
[ -n "$IP" ] && echo "  IP player:  http://$IP:8080"
echo "  Diagnostics: sudo potato-audio-diagnose"
echo
EOF
    chmod +x /etc/update-motd.d/99-potato-audio

    # Allow Armbian to resize rootfs to fill the SD card on first boot.
    rm -f /root/.no_rootfs_resize

    echo "=== Potato Audio OS customization complete ==="
}

Main "$@"
