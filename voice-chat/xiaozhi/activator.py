"""
Xiaozhi device activation — replicates the xiaozhi-esp32 OTA check + activate flow.

Reference: xiaozhi-esp32/main/ota.cc, application.cc

Flow:
  1. POST system info to OTA URL → get websocket config + activation challenge
  2. If activation challenge present, POST to /activate with proof
  3. Use returned websocket URL + token for WS connection

On PC we don't have ESP32 HMAC efuse, so we use the "no serial number" path
which sends an empty JSON {} to /activate.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

DEFAULT_OTA_URL = "https://api.tenclass.net/xiaozhi/ota/"
APP_VERSION = "1.0.0"
APP_NAME = "reachy-mini-voice-chat"

_IDENTITY_PATH = Path.home() / ".config" / "reachy-voice-chat" / "identity.json"


def load_or_create_identity(identity_path: Path = _IDENTITY_PATH) -> tuple[str, str]:
    """Load persisted device_id and client_id, or create and save new ones.

    Returns:
        (device_id, client_id) — stable across restarts
    """
    if identity_path.exists():
        try:
            data = json.loads(identity_path.read_text())
            device_id = data.get("device_id", "")
            client_id = data.get("client_id", "")
            if device_id and client_id:
                logger.debug("Loaded identity: device_id=%s", device_id)
                return device_id, client_id
        except Exception as e:
            logger.warning("Failed to load identity file, regenerating: %s", e)

    h = uuid.uuid4().hex[:12]
    device_id = ":".join(h[i:i+2] for i in range(0, 12, 2))
    client_id = str(uuid.uuid4())

    identity_path.parent.mkdir(parents=True, exist_ok=True)
    identity_path.write_text(json.dumps({
        "device_id": device_id,
        "client_id": client_id,
    }, indent=2))
    logger.info("Created new identity: device_id=%s, saved to %s", device_id, identity_path)
    return device_id, client_id


@dataclass
class ActivationResult:
    """Result of OTA check + activation flow."""
    websocket_url: str = ""
    websocket_token: str = ""
    websocket_version: int = 3
    mqtt_config: dict = field(default_factory=dict)
    server_time: Optional[float] = None
    timezone_offset_ms: int = 0
    activation_code: str = ""
    activation_message: str = ""
    activated: bool = False
    firmware_version: str = ""
    firmware_url: str = ""


def _get_system_info(device_id: str, client_id: str) -> dict:
    """Build system info JSON matching xiaozhi-esp32 board.cc::GetSystemInfoJson() exactly."""
    return {
        "version": 2,
        "language": "zh",
        "flash_size": 0,
        "minimum_free_heap_size": "0",
        "mac_address": device_id,
        "uuid": client_id,
        "chip_model_name": "esp32s3",
        "chip_info": {
            "model": 9,
            "cores": 2,
            "revision": 0,
            "features": 0,
        },
        "application": {
            "name": "xiaozhi",
            "version": "1.5.7",
            "compile_time": "2024-01-01T00:00:00Z",
            "idf_version": "v5.3.1",
            "elf_sha256": "0" * 64,
        },
        "partition_table": [],
        "ota": {"label": "ota_0"},
        "board": {
            "type": "xiaozhi-esp32",
            "name": "xiaozhi",
            "flash_size": 8388608,
            "minimum_free_heap_size": 200000,
        },
    }


def _get_user_agent(device_id: str, client_id: str) -> str:
    """Build User-Agent string matching xiaozhi-esp32 pattern."""
    return f"{APP_NAME}/{APP_VERSION} (device={device_id}; client={client_id}; platform={platform.system()}/{platform.machine()})"


async def check_and_activate(
    ota_url: str = DEFAULT_OTA_URL,
    device_id: str = "",
    client_id: str = "",
    ota_url_override: str = "",
    max_activate_retries: int = 10,
    activate_retry_delay: float = 3.0,
    http_timeout: float = 30.0,
) -> ActivationResult:
    """
    Full OTA check + activation flow matching xiaozhi-esp32 behavior.

    1. POST system info to OTA URL
    2. Parse response: websocket config, activation challenge, mqtt config
    3. If activation challenge present, loop POST /activate until success or max retries
    4. Return ActivationResult with websocket URL + token

    Args:
        ota_url: OTA endpoint URL (default: https://api.tenclass.net/xiaozhi/ota/)
        device_id: Device identifier (auto-generated if empty)
        client_id: Client UUID (auto-generated if empty)
        ota_url_override: Override OTA URL (from config/settings)
        max_activate_retries: Max activation retry attempts
        activate_retry_delay: Delay between retries in seconds
        http_timeout: HTTP request timeout

    Returns:
        ActivationResult with websocket connection details
    """
    if ota_url_override:
        ota_url = ota_url_override

    if not device_id or not client_id:
        _did, _cid = load_or_create_identity()
        device_id = device_id or _did
        client_id = client_id or _cid
    result = ActivationResult()

    user_agent = _get_user_agent(device_id, client_id)
    system_info = _get_system_info(device_id, client_id)

    headers = {
        "Activation-Version": "1",
        "Device-Id": device_id,
        "Client-Id": client_id,
        "User-Agent": user_agent,
        "Accept-Language": "zh",
        "Content-Type": "application/json",
    }

    # Step 1: Check version (POST system info)
    logger.info("OTA check: POST %s", ota_url)
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=http_timeout)) as session:
            async with session.post(ota_url, headers=headers, json=system_info) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error("OTA check failed: status=%d body=%s", resp.status, body[:200])
                    return result
                data = await resp.json()
    except Exception as e:
        logger.error("OTA check request failed: %s", e)
        return result

    logger.debug("OTA response: %s", json.dumps(data, indent=2, ensure_ascii=False)[:500])

    # Parse activation info
    activation = data.get("activation", {})
    if activation:
        result.activation_code = activation.get("code", "")
        result.activation_message = activation.get("message", "")
        challenge = activation.get("challenge", "")
        timeout_ms = activation.get("timeout_ms", 60000)

    # Parse websocket config — this is what we need for WS connection
    ws_config = data.get("websocket", {})
    if ws_config:
        result.websocket_url = ws_config.get("url", "")
        result.websocket_token = ws_config.get("token", "")
        result.websocket_version = int(ws_config.get("version", 3))
        logger.info(
            "Websocket config: url=%s, version=%d, token=%s...",
            result.websocket_url,
            result.websocket_version,
            result.websocket_token[:8] if result.websocket_token else "(none)",
        )

    # Parse mqtt config (alternative transport)
    mqtt_config = data.get("mqtt", {})
    if mqtt_config:
        result.mqtt_config = mqtt_config

    # Parse server time
    server_time = data.get("server_time", {})
    if server_time:
        result.server_time = server_time.get("timestamp")
        result.timezone_offset_ms = server_time.get("timezone_offset", 0)

    # Parse firmware info
    firmware = data.get("firmware", {})
    if firmware:
        result.firmware_version = firmware.get("version", "")
        result.firmware_url = firmware.get("url", "")

    # Step 2: Activate if challenge present
    challenge = activation.get("challenge", "") if activation else ""
    if not challenge:
        logger.info("No activation challenge, device is already activated")
        result.activated = True
        return result

    # Show activation code to user if present
    if result.activation_code:
        logger.info("Activation code: %s (%s)", result.activation_code, result.activation_message)

    # Activate loop — PC has no serial number, send empty JSON {}
    activate_url = ota_url.rstrip("/") + "/activate"

    for attempt in range(1, max_activate_retries + 1):
        logger.info("Activation attempt %d/%d: POST %s", attempt, max_activate_retries, activate_url)

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=http_timeout)) as session:
                async with session.post(activate_url, headers=headers, json={}) as resp:
                    if resp.status == 200:
                        logger.info("Activation successful!")
                        result.activated = True
                        return result
                    elif resp.status == 202:
                        logger.info("Activation pending (202), retrying in %.1fs...", activate_retry_delay)
                        await asyncio.sleep(activate_retry_delay)
                        continue
                    else:
                        body = await resp.text()
                        logger.error("Activation failed: status=%d body=%s", resp.status, body[:200])
                        await asyncio.sleep(activate_retry_delay)
                        continue
        except Exception as e:
            logger.error("Activation request failed: %s", e)
            await asyncio.sleep(activate_retry_delay)
            continue

    logger.warning("Activation failed after %d attempts", max_activate_retries)
    return result