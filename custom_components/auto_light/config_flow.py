"""Config flow for Auto Light integration."""
import logging
import voluptuous as vol
from datetime import datetime, time
from typing import Any, Dict, List, Optional

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TimeSelector,
)

from .const import (
    DOMAIN,
    SENSOR_TYPE_PRESENCE,
    SENSOR_TYPE_MOTION,
    LIGHT_TYPE_SINGLE,
    LIGHT_TYPE_MULTIPLE_PARALLEL,
    LIGHT_TYPE_MULTIPLE_ALTERNATE,
    CONF_SENSOR_TYPE,
    CONF_PRESENCE_SENSOR,
    CONF_BRIGHTNESS_SENSOR,
    CONF_LIGHT_TYPE,
    CONF_LIGHTS,
    CONF_LIGHT_SCHEDULES,
    CONF_NAME,
    DEFAULT_NAME,
    CONF_BRIGHTNESS_THRESHOLD,
    CONF_DELAY_OFF_TIME,
    DEFAULT_BRIGHTNESS_THRESHOLD,
    DEFAULT_DELAY_OFF_TIME,
)

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = [
    {"value": SENSOR_TYPE_PRESENCE, "label": "人在传感器"},
    {"value": SENSOR_TYPE_MOTION, "label": "人体传感器"},
]

LIGHT_TYPES = [
    {"value": LIGHT_TYPE_SINGLE, "label": "单灯光"},
    {"value": LIGHT_TYPE_MULTIPLE_PARALLEL, "label": "多灯光并列"},
    {"value": LIGHT_TYPE_MULTIPLE_ALTERNATE, "label": "多灯光交替"},
]

async def _validate_light_schedules(
    hass: HomeAssistant, light_schedules: Dict[str, Dict[str, str]]
) -> bool:
    """Validate that light schedules cover 24 hours."""
    if not light_schedules:
        return False
    
    # 检查是否覆盖了24小时
    hours_covered = set()
    
    for light_id, schedule in light_schedules.items():
        # 提取小时部分
        start_hour = int(schedule["start"].split(":")[0])
        end_hour = int(schedule["end"].split(":")[0])
        
        # 处理相等或跨午夜的情况
        if start_hour == end_hour:
            # 如果开始和结束时间相同，认为是24小时覆盖
            _LOGGER.info(f"灯光 {light_id} 设置为24小时运行 (开始={start_hour}, 结束={end_hour})")
            hours_covered = set(range(24))
            break
        elif start_hour < end_hour:
            hours_covered.update(range(start_hour, end_hour))
            _LOGGER.info(f"灯光 {light_id} 覆盖时间段: {start_hour}-{end_hour}")
        else:
            hours_covered.update(range(start_hour, 24))
            hours_covered.update(range(0, end_hour))
            _LOGGER.info(f"灯光 {light_id} 覆盖跨午夜时间段: {start_hour}-24 和 0-{end_hour}")
    
    _LOGGER.info(f"总覆盖小时数: {len(hours_covered)}, 覆盖的小时: {sorted(hours_covered)}")
    # 检查是否覆盖了所有24小时
    return len(hours_covered) == 24

class AutoLightConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Auto Light."""

    VERSION = 1
    
    def __init__(self):
        """Initialize the config flow."""
        self._data = {}
        self._light_schedules = {}
    
    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        return await self.async_step_sensor_type()
    
    async def async_step_sensor_type(self, user_input=None) -> FlowResult:
        """Handle the sensor type selection step."""
        errors = {}
        
        if user_input is not None:
            self._data[CONF_SENSOR_TYPE] = user_input[CONF_SENSOR_TYPE]
            return await self.async_step_presence_sensor()
        
        schema = vol.Schema(
            {
                vol.Required(CONF_SENSOR_TYPE): SelectSelector(
                    SelectSelectorConfig(
                        options=SENSOR_TYPES,
                        mode=SelectSelectorMode.DROPDOWN,
                        translation_key="sensor_type",
                    )
                ),
            }
        )
        
        return self.async_show_form(
            step_id="sensor_type",
            data_schema=schema,
            errors=errors,
            last_step=False,
        )
    
    async def async_step_presence_sensor(self, user_input=None) -> FlowResult:
        """Handle the presence sensor selection step."""
        errors = {}
        
        if user_input is not None:
            self._data[CONF_PRESENCE_SENSOR] = user_input[CONF_PRESENCE_SENSOR]
            return await self.async_step_brightness_sensor()
        
        schema = vol.Schema(
            {
                vol.Required(CONF_PRESENCE_SENSOR): EntitySelector(
                    EntitySelectorConfig(domain=["binary_sensor", "sensor", "device_tracker"])
                ),
            }
        )
        
        return self.async_show_form(
            step_id="presence_sensor",
            data_schema=schema,
            errors=errors,
            last_step=False,
            description_placeholders={
                "sensor_type": "人在传感器" if self._data[CONF_SENSOR_TYPE] == SENSOR_TYPE_PRESENCE else "人体传感器"
            },
        )
    
    async def async_step_brightness_sensor(self, user_input=None) -> FlowResult:
        """Handle the brightness sensor selection step."""
        errors = {}
        
        if user_input is not None:
            self._data[CONF_BRIGHTNESS_SENSOR] = user_input[CONF_BRIGHTNESS_SENSOR]
            return await self.async_step_light_type()
        
        schema = vol.Schema(
            {
                vol.Required(CONF_BRIGHTNESS_SENSOR): EntitySelector(
                    EntitySelectorConfig(domain=["sensor"])
                ),
            }
        )
        
        return self.async_show_form(
            step_id="brightness_sensor",
            data_schema=schema,
            errors=errors,
            last_step=False,
        )
    
    async def async_step_light_type(self, user_input=None) -> FlowResult:
        """Handle the light type selection step."""
        errors = {}
        
        if user_input is not None:
            self._data[CONF_LIGHT_TYPE] = user_input[CONF_LIGHT_TYPE]
            return await self.async_step_lights()
        
        schema = vol.Schema(
            {
                vol.Required(CONF_LIGHT_TYPE): SelectSelector(
                    SelectSelectorConfig(
                        options=LIGHT_TYPES,
                        mode=SelectSelectorMode.DROPDOWN,
                        translation_key="light_type",
                    )
                ),
            }
        )
        
        return self.async_show_form(
            step_id="light_type",
            data_schema=schema,
            errors=errors,
            last_step=False,
        )
    
    async def async_step_lights(self, user_input=None) -> FlowResult:
        """Handle the lights selection step."""
        errors = {}
        
        if user_input is not None:
            # 处理单灯光模式下的实体选择
            if self._data[CONF_LIGHT_TYPE] == LIGHT_TYPE_SINGLE:
                # 如果是字符串，说明只选择了一个实体
                if isinstance(user_input[CONF_LIGHTS], str):
                    self._data[CONF_LIGHTS] = [user_input[CONF_LIGHTS]]
                # 如果是列表但长度不为1，则报错
                elif len(user_input[CONF_LIGHTS]) != 1:
                    errors["base"] = "single_light_required"
                    return self.async_show_form(
                        step_id="lights",
                        data_schema=vol.Schema(
                            {
                                vol.Required(CONF_LIGHTS): EntitySelector(
                                    EntitySelectorConfig(domain=["light"], multiple=False)
                                ),
                            }
                        ),
                        errors=errors,
                        last_step=False,
                    )
                else:
                    self._data[CONF_LIGHTS] = user_input[CONF_LIGHTS]
            else:
                # 多灯光模式
                self._data[CONF_LIGHTS] = user_input[CONF_LIGHTS]
            
            # 处理后续步骤
            if self._data[CONF_LIGHT_TYPE] == LIGHT_TYPE_MULTIPLE_ALTERNATE:
                # 创建一个合并的步骤，同时选择灯光和时间段
                return await self.async_step_light_schedule_combined()
            else:
                return await self.async_step_advanced()
        
        # 根据灯光类型选择是否允许多选
        is_multiple = self._data[CONF_LIGHT_TYPE] != LIGHT_TYPE_SINGLE
        
        schema = vol.Schema(
            {
                vol.Required(CONF_LIGHTS): EntitySelector(
                    EntitySelectorConfig(domain=["light"], multiple=is_multiple)
                ),
            }
        )
        
        return self.async_show_form(
            step_id="lights",
            data_schema=schema,
            errors=errors,
            last_step=False,
        )
    
    async def async_step_light_schedule(self, light_id=None, user_input=None) -> FlowResult:
        """Handle the light schedule configuration step."""
        errors = {}
        
        if light_id is None:
            # All schedules are configured, validate and proceed
            if await _validate_light_schedules(self.hass, self._light_schedules):
                self._data[CONF_LIGHT_SCHEDULES] = self._light_schedules
                return await self.async_step_advanced()
            else:
                errors["base"] = "invalid_schedules"
                # Restart schedule configuration
                light_id = list(self._light_schedules.keys())[0]
        
        if user_input is not None:
            self._light_schedules[light_id] = {
                "start": user_input["start_time"],
                "end": user_input["end_time"],
            }
            
            # Move to next light or finish
            light_ids = list(self._light_schedules.keys())
            current_index = light_ids.index(light_id)
            
            if current_index < len(light_ids) - 1:
                return await self.async_step_light_schedule(light_ids[current_index + 1])
            else:
                # Validate schedules
                return await self.async_step_light_schedule(None)
        
        schema = vol.Schema(
            {
                vol.Required("start_time"): TimeSelector(),
                vol.Required("end_time"): TimeSelector(),
            }
        )
        
        return self.async_show_form(
            step_id="light_schedule",
            data_schema=schema,
            errors=errors,
            last_step=False,
            description_placeholders={"light_name": light_id},
        )
    
    async def async_step_light_schedule_combined(self, user_input=None) -> FlowResult:
        """Handle the combined light and schedule selection step."""
        errors = {}
        
        if user_input is not None:
            # 处理提交的数据
            light_schedules = {}
            
            # 从用户输入中提取灯光和时间段
            for i, light in enumerate(self._data[CONF_LIGHTS], 1):
                entity_name = self.hass.states.get(light).attributes.get('friendly_name')  # 获取实体的友好名称
                
                # 查找对应的开始和结束时间键
                start_key = f"【 {entity_name} 】开始时间"
                end_key = f"【 {entity_name} 】结束时间"
                
                if start_key in user_input and end_key in user_input:
                    # 将小时转换为时间字符串
                    start_hour = int(user_input[start_key])
                    end_hour = int(user_input[end_key])
                    
                    # 创建时间字符串 (HH:00:00 格式)
                    start_time = f"{start_hour:02d}:00:00"
                    end_time = f"{end_hour:02d}:00:00"
                    
                    _LOGGER.info(f"处理灯光 {light} (名称: {entity_name}): 开始时间={start_time}, 结束时间={end_time}")
                    
                    light_schedules[light] = {
                        "start": start_time,
                        "end": end_time
                    }
            
            # 检查是否覆盖了24小时
            hours_covered = set()
            for light, schedule in light_schedules.items():
                start_hour = int(schedule["start"].split(":")[0])
                end_hour = int(schedule["end"].split(":")[0])
                
                # 处理跨午夜的情况或相等的情况
                if start_hour == end_hour:
                    # 如果开始和结束时间相同，认为是24小时覆盖
                    hours_covered = set(range(24))
                    _LOGGER.info(f"灯光 {light} 设置为24小时运行 (开始={start_hour}, 结束={end_hour})")
                    break
                elif start_hour < end_hour:
                    hours_covered.update(range(start_hour, end_hour))
                    _LOGGER.info(f"灯光 {light} 覆盖时间段: {start_hour}-{end_hour}")
                else:
                    hours_covered.update(range(start_hour, 24))
                    hours_covered.update(range(0, end_hour))
                    _LOGGER.info(f"灯光 {light} 覆盖跨午夜时间段: {start_hour}-24 和 0-{end_hour}")
            
            _LOGGER.info(f"总覆盖小时数: {len(hours_covered)}, 覆盖的小时: {sorted(hours_covered)}")
            if len(hours_covered) == 24:
                self._data[CONF_LIGHT_SCHEDULES] = light_schedules
                return await self.async_step_advanced()
            else:
                errors["base"] = "invalid_schedules"
        
        # 创建动态表单
        schema_fields = {}
        
        # 为每个灯光添加开始和结束小时选择器
        for i, light in enumerate(self._data[CONF_LIGHTS], 1):
            entity_name = self.hass.states.get(light).attributes.get('friendly_name')  # 获取实体的友好名称
            
            # 创建小时选项 (0-23)
            hour_options = [{"value": str(h), "label": f"{h}:00"} for h in range(24)]
            
            schema_fields[vol.Required(f"【 {entity_name} 】开始时间", 
                description=f"第{i}段开始小时")] = SelectSelector(
                    SelectSelectorConfig(
                        options=hour_options,
                        mode=SelectSelectorMode.DROPDOWN
                    )
                )
            schema_fields[vol.Required(f"【 {entity_name} 】结束时间", 
                description=f"第{i}段结束小时")] = SelectSelector(
                    SelectSelectorConfig(
                        options=hour_options,
                        mode=SelectSelectorMode.DROPDOWN
                    )
                )
        
        schema = vol.Schema(schema_fields)
        
        return self.async_show_form(
            step_id="light_schedule_combined",
            data_schema=schema,
            errors=errors,
            last_step=False,
            description_placeholders={"light_count": str(len(self._data[CONF_LIGHTS]))},
        )
    
    async def async_step_advanced(self, user_input=None) -> FlowResult:
        """Handle the advanced configuration step."""
        errors = {}
        
        if user_input is not None:
            self._data[CONF_BRIGHTNESS_THRESHOLD] = user_input[CONF_BRIGHTNESS_THRESHOLD]
            self._data[CONF_DELAY_OFF_TIME] = user_input[CONF_DELAY_OFF_TIME]
            return await self.async_step_name()
        
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_BRIGHTNESS_THRESHOLD,
                    default=DEFAULT_BRIGHTNESS_THRESHOLD
                ): cv.positive_int,
                vol.Required(
                    CONF_DELAY_OFF_TIME,
                    default=DEFAULT_DELAY_OFF_TIME
                ): cv.positive_int,
            }
        )
        
        return self.async_show_form(
            step_id="advanced",
            data_schema=schema,
            errors=errors,
            last_step=False,
        )
        
    async def async_step_name(self, user_input=None) -> FlowResult:
        """Handle the name configuration step."""
        errors = {}
        
        if user_input is not None:
            self._data[CONF_NAME] = user_input[CONF_NAME]
            
            # Create entry
            return self.async_create_entry(
                title=self._data[CONF_NAME],
                data=self._data,
            )
        
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): TextSelector(
                    TextSelectorConfig()
                ),
            }
        )
        
        return self.async_show_form(
            step_id="name",
            data_schema=schema,
            errors=errors,
            last_step=True,
        )
        
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return AutoLightOptionsFlow(config_entry)


class AutoLightOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Auto Light."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry
        self._data = dict(config_entry.data)

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}
        
        if user_input is not None:
            # 更新配置
            self._data[CONF_BRIGHTNESS_THRESHOLD] = user_input[CONF_BRIGHTNESS_THRESHOLD]
            self._data[CONF_DELAY_OFF_TIME] = user_input[CONF_DELAY_OFF_TIME]
            
            # 更新配置条目
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=self._data
            )
            
            # 重新加载集成
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            
            return self.async_create_entry(title="", data={})
        
        # 创建表单
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_BRIGHTNESS_THRESHOLD,
                    default=self._data.get(CONF_BRIGHTNESS_THRESHOLD, DEFAULT_BRIGHTNESS_THRESHOLD)
                ): cv.positive_int,
                vol.Required(
                    CONF_DELAY_OFF_TIME,
                    default=self._data.get(CONF_DELAY_OFF_TIME, DEFAULT_DELAY_OFF_TIME)
                ): cv.positive_int,
            }
        )
        
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
