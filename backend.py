#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票信息查看器后端主程序
整合所有模块，启动Flask应用服务
"""

from flask import Flask, send_from_directory
from flask_cors import CORS
import os

# 导入自定义模块
from stock_data import create_stock_cache, STOCK_LIST_CACHE_FILE
from stock_api import setup_stock_routes

# Flask应用配置
FLASK_CONFIG = {
    'host': '0.0.0.0',
    'port': 5002,
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

# 添加前端静态文件路由
@app.route('/')
def index():
    """主页面"""
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    """静态文件服务"""
    return send_from_directory('.', filename)


def main():
    """主函数 - 启动Flask应用"""
    print("股票信息查看器启动中...")
    print("股票列表缓存状态:", "有效" if cache.is_cache_valid(STOCK_LIST_CACHE_FILE) else "需要更新")
    print("📡 数据源: EasyQuotation (实时数据)")
    print("")
    print("前端页面: http://127.0.0.1:5001")
    print("API接口: http://127.0.0.1:5001/api")
    print("")
    print("一体化服务启动 - 无需启动多个服务！")
    print("=" * 50)
    
    # 启动Flask应用
    app.run(**FLASK_CONFIG)


if __name__ == '__main__':
    main()