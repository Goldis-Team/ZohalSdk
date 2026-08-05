"""One HTTP round-trip, in both flavours, shared by every service family.

Zohal is REST/JSON throughout, so the transport lives here once and every family differs only in
path and payload. Keeping it in one place is also what stops the async engine from quietly growing
a blocking call: a synchronous request inside a coroutine parks the entire event loop for up to the
timeout, so one slow government upstream stalls every other request in the process, not just the
one waiting on it.

**Two clients, on purpose.** ``aiohttp`` drives the async engine and has no synchronous API, so the
sync engine uses ``requests``. Both are normalised here — same arguments, same return type, same
errors — so nothing above this module can tell which one ran.

Everything that stopped the round-trip from completing raises
:class:`~zohal_sdk.common.exceptions.ZohalNetworkError`. A 401 or 403 raises
:class:`~zohal_sdk.common.exceptions.ZohalAuthenticationError`. Every other status is handed
upwards with its body, because Zohal reports what actually went wrong in the body under 400, 404,
500 and 503 alike — see :mod:`zohal_sdk.common.envelope`.
"""

import asyncio
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import IO, Any, NamedTuple, Union

import aiohttp
import requests

from zohal_sdk.common.constants import AUTH_STATUSES, DEFAULT_TIMEOUT
from zohal_sdk.common.exceptions import ZohalAuthenticationError, ZohalNetworkError

FileInput = Union[str, "os.PathLike[str]", bytes, bytearray, IO[bytes]]
"""What an upload argument accepts: a path, the bytes themselves, or an open binary file."""


class RawResponse(NamedTuple):
    """A decoded body and the status it arrived under.

    Both are carried because neither is sufficient on its own: Zohal's ``result`` code lives in the
    body and is what describes the failure, while the status is what a support ticket needs to
    distinguish "Zohal declined this" from "Zohal's front door declined this".
    """

    body: dict[str, Any]
    status: int


def auth_headers(token: str) -> dict[str, str]:
    """The one header every Zohal call carries."""
    return {"Authorization": f"Bearer {token}"}


def decode(text: str, status: int, service: str) -> RawResponse:
    """Decode a response into a dict, or say precisely what arrived instead.

    The body is parsed from text rather than through the client's own JSON helper, so that a
    response declaring the wrong content type — or none — is still read. ``aiohttp`` refuses those
    by default, and an inquiry that has already been billed is not the place to discover it.

    A 401 or 403 short-circuits before parsing: those bodies are the framework's, not Zohal's, and
    they usually are not JSON at all.
    """
    if status in AUTH_STATUSES:
        raise ZohalAuthenticationError(
            f"zohal rejected the request for {service} with HTTP {status} — check the token, and "
            f"check that this host's IP is registered on your panel",
            status=status,
        )
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ZohalNetworkError(
            f"zohal answered HTTP {status} for {service} with non-JSON content: {text[:200]!r}"
        ) from exc
    if not isinstance(data, dict):
        raise ZohalNetworkError(
            f"zohal answered {type(data).__name__} for {service}, not an object"
        )
    return RawResponse(body=data, status=status)


def as_upload(name: str, value: FileInput) -> tuple[str, bytes]:
    """Resolve an upload argument to ``(filename, content)``.

    Paths are read into memory rather than streamed. These uploads are ID-card photographs and
    short selfie videos, and holding one in memory buys something worth more than the bytes: the
    sync and async transports receive exactly the same thing, so an upload cannot behave
    differently on one engine than the other, and a test can hand either of them a literal
    ``b"..."``.
    """
    if isinstance(value, (bytes, bytearray)):
        return name, bytes(value)
    if isinstance(value, (str, os.PathLike)):
        path = Path(value)
        try:
            return path.name, path.read_bytes()
        except OSError as exc:
            raise ZohalNetworkError(f"could not read {name} from {path}: {exc}") from exc
    content = value.read()
    filename = getattr(value, "name", name)
    return Path(str(filename)).name, bytes(content)


def _files_payload(files: Mapping[str, FileInput]) -> dict[str, tuple[str, bytes]]:
    return {field: as_upload(field, value) for field, value in files.items()}


