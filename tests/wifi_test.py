import subprocess
from unittest.mock import MagicMock, patch

import pytest
from src import wifi
from src.wifi import (
    WifiError,
    WifiNetwork,
    connect_wifi,
    parse_wifi_list,
    signal_level,
    split_terse_line,
)


def completed(stdout="", returncode=0, stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)


def test_split_terse_line_unescapes():
    assert split_terse_line(r"*:My\:Net:80:WPA2") == ["*", "My:Net", "80", "WPA2"]
    assert split_terse_line(r" :back\\slash:5:") == [" ", "back\\slash", "5", ""]


def test_parse_wifi_list_dedupes_and_sorts():
    output = "\n".join(
        [
            " :Neighbour:40:WPA2",
            "*:Home:62:WPA1 WPA2",
            " :Home:70:WPA2",
            " :Cafe:90:",
            " ::99:WPA2",  # hidden network
            " :Guest:20:--",
        ]
    )
    networks = parse_wifi_list(output)
    assert networks == [
        WifiNetwork("Home", 70, True, in_use=True),
        WifiNetwork("Cafe", 90, False),
        WifiNetwork("Neighbour", 40, True),
        WifiNetwork("Guest", 20, False),
    ]


def test_signal_level_matches_stock_thresholds():
    # 2 * (dBm + 100): -55 dBm = 90, -78 dBm = 44, -89 dBm = 22
    assert signal_level(100) == 4
    assert signal_level(90) == 4
    assert signal_level(89) == 3
    assert signal_level(44) == 3
    assert signal_level(43) == 2
    assert signal_level(22) == 2
    assert signal_level(21) == 1
    assert signal_level(0) == 1


def test_nmcli_errors_are_summarised():
    with patch.object(
        wifi.subprocess,
        "run",
        return_value=completed(
            returncode=4,
            stderr="Error: Connection activation failed: Secrets were required, but not provided.\n",
        ),
    ):
        with pytest.raises(WifiError, match="Wrong password"):
            wifi.set_wifi_radio(True)


def test_connect_new_network():
    run = MagicMock(side_effect=[completed("abcd:802-3-ethernet\n"), completed()])
    with patch.object(wifi.subprocess, "run", run):
        connect_wifi("Home", "hunter22")
    args = run.call_args_list[1].args[0]
    assert args == [
        "nmcli", "--wait", "45", "device", "wifi", "connect", "Home",
        "password", "hunter22", "ifname", "wlan0",
    ]


def test_connect_reuses_saved_profile():
    run = MagicMock(
        side_effect=[
            completed("u-eth:802-3-ethernet\nu-other:802-11-wireless\nu-home:802-11-wireless\n"),
            completed("Other\n"),
            completed("Home\n"),
            completed(),
            completed(),
        ]
    )
    with patch.object(wifi.subprocess, "run", run):
        connect_wifi("Home", "hunter22")
    calls = [c.args[0] for c in run.call_args_list]
    assert calls[3] == ["nmcli", "connection", "modify", "uuid", "u-home", "wifi-sec.psk", "hunter22"]
    assert calls[4] == [
        "nmcli", "--wait", "45", "connection", "up", "uuid", "u-home", "ifname", "wlan0",
    ]


def test_connect_open_network_has_no_password():
    run = MagicMock(side_effect=[completed(""), completed()])
    with patch.object(wifi.subprocess, "run", run):
        connect_wifi("Cafe")
    assert "password" not in run.call_args_list[1].args[0]


def test_get_wlan0_ip():
    with patch.object(wifi.subprocess, "run", return_value=completed("192.168.1.20/24 | 10.0.0.5/8\n")):
        assert wifi.get_wlan0_ip() == "192.168.1.20"
    with patch.object(wifi.subprocess, "run", return_value=completed("\n")):
        assert wifi.get_wlan0_ip() is None
