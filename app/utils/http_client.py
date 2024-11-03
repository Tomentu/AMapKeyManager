import http.client
import json
import ssl
import socket
from typing import Dict, Optional, Tuple, Any, Union
from urllib.parse import urlencode
from app.core.logger import logger
import time

class ProxyHTTPSConnection(http.client.HTTPSConnection):
    """支持代理的HTTPS连接"""
    
    def __init__(self, host, port=None, timeout=None, context=None):
        super().__init__(host, port, timeout=timeout, context=context)
        # 保存原始目标信息
        self._real_host = host
        self._real_port = port
    
    def connect(self):
        """建立代理连接"""
        # 创建到代理服务器的socket
        sock = socket.create_connection((self._real_host, self._real_port), self.timeout)
        
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        
        # 包装SSL
        self.sock = self._context.wrap_socket(sock, server_hostname=self._real_host)

class HttpClient:
    """HTTP客户端工具类"""
    
    def __init__(
        self, 
        timeout: int = 5,
        use_ssl: bool = True,
        verify_ssl: bool = False
    ):
        self.timeout = timeout
        self.use_ssl = use_ssl
        self.verify_ssl = verify_ssl
        
        if self.use_ssl:
            self.ssl_context = ssl._create_unverified_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        
    def request(
        self,
        method: str,
        ip: str,
        host: str,
        path: str,
        port: int = 443,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        body: Any = None,
        parse_json: bool = True,
        proxy: Optional[Dict[str, Union[str, int]]] = None  # 代理配置
    ) -> Tuple[Union[Dict, bytes], float]:
        try:
            url = path
            if params:
                url = f"{path}?{urlencode(params)}"
            
            default_headers = {
                'Host': host,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/json',
                'Connection': 'keep-alive'
            }
            if headers:
                default_headers.update(headers)
            
            # 创建连接
            if self.use_ssl:
                if proxy:
                    # 使用代理的HTTPS连接
                    conn = ProxyHTTPSConnection(
                        proxy['host'],
                        proxy['port'],
                        timeout=self.timeout,
                        context=self.ssl_context
                    )
                    # 设置实际目标
                    conn._tunnel_host = ip
                    conn._tunnel_port = port
                else:
                    # 直接HTTPS连接
                    conn = http.client.HTTPSConnection(
                        ip,
                        port,
                        timeout=self.timeout,
                        context=self.ssl_context
                    )
            else:
                if proxy:
                    conn = http.client.HTTPConnection(
                        proxy['host'],
                        proxy['port'],
                        timeout=self.timeout
                    )
                else:
                    conn = http.client.HTTPConnection(
                        ip,
                        port,
                        timeout=self.timeout
                    )
            
            logger.debug(f"Request: {method} {'https' if self.use_ssl else 'http'}://{ip}:{port}{url}")
            logger.debug(f"Host Header: {host}")
            logger.debug(f"Headers: {default_headers}")
            if proxy:
                logger.debug(f"Using proxy: {proxy['host']}:{proxy['port']}")
            
            start_time = time.time()
            conn.request(method, url, body, default_headers)
            
            response = conn.getresponse()
            response_data = response.read()
            response_time = time.time() - start_time
            
            logger.debug(f"Response Status: {response.status}")
            logger.debug(f"Response Time: {response_time:.3f}s")
            
            conn.close()
            
            if parse_json:
                try:
                    result = json.loads(response_data.decode('utf-8'))
                    return result, response_time
                except json.JSONDecodeError:
                    return response_data, response_time
            else:
                return response_data, response_time
            
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            raise
          