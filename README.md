# Potato Audio OS v2

A flashable, Volumio-style audio appliance for the **Libre Computer AML-S905X-CC (Le Potato)**.

## New in v2

- HDMI fullscreen Now Playing display
- Custom Internet Radio with saved stations
- Browser-selectable HDMI / USB DAC audio outputs
- Audio output test tone
- Persistent radio and output settings

The phone/computer remote remains available at `http://potatoaudio.local:8080`.

## Build

Run **Actions → Build Potato Audio OS → Run workflow** and choose the `v2` branch.

The build uses Armbian for `lepotato`, Debian 13/Trixie, current kernel, and the minimal base image. V2 adds the X/Chromium kiosk stack required for HDMI display.

## First boot

1. Flash the resulting `.img.xz` to microSD.
2. Insert it into Le Potato.
3. Connect Ethernet and HDMI.
4. Connect HDMI audio or a USB DAC.
5. Power on.
6. Open `http://potatoaudio.local:8080`.

## Radio

Use a direct HTTP/HTTPS audio stream URL, not just the station website.

## Diagnostics

```bash
sudo potato-audio-diagnose
aplay -l
mpc status
systemctl status potato-audio
systemctl status potato-audio-kiosk
```
