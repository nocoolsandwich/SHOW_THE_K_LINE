#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票数据处理核心模块
包含股票数据缓存、获取、处理等核心功能
"""

import tushare as ts
import pandas as pd
import pickle
import os
import time
import easyquotation
from datetime import datetime, timedelta

# =============================================================================
# 配置常量
# =============================================================================
# Tushare API配置
TUSHARE_TOKEN = '2876ea85cb005fb5fa17c809a98174f2d5aae8b1f830110a5ead6211'

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

# 初始化Tushare
ts.set_token(TUSHARE_TOKEN)
pro = ts.pro_api()

# 创建easyquotation实例，用于获取实时行情
quotation = easyquotation.use('sina')


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
        """更新每日行情数据"""
        try:
            # 获取当前日期和时间
            current_date = datetime.now()
            current_time = current_date.time()
            market_close_time = datetime.strptime(TRADING_TIME_CONFIG['market_close'], '%H:%M').time()
            is_after_market_close = current_time >= market_close_time
            
            # 如果已经有缓存且是今天的数据，直接返回
            if (self.daily_quotes is not None and 
                self.last_quote_update is not None and 
                self.last_quote_update.date() == current_date.date()):
                print("使用缓存的行情数据")
                return True
            
            # 获取最近的交易日期
            today_str = current_date.strftime('%Y%m%d')
            print(f"获取截至 {today_str} 的最近交易日数据...")
            
            # 获取最近交易日历
            trade_cal = pro.trade_cal(
                exchange='SSE',
                start_date=(current_date - timedelta(days=10)).strftime('%Y%m%d'),
                end_date=today_str,
                fields='cal_date,is_open,pretrade_date'
            )
            
            # 获取最近的交易日
            latest_trade_date = None
            previous_trade_date = None
            
            for _, row in trade_cal.sort_values('cal_date', ascending=False).iterrows():
                if row['is_open'] == 1:
                    if latest_trade_date is None:
                        latest_trade_date = row['cal_date']
                    elif previous_trade_date is None:
                        previous_trade_date = row['cal_date']
                        break
            
            if not latest_trade_date:
                print("未找到最近的交易日")
                return False
                
            # 如果当前日期是交易日，但未收盘，则使用前一交易日的数据
            selected_trade_date = latest_trade_date
            if today_str == latest_trade_date and not is_after_market_close and previous_trade_date:
                selected_trade_date = previous_trade_date
                print(f"当前时间 {current_time} 未收盘，使用前一交易日 {selected_trade_date} 的数据")
            else:
                print(f"使用最近交易日 {selected_trade_date} 的数据")
                
            print(f"获取 {selected_trade_date} 的行情数据...")
            
            # 使用trade_date参数获取行情数据
            df = pro.daily(trade_date=selected_trade_date)
            print(f"获取到数据: {len(df) if df is not None else 0} 条记录")
            
            if df is not None and not df.empty:
                # 打印一些数据样本以验证
                print("数据样本:")
                print(df.head())
                
                # 将数据转换为以ts_code为索引的字典
                self.daily_quotes = df.set_index('ts_code').to_dict('index')
                self.last_quote_update = current_date
                
                # 验证缓存的数据
                print(f"成功缓存 {len(self.daily_quotes)} 只股票的行情数据")
                sample_stock = next(iter(self.daily_quotes))
                print(f"样本数据 ({sample_stock}):", self.daily_quotes[sample_stock])
                
                return True
            else:
                print("获取行情数据失败：返回数据为空")
                return False
                
        except Exception as e:
            print(f"获取行情数据失败: {e}")
            import traceback
            print("错误详情:", traceback.format_exc())
            return False
    
    def get_stock_quote(self, ts_code):
        """获取股票行情数据"""
        try:
            # 获取当前时间，判断是否在交易时间内
            current_date = datetime.now()
            current_time = current_date.time()
            is_trading_time = self.is_trading_time(current_time)
            
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
                            
                            # 计算实时涨跌幅
                            current_price = float(real_time_quote['now'])
                            pre_close = float(real_time_quote['close'])
                            change = round(current_price - pre_close, 2)
                            pct_chg = round((change / pre_close * 100), 2)
                            
                            return {
                                'code': ts_code.split('.')[0],
                                'ts_code': ts_code,
                                'trade_date': current_date.strftime('%Y%m%d'),
                                'close': current_price,
                                'pre_close': pre_close,
                                'change': change,
                                'pct_chg': pct_chg,
                                'data_type': 'realtime',  # 标记数据来源为实时数据
                                'data_timestamp': current_date.strftime('%Y-%m-%d %H:%M:%S')  # 添加数据获取时间戳
                            }
                except Exception as e:
                    print(f"获取实时行情失败: {e}，将使用历史数据")
            
            # 如果不是交易时间或获取实时数据失败，使用历史数据
            # 确保行情数据是最新的
            self.update_daily_quotes()
            
            # 从缓存中获取数据
            if self.daily_quotes and ts_code in self.daily_quotes:
                quote = self.daily_quotes[ts_code]
                
                # 使用历史数据
                return {
                    'code': ts_code.split('.')[0],
                    'ts_code': ts_code,
                    'trade_date': quote['trade_date'],
                    'close': quote['close'],
                    'pre_close': quote['pre_close'],
                    'change': quote['change'],
                    'pct_chg': quote['pct_chg'],
                    'data_type': 'historical',  # 标记数据来源为历史数据
                    'data_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 添加数据获取时间戳
                }
            return None
            
        except Exception as e:
            print(f"获取股票 {ts_code} 行情失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_daily_data(self, ts_code, days=60):
        """获取股票日K线数据"""
        try:
            current_date = datetime.now()
            end_date = current_date.strftime('%Y%m%d')
            start_date = (current_date - timedelta(days=days+30)).strftime('%Y%m%d')  # 多获取30天以应对节假日
            
            print(f"获取股票 {ts_code} 的日K线数据，时间范围: {start_date} - {end_date}")
            
            # 判断是否在交易时间内
            current_time = current_date.time()
            is_trading_time = self.is_trading_time(current_time)
            
            # 获取历史日K数据
            daily_data = pro.daily(ts_code=ts_code, 
                                 start_date=start_date, 
                                 end_date=end_date)
            
            if daily_data is None or daily_data.empty:
                return None
            
            # 如果在交易时间内，获取实时数据
            if is_trading_time:
                try:
                    print(f"获取 {ts_code} 的实时行情...")
                    
                    # 将ts_code转换为easyquotation使用的格式（去掉.SH/.SZ，改为前缀形式）
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
                            
                            # 获取当前时间
                            current_time = datetime.now().time()
                            is_market_open = self.is_trading_time(current_time)
                            
                            # 确定开盘价
                            open_price = float(real_time_quote['open'])
                            if not is_market_open:
                                # 非交易时间，使用历史数据中的开盘价
                                if len(daily_data) > 0 and daily_data.iloc[-1]['trade_date'] == current_date.strftime('%Y%m%d'):
                                    open_price = float(daily_data.iloc[-1]['open'])
                            
                            # 创建今日实时数据行
                            today_data = pd.DataFrame([{
                                'ts_code': ts_code,
                                'trade_date': current_date.strftime('%Y%m%d'),
                                'open': open_price,  # 使用确定的开盘价
                                'high': float(real_time_quote['high']),
                                'low': float(real_time_quote['low']),
                                'close': float(real_time_quote['now']),  # 当前价格作为收盘价
                                'pre_close': float(real_time_quote['close']),  # 昨收价
                                'vol': float(real_time_quote['turnover']),  # 成交量
                                'amount': float(real_time_quote['volume'])  # 成交额
                            }])
                            
                            # 如果最后一行是今天的数据，替换它；否则添加新行
                            if len(daily_data) > 0 and daily_data.iloc[-1]['trade_date'] == current_date.strftime('%Y%m%d'):
                                daily_data = daily_data.iloc[:-1]
                            daily_data = pd.concat([daily_data, today_data], ignore_index=True)
                            
                            print("实时数据合并完成")
                        else:
                            print(f"未找到股票 {easy_code} 的实时行情")
                except Exception as e:
                    print(f"获取实时数据失败: {e}，将只使用历史数据")
                    import traceback
                    traceback.print_exc()
            
            # 按日期排序并取最近的数据
            daily_data = daily_data.sort_values('trade_date').tail(days)
            
            return daily_data
            
        except Exception as e:
            print(f"获取股票 {ts_code} 的日K线数据失败: {e}")
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
# 创建全局缓存实例
# =============================================================================
def create_stock_cache():
    """创建股票数据缓存实例"""
    cache = StockDataCache()
    
    # 如果缓存为空，立即更新
    if cache.stock_list is None:
        cache.update_stock_list()
    
    return cache
