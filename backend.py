#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票信息查看器后端主程序
整合所有模块，启动Flask应用服务
"""

from flask import Flask
from flask_cors import CORS

# 导入自定义模块
from stock_data import create_stock_cache, STOCK_LIST_CACHE_FILE
from stock_api import setup_stock_routes

# Flask应用配置
FLASK_CONFIG = {
    'host': '0.0.0.0',
    'port': 5000,
    'debug': False
}

# CORS配置
CORS_CONFIG = {
    'origins': ['*'],
    'methods': ['GET', 'POST', 'OPTIONS'],
    'allow_headers': ['Content-Type'],
    'supports_credentials': False
}

# 创建Flask应用
app = Flask(__name__)

# 配置CORS - 允许所有来源的跨域请求
CORS(app, **CORS_CONFIG)

# 创建股票数据缓存实例
cache = create_stock_cache()

# 设置所有API路由
setup_stock_routes(app, cache)


def main():
    """主函数 - 启动Flask应用"""
    print("启动股票信息查看器后端服务...")
    print("股票列表缓存状态:", "有效" if cache.is_cache_valid(STOCK_LIST_CACHE_FILE) else "需要更新")
    
    # 启动Flask应用
    print(f"* 启动服务于 http://{FLASK_CONFIG['host']}:{FLASK_CONFIG['port']}")
    app.run(**FLASK_CONFIG)


if __name__ == '__main__':
    main()