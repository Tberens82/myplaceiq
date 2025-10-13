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
        self._last_valid_data = None  # Cache last valid data
        logger.debug(
            "Initializing MyPlaceIQDataUpdateCoordinator with update_interval: %s seconds",
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
        try:
            logger.debug("Fetching data from MyPlaceIQ (poll interval: %s seconds)", self.update_interval.total_seconds())
            response = await self.myplaceiq.send_command(
                {"commands": [{"__type": "GetFullDataEvent"}]})
            if not isinstance(response, dict) or "body" not in response:
                logger.error("Invalid response from MyPlaceIQ: %s", response)
                raise UpdateFailed("Invalid response from MyPlaceIQ")
            
            # Parse and validate response
            try:
                body = json.loads(response["body"])
            except json.JSONDecodeError as err:
                logger.error("Failed to parse response body: %s", err)
                raise UpdateFailed(f"Failed to parse response body: {err}")
            
            # Check for required keys
            if not body.get("aircons") or not body.get("zones"):
                logger.warning("Incomplete response missing aircons or zones: %s", response)
                if self._last_valid_data:
                    logger.debug("Using last valid data due to incomplete response")
                    return self._last_valid_data
                else:
                    logger.error("No valid cached data available")
                    raise UpdateFailed("Incomplete response and no valid cached data")
            
            # Ensure body is a JSON string
            response["body"] = json.dumps(body)
            logger.debug("Received valid data in %.3f seconds: %s", time.time() - start_time, response)
            # Cache valid data
            self._last_valid_data = response
            return response
        except Exception as err:
            logger.error("Error fetching data in %.3f seconds: %s", time.time() - start_time, err)
            if self._last_valid_data:
                logger.debug("Returning last valid data due to fetch failure")
                return self._last_valid_data
            raise UpdateFailed(f"Error fetching MyPlaceIQ data: {err}")
