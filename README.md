# Potato Audio OS

A flashable, Volumio-style audio appliance image for the **Libre Computer AML-S905X-CC (Le Potato)**.

The repository is designed to build the complete microSD image using the official Armbian GitHub Action.

## What is built into the image

- Armbian Minimal / Debian 13 (Trixie)
- Current Armbian kernel branch for `lepotato`
- MPD music playback engine
- ALSA HDMI / USB-DAC support
- Potato Audio responsive web interface
- Library search and queue
- Play / pause / previous / next
- Software volume
- Audio-device detection
- Avahi / mDNS discovery
- Automatic service startup
- Automatic SD-card root filesystem expansion
- Built-in diagnostics command

## Build the one-file OS image

### 1. Create a GitHub repository

Create a new repository such as:

`potato-audio-os`

### 2. Upload everything in this ZIP

The repository root must contain:

```text
.github/
userpatches/
README.md
```

Do **not** upload the outer `potato-audio-os` folder as an extra level.

### 3. Run the builder

In GitHub:

**Actions → Build Potato Audio OS → Run workflow**

The workflow uses the official `armbian/build` GitHub Action with:

- board: `lepotato`
- release: `trixie`
- kernel: `current`
- UI: `minimal`
- output: compressed image (`.img.xz`)

When the build succeeds, the Armbian action creates a **GitHub Release** and attaches the finished image files.

## Flash the image

Download the `.img.xz` file from the GitHub Release.

You can flash the compressed `.img.xz` directly with tools such as:

- Balena Etcher
- Raspberry Pi Imager
- USBImager

Select the file, select the microSD card, and flash.

## First boot

1. Insert the microSD into Le Potato.
2. Connect Ethernet.
3. Connect HDMI to a receiver/TV, or attach a USB DAC.
4. Power on.
5. Give the board time to complete its first-boot filesystem expansion.
6. From another device on the same network, open:

`http://potatoaudio.local:8080`

If `.local` discovery is unavailable on your network, obtain the board IP from your router and use:

`http://BOARD-IP:8080`

Armbian may still ask you to create a secure user/password when you first log in locally or through SSH. The Potato Audio web service does not require that interactive login before it can start.

## Add local music

Music lives at:

`/var/lib/mpd/music`

After copying music there, use the web interface **Rescan** command.

## Diagnostics

On the Le Potato:

```bash
sudo potato-audio-diagnose
```

Also useful:

```bash
aplay -l
mpc status
systemctl status mpd
systemctl status potato-audio
journalctl -u potato-audio -n 100 --no-pager
```

## Current v1 limitation

Potato Audio detects ALSA audio outputs in the web interface, but changing the active MPD output still requires editing `/etc/mpd.conf`.

The next OS revision should add:
- output switching from the browser
- test tone
- NAS / SMB setup
- Internet radio
- album artwork
- AirPlay
- optional Spotify Connect-compatible receiver support
- Bluetooth receiver mode
- optional Wi-Fi setup wizard
