from .request import AsyncHttpClient
import os
import json
from cryptography.fernet import Fernet
from pathlib import Path
from .logger import logger
import asyncio
from functools import wraps

requests = AsyncHttpClient()

class TokenManager:
    """全局Token管理器（单例模式）"""
    _instance = None
    _token = None
    _initialized = False
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.token_file = Path("token.enc")
            self.key = self._get_or_create_key()
            self.cipher = Fernet(self.key)
            self._initialized = True

    def _get_or_create_key(self) -> bytes:
        """获取或创建加密密钥"""
        key_file = Path("secret.key")
        if key_file.exists():
            with open(key_file, "rb") as f:
                return f.read()
        
        key = Fernet.generate_key()
        with open(key_file, "wb") as f:
            f.write(key)
        key_file.chmod(0o600)
        return key

    async def load_token(self) -> bool:
        """加载Token（线程安全）"""
        async with self._lock:
            if self._token is not None:
                return True

            if not self.token_file.exists():
                await logger.debug("未找到本地Token文件")
                return False

            try:
                with open(self.token_file, "rb") as f:
                    encrypted = f.read()
                self._token = self.cipher.decrypt(encrypted).decode()
                await logger.info("Token加载成功")
                return True
            except Exception as e:
                await logger.error(f"Token加载失败: {str(e)}")
                return False

    def save_token(self, token: str):
        """保存Token"""
        try:
            encrypted = self.cipher.encrypt(token.encode())
            with open(self.token_file, "wb") as f:
                f.write(encrypted)
            self.token_file.chmod(0o600)
            self._token = token
            logger.info("Token保存成功")
        except Exception as e:
            logger.error(f"Token保存失败: {str(e)}")

    def clear_token(self):
        """清除Token"""
        self._token = None
        try:
            if self.token_file.exists():
                self.token_file.unlink()
                logger.info("Token已清除")
        except Exception as e:
            logger.error(f"清除Token文件失败: {str(e)}")

    @property
    def token(self):
        return self._token

def require_token(func):
    """装饰器：确保有有效Token"""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        if not await TokenManager().load_token():
            await logger.error("请先登录获取Token")
            return {"code": -1, "msg": "Authentication required"}
        return await func(self, *args, **kwargs)
    return wrapper

class BaseAPIClient:
    """所有API类的基类"""
    def __init__(self):
        self.token_manager = TokenManager()
        self._init_task = asyncio.create_task(self._async_init())

    async def _async_init(self):
        """异步初始化"""
        await self.token_manager.load_token()

    async def wait_for_init(self):
        """等待初始化完成"""
        await self._init_task

    @property
    def token(self):
        return self.token_manager.token

class User(BaseAPIClient):
    """用户服务"""
    async def login(self, email: str, password: str) -> dict:
        """
        邮箱登录
        :param email: 登录邮箱
        :param password: 登录密码
        :return: 登录结果
        """
        if self.token:
            await logger.info("已存在有效Token，无需重复登录")
            return {"code": 1, "msg": "already logged in"}

        try:
            response = await requests.post(
                url="https://chat-go.jwzhd.com/v1/user/email-login",
                headers={
                    "Accept": "*/*",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                    "Connection": "keep-alive",
                    "Origin": "https://chat.yhchat.com",
                    "Referer": "https://chat.yhchat.com/",
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "cross-site",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
                    "content-type": "application/json",
                    "sec-ch-ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Microsoft Edge";v="126"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"'
                },
                data=json.dumps({
                    "email": email,
                    "password": password,
                    "deviceId": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
                    "platform": "Web"
                })
            )
            
            result = response.json()
            if result.get('code') == 1:
                self.token_manager.save_token(result.get('data', {}).get('token'))
                await logger.info("登录成功")
            else:
                await logger.error(f"登录失败: {result.get('msg')}")
            return result
            
        except Exception as e:
            await logger.error(f"登录请求出错: {str(e)}")
            return {"code": -1, "msg": str(e)}

    async def logout(self):
        """注销登录"""
        self.token_manager.clear_token()
        await logger.info("已注销")

