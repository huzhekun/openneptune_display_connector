import logging
from unittest.mock import AsyncMock, call

import pytest
from src.neptune4 import MODEL_N4_MAX, MODEL_N4_PLUS, MODEL_N4_PRO, MODEL_N4_REGULAR, ElegooNeptune4DisplayCommunicator, ElegooNeptune4Mapper, ElegooNeptune4MaxMapper, ElegooNeptune4PlusMapper, ElegooNeptune4ProMapper
from src.mapping import PAGE_PREPARE_TEMP, PAGE_PRINTING_FILAMENT, PAGE_SETTINGS, PAGE_SETTINGS_ABOUT
from src.wifi import WifiNetwork


def test_n4_pro_mapping():
    mapper = ElegooNeptune4ProMapper()
    assert mapper.map_page(PAGE_PREPARE_TEMP) == "pretemp"
    assert mapper.map_page(PAGE_PRINTING_FILAMENT) == "adjusttemp_pro"


def test_plus_max_use_wlan_settings_page():
    for mapper in (ElegooNeptune4PlusMapper(), ElegooNeptune4MaxMapper()):
        assert mapper.map_page(PAGE_SETTINGS) == "set_4_max"
        assert mapper.data_mapping["fan"]["speed"][1].fields == ["set_4_max.fanstatue"]
    assert ElegooNeptune4Mapper().map_page(PAGE_SETTINGS) == "set"
    assert ElegooNeptune4ProMapper().map_page(PAGE_SETTINGS) == "set"


@pytest.mark.asyncio
async def test_wifi_list_ui():
    communicator = ElegooNeptune4DisplayCommunicator(logging, MODEL_N4_MAX, None)
    communicator.display.command = AsyncMock()
    networks = [
        WifiNetwork("Home", 95, True, in_use=True),
        WifiNetwork('Say "hi"', 50, True),
        WifiNetwork("Cafe", 10, False),
    ]
    await communicator.update_wifi_list_ui(networks, 0, {"Cafe": "failed"}, True, "IP:192.168.1.20")
    sent = [c.args[0] for c in communicator.display.command.call_args_list]
    assert sent[:9] == [
        'wifi_list.t0.txt="Home"',
        "wifi_list.q0.picc=346",
        "wifi_list.q8.picc=346",
        "wifi_list.t1.txt=\"Say 'hi'\"",
        "wifi_list.q1.picc=343",
        "wifi_list.q9.picc=341",
        'wifi_list.t2.txt="Cafe"',
        "wifi_list.q2.picc=341",
        "wifi_list.q10.picc=347",
    ]
    assert 'wifi_list.t7.txt=""' in sent
    assert "wifi_list.q15.picc=340" in sent
    assert sent[-2:] == ["wifi_list.q16.picc=348", 'wifi_list.t9.txt="IP:192.168.1.20"']


def test_get_mapper_4():
    communicator = ElegooNeptune4DisplayCommunicator(None, MODEL_N4_REGULAR, None)
    assert isinstance(communicator.mapper, ElegooNeptune4Mapper)


def test_get_mapper_pro():
    communicator = ElegooNeptune4DisplayCommunicator(None, MODEL_N4_PRO, None)
    assert isinstance(communicator.mapper, ElegooNeptune4ProMapper)


def test_get_mapper_plus():
    communicator = ElegooNeptune4DisplayCommunicator(None, MODEL_N4_PLUS, None)
    assert isinstance(communicator.mapper, ElegooNeptune4PlusMapper)


def test_get_mapper_max():
    communicator = ElegooNeptune4DisplayCommunicator(None, MODEL_N4_MAX, None)
    assert isinstance(communicator.mapper, ElegooNeptune4MaxMapper)


def test_get_mapper_invalid():
    communicator = ElegooNeptune4DisplayCommunicator(logging, "abc", None)
    assert isinstance(communicator.mapper, ElegooNeptune4Mapper)


@pytest.mark.asyncio
async def test_initializing():
    communicator = ElegooNeptune4DisplayCommunicator(logging, MODEL_N4_REGULAR, None)
    communicator.display.command = AsyncMock()
    await communicator.initialize_display()
    assert communicator.mapper is not None
    communicator.display.command.assert_has_calls([
        call("sendxy=1", 5),
        call("main.q4.picc=213", 5)
        ])
    

@pytest.mark.asyncio
async def test_initializing_pro():
    communicator = ElegooNeptune4DisplayCommunicator(logging, MODEL_N4_PRO, None)
    communicator.display.command = AsyncMock()
    await communicator.initialize_display()
    assert communicator.mapper is not None
    communicator.display.command.assert_has_calls([
        call("sendxy=1", 5),
        call('main.disp_q5.val=1', 5),
        call("main.q4.picc=214", 5)
        ])
    

@pytest.mark.asyncio
async def test_initializing_plus():
    communicator = ElegooNeptune4DisplayCommunicator(logging, MODEL_N4_PLUS, None)
    communicator.display.command = AsyncMock()
    await communicator.initialize_display()
    assert communicator.mapper is not None
    communicator.display.command.assert_has_calls([
        call("sendxy=1", 5),
        call("main.q4.picc=313", 5)
        ])
    

@pytest.mark.asyncio
async def test_initializing_max():
    communicator = ElegooNeptune4DisplayCommunicator(logging, MODEL_N4_MAX, None)
    communicator.display.command = AsyncMock()
    await communicator.initialize_display()
    assert communicator.mapper is not None
    communicator.display.command.assert_has_calls([
        call("sendxy=1", 5),
        call("main.q4.picc=314", 5)
        ])

@pytest.mark.asyncio
async def test_about_page_fields_by_name():
    # The component ids on the about page differ between UI versions (1.2.22
    # added one before them), so the fields are written by name
    communicator = ElegooNeptune4DisplayCommunicator(logging, MODEL_N4_MAX, None)
    communicator.display.command = AsyncMock()
    communicator.ips = "192.168.1.20"
    await communicator.update_machine_size_ui(430, 430, 505)
    await communicator.update_klipper_version_ui("v0.13.0-816")
    await communicator.special_page_handling(PAGE_SETTINGS_ABOUT)
    sent = [c.args[0] for c in communicator.display.command.call_args_list]
    assert sent[:3] == [
        'information.size.txt="430x430x505"',
        'information.sversion.txt="v0.13.0-816"',
        'information.t9.txt="192.168.1.20"',
    ]
