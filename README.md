# AMapKeyManager (AMKM)

高德地图 API Key 管理与代理服务

## 功能特点

- API Key 池管理
- 自动负载均衡
- 使用量统计
- 代理请求转发
- 每日使用量重置
- 支持多种搜索服务
  - 关键字搜索
  - 周边搜索
  - 多边形搜索

## 快速开始

1. 克隆项目
''' bash
git clone https://github.com/yourusername/AMapKeyManager.git
cd AMapKeyManager

2 docker 
''' bash
docker build -t amkm .
'''

3 运行容器
''' bash
docker run -d \
  --name amkm \
  -p 5001:5000 \
  -v $(pwd)/app:/app/app \
  -v $(pwd)/results:/app/results \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  --restart unless-stopped \
  amkm
'''

## 2. 环境配置

### 2.1 基础配置
1. 复制示例配置文件：
''' bash
cp .env.example .env
'''

2. 编辑 .env 文件，设置必要的配置项：

### 2.2 必需配置项

#### 数据库配置
```bash
DB_USER=your_username      # 数据库用户名
DB_PASS=your_password     # 数据库密码
DB_HOST=your_host         # 数据库地址
DB_PORT=3306             # 数据库端口
DB_NAME=amkm            # 数据库名称
```

#### API配置
```bash
AMAP_BASE_URL=https://restapi.amap.com  # 高德地图API地址
REQUEST_TIMEOUT=180000                   # 请求超时时间(毫秒)
```

#### 管理员配置
```bash
ADMIN_USERNAME=admin          # 管理后台用户名
ADMIN_PASSWORD=your_password  # 管理后台密码
```

### 2.3 可选配置项

#### 代理设置

## 使用说明

### API 端点

- 关键字搜索: `/v3/place/text`
- 周边搜索: `/v3/place/around`
- 多边形搜索: `/v3/place/polygon`

### 管理界面

访问 `/admin/` 进行 API Key 管理
