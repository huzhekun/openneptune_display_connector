<p align="center">
  <img src="https://github.com/OpenNeptune3D/OpenNept4une/raw/main/pictures/OpenNept4une.png" alt="OpenNept4une Logo" width="250">
  <h1 align="center">OpenNept4une Display Connector</h1>
</p>

![GitHub commit activity](https://img.shields.io/github/commit-activity/w/OpenNeptune3D/display_connector) ![GitHub License](https://img.shields.io/github/license/OpenNeptune3D/display_connector) ![GitHub top language](https://img.shields.io/github/languages/top/OpenNeptune3D/display_connector) ![Static Badge](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)

Allows you to use the Touch screen from your neptune 3 or 4 printer with a stock Klipper installation. Currently optimized for the Neptune 4 models.

## About this fork

This is a fork of [OpenNeptune3D/display_connector](https://github.com/OpenNeptune3D/display_connector),
used with [huzhekun/OpenNept4une](https://github.com/huzhekun/OpenNept4une)
and tested on the Neptune 4 Max with the stock Elegoo screen firmware 1.2.22.
It includes upstream's `dev` branch (up to 3272efe, 2026-10-09) and adds:

- **On-screen Wi-Fi setup** on the Neptune 4 Plus/Max ([docs/wifi.md](docs/wifi.md)).
- **Power-loss recovery** for OpenNept4une's resume after a power cut: the
  screen's "Power Loss Recovery" prompt offers to continue the print, and the
  Power Loss Recovery switch in the advanced settings turns recovery on and off.
- **Screen sleep:** the screen turns off when it isn't used, and on again on a
  touch or when something happens ([docs/screen-sleep.md](docs/screen-sleep.md)).
- **Fixes for screen firmware 1.2.22:** it's supported, and the about page
  shows the size, firmware version and IP in the right fields.
- **UTF-8 text** on the screen, so values such as "°" aren't dropped.

## Supported Displays and Firmware

- TJC4827X243_011 (Neptune 3 and 4 Display)
  - Elegoo firmware 1.2.11, 1.2.12, 1.2.13, 1.2.14, 1.2.14.1, 1.2.16, 1.2.17, 1.2.18 and 1.2.22
  - OpenNeptune firmware 0.1.5


## Supported Printer Models

- Elegoo Neptune 4
- Elegoo Neptune 4 Pro
- Elegoo Neptune 4 Plus
- Elegoo Neptune 4 Max

## Install

Running the `display-service-installer.sh` script on your printer should be enough to get everything working. Currently the connector mostly works on printers with [OpenNept4une](https://github.com/OpenNeptune3D/OpenNept4une).

## Wi-Fi Setup (Neptune 4 Plus/Max)

On the Elegoo display firmware, Settings → WLAN lists nearby networks and joins one using the on-screen keyboard, through NetworkManager. The installer adds a polkit rule so the display service can do this without root. See [docs/wifi.md](docs/wifi.md) for how it works and how to test it.

## Screen Sleep

After 20 minutes without touches, page changes or print state changes, the
screen turns off; it stays on during prints. A touch turns it back on, as
does a print starting or ending, or a prompt. The timeouts are in
`[screen_sleep]` in `display_connector.cfg`. See [docs/screen-sleep.md](docs/screen-sleep.md).

## Power-Loss Recovery

With OpenNept4une's power-loss recovery
([docs](https://github.com/huzhekun/OpenNept4une/blob/main/docs/power-loss-recovery.md)),
the screen shows the stock "Power Loss Recovery" page after a power cut with
the file name, or why the print can't be resumed: Confirm runs `PLR_RESUME`,
Cancel `PLR_DISCARD`. The Power Loss Recovery switch in the advanced settings
creates or removes `~/printer_data/plr/disabled`, which turns recovery off
while it exists.
