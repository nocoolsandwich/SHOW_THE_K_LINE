#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tushare as ts
import pandas as pd
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import pickle
import time

app = Flask(__name__)

# 配置CORS - 允许所有来源的跨域请求
CORS(app, 
     origins=['*'],
     methods=['GET', 'POST', 'OPTIONS'],
     allow_headers=['Content-Type'],
     supports_credentials=False)

# Tushare API配置
TUSHARE_TOKEN = '2876ea85cb005fb5fa17c809a98174f2d5aae8b1f830110a5ead6211'
ts.set_token(TUSHARE_TOKEN)
pro = ts.pro_api()

# 缓存配置
CACHE_DIR = 'cache'
STOCK_LIST_CACHE_FILE = os.path.join(CACHE_DIR, 'stock_list.pkl')
CACHE_EXPIRY_HOURS = 24  # 缓存过期时间（小时）

# 确保缓存目录存在
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

class StockDataCache:
    def __init__(self):
        self.stock_list = None
        self.stock_dict = {}  # 股票代码映射字典
        self.load_stock_list_cache()
    
    def is_cache_valid(self, file_path):
        """检查缓存是否有效"""
        if not os.path.exists(file_path):
            return False
        
        # 检查文件修改时间
        file_time = os.path.getmtime(file_path)
        current_time = time.time()
        return (current_time - file_time) < (CACHE_EXPIRY_HOURS * 3600)
    
    def load_stock_list_cache(self):
        """加载股票列表缓存"""
        if self.is_cache_valid(STOCK_LIST_CACHE_FILE):
            try:
                with open(STOCK_LIST_CACHE_FILE, 'rb') as f:
                    cache_data = pickle.load(f)
                    self.stock_list = cache_data['stock_list']
                    self.stock_dict = cache_data['stock_dict']
                    print("股票列表缓存加载成功")
                    return True
            except Exception as e:
                print(f"缓存加载失败: {e}")
        return False
    
    def save_stock_list_cache(self):
        """保存股票列表缓存"""
        try:
            cache_data = {
                'stock_list': self.stock_list,
                'stock_dict': self.stock_dict
            }
            with open(STOCK_LIST_CACHE_FILE, 'wb') as f:
                pickle.dump(cache_data, f)
            print("股票列表缓存保存成功")
        except Exception as e:
            print(f"缓存保存失败: {e}")
    
    def update_stock_list(self):
        """更新股票列表"""
        try:
            print("正在获取股票列表...")
            # 获取A股股票列表
            stock_list = pro.stock_basic(exchange='', list_status='L',
                                       fields='ts_code,symbol,name,area,industry,market,list_date')
            
            if stock_list is not None and not stock_list.empty:
                self.stock_list = stock_list
                
                # 创建股票代码映射字典
                self.stock_dict = {}
                for _, row in stock_list.iterrows():
                    # 标准代码 -> 名称映射
                    self.stock_dict[row['ts_code']] = {
                        'name': row['name'],
                        'symbol': row['symbol'],
                        'market': row['market']
                    }
                    
                    # 6位代码 -> 标准代码映射
                    self.stock_dict[row['symbol']] = row['ts_code']
                    
                    # 名称 -> 标准代码映射
                    self.stock_dict[row['name']] = row['ts_code']
                
                self.save_stock_list_cache()
                print(f"股票列表更新成功，共{len(stock_list)}只股票")
                return True
            else:
                print("获取股票列表失败：返回数据为空")
                return False
                
        except Exception as e:
            print(f"获取股票列表失败: {e}")
            return False
    
    def get_stock_ts_code(self, stock_input):
        """根据输入获取标准的TS代码"""
        if not self.stock_list is None:
            if stock_input in self.stock_dict:
                ts_code = self.stock_dict[stock_input]
                if isinstance(ts_code, str) and ('.' in ts_code):
                    return ts_code
                elif isinstance(ts_code, dict):
                    return stock_input  # 已经是标准代码
        
        # 如果缓存中没找到，尝试直接构造
        if len(stock_input) == 6 and stock_input.isdigit():
            if stock_input.startswith(('60', '68', '90')):
                return f"{stock_input}.SH"
            elif stock_input.startswith(('00', '30', '20')):
                return f"{stock_input}.SZ"
        
        return None
    
    def get_all_stock_mappings(self):
        """获取所有股票的映射关系，用于前端精确识别"""
        if self.stock_list is None:
            return {}
        
        mappings = {}
        for _, row in self.stock_list.iterrows():
            # 添加股票代码映射
            mappings[row['symbol']] = {
                'ts_code': row['ts_code'],
                'name': row['name'],
                'symbol': row['symbol'],
                'market': row['market']
            }
            
            # 添加股票名称映射
            mappings[row['name']] = {
                'ts_code': row['ts_code'],
                'name': row['name'],
                'symbol': row['symbol'],
                'market': row['market']
            }
            
            # 添加完整ts_code映射
            mappings[row['ts_code']] = {
                'ts_code': row['ts_code'],
                'name': row['name'],
                'symbol': row['symbol'],
                'market': row['market']
            }
        
        return mappings

