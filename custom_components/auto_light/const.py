"""Constants for the Auto Light integration."""

DOMAIN = "auto_light"

# Sensor types
SENSOR_TYPE_PRESENCE = "presence"
SENSOR_TYPE_MOTION = "motion"

# Light types
LIGHT_TYPE_SINGLE = "single"
LIGHT_TYPE_MULTIPLE_PARALLEL = "multiple_parallel"
LIGHT_TYPE_MULTIPLE_ALTERNATE = "multiple_alternate"

# Config flow options
CONF_SENSOR_TYPE = "sensor_type"
CONF_PRESENCE_SENSOR = "presence_sensor"
CONF_BRIGHTNESS_SENSOR = "brightness_sensor"
CONF_LIGHT_TYPE = "light_type"
CONF_LIGHTS = "lights"
CONF_LIGHT_SCHEDULES = "light_schedules"
CONF_NAME = "name"
CONF_BRIGHTNESS_THRESHOLD = "brightness_threshold"
CONF_DELAY_OFF_TIME = "delay_off_time"

# Default values
DEFAULT_NAME = "灯光自动化"
DEFAULT_BRIGHTNESS_THRESHOLD = 60
DEFAULT_DELAY_OFF_TIME = 0
