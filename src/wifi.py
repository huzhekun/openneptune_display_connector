import subprocess  # nosec
from dataclasses import dataclass

WIFI_INTERFACE = "wlan0"
NMCLI_CONNECT_TIMEOUT = 45  # seconds nmcli waits for the connection to activate


def get_wlan0_status():
    """
    Get WiFi status without triggering a scan by using cached data.
    This is much lighter on the hardware.
    """
    try:
        # Get connection name and state from device info (no scan)
        connection_output = subprocess.check_output(
            ["nmcli", "-t", "-f", "GENERAL.CONNECTION,GENERAL.STATE", "dev", "show", "wlan0"]
        ).decode("utf-8")  # nosec B603, B607
        
        # Check if we're connected and get the connection name
        is_connected = False
        connection_name = None
        for line in connection_output.strip().split("\n"):
            if line.startswith("GENERAL.STATE:") and "connected" in line:
                is_connected = True
            elif line.startswith("GENERAL.CONNECTION:"):
                connection_name = line.split(":", 1)[1]
        
        if not is_connected or not connection_name:
            return False, None, None
        
        # Get SSID from the connection details (no scan)
        ssid_output = subprocess.check_output(
            ["nmcli", "-t", "-f", "connection.id,802-11-wireless.ssid", 
             "connection", "show", connection_name]
        ).decode("utf-8")  # nosec B603, B607
        
        ssid = connection_name  # Default to connection name
        for line in ssid_output.strip().split("\n"):
            if line.startswith("802-11-wireless.ssid:"):
                found_ssid = line.split(":", 1)[1]
                if found_ssid:
                    ssid = found_ssid
                break
        
        # Get signal strength using cached data (--rescan no prevents scanning)
        signal_output = subprocess.check_output(
            ["nmcli", "-t", "-m", "tabular", "-f", "IN-USE,SIGNAL", 
             "dev", "wifi", "list", "--rescan", "no"]
        ).decode("utf-8")  # nosec B603, B607
        
        rssi = None
        for line in signal_output.strip().split("\n"):
            if line.startswith("*:"):
                try:
                    rssi = int(line.split(":")[1])
                except (ValueError, IndexError):
                    pass
                break
        
        # Categorise the signal strength
        rssi_category = categorize_signal_strength(rssi)
        
        return True, ssid, rssi_category

    except subprocess.CalledProcessError:
        return False, None, None
    except FileNotFoundError:
        return False, None, None


def categorize_signal_strength(signal_percentage):
    if signal_percentage is None:
        return 0
    elif signal_percentage < 25:
        return 1
    elif 25 <= signal_percentage < 50:
        return 2
    elif 50 <= signal_percentage < 75:
        return 3
    else:
        return 4


@dataclass
class WifiNetwork:
    ssid: str
    signal: int  # 0-100, as reported by NetworkManager
    secured: bool
    in_use: bool = False


class WifiError(Exception):
    pass


def signal_level(signal_percentage):
    """Map a NetworkManager signal percentage to the 1-4 bar levels used by the
    stock Elegoo firmware. NetworkManager derives the percentage from dBm as
    2 * (dBm + 100), so these are the stock -55/-78/-89 dBm thresholds."""
    if signal_percentage >= 90:
        return 4
    elif signal_percentage >= 44:
        return 3
    elif signal_percentage >= 22:
        return 2
    return 1


def split_terse_line(line):
    """Split one line of `nmcli -t` output, honouring its backslash escapes."""
    fields = []
    current = []
    escaped = False
    for char in line:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(char)
    fields.append("".join(current))
    return fields


