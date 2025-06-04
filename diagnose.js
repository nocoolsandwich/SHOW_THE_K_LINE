// 诊断脚本 - 测试API连接
const API_BASE_URL = 'http://127.0.0.1:5000/api';

async function testAPI() {
    console.log('🔧 开始API诊断测试...\n');
    
    // 测试1: 健康检查
    try {
        console.log('1. 测试健康检查...');
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        console.log('✅ 健康检查成功:', data);
    } catch (error) {
        console.log('❌ 健康检查失败:', error.message);
        return;
    }
    
    // 测试2: 股票列表
    try {
        console.log('\n2. 测试股票列表...');
        const response = await fetch(`${API_BASE_URL}/stock_list`);
        const data = await response.json();
        console.log('✅ 股票列表成功:');
        console.log(`   总股票数: ${data.total}`);
        console.log(`   代码数量: ${data.codes?.length || 0}`);
        console.log(`   名称数量: ${data.names?.length || 0}`);
        console.log(`   映射数量: ${Object.keys(data.mappings || {}).length}`);
        
        // 显示前5只股票
        if (data.codes && data.codes.length > 0) {
            console.log('\n   前5只股票:');
            data.codes.slice(0, 5).forEach((stock, i) => {
                console.log(`   ${i+1}. ${stock.name}(${stock.code}) - ${stock.ts_code}`);
            });
        }
        
    } catch (error) {
        console.log('❌ 股票列表失败:', error.message);
        return;
    }
    
    // 测试3: 股票数据
    try {
        console.log('\n3. 测试股票数据 (平安银行 000001)...');
        const response = await fetch(`${API_BASE_URL}/daily_data/000001`);
        const data = await response.json();
        console.log('✅ 股票数据成功:');
        console.log(`   当前价格: ${data.current_price}`);
        console.log(`   涨跌幅: ${data.change_percent}%`);
        console.log(`   成交量: ${data.volume}`);
        console.log(`   K线数据点数: ${data.chart_data?.length || 0}`);
        
    } catch (error) {
        console.log('❌ 股票数据失败:', error.message);
    }
    
    console.log('\n🎉 API诊断完成！');
}

// 运行测试
testAPI().catch(console.error); 