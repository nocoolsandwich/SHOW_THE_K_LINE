#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票API路由模块
包含所有股票相关的Flask路由处理函数
"""

import pandas as pd
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from stock_data import API_CONFIG, STOCK_LIST_CACHE_FILE


def setup_stock_routes(app, cache):
    """设置所有股票相关的API路由"""
    
    # 添加请求前的日志记录
    @app.before_request
    def log_request_info():
        print(f"收到请求: {request.method} {request.url}")
        print(f"来源: {request.environ.get('HTTP_ORIGIN', 'N/A')}")
        print(f"User-Agent: {request.environ.get('HTTP_USER_AGENT', 'N/A')}")

    @app.route('/api/stock_list', methods=['GET', 'OPTIONS'])
    def get_stock_list():
        """获取所有股票列表用于前端识别"""
        if request.method == 'OPTIONS':
            # 处理预检请求
            return '', 200
            
        try:
            print("处理股票列表请求...")
            
            if cache.stock_list is None:
                print("股票列表未加载")
                return jsonify({'error': '股票列表未加载'}), 500
            
            # 获取所有股票映射
            mappings = cache.get_all_stock_mappings()
            
            # 返回股票代码和名称列表
            stock_codes = []
            stock_names = []
            
            for _, row in cache.stock_list.iterrows():
                stock_codes.append({
                    'code': row['symbol'],
                    'ts_code': row['ts_code'],
                    'name': row['name'],
                    'market': row['market']
                })
                stock_names.append({
                    'name': row['name'],
                    'ts_code': row['ts_code'],
                    'symbol': row['symbol'],
                    'market': row['market']
                })
            
            result = {
                'codes': stock_codes,
                'names': stock_names,
                'mappings': mappings,
                'total': len(cache.stock_list)
            }
            
            print(f"返回股票数据，共 {len(cache.stock_list)} 只股票")
            
            response = jsonify(result)
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
            response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
            
            return response
            
        except Exception as e:
            print(f"股票列表请求处理失败: {e}")
            error_response = jsonify({'error': str(e)})
            error_response.headers.add('Access-Control-Allow-Origin', '*')
            return error_response, 500

    @app.route('/api/stock_info/<stock_code>', methods=['GET', 'OPTIONS'])
    def get_stock_info(stock_code):
        """获取股票基本信息"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            ts_code = cache.get_stock_ts_code(stock_code)
            if not ts_code:
                return jsonify({'error': f'未找到股票代码: {stock_code}'}), 404
            
            # 从缓存中获取股票信息
            if ts_code in cache.stock_dict:
                stock_info = cache.stock_dict[ts_code]
                response = jsonify({
                    'ts_code': ts_code,
                    'name': stock_info['name'],
                    'symbol': stock_info['symbol'],
                    'market': stock_info['market']
                })
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response
            
            return jsonify({'error': '股票信息不存在'}), 404
            
        except Exception as e:
            error_response = jsonify({'error': str(e)})
            error_response.headers.add('Access-Control-Allow-Origin', '*')
            return error_response, 500

    @app.route('/api/daily_data/<stock_code>', methods=['GET', 'OPTIONS'])
    def get_daily_data(stock_code):
        """获取股票日K线数据"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            ts_code = cache.get_stock_ts_code(stock_code)
            if not ts_code:
                return jsonify({'error': f'未找到股票代码: {stock_code}'}), 404
            
            # 获取参数
            days = request.args.get('days', API_CONFIG['default_days'], type=int)  # 默认获取60天数据
            
            # 获取日K线数据
            daily_data = cache.get_daily_data(ts_code, days)
            
            if daily_data is None or daily_data.empty:
                return jsonify({'error': '未获取到历史数据'}), 404
            
            # 转换数据格式
            chart_data = []
            for _, row in daily_data.iterrows():
                chart_data.append({
                    'date': f"{row['trade_date'][:4]}-{row['trade_date'][4:6]}-{row['trade_date'][6:]}",
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': int(row['vol']) if pd.notna(row['vol']) else 0
                })
            
            # 计算当前价格和涨跌幅
            if len(chart_data) >= 1:
                current_price = chart_data[-1]['close']
                # 使用当日的pre_close计算涨跌幅
                pre_close = float(daily_data.iloc[-1]['pre_close'])
                change_percent = ((current_price - pre_close) / pre_close * 100)
            else:
                current_price = 0
                change_percent = 0
            
            # 判断数据类型
            current_time = datetime.now().time()
            is_trading_time = cache.is_trading_time(current_time)
            
            result = {
                'current_price': round(current_price, 2),
                'change_percent': round(change_percent, 2),
                'volume': chart_data[-1]['volume'] if chart_data else 0,
                'chart_data': chart_data,
                'data_type': 'realtime' if is_trading_time else 'historical'
            }
            
            response = jsonify(result)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
            
        except Exception as e:
            print(f"获取日K线数据失败: {e}")
            import traceback
            traceback.print_exc()
            error_response = jsonify({'error': str(e)})
            error_response.headers.add('Access-Control-Allow-Origin', '*')
            return error_response, 500

    @app.route('/api/search_stocks/<query>', methods=['GET', 'OPTIONS'])
    def search_stocks(query):
        """搜索股票"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            if cache.stock_list is None:
                return jsonify({'error': '股票列表未加载'}), 500
            
            # 使用缓存的搜索功能
            results = cache.search_stocks(query, API_CONFIG['search_limit'])
            
            response = jsonify(results)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
            
        except Exception as e:
            error_response = jsonify({'error': str(e)})
            error_response.headers.add('Access-Control-Allow-Origin', '*')
            return error_response, 500

    @app.route('/api/update_stock_list', methods=['POST', 'OPTIONS'])
    def update_stock_list():
        """手动更新股票列表"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            success = cache.update_stock_list()
            if success:
                response = jsonify({'message': '股票列表更新成功'})
                status_code = 200
            else:
                response = jsonify({'error': '股票列表更新失败'})
                status_code = 500

            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, status_code
        except Exception as e:
            error_response = jsonify({'error': str(e)})
            error_response.headers.add('Access-Control-Allow-Origin', '*')
            return error_response, 500

    @app.route('/api/health', methods=['GET', 'OPTIONS'])
    def health_check():
        """健康检查接口"""
        if request.method == 'OPTIONS':
            return '', 200
            
        result = {
            'status': 'ok',
            'stock_count': len(cache.stock_list) if cache.stock_list is not None else 0,
            'cache_valid': cache.is_cache_valid(STOCK_LIST_CACHE_FILE)
        }
        
        response = jsonify(result)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        
        return response

    @app.route('/api/latest_quote/<stock_code>', methods=['GET', 'OPTIONS'])
    def get_latest_quote(stock_code):
        """获取股票最新行情数据"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            print(f"获取股票 {stock_code} 的最新行情...")
            
            # 获取标准TS代码
            ts_code = cache.get_stock_ts_code(stock_code)
            if not ts_code:
                return jsonify({'error': '无效的股票代码'}), 400
                
            # 从缓存中获取行情数据
            quote = cache.get_stock_quote(ts_code)
            if not quote:
                return jsonify({'error': '未找到股票数据'}), 404
                
            response = jsonify(quote)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
            
        except Exception as e:
            print(f"获取最新行情失败: {e}")
            error_response = jsonify({'error': str(e)})
            error_response.headers.add('Access-Control-Allow-Origin', '*')
            return error_response, 500

    # 注意：分时数据API已从原代码中移除，因为它使用了不太稳定的实时数据接口
    # 如需要分时数据，建议使用其他更稳定的数据源
    
    print("股票API路由设置完成")
