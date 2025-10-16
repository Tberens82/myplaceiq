import logging
import json
import time
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN

logger = logging.getLogger(__name__)

class MyPlaceIQDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching MyPlaceIQ data."""

    def __init__(self, hass: HomeAssistant, myplaceiq, update_interval: int):
        """Initialize the coordinator."""
        self.myplaceiq = myplaceiq
        self.hass = hass
        self._last_valid_data = None
        logger.debug("Initializing MyPlaceIQDataUpdateCoordinator with update_interval: %s seconds",
                     update_interval)
        super().__init__(
            hass,
            logger,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self):
        """Fetch data from MyPlaceIQ."""
        start_time = time.time()
        logger.debug("Poll started at %s (interval: %s seconds)",
                     time.strftime("%H:%M:%S", time.localtime(start_time)),
                     self.update_interval.total_seconds())
        try:
            response = await self.myplaceiq.send_command(
                {"commands": [{"__type": "GetFullDataEvent"}]}, await_response=True)
            if not isinstance(response, dict) or "body" not in response:
                logger.error("Invalid response from MyPlaceIQ: %s", response)
                raise UpdateFailed("Invalid response from MyPlaceIQ")

            try:
                body = json.loads(response["body"])
            except json.JSONDecodeError as err:
                logger.error("Failed to parse response body: %s", err)
                raise UpdateFailed(f"Failed to parse response body: {err}") from err

            if not body.get("aircons") or not body.get("zones"):
                logger.warning("Incomplete response missing aircons or zones")
                if self._last_valid_data:
                    logger.debug("Using last valid data")
                    return self._last_valid_data
                raise UpdateFailed("Incomplete response and no valid cached data")

            # Log summary instead of full response
            aircon = body.get("aircons", {}).get("019469", {})
            logger.debug("Poll completed in %.3f seconds: aircon 019469 isOn=%s, mode=%s, zones=%d",
                         time.time() - start_time,
                         aircon.get("isOn", "missing"),
                         aircon.get("mode", "missing"),
                         len(body.get("zones", {})))

            response["body"] = json.dumps(body)
            self._last_valid_data = response
            return response
        except Exception as err:
            logger.error("Poll failed in %.3f seconds: %s", time.time() - start_time, err)
            if self._last_valid_data:
                logger.debug("Returning last valid data")
                return self._last_valid_data
            raise UpdateFailed(f"Error fetching MyPlaceIQ data: {err}") from err
