from .sdk import sdk
import requests
from .logger import logger

class api:
    def ban(cls, user_id, group_id, time):
        allow_time = ["10", "1h", "6h", "12h"]
        if time not in allow_time:
            logger.error("不支持的时间："+time)