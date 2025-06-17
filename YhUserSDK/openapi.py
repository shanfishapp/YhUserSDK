import requests
import os
from logger import logger

class api:
    # 环境变量配置
    TOKEN_ENV_VAR = "CHAT_API_TOKEN"  # 存储token的环境变量名
    
    # API配置
    token = None
    headers = {
        "User-Agent": "android 1.4.71",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "token": token,
        "Host": "chat-go.jwzhd.com"
    }
    base_url = "https://chat-go.jwzhd.com/v1"

    # --------------------------
    # Token管理（环境变量版）
    # --------------------------
    @classmethod
    def _save_token(cls, token: str):
        """保存Token到环境变量"""
        os.environ[cls.TOKEN_ENV_VAR] = token
        logger.info("Token已保存到环境变量")

    @classmethod
    def _load_token(cls) -> str:
        """从环境变量加载Token"""
        return os.environ.get(cls.TOKEN_ENV_VAR)

    # --------------------------
    # 核心请求方法
    # --------------------------
    @classmethod
    def _make_request(cls, url, data, action_name):
        """统一的请求处理方法"""
        try:
            response = requests.post(
                url=url,
                headers=cls.headers,
                json=data,
                timeout=10
            )
            response_data = response.json()
            
            return {
                'success': response_data.get('code') == 1,
                'code': response_data.get('code', -1),
                'message': response_data.get('msg', '操作失败'),
                'data': response_data.get('data')
            }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"{action_name}网络错误：{str(e)}")
            return {'success': False, 'code': -2, 'message': f"网络错误: {str(e)}", 'data': None}
        except Exception as e:
            logger.error(f"{action_name}未知错误：{str(e)}")
            return {'success': False, 'code': -3, 'message': f"未知错误: {str(e)}", 'data': None}

    # --------------------------
    # 初始化与登录
    # --------------------------
    @classmethod
    def initialize(cls):
        """初始化时尝试加载环境变量中的token"""
        cls.token = cls._load_token()
        if cls.token:
            cls.headers["token"] = cls.token
            logger.info("已从环境变量加载Token")

    @classmethod
    def login(cls, email, password, force=False):
        """
        登录方法
        :param force: 是否强制重新登录（忽略现有token）
        :return: 统一格式的响应字典
        """
        if not force and cls.token:
            return {'success': True, 'code': 1, 'message': '已使用现有Token', 'data': None}

        url = cls.base_url + "/user/email-login"
        data = {
            "email": email,
            "password": password,
            "deviceId": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
            "platform": "windows"
        }
        
        result = cls._make_request(url, data, "登录")
        if result['success']:
            cls.token = result['data']['token']
            cls.headers["token"] = cls.token
            cls._save_token(cls.token)
        return result

    # --------------------------
    # 群组管理API
    # --------------------------
    @classmethod
    def ban_request(cls, user_id, group_id, time):
        """禁言请求方法"""
        allow_time = ["10", "1h", "6h", "12h", "0"]
        if time not in allow_time:
            return {'success': False, 'code': -4, 'message': f"不支持的时间: {time}", 'data': None}
        
        url = cls.base_url + "/group/gag_member"
        data = {"groupId": group_id, "userId": user_id, "time": time}
        action = "取消禁言" if time == "0" else "禁言"
        return cls._make_request(url, data, action)

    @classmethod
    def ban(cls, group_id, user_id, time):
        """禁言快捷方法"""
        return cls.ban_request(user_id, group_id, time)

    @classmethod
    def unban(cls, group_id, user_id):
        """取消禁言快捷方法"""
        return cls.ban_request(user_id, group_id, "0")

    @classmethod
    def kick(cls, group_id, user_id):
        """踢出成员"""
        url = cls.base_url + "/group/remove-member"
        data = {"groupId": group_id, "userId": user_id}
        return cls._make_request(url, data, "踢出成员")

    # --------------------------
    # 标签管理类
    # --------------------------
    class tag:
        """标签管理（自动继承api的token和配置）"""
        
        @classmethod
        def add(cls, group_id, tag_name, color="#2196F3", desc="", sort=0):
            """添加标签组"""
            url = api.base_url + "/group-tag/create"
            data = {
                "groupId": group_id,
                "tag": tag_name,
                "color": color,
                "desc": desc,
                "sort": sort
            }
            return api._make_request(url, data, "添加标签组")

        @classmethod
        def remove(cls, tag_id):
            """删除标签组"""
            if not isinstance(tag_id, int):
                return {'success': False, 'code': -4, 'message': "tag_id必须为整数", 'data': None}
                
            url = api.base_url + "/group-tag/delete"
            data = {"id": tag_id}
            return api._make_request(url, data, "删除标签组")

        @classmethod
        def list(cls, group_id):
            """获取标签组列表"""
            url = api.base_url + "/group-tag/list"
            data = {"groupId": group_id}
            return api._make_request(url, data, "获取标签组")

        @classmethod
        def edit(cls, tag_id, group_id, tag_name, color="#2196F3", desc="", sort=0):
            """编辑标签组"""
            if not isinstance(tag_id, int):
                return {'success': False, 'code': -4, 'message': "tag_id必须为整数", 'data': None}
                
            url = api.base_url + "/group-tag/edit"
            data = {
                "id": tag_id,
                "groupId": group_id,
                "tag": tag_name,
                "color": color,
                "desc": desc,
                "sort": sort
            }
            return api._make_request(url, data, "编辑标签组")

        @classmethod
        def set_user_tag(cls, user_id, tag_id):
            """为用户设置标签"""
            if not isinstance(tag_id, int):
                return {'success': False, 'code': -4, 'message': "tag_id必须为整数", 'data': None}
                
            url = api.base_url + "/group-tag/relate"
            data = {
                "userId": user_id,
                "tagGroupId": tag_id
            }
            return api._make_request(url, data, "设置用户标签")

# 初始化API模块（自动加载环境变量中的token）
api.initialize()