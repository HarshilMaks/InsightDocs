from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from backend.api.query import _abort_if_client_disconnected


@pytest.mark.asyncio
async def test_client_disconnect_aborts_query_before_persistence():
    request = AsyncMock(spec=Request)
    request.is_disconnected = AsyncMock(return_value=True)

    with pytest.raises(HTTPException) as exc_info:
        await _abort_if_client_disconnected(request)

    assert exc_info.value.status_code == 499
    assert "cancelled" in exc_info.value.detail.lower()
    request.is_disconnected.assert_awaited_once()


@pytest.mark.asyncio
async def test_connected_client_continues_query_processing():
    request = AsyncMock(spec=Request)
    request.is_disconnected = AsyncMock(return_value=False)

    await _abort_if_client_disconnected(request)

    request.is_disconnected.assert_awaited_once()
