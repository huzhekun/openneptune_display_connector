import asyncio
from unittest.mock import MagicMock

import pytest
from src.tjc import EventType, TJCClient, TJCNumericInputPayload, TJCProtocol, TJCStringInputPayload, TJCTouchCoordinatePayload, TJCTouchDataPayload


@pytest.fixture(autouse=True)
def ensure_event_loop():
    """Provide an event loop for sync tests that instantiate TJCProtocol.

    NextionProtocol.__init__ (upstream) calls asyncio.get_event_loop().create_future(),
    which raises RuntimeError in Python 3.10+ when no loop is set in the current thread.
    Async tests (marked with @pytest.mark.asyncio) get their own loop from pytest-asyncio;
    this fixture guarantees sync tests have one too.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield
    loop.close()
    asyncio.set_event_loop(None)


def test_is_event():
    protocol = TJCProtocol(None)
    assert protocol.is_event(b"\x65") is True
    assert protocol.is_event(b"\x71") is False
    assert protocol.is_event(b"\x72") is True

def test_data_received_touch_event():
    m = MagicMock()
    protocol = TJCProtocol(m)
    protocol.data_received(b"\x65\xF1\x02\xFF\xFF\xFF\xFF")
    m.assert_called_once_with(b"\x65\xF1\x02")

def test_data_received_number():
    m = MagicMock()
    protocol = TJCProtocol(m)
    # 0x72 packet: 1 header + 2 (page, component) + 2 (value) + 3 EOL = 8 bytes total
    protocol.data_received(b"\x72\xF1\x02\x03\x05\xFF\xFF\xFF")
    # Handler should see the message without the EOL bytes
    m.assert_called_once_with(b"\x72\xF1\x02\x03\x05")

#def test_data_received_number():
#    m = MagicMock()
#    protocol = TJCProtocol(m)
#    protocol.data_received(b"\x72\xF1\x02\x03\x05\x04\xFF\xFF\xFF")
#    m.assert_called_once_with(b"\x72\xF1\x02\x03\x05\x04")


def test_data_received_number_broken():
    m = MagicMock()
    protocol = TJCProtocol(m)
    protocol.data_received(b"\x71\xF1\x02\x03\x05")
    m.assert_called_once_with(b"\x72\xF1\x02\x03\x05")


@pytest.mark.asyncio
async def test_data_received_variable():
    m = MagicMock()
    protocol = TJCProtocol(m)
    protocol.data_received(b"\x70\x10\x20\x30\x40\xFF\xFF\xFF")
    item = await protocol.queue.get()
    assert item == b"\x70\x10\x20\x30\x40"


def test_keyboard_input_without_terminator_is_flushed():
    m = MagicMock()
    protocol = TJCProtocol(m)
    protocol.data_received(b"\x70\x84\x02hunter")
    protocol.data_received(b"22")
    m.assert_not_called()
    assert protocol._keyboard_input_timer is not None
    protocol._flush_keyboard_input()
    m.assert_called_once_with(b"\x70\x84\x02hunter22")
    assert protocol.buffer == b""


@pytest.mark.asyncio
async def test_keyboard_input_flushes_after_idle():
    m = MagicMock()
    protocol = TJCProtocol(m)
    protocol.data_received(b"\x70\x84\x02secret")
    await asyncio.sleep(0.1)
    m.assert_called_once_with(b"\x70\x84\x02secret")


@pytest.mark.asyncio
async def test_terminated_string_reply_is_not_keyboard_input():
    m = MagicMock()
    protocol = TJCProtocol(m)
    protocol.data_received(b"\x701.2.18")
    protocol.data_received(b"\xFF\xFF\xFF")
    assert protocol._keyboard_input_timer is None
    assert await protocol.queue.get() == b"\x701.2.18"
    m.assert_not_called()


def test_event_keyboard_input():
    m = MagicMock()
    client = TJCClient(None)
    client._schedule_event_message_handler = m
    client.event_message_handler(b"\x70\x84\x02hunter22")
    m.assert_called_once_with(EventType.KEYBOARD_INPUT, TJCStringInputPayload(page_id=0x84, component_id=2, string="hunter22"))


def test_event_touch_coordinate():
    m = MagicMock()
    client = TJCClient(None)
    client._schedule_event_message_handler = m
    client.event_message_handler(b"\x67\xF1\x02\x30\x20\x01")
    m.assert_called_once_with(EventType.TOUCH_COORDINATE, TJCTouchCoordinatePayload(x=61698, y=12320, touch_event=1))


def test_event_touch():
    m = MagicMock()
    client = TJCClient(None)
    client._schedule_event_message_handler = m
    client.event_message_handler(b"\x65\x02\x15")
    m.assert_called_once_with(EventType.TOUCH, TJCTouchDataPayload(page_id=2, component_id=21))


def test_numeric_input():
    m = MagicMock()
    client = TJCClient(None)
    client._schedule_event_message_handler = m
    client.event_message_handler(b"\x72\x03\x15\x10\x08")
    m.assert_called_once_with(EventType.NUMERIC_INPUT, TJCNumericInputPayload(page_id=3, component_id=21, value=2064))


def test_event_slider():
    m = MagicMock()
    client = TJCClient(None)
    client._schedule_event_message_handler = m
    client.event_message_handler(b"\x72\x03\x16\x10\x09")
    m.assert_called_once_with(EventType.NUMERIC_INPUT, TJCNumericInputPayload(page_id=3, component_id=22, value=2320))


def test_sleep_events_are_passed_on():
    client = TJCClient("/dev/null", 115200, None)
    events = []
    client._schedule_event_message_handler = lambda t, d: events.append((t, d))
    client.event_message_handler(bytes([0x68, 0, 0x81, 0, 0xF5, 1]))
    client.event_message_handler(bytes([0x86]))
    client.event_message_handler(bytes([0x87]))
    assert events == [(EventType.TOUCH_IN_SLEEP, None), (EventType.AUTO_SLEEP, None),
                      (EventType.AUTO_WAKE, None)]