class Admin(BaseAPIClient):
    """群组服务"""
    @require_token
    async def ban(self, group_id: str, user_id: str, duration: str):
        """禁言用户"""
        try:
            response = await requests.post(
                url="https://chat-go.jwzhd.com/v1/group/gag-member",
                headers={
                    "User-Agent": "windows 1.5.47",
                    "Accept": "application/x-protobuf",
                    "Accept-Encoding": "gzip",
                    "Host": "www.yhchat.com",
                    "Content-Type": "application/x-protobuf",
                    "token": self.token
                },
                data={
                    "groupId": group_id,
                    "userId": user_id,
                    "gag": duration
                }
            )
            
            if response['code'] != 1:
                await logger.error(f"禁言失败：{response['msg']}({response['code']})")
            else:
                await logger.info(f"已成功禁言 {group_id} 群的 {user_id} 用户 {duration}")
            return response
            
        except Exception as e:
            await logger.error(f"禁言请求出错: {str(e)}")
            return {"code": -1, "msg": str(e)}

    @require_token
    async def unban(self, group_id: str, user_id: str):
        """解除禁言"""
        return await self.ban(group_id, user_id, 0)

    @require_token
    async def kick(self, group_id: str, user_id: str):
        """踢出用户"""
        try:
            response = await requests.post(
                url="https://chat-go.jwzhd.com/v1/group/remove-member",
                headers={
                    "User-Agent": "windows 1.5.47",
                    "Accept": "application/x-protobuf",
                    "Accept-Encoding": "gzip",
                    "Host": "yhchat.hqycloud.top",
                    "Content-Type": "application/x-protobuf",
                    "token": self.token
                },
                data=json.dumps({
                    "groupId": group_id,
                    "userId": user_id
                })
            )
            
            if response['code'] != 1:
                await logger.error(f"踢出失败：{response['msg']}({response['code']})")
            else:
                await logger.info(f"已成功踢出 {group_id} 群的用户 {user_id}")
            return response
                
        except Exception as e:
            await logger.error(f"踢出请求出错: {str(e)}")
            return {"code": -1, "msg": str(e)}
class Tag(BaseAPIClient):
    @require_token
    async def edit(self, group, id, msg, color="#2196F3", desc=None, sort=0):
        try:
            response = await requests.post(
                url="https://chat-go.jwzhd.com/v1/group-tag/edit",
                headers={
                    "User-Agent": "windows 1.5.47",
                    "Accept": "application/x-protobuf",
                    "Accept-Encoding": "gzip",
                    "Host": "yhchat.hqycloud.top",
                    "Content-Type": "application/x-protobuf",
                    "token": self.token
                },
                data=json.dumps({
                    "id": id,
                    "groupId": group,
                    "tag": msg,
                    "color": color,
                    "desc": desc,
                    "sort": sort
                })
            )
            
            if response['code'] != 1:
                await logger.error(f"编辑标签组失败：{response['msg']}({response['code']})")
            else:
                await logger.info(f"已成功编辑 {group} 群的标签 {id} 为 {msg}")
            return response
                
        except Exception as e:
            await logger.error(f"编辑标签组请求出错: {str(e)}")
            return {"code": -1, "msg": str(e
    @require_token
    async def add(self, group, msg, color="#2196F3", desc=None, sort=0):
        try:
            response = await requests.post(
                url="https://chat-go.jwzhd.com/v1/group-tag/create",
                headers={
                    "User-Agent": "windows 1.5.47",
                    "Accept": "application/x-protobuf",
                    "Accept-Encoding": "gzip",
                    "Host": "yhchat.hqycloud.top",
                    "Content-Type": "application/x-protobuf",
                    "token": self.token
                },
                data=json.dumps({
                    "groupId": group,
                    "tag": msg,
                    "color": color,
                    "desc": desc,
                    "sort": sort
                })
            )
            
            if response['code'] != 1:
                await logger.error(f"创建标签组失败：{response['msg']}({response['code']})")
            else:
                await logger.info(f"已成功设置 {group} 群的标签{msg}")
            return response
        except Exception as e:
            await logger.error(f"编辑标签组请求出错: {str(e)}")
            return {"code": -1, "msg": str(e)}
    @require_token
    async def rm(self, id):
        try:
            response = await requests.post(
                url="https://chat-go.jwzhd.com/v1/group-tag/delete",
                headers={
                    "User-Agent": "windows 1.5.47",
                    "Accept": "application/x-protobuf",
                    "Accept-Encoding": "gzip",
                    "Host": "yhchat.hqycloud.top",
                    "Content-Type": "application/x-protobuf",
                    "token": self.token
                },
                data=json.dumps({
                    "id": id
                })
            )
            
            if response['code'] != 1:
                await logger.error(f"删除标签组失败：{response['msg']}({response['code']})")
            else:
                await logger.info(f"已成功删除标签 {id}")
            return response
        except Exception as e:
            await logger.error(f"编辑标签组请求出错: {str(e)}")
            return {"code": -1, "msg": str(e)}