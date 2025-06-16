from .sdk import sdk
import requests
from .logger import logger

class api:
    # 类变量：获取token和设置请求头
    token = sdk.get()
    headers = {
        "User-A-Agent": "android 1.4.71",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "Content-Length": "11",
        "token": token,  # 使用获取到的token
        "Host": "chat-go.jwzhd.com"
    }
    base_url = "https://chat-go.jwzhd.com/v1"  # API基础URL

    @classmethod
    def ban_request(cls, user_id, group_id, time):
        """
        禁言请求方法
        :param user_id: 用户ID
        :param group_id: 群组ID
        :param time: 禁言时间（"10", "1h", "6h", "12h", "0"）
        """
        allow_time = ["10", "1h", "6h", "12h", "0"]
        if time not in allow_time:
            logger.error("不支持的时间：" + time)
            return
        
        headers = cls.headers
        url = cls.base_url + "/group/gag_member"
        data = {
            "groupId": group_id,
            "userId": user_id,
            "time": time
        }
        title = "禁言" if time != "0" else "取消禁言"  # 根据时间判断操作类型
        
        try:
            response = requests.post(headers=headers, url=url, json=data)
            response_data = response.json()
            
            if response_data['code'] != 1:
                logger.error(f"{title}API 响应错误：{response_data['msg']}({response_data['code']})")
            else:
                logger.info(f"成功对{group_id}的{user_id}进行{title}操作")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"{title}操作时发生网络错误：{str(e)}")
        except Exception as e:
            logger.error(f"{title}操作时发生未知错误：{str(e)}")

    @classmethod
    def ban(cls, group_id, user_id, time):
        """
        禁言方法（参数顺序调整）
        """
        return cls.ban_request(user_id, group_id, time)

    @classmethod
    def unban(cls, group_id, user_id):
        """
        取消禁言方法
        """
        return cls.ban_request(user_id, group_id, "0")

    @classmethod
    def kick(cls, group_id, user_id):
        """
        踢出群成员方法
        """
        url = cls.base_url + "/group/remove-member"
        headers = cls.headers
        data = {
            "groupId": group_id,
            "userId": user_id
        }
        
        try:
            response = requests.post(headers=headers, url=url, json=data)
            response_data = response.json()
            
            if response_data['code'] != 1:
                logger.error(f"踢出成员API 响应错误：{response_data['msg']}({response_data['code']})")
            else:
                logger.info(f"成功对{group_id}的{user_id}进行踢出操作")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"踢出成员操作时发生网络错误：{str(e)}")
        except Exception as e:
            logger.error(f"踢出成员操作时发生未知错误：{str(e)}")


    class tag:
        """
        标签类（结构与api类类似）
        """
        token = sdk.get()
        headers = {
            "User-Agent": "android 1.4.71",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "Content-Length": "11",
            "token": token,
            "Host": "chat-go.jwzhd.com"
        }
        base_url = "https://chat-go.jwzhd.com/v1"
    @classmethod
    def add(cls, group_id, msg, color="#2196F3", desc="", sort=0):
        url = self.base_url + "/group-tag/create"