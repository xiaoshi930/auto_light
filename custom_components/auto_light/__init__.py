"""Auto Light integration for Home Assistant."""
import asyncio
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config):
    """Set up the Auto Light component."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Auto Light from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    # 创建一个可写的字典来存储数据
    hass.data[DOMAIN][entry.entry_id] = {
        "config": dict(entry.data),
        "state": {}
    }
    
    # Create automation based on config
    await _create_automation(hass, entry)
    
    # 设置开关平台
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(entry, ["switch"])
    )
    
    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    # 卸载开关平台
    await hass.config_entries.async_unload_platforms(entry, ["switch"])
    
    # Remove automation and clean up listeners
    if entry.entry_id in hass.data[DOMAIN]:
        # 移除事件监听器
        if "state" in hass.data[DOMAIN][entry.entry_id]:
            state_data = hass.data[DOMAIN][entry.entry_id]["state"]
            if "remove_state_listener" in state_data and state_data["remove_state_listener"] is not None:
                state_data["remove_state_listener"]()
            if "remove_interval" in state_data and state_data["remove_interval"] is not None:
                state_data["remove_interval"]()
            
            # 取消延迟关灯任务
            if "delay_off_task" in state_data and state_data["delay_off_task"] is not None:
                state_data["delay_off_task"]()
        
        # 删除组件数据
        del hass.data[DOMAIN][entry.entry_id]
    
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)

async def _create_automation(hass: HomeAssistant, entry: ConfigEntry):
    """Create automation based on config entry."""
    from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
    from datetime import timedelta
    import datetime
    from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
    from homeassistant.const import (
        STATE_ON,
        STATE_OFF,
    )
    
    # 设置日志级别为INFO，确保所有重要日志都能输出
    _LOGGER.setLevel(logging.INFO)
    
    _LOGGER.info("=== 开始创建自动化任务 ===")
    
    data = hass.data[DOMAIN][entry.entry_id]["config"]
    sensor_type = data.get("sensor_type")
    presence_sensor = data.get("presence_sensor")
    brightness_sensor = data.get("brightness_sensor")
    light_type = data.get("light_type")
    lights = data.get("lights", [])
    light_schedules = data.get("light_schedules", {})
    name = data.get("name", "主卫灯光自动化")
    
    # 设置默认启用状态
    hass.data[DOMAIN][entry.entry_id]["state"]["enabled"] = True
    
    def is_person_present(state):
        """Determine if a person is present based on sensor state."""
        _LOGGER.info(f"判断人在状态: 传感器类型={sensor_type}, 当前状态={state}")
        
        if sensor_type == "presence":
            # 扩展有人状态列表，增加更多可能的状态值
            present_states = ["有人", "one", "on", "On", "ON", "True", "true", "TRUE", "1", "2", True, "home", "Home", "HOME", "在家", "occupied", "Occupied"]
            # 尝试将状态转换为小写进行比较，增加匹配成功率
            result = state in present_states or str(state).lower() in [str(s).lower() for s in present_states]
            _LOGGER.info(f"presence模式: 状态={state}, 有人状态列表={present_states}, 判断结果={result}")
            return result
        elif sensor_type == "motion":
            # 扩展无人状态列表
            absent_states = ["2～5分钟无人移动", "5分钟以上无人移动", "无人", "无人移动", "no motion", "no_motion", "idle"]
            # 尝试将状态转换为小写进行比较
            result = state not in absent_states and str(state).lower() not in [str(s).lower() for s in absent_states]
            _LOGGER.info(f"motion模式: 状态={state}, 无人状态列表={absent_states}, 判断结果={result}")
            return result
        
        _LOGGER.info(f"未知传感器类型: {sensor_type}, 默认返回False")
        return False
    
    _LOGGER.info("自动化任务创建完成")
    
    def is_brightness_low(state):
        """Determine if brightness is low based on sensor state."""
        _LOGGER.info(f"判断亮度状态: {state}")
        try:
            # 处理可能的None值
            if state is None:
                _LOGGER.info("亮度状态为None，默认返回False")
                return False
                
            # 处理字符串"None"
            if state == "None" or state == "unknown" or state == "unavailable":
                _LOGGER.info(f"亮度状态为特殊值: {state}，默认返回False")
                return False
                
            if sensor_type == "presence":
                try:
                    # 尝试将状态转换为数值
                    brightness_value = float(state)
                    # 使用配置的亮度阈值
                    brightness_threshold = hass.data[DOMAIN][entry.entry_id]["config"].get(
                        "brightness_threshold", 60
                    )
                    result = brightness_value < brightness_threshold
                    _LOGGER.info(f"亮度值: {brightness_value}, 阈值: {brightness_threshold}, 判断结果: {result}")
                    return result
                except (ValueError, TypeError):
                    # 如果无法转换为数值，尝试其他判断方法
                    _LOGGER.info(f"无法将亮度状态转换为数值: {state}")
                    
                    # 检查是否包含表示暗的关键词
                    dark_keywords = ["dark", "暗", "weak", "low", "dim", "night", "夜间", "黑"]
                    for keyword in dark_keywords:
                        if keyword.lower() in str(state).lower():
                            _LOGGER.info(f"亮度状态包含暗关键词: {keyword}")
                            return True
                    
                    # 默认返回False
                    return False
            elif sensor_type == "motion":
                # 扩展弱光状态列表
                weak_light_states = ["weak", "Weak", "暗", "dark", "Dark", "dim", "Dim", "low", "Low", "night", "Night"]
                result = str(state) in weak_light_states or str(state).lower() in [s.lower() for s in weak_light_states]
                _LOGGER.info(f"亮度状态: {state}, 弱光状态列表: {weak_light_states}, 判断结果: {result}")
                return result
                
            _LOGGER.info(f"未知传感器类型: {sensor_type}, 默认返回False")
            return False
        except Exception as e:
            _LOGGER.error(f"判断亮度时出错: {e}", exc_info=True)
            return False
    
    _LOGGER.info("自动化任务创建完成")
    
    def get_active_lights():
        """Get active lights based on light type and current time."""
        try:
            if light_type == "single" or light_type == "multiple_parallel":
                _LOGGER.info(f"单灯光或多灯光并列模式，返回所有灯光: {lights}")
                return lights
            elif light_type == "multiple_alternate":
                now = datetime.datetime.now()
                now_hour = now.hour
                now_minute = now.minute
                _LOGGER.info(f"多灯光交替模式，当前时间: {now_hour}:{now_minute:02d}, 检查灯光调度")
                
                # 记录所有灯光的调度
                _LOGGER.info(f"灯光调度配置: {light_schedules}")
                
                for light_id, schedule in light_schedules.items():
                    # 提取小时部分
                    start_hour = int(schedule["start"].split(":")[0])
                    end_hour = int(schedule["end"].split(":")[0])
                    
                    _LOGGER.info(f"检查灯光 {light_id}: 开始时间={start_hour}, 结束时间={end_hour}")
                    
                    # 处理相等或跨午夜的情况
                    if start_hour == end_hour:
                        # 24小时运行的情况
                        _LOGGER.info(f"灯光 {light_id} 设置为24小时运行 (开始={start_hour}, 结束={end_hour})")
                        return [light_id]
                    elif start_hour < end_hour:
                        # 正常时间段 (例如 8:00-20:00)
                        if start_hour <= now_hour < end_hour:
                            _LOGGER.info(f"匹配到灯光 {light_id}: {start_hour} <= {now_hour} < {end_hour}")
                            return [light_id]
                    else:
                        # 跨午夜时间段 (例如 20:00-8:00)
                        if now_hour >= start_hour or now_hour < end_hour:
                            _LOGGER.info(f"匹配到灯光 {light_id}: {now_hour} >= {start_hour} 或 {now_hour} < {end_hour}")
                            return [light_id]
                
                # Default to first light if no schedule matches
                if light_schedules:
                    default_light = [next(iter(light_schedules.keys()))]
                    _LOGGER.info(f"没有匹配的灯光调度，使用默认灯光: {default_light}")
                    return default_light
                else:
                    _LOGGER.warning("没有灯光调度配置，返回空列表")
                    return []
            
            _LOGGER.warning(f"未知灯光类型: {light_type}, 返回空列表")
            return []
        except Exception as e:
            _LOGGER.error(f"获取活跃灯光时出错: {e}", exc_info=True)
            # 出错时返回所有灯光作为备选
            _LOGGER.info(f"出错时返回所有灯光作为备选: {lights}")
            return lights
    
    async def handle_presence_change(event):
        """Handle changes to the presence sensor."""
        try:
            # 检查自动化是否启用
            if not hass.data[DOMAIN][entry.entry_id]["state"].get("enabled", True):
                _LOGGER.info("自动化当前已禁用，忽略状态变化")
                return
                
            new_state = event.data.get("new_state")
            old_state = event.data.get("old_state")
            
            _LOGGER.info(f"收到状态变化事件: new_state={new_state}, old_state={old_state}")
            
            if not new_state:
                _LOGGER.warning("状态变化事件中缺少新状态，忽略此事件")
                return
                
            # 即使没有旧状态也继续处理
            new_presence = is_person_present(new_state.state)
            old_presence = is_person_present(old_state.state if old_state else None)
            
            _LOGGER.info(f"人在状态变化: 旧状态={old_state.state if old_state else '无'}({old_presence}), 新状态={new_state.state}({new_presence})")
            _LOGGER.info(f"传感器类型: {sensor_type}, 判断函数: {is_person_present.__name__}")
            
            # 如果新旧状态相同，仍然执行逻辑以确保灯光状态正确
            if new_presence == old_presence:
                _LOGGER.info(f"人在状态未变化 (仍为 {new_presence})，但仍检查灯光状态")
                if new_presence:
                    # 人在，检查亮度并决定是否开灯
                    brightness_state = hass.states.get(brightness_sensor)
                    if brightness_state and is_brightness_low(brightness_state.state):
                        _LOGGER.info(f"人在且亮度低，准备开灯")
                        active_lights = get_active_lights()
                        for light in active_lights:
                            if hass.states.is_state(light, STATE_OFF):
                                _LOGGER.info(f"正在打开灯光: {light}")
                                await hass.services.async_call(
                                    LIGHT_DOMAIN, "turn_on", {"entity_id": light}
                                )
                else:
                    # 人不在，关灯
                    _LOGGER.info("人不在，准备关闭灯光")
                    for light in lights:
                        if hass.states.is_state(light, STATE_ON):
                            _LOGGER.info(f"正在关闭灯光: {light}")
                            await hass.services.async_call(
                                LIGHT_DOMAIN, "turn_off", {"entity_id": light}
                            )
                return
            
            # Person left
            if old_presence and not new_presence:
                delay_off_time = hass.data[DOMAIN][entry.entry_id]["config"].get(
                    "delay_off_time", 0
                )
                
                if delay_off_time > 0:
                    _LOGGER.info(f"检测到人离开，将在{delay_off_time}秒后关闭灯光")
                    
                    # 存储延迟关灯任务
                    if "delay_off_task" not in hass.data[DOMAIN][entry.entry_id]["state"]:
                        hass.data[DOMAIN][entry.entry_id]["state"]["delay_off_task"] = None
                    
                    # 取消之前的延迟任务（如果有）
                    if hass.data[DOMAIN][entry.entry_id]["state"]["delay_off_task"] is not None:
                        hass.data[DOMAIN][entry.entry_id]["state"]["delay_off_task"]()
                    
                    # 创建新的延迟任务
                    async def delayed_turn_off():
                        await asyncio.sleep(delay_off_time)
                        
                        # 检查是否仍然没有人
                        presence_state = hass.states.get(presence_sensor)
                        if presence_state:
                            is_present = is_person_present(presence_state.state)
                            _LOGGER.info(f"延迟{delay_off_time}秒后检查人在状态: {presence_state.state}, 判断结果={is_present}")
                            
                            if not is_present:
                                _LOGGER.info(f"确认无人在场，现在关闭灯光")
                                for light in lights:
                                    if hass.states.is_state(light, STATE_ON):
                                        _LOGGER.info(f"正在关闭灯光: {light}")
                                        await hass.services.async_call(
                                            LIGHT_DOMAIN, "turn_off", {"entity_id": light}
                                        )
                            else:
                                _LOGGER.info(f"检测到人已返回，取消关灯操作")
                        
                        # 清除任务引用
                        hass.data[DOMAIN][entry.entry_id]["state"]["delay_off_task"] = None
                    
                    hass.data[DOMAIN][entry.entry_id]["state"]["delay_off_task"] = hass.async_create_task(delayed_turn_off())
                else:
                    _LOGGER.info("检测到人离开，立即关闭灯光")
                    for light in lights:
                        if hass.states.is_state(light, STATE_ON):
                            _LOGGER.info(f"正在关闭灯光: {light}")
                            await hass.services.async_call(
                                LIGHT_DOMAIN, "turn_off", {"entity_id": light}
                            )
            
            # Person arrived
            elif not old_presence and new_presence:
                _LOGGER.info("检测到人到达，准备检查亮度并开灯")
                brightness_state = hass.states.get(brightness_sensor)
                if brightness_state and is_brightness_low(brightness_state.state):
                    _LOGGER.info(f"亮度低，准备开灯")
                    active_lights = get_active_lights()
                    for light in active_lights:
                        if hass.states.is_state(light, STATE_OFF):
                            _LOGGER.info(f"正在打开灯光: {light}")
                            await hass.services.async_call(
                                LIGHT_DOMAIN, "turn_on", {"entity_id": light}
                            )
        except Exception as e:
            _LOGGER.error(f"处理人在状态变化时出错: {e}", exc_info=True)
    
    async def periodic_check(now=None):
        """Run periodic check to ensure automation logic is applied."""
        try:
            # 检查自动化是否启用
            if not hass.data[DOMAIN][entry.entry_id]["state"].get("enabled", True):
                _LOGGER.debug("自动化当前已禁用，跳过定期检查")
                return
                
            _LOGGER.info(f"执行定期检查 (时间: {now})")
            
            presence_state = hass.states.get(presence_sensor)
            brightness_state = hass.states.get(brightness_sensor)
            
            if not presence_state:
                return
                
            if not brightness_state:
                return
                
            is_present = is_person_present(presence_state.state)
            is_dark = is_brightness_low(brightness_state.state)
            
            _LOGGER.info(f"定期检查: 人在状态={presence_state.state}({is_present}), 亮度状态={brightness_state.state}({is_dark})")
            
            # 获取当前活跃的灯光
            active_lights = get_active_lights()
            _LOGGER.info(f"当前活跃灯光: {active_lights}")
            
            # 检查当前灯光状态
            for light in lights:
                light_state = hass.states.get(light)
                if light_state:
                    _LOGGER.info(f"灯光 {light} 当前状态: {light_state.state}")
                else:
                    _LOGGER.info(f"无法获取灯光 {light} 的状态")
            
            # If person is present and it's dark, turn on lights
            if is_present and is_dark:
                _LOGGER.info("人在且亮度低，准备开灯")
                for light in active_lights:
                    if hass.states.is_state(light, STATE_OFF):
                        _LOGGER.info(f"正在打开灯光: {light}")
                        await hass.services.async_call(
                            LIGHT_DOMAIN, "turn_on", {"entity_id": light}
                        )
            
            # If no one is present, turn off lights
            elif not is_present:
                _LOGGER.info("人不在，准备关闭灯光")
                for light in lights:
                    if hass.states.is_state(light, STATE_ON):
                        _LOGGER.info(f"正在关闭灯光: {light}")
                        await hass.services.async_call(
                            LIGHT_DOMAIN, "turn_off", {"entity_id": light}
                        )
            else:
                _LOGGER.info(f"当前状态不需要操作灯光: 人在={is_present}, 亮度低={is_dark}")
        except Exception as e:
            _LOGGER.error(f"定期检查时出错: {e}", exc_info=True)
    
    # Register state change listener
    _LOGGER.info(f"注册状态变化监听器: 传感器={presence_sensor}")
    hass.data[DOMAIN][entry.entry_id]["state"]["remove_state_listener"] = async_track_state_change_event(
        hass, [presence_sensor], handle_presence_change
    )
    
    # 立即执行一次状态检查，确保初始状态正确
    _LOGGER.info("执行初始状态检查")
    await periodic_check()
    
    # Register periodic check (every 10 minutes)
    hass.data[DOMAIN][entry.entry_id]["state"]["remove_interval"] = async_track_time_interval(
        hass, periodic_check, timedelta(minutes=10)
    )