def post_json(
    url: str,
    payload: dict[str, Any],
    *,
    token: str,
    service: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> RawResponse:
    """POST JSON and return the decoded body. Sync engine, over ``requests``."""
    try:
        response = requests.post(url, json=payload, headers=auth_headers(token), timeout=timeout)
    except requests.Timeout as exc:
        raise ZohalNetworkError(f"zohal did not answer {service} within {timeout}s") from exc
    except requests.RequestException as exc:
        raise ZohalNetworkError(f"zohal request for {service} failed: {exc}") from exc
    return decode(response.text, response.status_code, service)


def get_json(
    url: str,
    *,
    token: str,
    service: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> RawResponse:
    """GET and return the decoded body. Sync engine, over ``requests``."""
    try:
        response = requests.get(url, headers=auth_headers(token), timeout=timeout)
    except requests.Timeout as exc:
        raise ZohalNetworkError(f"zohal did not answer {service} within {timeout}s") from exc
    except requests.RequestException as exc:
        raise ZohalNetworkError(f"zohal request for {service} failed: {exc}") from exc
    return decode(response.text, response.status_code, service)


def post_multipart(
    url: str,
    *,
    files: Mapping[str, FileInput],
    fields: Mapping[str, str] | None = None,
    token: str,
    service: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> RawResponse:
    """POST ``multipart/form-data`` and return the decoded body. Sync engine, over ``requests``.

    The boundary and content type are left to the client, which is why no ``Content-Type`` is set
    here — supplying one by hand omits the boundary and the upload arrives empty.
    """
    try:
        response = requests.post(
            url,
            files=_files_payload(files),
            data=dict(fields or {}),
            headers=auth_headers(token),
            timeout=timeout,
        )
    except requests.Timeout as exc:
        raise ZohalNetworkError(f"zohal did not answer {service} within {timeout}s") from exc
    except requests.RequestException as exc:
        raise ZohalNetworkError(f"zohal request for {service} failed: {exc}") from exc
    return decode(response.text, response.status_code, service)


async def apost_json(
    url: str,
    payload: dict[str, Any],
    *,
    token: str,
    service: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> RawResponse:
    """POST JSON and return the decoded body. Async engine, over ``aiohttp``."""
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    try:
        async with (
            aiohttp.ClientSession(timeout=client_timeout) as session,
            session.post(url, json=payload, headers=auth_headers(token)) as response,
        ):
            text = await response.text()
            status = response.status
    except asyncio.TimeoutError as exc:
        raise ZohalNetworkError(f"zohal did not answer {service} within {timeout}s") from exc
    except aiohttp.ClientError as exc:
        raise ZohalNetworkError(f"zohal request for {service} failed: {exc}") from exc
    return decode(text, status, service)


async def aget_json(
    url: str,
    *,
    token: str,
    service: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> RawResponse:
    """GET and return the decoded body. Async engine, over ``aiohttp``."""
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    try:
        async with (
            aiohttp.ClientSession(timeout=client_timeout) as session,
            session.get(url, headers=auth_headers(token)) as response,
        ):
            text = await response.text()
            status = response.status
    except asyncio.TimeoutError as exc:
        raise ZohalNetworkError(f"zohal did not answer {service} within {timeout}s") from exc
    except aiohttp.ClientError as exc:
        raise ZohalNetworkError(f"zohal request for {service} failed: {exc}") from exc
    return decode(text, status, service)


async def apost_multipart(
    url: str,
    *,
    files: Mapping[str, FileInput],
    fields: Mapping[str, str] | None = None,
    token: str,
    service: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> RawResponse:
    """POST ``multipart/form-data`` and return the decoded body. Async engine, over ``aiohttp``."""
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    form = aiohttp.FormData()
    for field, value in fields.items() if fields else ():
        form.add_field(field, value)
    for field, (filename, content) in _files_payload(files).items():
        form.add_field(field, content, filename=filename)
    try:
        async with (
            aiohttp.ClientSession(timeout=client_timeout) as session,
            session.post(url, data=form, headers=auth_headers(token)) as response,
        ):
            text = await response.text()
            status = response.status
    except asyncio.TimeoutError as exc:
        raise ZohalNetworkError(f"zohal did not answer {service} within {timeout}s") from exc
    except aiohttp.ClientError as exc:
        raise ZohalNetworkError(f"zohal request for {service} failed: {exc}") from exc
    return decode(text, status, service)
