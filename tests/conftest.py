"""Unit tests must never access external networks or paid APIs."""
from __future__ import annotations

import httpx
import pytest
import urllib.request


@pytest.fixture(autouse=True)
def block_unit_network(request, monkeypatch):
    if 'integration' in request.node.path.parts:
        return

    def blocked(*args, **kwargs):
        raise AssertionError('Unexpected network access in unit test')

    async def async_blocked(*args, **kwargs):
        raise AssertionError('Unexpected async network access in unit test')

    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request', blocked)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, 'handle_async_request', async_blocked)
    monkeypatch.setattr(urllib.request.OpenerDirector, 'open', blocked)
