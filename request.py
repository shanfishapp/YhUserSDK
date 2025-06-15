import asyncio
import aiohttp
from typing import Optional, Dict, Any, Union

class AsyncHTTPError(Exception):
    """自定义HTTP异常类"""
    def __init__(self, status_code: int, message: str, response_text: str):
        self.status_code = status_code
        self.message = message
        self.response_text = response_text
        super().__init__(f"{status_code} - {message}: {response_text}")

class AsyncHTTPClient:
    """异步HTTP客户端工具类，设计风格类似requests库"""
    
    def __init__(
        self,
        base_url: str = "",
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        raise_for_status: bool = True,
        cookies: Optional[Dict[str, str]] = None,
    ):
        """
        初始化异步HTTP客户端
        
        :param base_url: 基础URL，所有请求会基于此URL
        :param headers: 默认请求头
        :param timeout: 默认超时时间(秒)
        :param raise_for_status: 是否在非200状态码时抛出异常
        :param cookies: 默认cookies
        """
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.raise_for_status = raise_for_status
        self.cookies = cookies
        self.session = None

    async def __aenter__(self):
        """支持异步上下文管理"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """支持异步上下文管理"""
        await self.close()

    async def _ensure_session(self):
        """确保session已创建"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout,
                cookies=self.cookies,
            )

    async def request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        allow_redirects: bool = True,
        **kwargs
    ) -> Union[Dict[str, Any], str]:
        """
        发送HTTP请求
        
        :param method: HTTP方法 (GET, POST, PUT, DELETE等)
        :param url: 请求URL
        :param params: URL查询参数
        :param data: 请求体数据 (表单数据)
        :param json: JSON请求体数据
        :param headers: 请求头
        :param cookies: cookies
        :param allow_redirects: 是否允许重定向
        :param kwargs: 其他aiohttp.ClientSession.request参数
        :return: 响应数据 (自动解析JSON或返回文本)
        """
        await self._ensure_session()
        
        # 合并headers和cookies
        final_headers = {**self.headers, **(headers or {})}
        final_cookies = {**self.cookies, **(cookies or {})} if self.cookies or cookies else None
        
        async with self.session.request(
            method=method,
            url=url,
            params=params,
            data=data,
            json=json,
            headers=final_headers,
            cookies=final_cookies,
            allow_redirects=allow_redirects,
            **kwargs
        ) as response:
            return await self._handle_response(response)

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        allow_redirects: bool = True,
        **kwargs
    ) -> Union[Dict[str, Any], str]:
        """发送GET请求"""
        return await self.request(
            "GET", url,
            params=params,
            headers=headers,
            cookies=cookies,
            allow_redirects=allow_redirects,
            **kwargs
        )

    async def post(
        self,
        url: str,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        allow_redirects: bool = True,
        **kwargs
    ) -> Union[Dict[str, Any], str]:
        """发送POST请求"""
        return await self.request(
            "POST", url,
            data=data,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            allow_redirects=allow_redirects,
            **kwargs
        )

    async def put(
        self,
        url: str,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        allow_redirects: bool = True,
        **kwargs
    ) -> Union[Dict[str, Any], str]:
        """发送PUT请求"""
        return await self.request(
            "PUT", url,
            data=data,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            allow_redirects=allow_redirects,
            **kwargs
        )

    async def delete(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        allow_redirects: bool = True,
        **kwargs
    ) -> Union[Dict[str, Any], str]:
        """发送DELETE请求"""
        return await self.request(
            "DELETE", url,
            params=params,
            headers=headers,
            cookies=cookies,
            allow_redirects=allow_redirects,
            **kwargs
        )

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Union[Dict[str, Any], str]:
        """处理响应"""
        try:
            if response.content_type == "application/json":
                result = await response.json()
            else:
                result = await response.text()

            if self.raise_for_status and response.status >= 400:
                error_text = await response.text() if not isinstance(result, str) else result
                raise AsyncHTTPError(
                    status_code=response.status,
                    message=f"HTTP请求失败",
                    response_text=error_text
                )
                
            return result
        except Exception as e:
            if isinstance(e, AsyncHTTPError):
                raise
            raise AsyncHTTPError(
                status_code=response.status,
                message=f"处理响应时出错: {str(e)}",
                response_text=""
            )

    async def close(self):
        """关闭ClientSession"""
        if self.session and not self.session.closed:
            await self.session.close()

    @classmethod
    async def create(
        cls,
        base_url: str = "",
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        raise_for_status: bool = True,
        cookies: Optional[Dict[str, str]] = None,
    ) -> "AsyncHTTPClient":
        """工厂方法创建实例并初始化session"""
        client = cls(
            base_url=base_url,
            headers=headers,
            timeout=timeout,
            raise_for_status=raise_for_status,
            cookies=cookies,
        )
        await client._ensure_session()
        return client
