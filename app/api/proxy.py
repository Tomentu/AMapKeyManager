from flask import Blueprint, request, jsonify, Response, current_app
import requests
from app.services.key_manager import KeyManager
from app.core.logger import logger
import time

# 禁用SSL警告
requests.packages.urllib3.disable_warnings()

proxy_bp = Blueprint('proxy', __name__)

# 搜索服务的端点映射
SEARCH_ENDPOINTS = {
    'v3/place/text': 'keyword',      # 关键字搜索
    'v3/place/around': 'around',     # 周边搜索
    'v3/place/polygon': 'polygon'    # 多边形搜索
}

@proxy_bp.route('/<path:endpoint>', methods=['GET'])
def proxy_request(endpoint):
    """代理高德地图API请求"""
    try:
        # 检查是否是搜索服务请求
        search_type = SEARCH_ENDPOINTS.get(endpoint)
        
        if not search_type:
            return jsonify({
                'status': '0',
                'info': 'Invalid endpoint'
            }), 400

        # 获取可用的key
        key = KeyManager.get_available_key(search_type)
        if not key:
            return jsonify({
                'status': '0',
                'info': f'No available API key for {search_type} search',
                'info_code': '1008611'
            }), 503
        logger.info(f"Searching for {search_type} in {endpoint}, using key {key.masked_key},params: {request.args}")
        # 构建请求URL和参数
        url = f"{current_app.config['AMAP_BASE_URL']}/{endpoint}"
        params = dict(request.args)
        params['key'] = key.key
        
        # 构建代理设置
        proxies = None
        if current_app.config['PROXY_ENABLED']:
            proxies = {
                'http': current_app.config['HTTP_PROXY'],
                'https': current_app.config['HTTPS_PROXY']
            }
        
        # 发送请求
        response = requests.get(
            url,
            params=params,
            proxies=proxies,
            timeout=current_app.config['REQUEST_TIMEOUT'] / 1000,  # 转换为秒
            verify=False
        )
        # 处理响应
        if response.status_code == 200:
            result = response.json()
            
            # 检查是否是搜索服务请求
            search_type = SEARCH_ENDPOINTS.get(endpoint)
            if search_type and result.get('infocode') == '10000':
                # 增加对应搜索服务的使用次数
                logger.info(f"Incrementing usage for {search_type} search")
                KeyManager.increment_usage(key.id, search_type)
                return jsonify(result)
            else:
                info = result.get('info', '')
                if 'DAILY_QUERY_OVER_LIMIT' in info:
                    # 标记key对应服务超出限额并重试
                    if search_type:
                        KeyManager.mark_daily_limit(key.id, search_type)
                    return proxy_request(endpoint)
                elif 'INVALID_USER_KEY' in info:
                    # 禁用无效key并重试
                    KeyManager.disable_key(key, reason=info)
                    logger.warning(f"Key {key.masked_key} is invalid, reason: {info}")
                    return proxy_request(endpoint)
                return Response(
                    result,
                    status=400,
                    content_type=response.headers['content-type']
                )
        else:
            return Response(
                response.content,
                status=response.status_code,
                content_type=response.headers['content-type']
            )
            
    except Exception as e:
        logger.error(f"Proxy request failed: {str(e)}")
        return jsonify({
            'status': '0',
            'info': str(e),
            'info_code': '1008612'
        }), 500

