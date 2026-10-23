import logging
from unittest.mock import AsyncMock
import pytest

from src.communicator import DisplayCommunicator


@pytest.fixture
def communicator():
    # event_handler can be None for these unit tests, since we patch out I/O
    return DisplayCommunicator(logging, "N3", "/dev/ttyS0", None)


def test_get_device_name(communicator):
    # Simple sanity check: constructor stores the model name
    assert communicator.get_device_name() == "N3"


def test_get_display_type_name(communicator):
    # Should just be the class name
    assert communicator.get_display_type_name() == "DisplayCommunicator"


@pytest.mark.asyncio
async def test_navigate(communicator):
    # We don't want real I/O here, so patch write
    communicator.write = AsyncMock()

    await communicator.navigate_to("1")

    # navigate_to blocks other writes with a blocked_key="__nav__"
    communicator.write.assert_awaited_once_with(
        "page 1",
        blocked_key="__nav__",
        auto_unblock=False,
    )


def test_display_encodes_utf8(communicator):
    # nextion encodes every command with this; ASCII rejects "°" in temperatures
    assert communicator.display._encoding == "utf-8"


@pytest.mark.asyncio
async def test_sleep_drops_writes_until_a_page_change(communicator):
    communicator.display.command = AsyncMock()
    woke = []
    communicator.on_wake = lambda: woke.append(True)
    await communicator.sleep()
    assert communicator.sleeping
    # The panel ignores these while it sleeps
    await communicator.write('main.nozzletemp.txt="210"')
    # Changing the page wakes it first
    await communicator.write("page main")
    sent = [c.args[0] for c in communicator.display.command.call_args_list]
    assert sent == ["sleep=1", "sleep=0", "dim=multiset.h0.val", "page main"]
    assert not communicator.sleeping
    assert woke == [True]


@pytest.mark.asyncio
async def test_wake_when_awake_does_nothing(communicator):
    communicator.display.command = AsyncMock()
    await communicator.wake()
    communicator.display.command.assert_not_awaited()