def parse_wifi_list(output):
    """Parse `nmcli -t -f IN-USE,SSID,SIGNAL,SECURITY device wifi list` output.

    Hidden networks are dropped, each SSID is kept once with its strongest
    access point, and the result is sorted with the active network first and
    the rest by signal strength."""
    networks = {}
    for line in output.splitlines():
        if not line.strip():
            continue
        fields = split_terse_line(line)
        if len(fields) < 4:
            continue
        in_use, ssid, signal, security = fields[:4]
        if not ssid:
            continue
        try:
            signal = int(signal)
        except ValueError:
            signal = 0
        network = WifiNetwork(
            ssid=ssid,
            signal=signal,
            secured=security.strip() not in ("", "--"),
            in_use=in_use.strip() == "*",
        )
        existing = networks.get(ssid)
        if existing is None:
            networks[ssid] = network
        else:
            existing.in_use = existing.in_use or network.in_use
            if network.signal > existing.signal:
                existing.signal = network.signal
                existing.secured = network.secured
    return sorted(networks.values(), key=lambda n: (not n.in_use, -n.signal))


def _run_nmcli(args, timeout=30):
    try:
        result = subprocess.run(  # nosec B603, B607
            ["nmcli", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as e:
        raise WifiError("NetworkManager (nmcli) is not installed") from e
    except subprocess.TimeoutExpired as e:
        raise WifiError("NetworkManager did not respond") from e
    if result.returncode != 0:
        raise WifiError(_describe_nmcli_error(result.stderr or result.stdout))
    return result.stdout


def _describe_nmcli_error(message):
    message = message.strip()
    if message.startswith("Error: "):
        message = message[len("Error: "):]
    lowered = message.lower()
    if "secrets were required" in lowered or "802-1x supplicant" in lowered:
        return "Wrong password"
    if "not authorized" in lowered or "insufficient privileges" in lowered:
        return "Permission denied"
    if "no network with ssid" in lowered:
        return "Network not found"
    if "timeout" in lowered:
        return "Connection timed out"
    return message.splitlines()[0] if message else "Unknown error"


def scan_wifi_networks(rescan=True):
    output = _run_nmcli(
        [
            "-t",
            "-f",
            "IN-USE,SSID,SIGNAL,SECURITY",
            "device",
            "wifi",
            "list",
            "ifname",
            WIFI_INTERFACE,
            "--rescan",
            "yes" if rescan else "no",
        ]
    )
    return parse_wifi_list(output)


def _find_wifi_profile(ssid):
    """Return the UUID of a saved Wi-Fi connection profile for this SSID."""
    output = _run_nmcli(["-t", "-f", "UUID,TYPE", "connection", "show"])
    for line in output.splitlines():
        fields = split_terse_line(line)
        if len(fields) < 2 or fields[1] != "802-11-wireless":
            continue
        uuid = fields[0]
        profile_ssid = split_terse_line(
            _run_nmcli(
                ["-g", "802-11-wireless.ssid", "connection", "show", "uuid", uuid]
            ).rstrip("\n")
        )[0]
        if profile_ssid == ssid:
            return uuid
    return None


def connect_wifi(ssid, password=None):
    """Connect wlan0 to a network, raising WifiError on failure.

    A saved profile for the SSID is reused (with its password replaced when a
    new one is given) so repeated attempts don't pile up duplicate profiles."""
    wait = ["--wait", str(NMCLI_CONNECT_TIMEOUT)]
    timeout = NMCLI_CONNECT_TIMEOUT + 15
    uuid = _find_wifi_profile(ssid)
    if uuid is not None:
        if password:
            _run_nmcli(["connection", "modify", "uuid", uuid, "wifi-sec.psk", password])
        _run_nmcli(
            [*wait, "connection", "up", "uuid", uuid, "ifname", WIFI_INTERFACE],
            timeout=timeout,
        )
        return
    args = [*wait, "device", "wifi", "connect", ssid]
    if password:
        args += ["password", password]
    _run_nmcli([*args, "ifname", WIFI_INTERFACE], timeout=timeout)


def is_wifi_radio_enabled():
    try:
        return _run_nmcli(["radio", "wifi"]).strip() == "enabled"
    except WifiError:
        return False


def set_wifi_radio(enabled):
    _run_nmcli(["radio", "wifi", "on" if enabled else "off"])


def get_wlan0_ip():
    try:
        output = _run_nmcli(["-g", "IP4.ADDRESS", "device", "show", WIFI_INTERFACE])
    except WifiError:
        return None
    address = output.strip().split("|")[0].strip()
    return address.split("/")[0] if address else None
