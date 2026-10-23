# Screen sleep

Static pages left on the screen around the clock leave a ghost image on the
LCD. The connector turns the screen off (`sleep=1`, which switches off the
backlight) when nothing has happened on it for a while, and a touch turns it
back on (`thup=1`). The touch that wakes the screen isn't passed on to the
page, so it can't press a button.

```ini
[screen_sleep]
; minutes without activity before the screen turns off, 0 = never
idle_timeout = 20
; the same during a print; by default the screen stays on while printing
print_timeout = 0
```

These are the defaults, so the section is only needed to change them.

* Touches, page changes and print state changes count as activity. The values
  the connector updates on the screen all the time, like the temperatures,
  don't, otherwise the screen would never turn off.
* The screen turns on when a print starts, finishes, is cancelled or fails,
  and whenever the connector changes the page, for example for the power-loss
  recovery prompt or a filament runout.
* Turning off **Backlight** in the screen's advanced settings, which stops the
  screen firmware dimming the backlight after 3 minutes, turns sleep off too.

While the screen is off it ignores everything the connector sends without
replying. The connector drops those updates rather than waiting for replies
that don't come (which would make it reconnect, and that wakes the screen),
and sends the full printer status again once the screen is on.
