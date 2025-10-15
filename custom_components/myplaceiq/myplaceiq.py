import json
import logging
import uuid
import asyncio
import aiohttp
from homeassistant.exceptions import HomeAssistantError

logger = logging.getLogger(__name__)

class MyPlaceIQ:
    """Class to communicate with MyPlaceIQ API."""

    def __init__(self, host: str, port: int, client_id: str, client_secret: str) -> None:
        """Initialize MyPlaceIQ API client."""
        self._url = f"ws://{host}:{port}/ws"
        self._client_id = client_id
        self._client_secret = client_secret
        logger.debug("Initialized MyPlaceIQ with URL: %s", self._url)

    async def send_command(self, command: dict, await_response: bool = False) -> dict:
        """Send a command to MyPlaceIQ, optionally awaiting a response."""
        message = {"uuid": str(uuid.uuid1()), "body": json.dumps(command)}
        logger.debug("Sending command message: %s (await_response: %s)", message, await_response)
        max_retries = 3

        for attempt in range(1, max_retries + 1):
            session = None
            ws = None
            try:
                session = aiohttp.ClientSession()
                headers = {"client_id": self._client_id, "password": self._client_secret}
                logger.debug("Attempt %d/%d: Connecting to WebSocket at %s",
                    attempt, max_retries, self._url)
                async with session.ws_connect(self._url, headers=headers, timeout=5) as ws:
                    await ws.send_json(message)
                    logger.debug("Attempt %d/%d: Command sent successfully", attempt, max_retries)
                    if not await_response:
                        return {"status": "sent"}
                    # Await response for GetFullDataEvent
                    response = await ws.receive_json(timeout=10)
                    logger.debug("Attempt %d/%d: Received response: %s",
                        attempt, max_retries, response)
                    return response
            except (aiohttp.ClientError, aiohttp.WSMessageTypeError, asyncio.TimeoutError) as err:
                logger.error("Attempt %d/%d: Error sending command or receiving response: %s",
                             attempt, max_retries, err)
                if attempt < max_retries:
                    logger.debug("Retrying after 1-second delay")
                    await asyncio.sleep(1)
                    continue
                raise HomeAssistantError(
                    f"Failed to send MyPlaceIQ command after {max_retries} attempts: {err}") from err
            finally:
                if ws and not ws.closed:
                    await ws.close()
                    logger.debug("WebSocket closed")
                if session and not session.closed:
                    await session.close()
                    logger.debug("Client session closed")

        raise HomeAssistantError(f"Failed to send MyPlaceIQ command after {max_retries} attempts")
