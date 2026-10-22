# On-screen Wi-Fi setup

The stock Elegoo display firmware contains a Wi-Fi network list and a full
keyboard, but they only work when the stock printer software drives them. This
document records how that software uses those pages (worked out by decompiling
it) and how the connector reimplements the flow on top of NetworkManager.

## Sources

| Artifact | Version | Notes |
|---|---|---|
| Elegoo printer app `znp_tjc_klipper` | APP V1.2.3.4, built 2025-01-20 | Neptune 4 Plus/Max package, unstripped. Ships with screen UI 1.2.18. |
| Elegoo printer app `znp_tjc_klipper` | APP V1.4.1.5, built 2026-08-01 | Upgraded N4 Plus/Max ("-E") package, stripped but exports its function names. Ships with screen UI 1.2.22. |
| Stock and Slate HMI sources | [display_firmware](https://github.com/OpenNeptune3D/display_firmware) | Page and component layout, button codes. |

The Wi-Fi code in the two app builds is the same: identical page numbers,
button handling, picture ids and `wpa_supplicant` commands. Compiled `.tft`
files can't be compared directly (their contents are scrambled), so this is the
evidence that UI 1.2.22 needs nothing different from UI 1.2.18.

An older app build (2023-07, Neptune 4 Pro) has the same functions, but none of
them are reachable and its keyboard handler only logs. On-screen Wi-Fi was
finished in later builds.

## Stock protocol

### Pages

The stock app navigates with `page <number>`. For UI 1.2.18:

| Page | Number | Buttons (code sent in the `0x65` touch event) |
|---|---|---|
| `set_4_max`, Plus/Max settings | 125 | 1 Language, 2 WLAN, 3 Lights, 4 Fan, 5 Motors off, 6 Filament sensor, 7 Factory settings, 8 About, 9 Advanced, 0 Back |
| `wifi_list` | 130 | 1-8 network rows, 9 rescan, 10 previous page, 11 next page, 12 Wi-Fi on/off switch, 0 Back |
| `wifi_scaning`, loading animation | 131 (probably) | 0 Back |
| `keybdA`, keyboard | 132 (probably) | OK sends the keyboard frame below, 0 Back |

Only 125 and 130 are confirmed in both directions (the app both navigates to
them and handles their buttons). Page numbers also shift between screen
firmware versions, so the connector navigates by page name and dispatches these
pages' buttons by name too (`named_response_actions`).

The plain `set` page used by the Neptune 4 and 4 Pro has no Wi-Fi entry. Its
top-right hotspot (code 10) is a home button.

### Keyboard frame

`keybdA`'s OK button sends:

```
0x70  <current page>  <wifi_index>  <typed text...>
```

There is no `FF FF FF` terminator. The stock app reads the serial port with a
non-blocking `read()` every 5 ms and treats whatever arrived in one read as one
message. The connector does the equivalent: an unterminated `0x70` frame is
complete once the display has been idle for 50 ms (`src/tjc.py`). A terminated
`0x70` frame is still a normal reply to a `get` command.

The keyboard limits input to 30 characters. That's set in the display firmware.

### Wi-Fi list drawing

Rows are `t0`-`t7` (SSID text, max 32 bytes), `q0`-`q7` (signal, crop
pictures) and `q8`-`q15` (lock/state icon). Crop pictures show the region of a
full-screen picture at the component's position, which is why one picture id
can serve different icons.

| Picture | Used for |
|---|---|
| 340 | empty row / open network |
| 341 | lock icon (q8-q15), weakest signal (q0-q7) |
| 342, 343, 344 | signal: 2, 3, 4 bars |
| 353, 354, 355, 346 | signal 1-4 bars on the connected row |
| 345, 346, 347 | row state: connecting, connected, failed |
| 348 / 347 | `q16` Wi-Fi switch: on / off |
| 313, 314-317 | main page Wi-Fi icon: no Wi-Fi, 1-4 bars |

Signal bars use -55, -78 and -89 dBm as thresholds. NetworkManager reports
percent as `2 * (dBm + 100)`, so the connector uses 90 / 44 / 22 %.

`t9` holds a status line (stock: `IP:<address>`).

### Stock connection flow

1. WLAN on the settings page shows the loading page, then the list, and runs
   `SCAN` / `SCAN_RESULTS` over `wpa_supplicant`'s control socket. Up to 48
   networks (6 pages of 8). The connected network is moved to the top.
2. An open network is joined straight away. A secured one (`WPA` in the scan
   flags) opens `keybdA` with the SSID written to `t0`.
3. On OK: `SET_NETWORK 0 ssid/psk`, `key_mgmt WPA-PSK`, `SELECT_NETWORK 0`,
   `REASSOCIATE`, then poll `STATUS` every 2 s: `COMPLETED` with an IP means
   success (`SAVE_CONFIG`, rescan); `INACTIVE`, repeated `SCANNING` or a stuck
   `4WAY_HANDSHAKE` means failure.

## Implementation in the connector

* `src/wifi.py`: NetworkManager backend (`nmcli`): scan, connect (reusing
  a saved profile for the SSID when there is one), radio on/off, wlan0 address.
* `src/tjc.py`: `EventType.KEYBOARD_INPUT` and the idle-gap framing above.
* `src/response_actions.py`: `named_response_actions` for `set_4_max` and
  `wifi_list`.
* `src/neptune4.py`: Neptune 4 Plus/Max use `set_4_max` as the settings
  page on the Elegoo display firmware. Its unused Factory Settings row is
  relabelled "Temperature Settings" and opens the temperature presets, which
  the plain settings page offered.
* `src/elegoo_display.py`: list and keyboard drawing.
* `display.py`: the flow. Scan behind the loading page, select, password,
  connect, rescan. The last connection attempt is pinned to the top of the
  list with a connecting / failed icon and the error in `t9`.
* `wifi-permissions-setup.sh`: `display.service` runs as `mks` with
  `NoNewPrivileges=true`, so `sudo` is unavailable. The script installs a
  polkit rule that lets that user perform NetworkManager actions (and only
  those). Both the installer and `display.service` (as a best-effort
  `ExecStartPre`) run it.

The OpenNeptune (Slate) theme keeps the stock `wifi_list` and `keybdA` pages,
but its settings page has no WLAN entry, so Wi-Fi isn't reachable there yet.

## Running a fork on OpenNept4une

OpenNept4une clones the connector to `~/display_connector` and registers it
with Moonraker:

```ini
[update_manager display]
type: git_repo
primary_branch: main
path: /home/mks/display_connector
virtualenv: /home/mks/display_connector/venv
requirements: requirements.txt
origin: https://github.com/OpenNeptune3D/display_connector.git
managed_services: display
```

Two OpenNept4une actions undo a fork:

* Its update step rewrites this block with the upstream `origin` and the
  checkout's current branch.
* "Install Touch-Screen Display Service" deletes `~/display_connector` and
  clones upstream again.

To try a fork on the printer (replace `<you>` with your GitHub user):

```sh
cd ~/display_connector
git remote add fork https://github.com/<you>/display_connector.git
git fetch fork
git checkout -b wifi-settings fork/wifi-settings
sudo sh ~/display_connector/wifi-permissions-setup.sh mks
sudo systemctl restart display
```

No Python dependencies were added, so the existing venv keeps working.
`display.service` copies its own unit file from the repo on every start, so
the new `ExecStartPre` that runs the permission script takes effect from the
second restart onwards. Running the script by hand covers the first one.

Moonraker reports the repo as invalid while the checkout's branch or remote
doesn't match the block above. To have Moonraker track the fork instead, point
`origin` and `primary_branch` at it in `~/printer_data/config/moonraker.conf`,
make the fork the checkout's `origin` remote, and restart Moonraker:

```sh
git -C ~/display_connector remote set-url origin https://github.com/<you>/display_connector.git
git -C ~/display_connector branch -u origin/wifi-settings
```

Running OpenNept4une's updater afterwards rewrites the block back to upstream.

To go back to upstream: `git checkout main` (or OpenNept4une's branch) and
restart the service. The polkit rule can stay or be removed from
`/etc/polkit-1/rules.d/50-display-connector-networkmanager.rules`.

## Testing on a printer

1. Install the branch as above.
2. Check the permission rule took effect:
   `sudo -u mks nmcli device wifi rescan` should succeed without a prompt.
3. Settings → WLAN should show the loading animation, then the list.
4. Watch the log while tapping around: `journalctl -u display -f`. Taps that
   aren't handled show up as `Unhandled Response <page> <component>`.

Passwords never reach the log. Note that `nmcli` receives the password as a
command-line argument, so it's briefly visible in the process list.

## Known limits

* Hidden networks can't be joined (they aren't listed).
* SSIDs longer than 32 bytes are cut to fit the text field.
* Enterprise (802.1X) networks aren't supported.
* Screen UI versions other than 1.2.18/1.2.22 may name or number the Wi-Fi
  pages differently. They're untested.
