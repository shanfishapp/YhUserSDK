import requests
import os
import json
import base64
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
from .logger import logger

class api:
    # 配置项
    TOKEN_ENV_VAR = "CHAT_API_TOKEN"  # 环境变量名
    TOKEN_FILE = "api_token.enc"      # 加密令牌存储文件
    SALT_FILE = "api_token.salt"      # 加密盐值文件
    
    # AES配置
    AES_KEY_SIZE = 32   # AES-256
    SALT_SIZE = 16      # 盐值长度
    ITERATIONS = 100000  # PBKDF2迭代次数
    
    # API基础配置
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
    # 加密工具方法 (使用pycryptodome)
    # --------------------------
    @classmethod
    def _get_encryption_key(cls):
        """获取或生成加密密钥和盐值"""
        if os.path.exists(cls.SALT_FILE):
            with open(cls.SALT_FILE, 'rb') as f:
                salt = f.read()
        else:
            salt = get_random_bytes(cls.SALT_SIZE)
            with open(cls.SALT_FILE, 'wb') as f:
                f.write(salt)
        
        # 使用固定密码+盐值生成密钥（实际项目应考虑更安全的密钥管理）
        password = "default_password_should_be_changed".encode()
        return PBKDF2(password, salt, dkLen=cls.AES_KEY_SIZE, count=cls.ITERATIONS)

    @classmethod
    def _encrypt_token(cls, token: str) -> str:
        """加密令牌"""
        cipher = AES.new(cls._get_encryption_key(), AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(token.encode())
        
        # 组合nonce(12字节) + ciphertext + tag(16字节)
        encrypted_data = cipher.nonce + ciphertext + tag
        return base64.b64encode(encrypted_data).decode()

    @classmethod
    def _decrypt_token(cls, encrypted_token: str) -> str:
        """解密令牌"""
        try:
            encrypted_data = base64.b64decode(encrypted_token.encode())
            nonce = encrypted_data[:12]
            tag = encrypted_data[-16:]
            ciphertext = encrypted_data[12:-16]
            
            cipher = AES.new(cls._get_encryption_key(), AES.MODE_GCM, nonce=nonce)
            return cipher.decrypt_and_verify(ciphertext, tag).decode()
        except (ValueError, KeyError) as e:
            logger.error(f"令牌解密失败: {str(e)}")
            raise ValueError("无效的加密令牌")

    # --------------------------
    # 令牌管理
    # --------------------------
    @classmethod
    def _save_token(cls, token: str):
        """安全存储令牌"""
        # 加密存储到文件
        encrypted = cls._encrypt_token(token)
        with open(cls.TOKEN_FILE, 'w') as f:
            f.write(encrypted)
        
        # 同时保存到环境变量
        os.environ[cls.TOKEN_ENV_VAR] = token
        logger.info("令牌已加密存储")

    @classmethod
    def _load_token(cls) -> str:
        """加载令牌（优先从加密文件）"""
        # 优先尝试从加密文件加载
        if os.path.exists(cls.TOKEN_FILE):
            try:
                with open(cls.TOKEN_FILE, 'r') as f:
                    encrypted = f.read()
                return cls._decrypt_token(encrypted)
            except Exception as e:
                logger.warning(f"令牌解密失败: {str(e)}，尝试从环境变量加载")
        
        # 其次尝试从环境变量加载
        return os.environ.get(cls.TOKEN_ENV_VAR)

    # --------------------------
    # 核心请求方法
    # --------------------------
    @classmethod
    def _make_request(cls, url, data, action_name):
        """统一请求处理"""
        try:
            # 记录请求日志（脱敏处理）
            safe_data = data.copy()
            if 'password' in safe_data:
                safe_data['password'] = '******'
            logger.info(f"请求[{action_name}]: {url} 参数: {json.dumps(safe_data, ensure_ascii=False)}")
            
            response = requests.post(
                url=url,
                headers=cls.headers,
                json=data,
                timeout=10
            )
            
            # 记录响应状态
            logger.info(f"响应状态[{action_name}]: {response.status_code}")
            
            response_data = response.json()
            
            # 记录业务响应（脱敏处理）
            log_response = {
                'code': response_data.get('code'),
                'message': response_data.get('msg'),
                'data': '...' if response_data.get('data') else None
            }
            logger.info(f"业务响应[{action_name}]: {json.dumps(log_response, ensure_ascii=False)}")
            
            return {
                'success': response_data.get('code') == 1,
                'code': response_data.get('code', -1),
                'message': response_data.get('msg', '操作失败'),
                'data': response_data.get('data')
            }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"网络错误[{action_name}]: {str(e)}")
            return {'success': False, 'code': -2, 'message': f"网络错误: {str(e)}", 'data': None}
        except Exception as e:
            logger.error(f"未知错误[{action_name}]: {str(e)}")
            return {'success': False, 'code': -3, 'message': f"未知错误: {str(e)}", 'data': None}

    # --------------------------
    # 初始化与认证
    # --------------------------
    @classmethod
    def initialize(cls):
        """初始化加载令牌"""
        cls.token = cls._load_token()
        if cls.token:
            cls.headers["token"] = cls.token
            logger.info("已加载本地令牌")

    @classmethod
    def login(cls, email, password, force=False):
        """
        用户登录
        :param force: 是否强制重新登录
        :return: 统一响应格式
        """
        # 优先使用现有令牌
        if not force and cls.token:
            return {'success': True, 'code': 1, 'message': '使用现有令牌', 'data': None}

        url = cls.base_url + "/user/email-login"
        data = {
            "email": email,
            "password": password,
            "deviceId": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
            "platform": "windows"
        }
        
        result = cls._make_request(url, data, "用户登录")
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
        """禁言操作"""
        allow_time = ["10", "1h", "6h", "12h", "0"]
        time_match = {
            "10": 600,
            "1h": 6000,
            "6h": 21600,
            "12h": 43200,
            "0": 0
        }
        if time not in allow_time:
            return {'success': False, 'code': -4, 'message': f"不支持的时间参数: {time}", 'data': None}
        seconds = time_match[time]
        url = "https://chat-go.jwzhd.com/v1/group/gag-member"
        data = {"groupId": group_id, "userId": user_id, "gag": seconds}
        action = "取消禁言" if time == "0" else "禁言"
        return cls._make_request(url, data, action)

    @classmethod
    def ban(cls, group_id, user_id, time):
        """禁言快捷方法"""
        return cls.ban_request(user_id, group_id, time)

    @classmethod
    def unban(cls, group_id, user_id):
        """解除禁言"""
        return cls.ban_request(user_id, group_id, "0")

    @classmethod
    def kick(cls, group_id, user_id):
        """移除成员"""
        url = cls.base_url + "/group/remove-member"
        data = {"groupId": group_id, "userId": user_id}
        return cls._make_request(url, data, "移除成员")

    # --------------------------
    # 标签管理
    # --------------------------
    class tag:
        """标签管理"""
        
        @classmethod
        def add(cls, group_id, tag_name, color="#2196F3", desc="", sort=0):
            """创建标签"""
            url = api.base_url + "/group-tag/create"
            data = {
                "groupId": group_id,
                "tag": tag_name,
                "color": color,
                "desc": desc,
                "sort": sort
            }
            return api._make_request(url, data, "创建标签")

        @classmethod
        def rm(cls, tag_id):
            """删除标签"""
            if not isinstance(tag_id, int):
                return {'success': False, 'code': -4, 'message': "标签ID必须为整数", 'data': None}
                
            url = api.base_url + "/group-tag/delete"
            data = {"id": tag_id}
            return api._make_request(url, data, "删除标签")

        @classmethod
        def list(cls, group_id):
            """获取标签列表"""
            url = api.base_url + "/group-tag/list"
            data = {"groupId": group_id}
            return api._make_request(url, data, "获取标签列表")

        @classmethod
        def edit(cls, tag_id, group_id, tag_name, color="#2196F3", desc="", sort=0):
            """编辑标签"""
            if not isinstance(tag_id, int):
                return {'success': False, 'code': -4, 'message': "标签ID必须为整数", 'data': None}
                
            url = api.base_url + "/group-tag/edit"
            data = {
                "id": tag_id,
                "groupId": group_id,
                "tag": tag_name,
                "color": color,
                "desc": desc,
                "sort": sort
            }
            return api._make_request(url, data, "编辑标签")

        @classmethod
        def set(cls, user_id, tag_id):
            """设置用户标签"""
            if not isinstance(tag_id, int):
                return {'success': False, 'code': -4, 'message': "标签ID必须为整数", 'data': None}
                
            url = api.base_url + "/group-tag/relate"
            data = {
                "userId": user_id,
                "tagGroupId": tag_id
            }
            return api._make_request(url, data, "设置用户标签")

    # --------------------------
    # 好友/群组操作
    # --------------------------
    class join:
        """加入操作"""
        
        @classmethod
        def join_requests(cls, type, id, msg):
            """通用加入请求"""
            if not isinstance(id, str):
                logger.error("ID必须为字符串")
            url = api.base_url + "/friend/apply"
            data = {
                "chatId": id,
                "chatType": type,
                "remark": msg
            }
            title = {1: "用户", 2: "群聊", 3: "机器人"}.get(type, "未知")
            return api._make_request(url, data, f"添加{title}")

        @classmethod
        def user(cls, id, msg=""):
            """添加好友"""
            return cls.join_requests(1, id, msg)

        @classmethod
        def group(cls, id, msg=""):
            """加入群聊"""
            return cls.join_requests(2, id, msg)

        @classmethod
        def bot(cls, id, msg=""):
            """添加机器人"""
            return cls.join_requests(3, id, msg)

    class leave:
        """离开操作"""
        
        @classmethod
        def leave_requests(cls, type, id):
            """通用离开请求"""
            if not isinstance(id, str):
                logger.error("ID必须为字符串")
            url = api.base_url + "/friend/delete-friend"
            data = {
                "chatId": id,
                "chatType": type,
            }
            title = {1: "用户", 2: "群聊", 3: "机器人"}.get(type, "未知")
            return api._make_request(url, data, f"删除{title}")

        @classmethod
        def user(cls, id):
            """删除好友"""
            return cls.leave_requests(1, id)

        @classmethod
        def group(cls, id):
            """退出群聊"""
            return cls.leave_requests(2, id)

        @classmethod
        def bot(cls, id):
            """移除机器人"""
            return cls.leave_requests(3, id)

# 初始化API模块
api.initialize()