# 创建缓存实例
cache = StockDataCache()

# 如果缓存为空，立即更新
if cache.stock_list is None:
    cache.update_stock_list()

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
        days = request.args.get('days', 60, type=int)  # 默认获取60天数据（约两个月）
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days+30)).strftime('%Y%m%d')  # 多获取30天以应对节假日
        
        print(f"获取股票 {ts_code} 的日K线数据，时间范围: {start_date} - {end_date}")
        
        # 调用Tushare API获取日线数据
        daily_data = pro.daily(ts_code=ts_code, 
                              start_date=start_date, 
                              end_date=end_date)
        
        if daily_data is None or daily_data.empty:
            return jsonify({'error': '未获取到数据'}), 404
        
        # 按日期排序并取最近的数据
        daily_data = daily_data.sort_values('trade_date').tail(days)
        
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
        if len(chart_data) >= 2:
            current_price = chart_data[-1]['close']
            prev_price = chart_data[-2]['close']
            change_percent = ((current_price - prev_price) / prev_price * 100)
        else:
            current_price = chart_data[-1]['close'] if chart_data else 0
            change_percent = 0
        
        result = {
            'current_price': round(current_price, 2),
            'change_percent': round(change_percent, 2),
            'volume': chart_data[-1]['volume'] if chart_data else 0,
            'chart_data': chart_data
        }
        
        response = jsonify(result)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        print(f"获取日K线数据失败: {e}")
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
        
        # 搜索匹配的股票
        results = []
        query_lower = query.lower()
        
        for _, row in cache.stock_list.iterrows():
            if (query_lower in row['name'].lower() or 
                query in row['symbol'] or 
                query in row['ts_code']):
                results.append({
                    'ts_code': row['ts_code'],
                    'symbol': row['symbol'],
                    'name': row['name'],
                    'market': row['market']
                })
                
                if len(results) >= 10:  # 限制返回数量
                    break
        
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

@app.route('/api/intraday_data/<stock_code>', methods=['GET', 'OPTIONS'])
def get_intraday_data(stock_code):
    """获取股票分时数据"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        ts_code = cache.get_stock_ts_code(stock_code)
        if not ts_code:
            return jsonify({'error': f'未找到股票代码: {stock_code}'}), 404
        
        # 获取当前日期
        current_date = datetime.now().strftime('%Y%m%d')
        
        print(f"获取股票 {ts_code} 的分时数据，日期: {current_date}")
        
        # 调用Tushare API获取分时数据
        intraday_data = pro.rt_k(ts_code=ts_code)
        
        if intraday_data is None or intraday_data.empty:
            return jsonify({'error': '未获取到数据'}), 404
        
        # 打印返回的数据结构，用于调试
        print("分时数据列：", intraday_data.columns.tolist())
        print("分时数据样例：", intraday_data.iloc[0].to_dict())
        
        # 转换数据格式
        chart_data = []
        # 生成当前时间序列
        current_time = datetime.now()
        start_time = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
        times = []
        
        # 创建从9:30到15:00的时间点，排除11:30-13:00的休市时间
        current = start_time
        while current <= current_time.replace(hour=15, minute=0, second=0):
            if not (current.hour == 11 and current.minute >= 30) and not (current.hour == 12):
                times.append(current.strftime("%H:%M"))
            current = current + timedelta(minutes=1)
        
        # 为每个时间点生成一个数据点
        for i, time_str in enumerate(times):
            # 模拟价格数据
            index = min(i, len(intraday_data) - 1)  # 避免索引超出范围
            row = intraday_data.iloc[index]
            
            chart_data.append({
                'time': time_str,
                'price': float(row['close']),
                'volume': int(row['vol']) if pd.notna(row['vol']) else 0,
                'amount': int(row['amount']) if pd.notna(row['amount']) else 0
            })
        
        # 计算当前价格和涨跌幅
        if len(chart_data) >= 2:
            current_price = chart_data[-1]['price']
            prev_close = float(intraday_data['pre_close'].iloc[0]) if 'pre_close' in intraday_data.columns else chart_data[0]['price']
            change_percent = ((current_price - prev_close) / prev_close * 100)
        else:
            current_price = chart_data[-1]['price'] if chart_data else 0
            change_percent = 0
        
        result = {
            'current_price': round(current_price, 2),
            'change_percent': round(change_percent, 2),
            'volume': chart_data[-1]['volume'] if chart_data else 0,
            'chart_data': chart_data
        }
        
        response = jsonify(result)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
        
    except Exception as e:
        print(f"获取分时数据失败: {e}")
        import traceback
        traceback.print_exc()
        error_response = jsonify({'error': str(e)})
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

if __name__ == '__main__':
    print("启动Tushare股票数据API服务...")
    cache.update_stock_list()
    
    # 允许从外部设备访问，0.0.0.0表示监听所有网络接口
    app.run(host='0.0.0.0', port=5000, debug=True) 