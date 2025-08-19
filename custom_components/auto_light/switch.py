"""Switch platform for Auto Light integration."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_NAME, DEFAULT_NAME

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Auto Light switch."""
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    
    async_add_entities([AutoLightSwitch(hass, entry.entry_id, name)])

class AutoLightSwitch(SwitchEntity):
    """Representation of an Auto Light switch."""

    def __init__(self, hass: HomeAssistant, entry_id: str, name: str) -> None:
        """Initialize the Auto Light switch."""
        self.hass = hass
        self.entry_id = entry_id
        self._name = name
        self._attr_unique_id = f"{entry_id}_switch"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # 确保组件数据结构已初始化
        if DOMAIN not in hass.data or entry_id not in hass.data[DOMAIN]:
            hass.data.setdefault(DOMAIN, {})
            hass.data[DOMAIN].setdefault(entry_id, {"state": {}})
        
        # 默认启用
        if "enabled" not in hass.data[DOMAIN][entry_id].get("state", {}):
            hass.data[DOMAIN][entry_id].setdefault("state", {})
            hass.data[DOMAIN][entry_id]["state"]["enabled"] = True

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return f"{self._name}"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.hass.data[DOMAIN][self.entry_id]["state"].get("enabled", True)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self.hass.data[DOMAIN][self.entry_id]["state"]["enabled"] = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self.hass.data[DOMAIN][self.entry_id]["state"]["enabled"] = False
        self.async_write_ha_state()