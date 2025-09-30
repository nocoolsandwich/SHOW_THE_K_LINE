#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票数据处理核心模块
包含股票数据缓存、获取、处理等核心功能
"""

import pandas as pd
import pickle
import os
import time
import easyquotation
from datetime import datetime, timedelta
from functools import lru_cache

# =============================================================================
# 配置常量
# =============================================================================
# 缓存配置
CACHE_DIR = 'cache'
STOCK_LIST_CACHE_FILE = os.path.join(CACHE_DIR, 'stock_list.pkl')
CACHE_EXPIRY_HOURS = 24  # 缓存过期时间（小时）

# 交易时间配置
TRADING_TIME_CONFIG = {
    'morning_start': '09:30',
    'morning_end': '11:30', 
    'afternoon_start': '13:00',
    'afternoon_end': '15:00',
    'market_close': '15:00'
}

# API配置
API_CONFIG = {
    'default_days': 60,  # 默认K线数据天数
    'search_limit': 10,  # 搜索结果限制
    'extra_days': 30     # 额外获取天数以应对节假日
}


# =============================================================================
# 目录初始化
# =============================================================================
def init_cache_directory():
    """初始化缓存目录"""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
        print(f"创建缓存目录: {CACHE_DIR}")

# 初始化目录
init_cache_directory()

# =============================================================================
# LRU缓存函数 - 日K数据
# =============================================================================
@lru_cache(maxsize=200)  # 缓存200只股票的数据
def _fetch_daily_kline_data(ts_code, days=60):
    """获取股票日K线数据的核心函数 - 带LRU缓存"""
    import requests
    import json
    
    print(f"[缓存未命中] 从新浪财经获取 {ts_code} 的真实历史K线数据...")
    
    # 将ts_code转换为新浪财经使用的格式
    market_code = ts_code.split('.')
    if len(market_code) != 2:
        print(f"无效的股票代码格式: {ts_code}")
        return None
        
    code = market_code[0]
    market = market_code[1].lower()
    sina_code = f"{market}{code}"  # 例如: sz000001, sh600519
    
    try:
        # 新浪财经历史K线API
        url = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
        params = {
            'symbol': sina_code,
            'scale': '240',  # 日线
            'ma': 'no',
            'datalen': str(days)  # 获取指定天数
        }
        
        print(f"请求新浪财经API: {sina_code}")
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"新浪财经API请求失败，状态码: {response.status_code}")
            return None
        
        content = response.text
        if not content.strip():
            print("新浪财经API返回空数据")
            return None
        
        # 解析JSON数据
        try:
            kline_data = json.loads(content)
            if not kline_data:
                print("新浪财经API返回空的K线数据")
                return None
            
            print(f"从新浪财经获取到 {len(kline_data)} 条真实K线数据")
            
            # 转换为标准格式
            daily_data_list = []
            for record in kline_data:
                try:
                    # 新浪财经返回格式: {"day":"2025-07-08","open":"12.750","high":"12.840","low":"12.650","close":"12.690","volume":"109098597"}
                    trade_date = record['day'].replace('-', '')  # 转换为YYYYMMDD格式
                    
                    daily_data_list.append({
                        'ts_code': ts_code,
                        'trade_date': trade_date,
                        'open': float(record['open']),
                        'high': float(record['high']),
                        'low': float(record['low']),
                        'close': float(record['close']),
                        'pre_close': 0.0,  # 新浪数据中没有昨收价，后续计算
                        'vol': int(float(record['volume'])),
                        'amount': 0  # 新浪数据中没有成交额
                    })
                except (KeyError, ValueError) as e:
                    print(f"解析K线记录失败: {e}, 记录: {record}")
                    continue
            
            if not daily_data_list:
                print("没有有效的K线数据")
                return None
            
            # 计算昨收价 (pre_close)
            for i in range(len(daily_data_list)):
                if i > 0:
                    daily_data_list[i]['pre_close'] = daily_data_list[i-1]['close']
                else:
                    # 第一条记录的昨收价设为开盘价
                    daily_data_list[i]['pre_close'] = daily_data_list[i]['open']
            
            # 按日期排序 (确保时间顺序正确)
            daily_data_list.sort(key=lambda x: x['trade_date'])
            
            # 返回字典列表，避免DataFrame的序列化问题
            return daily_data_list
            
        except json.JSONDecodeError as e:
            print(f"新浪财经API返回数据解析失败: {e}")
            print(f"返回内容片段: {content[:200]}...")
            return None
            
    except Exception as e:
        print(f"获取 {ts_code} 的新浪财经数据时出错: {e}")
        return None

# 创建easyquotation实例，用于获取实时行情
try:
    quotation = easyquotation.use('sina')
    print("easyquotation初始化成功")
except Exception as e:
    print(f"easyquotation初始化失败: {e}")
    quotation = None


class StockDataCache:
    """股票数据缓存管理类"""
    
    def __init__(self):
        self.stock_list = None
        self.stock_dict = {}  # 股票代码映射字典
        self.daily_quotes = None  # 每日行情数据缓存
        self.last_quote_update = None  # 最后更新行情的时间
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
        """更新股票列表 - 从easyquotation获取全量股票数据"""
        try:
            print("正在从easyquotation获取全量股票列表...")
            print("这可能需要几分钟时间，请耐心等待...")
            
            if not quotation:
                raise RuntimeError("easyquotation未初始化，无法获取股票数据")
            
            # 获取全量股票数据
            all_stocks = []
            
            try:
                # 从easyquotation获取市场快照，这里包含了大量的股票
                print("正在获取市场快照数据...")
                market_data = quotation.market_snapshot(prefix=True)
                
                if market_data:
                    print(f"获取到 {len(market_data)} 个股票的市场数据")
                    
                    # 处理所有股票数据
                    processed_count = 0
                    for code, data in market_data.items():
                        try:
                            if code.startswith(('sh6', 'sz0', 'sz3', 'sz2')):  # A股代码格式
                                symbol = code[2:]  # 去除sh/sz前缀
                                ts_code = f"{symbol}.{'SH' if code.startswith('sh') else 'SZ'}"
                                name = data.get('name', f'股票{symbol}')
                                
                                # 判断市场
                                if code.startswith('sh'):
                                    market = '沪A'
                                else:
                                    market = '深A'
                                
                                # 根据代码判断板块
                                industry = '未分类'
                                if symbol.startswith('60'):
                                    industry = '主板'
                                elif symbol.startswith('688'):
                                    industry = '科创板'
                                elif symbol.startswith('00'):
                                    industry = '主板'
                                elif symbol.startswith('002'):
                                    industry = '中小板'
                                elif symbol.startswith('30'):
                                    industry = '创业板'
                                
                                stock_info = {
                                    'ts_code': ts_code,
                                    'symbol': symbol,
                                    'name': name,
                                    'market': market,
                                    'area': '未知',
                                    'industry': industry
                                }
                                
                                # 检查是否已存在（避免重复）
                                exists = False
                                for existing_stock in all_stocks:
                                    if existing_stock['symbol'] == symbol:
                                        exists = True
                                        break
                                
                                if not exists:
                                    all_stocks.append(stock_info)
                                    processed_count += 1
                                    
                                    # 每处理100只股票显示一次进度
                                    if processed_count % 100 == 0:
                                        print(f"已处理 {processed_count} 只股票...")
                            
                        except Exception as e:
                            # 忽略单个股票处理错误
                            continue
                    
                    print(f"从easyquotation成功获取 {processed_count} 只新股票")
                else:
                    raise RuntimeError("未获取到市场数据")
            
            except Exception as e:
                print(f"从easyquotation获取数据失败: {e}")
                raise
            
            # 创建DataFrame
            self.stock_list = pd.DataFrame(all_stocks)
            
            # 创建股票代码映射字典
            self.stock_dict = {}
            for _, row in self.stock_list.iterrows():
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
            
            # 保存到缓存
            self.save_stock_list_cache()
            print(f"股票列表更新成功！共获取 {len(self.stock_list)} 只股票")
            return True
                
        except Exception as e:
            print(f"股票列表更新失败: {e}")
            import traceback
            traceback.print_exc()
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
    
    def is_trading_time(self, current_time=None):
        """判断是否在交易时间内"""
        if current_time is None:
            current_time = datetime.now().time()
        
        morning_start = datetime.strptime(TRADING_TIME_CONFIG['morning_start'], '%H:%M').time()
        morning_end = datetime.strptime(TRADING_TIME_CONFIG['morning_end'], '%H:%M').time()
        afternoon_start = datetime.strptime(TRADING_TIME_CONFIG['afternoon_start'], '%H:%M').time()
        afternoon_end = datetime.strptime(TRADING_TIME_CONFIG['afternoon_end'], '%H:%M').time()
        
        return ((current_time >= morning_start and current_time <= morning_end) or
                (current_time >= afternoon_start and current_time <= afternoon_end))
    
    def update_daily_quotes(self):
        """更新每日行情数据 - 使用easyquotation实时数据"""
        try:
            # 获取当前日期和时间
            current_date = datetime.now()
            
            # 如果已经有缓存且是今天的数据，直接返回
            if (self.daily_quotes is not None and 
                self.last_quote_update is not None and 
                self.last_quote_update.date() == current_date.date()):
                print("使用缓存的行情数据")
                return True
            
            print("正在从easyquotation获取实时行情数据...")
            
            if not quotation:
                print("easyquotation未初始化，无法获取行情数据")
                return False
            
            try:
                # 获取实时市场快照
                market_data = quotation.market_snapshot(prefix=True)
                
                if not market_data:
                    print("未获取到市场数据")
                    return False
                
                # 构建行情数据字典
                self.daily_quotes = {}
                
                for code, data in market_data.items():
                    try:
                        # 转换代码格式
                        if code.startswith(('sh6', 'sz0', 'sz3')):  # A股代码格式
                            symbol = code[2:]  # 去除sh/sz前缀
                            ts_code = f"{symbol}.{'SH' if code.startswith('sh') else 'SZ'}"
                            
                            # 构建标准化的行情数据
                            current_price = float(data.get('now', 0))
                            pre_close = float(data.get('close', current_price))
                            change = round(current_price - pre_close, 2)
                            pct_chg = round((change / pre_close * 100), 2) if pre_close > 0 else 0
                            
                            self.daily_quotes[ts_code] = {
                                'trade_date': current_date.strftime('%Y%m%d'),
                                'close': current_price,
                                'pre_close': pre_close,
                                'change': change,
                                'pct_chg': pct_chg,
                                'open': float(data.get('open', current_price)),
                                'high': float(data.get('high', current_price)),
                                'low': float(data.get('low', current_price)),
                                'vol': float(data.get('turnover', 0)),
                                'amount': float(data.get('volume', 0))
                            }
                    except Exception as e:
                        print(f"处理股票 {code} 数据时出错: {e}")
                        continue
                
                self.last_quote_update = current_date
                print(f"成功获取 {len(self.daily_quotes)} 只股票的实时行情数据")
                
                # 显示一些样本数据
                if self.daily_quotes:
                    sample_stock = next(iter(self.daily_quotes))
                    print(f"样本数据 ({sample_stock}):", self.daily_quotes[sample_stock])
                
                return True
                
            except Exception as e:
                print(f"从easyquotation获取数据失败: {e}")
                return False
                
        except Exception as e:
            print(f"更新行情数据失败: {e}")
            import traceback
            print("错误详情:", traceback.format_exc())
            return False
    
    def get_stock_quote(self, ts_code):
        """获取股票行情数据，包含多期间涨跌幅"""
        try:
            # 获取当前时间，判断是否在交易时间内
            current_date = datetime.now()
            current_time = current_date.time()
            is_trading_time = self.is_trading_time(current_time)
            
            # 首先获取历史K线数据来计算多期间涨跌幅
            historical_data = self.get_daily_data(ts_code, days=15)  # 获取15天数据确保有足够的交易日
            
            current_price = None
            pre_close = None
            
            # 如果是交易时间，尝试获取实时数据
            if is_trading_time:
                try:
                    print(f"获取 {ts_code} 的实时行情...")
                    
                    # 将ts_code转换为easyquotation使用的格式
                    market_code = ts_code.split('.')
                    if len(market_code) == 2:
                        code = market_code[0]
                        market = market_code[1].lower()
                        easy_code = f"{market}{code}"
                        
                        # 获取实时行情
                        market_data = quotation.market_snapshot(prefix=True)
                        
                        if easy_code in market_data:
                            real_time_quote = market_data[easy_code]
                            print(f"获取到实时行情: {real_time_quote}")
                            
                            # 使用实时价格
                            current_price = float(real_time_quote['now'])
                            pre_close = float(real_time_quote['close'])
                            
                except Exception as e:
                    print(f"获取实时行情失败: {e}，将使用历史数据")
            
            # 如果没有实时数据，使用最新历史数据
            if current_price is None and historical_data is not None and len(historical_data) > 0:
                latest_data = historical_data.iloc[-1]
                current_price = float(latest_data['close'])
                pre_close = float(latest_data['pre_close'])
            
            if current_price is None:
                print(f"无法获取 {ts_code} 的价格数据")
                return None
            
            # 计算当日涨跌幅
            change = round(current_price - pre_close, 2)
            pct_chg = round((change / pre_close * 100), 2)
            
            # 计算多期间涨跌幅
            multi_period_changes = {}
            if historical_data is not None and len(historical_data) > 0:
                # 按日期排序，确保顺序正确
                historical_data = historical_data.sort_values('trade_date').reset_index(drop=True)
                
                # 计算3日、5日、10日涨跌幅
                periods = [3, 5, 10]
                for period in periods:
                    if len(historical_data) >= period:
                        # 获取N天前的收盘价（倒数第N个交易日）
                        n_days_ago_price = float(historical_data.iloc[-(period+1)]['close']) if len(historical_data) > period else float(historical_data.iloc[0]['close'])
                        period_change_pct = round(((current_price - n_days_ago_price) / n_days_ago_price * 100), 2)
                        multi_period_changes[f'{period}d'] = period_change_pct
                    else:
                        # 如果数据不足，标记为无数据
                        multi_period_changes[f'{period}d'] = None
            
            # 构建返回数据
            result = {
                'code': ts_code.split('.')[0],
                'ts_code': ts_code,
                'trade_date': current_date.strftime('%Y%m%d'),
                'close': current_price,
                'pre_close': pre_close,
                'change': change,
                'pct_chg': pct_chg,
                'multi_period_changes': multi_period_changes,  # 新增多期间涨跌幅
                'data_type': 'realtime' if is_trading_time else 'historical',
                'data_timestamp': current_date.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            print(f"获取 {ts_code} 行情成功，多期间涨跌幅: {multi_period_changes}")
            return result
            
        except Exception as e:
            print(f"获取股票 {ts_code} 行情失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_daily_data(self, ts_code, days=60):
        """获取股票日K线数据 - 使用LRU缓存的新浪财经真实历史数据"""
        try:
            # 使用LRU缓存函数获取数据
            daily_data_list = _fetch_daily_kline_data(ts_code, days)
            
            if daily_data_list is None:
                return None
            
            # 将字典列表转换为DataFrame
            daily_data = pd.DataFrame(daily_data_list)
            
            # 显示缓存状态和样本数据
            cache_info = _fetch_daily_kline_data.cache_info()
            print(f"[LRU缓存] 命中: {cache_info.hits}, 未命中: {cache_info.misses}, 当前大小: {cache_info.currsize}")
            
            if len(daily_data) > 0:
                latest = daily_data.iloc[-1]
                print(f"最新数据: {latest['trade_date']} 收盘价: {latest['close']}")
            
            return daily_data
                
        except Exception as e:
            print(f"获取股票 {ts_code} 日K线数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def search_stocks(self, query, limit=10):
        """搜索股票"""
        if self.stock_list is None:
            return []
        
        results = []
        query_lower = query.lower()
        
        for _, row in self.stock_list.iterrows():
            if (query_lower in row['name'].lower() or 
                query in row['symbol'] or 
                query in row['ts_code']):
                results.append({
                    'ts_code': row['ts_code'],
                    'symbol': row['symbol'],
                    'name': row['name'],
                    'market': row['market']
                })
                
                if len(results) >= limit:  # 限制返回数量
                    break
        
        return results


# =============================================================================
# LRU缓存管理函数
# =============================================================================
def get_daily_cache_info():
    """获取日K线数据的LRU缓存信息"""
    return _fetch_daily_kline_data.cache_info()

def clear_daily_cache():
    """清除日K线数据的LRU缓存"""
    _fetch_daily_kline_data.cache_clear()
    print("日K线数据LRU缓存已清空")

# =============================================================================
# 创建全局缓存实例
# =============================================================================
def create_stock_cache():
    """创建股票数据缓存实例"""
    cache = StockDataCache()
    
    # 如果缓存为空，立即更新
    if cache.stock_list is None:
        cache.update_stock_list()
    
    return cache
