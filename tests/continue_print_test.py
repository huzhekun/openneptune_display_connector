import logging
from unittest.mock import AsyncMock

import pytest

from src.elegoo_display import ElegooDisplayCommunicator, ElegooDisplayMapper
from src.mapping import PAGE_CONTINUE_PRINT
from src.openneptune_display import OpenNeptuneDisplayMapper
from src.response_actions import named_response_actions


def test_continue_print_page_in_both_themes():
    assert OpenNeptuneDisplayMapper().map_page(PAGE_CONTINUE_PRINT) == "continueprint"
    # Confirm sends code 0, Cancel code 1
    assert named_response_actions["continueprint"] == {0: "plr_resume", 1: "plr_discard"}


@pytest.mark.asyncio
async def test_continue_print_text_is_quoted_and_cut():
    display = ElegooDisplayCommunicator(logging, "N4", "/dev/ttyS0", None)
    display.mapper = ElegooDisplayMapper()
    display.write = AsyncMock()
    await display.update_continue_print_ui('a "b" \\c' + "é" * 100)
    text = display.write.await_args.args[0]
    assert text.startswith("continueprint.t0.txt=\"a 'b' /c")
    assert len(text.split('"', 1)[1][:-1].encode("utf-8")) <= 127
