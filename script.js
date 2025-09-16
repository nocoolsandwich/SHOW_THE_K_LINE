// 真实股票数据缓存
let stockMappings = {};
let stockCodes = [];
let stockNames = [];
let stockDataLoaded = false;

let currentChart = null;

// 动态获取API基础URL
const API_BASE_URL = getAPIBaseURL();

// 获取API基础URL
function getAPIBaseURL() {
    // 获取当前主机
    const host = '127.0.0.1';
    const port = '5000'; // 后端服务端口
    
    // 使用相对协议，自动适应http或https
    return `${window.location.protocol}//${host}:${port}/api`;
}

// 更新状态显示
function updateStatus(type, status, className = '') {
    const element = document.getElementById(type + 'Status');
    if (element) {
        element.textContent = status;
        element.className = 'status-value ' + className;
    }
}

// 等待函数
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// 检查后端服务状态 - 增加重试机制
async function checkBackendHealth(retries = 3) {
    for (let i = 0; i < retries; i++) {
        try {
            console.log(`检查后端服务状态... (尝试 ${i + 1}/${retries})`);
            updateStatus('backend', `检查中... (${i + 1}/${retries})`, 'checking');
            
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000); // 5秒超时
            
            const response = await fetch(`${API_BASE_URL}/health`, {
                method: 'GET',
                mode: 'cors',
                cache: 'no-cache',
                signal: controller.signal,
                headers: {
                    'Accept': 'application/json',
                }
            });
            
            clearTimeout(timeoutId);
            console.log('健康检查响应状态:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('后端服务状态:', data);
            
            const isHealthy = data.status === 'ok' && data.stock_count > 0;
            updateStatus('backend', isHealthy ? '正常运行' : '服务异常', isHealthy ? 'success' : 'error');
            
            return isHealthy;
        } catch (error) {
            console.error(`后端服务连接失败 (尝试 ${i + 1}):`, error.message);
            
            if (i === retries - 1) {
                updateStatus('backend', '连接失败', 'error');
                return false;
            }
            
            // 等待1秒后重试
            await sleep(1000);
        }
    }
    return false;
}

// 加载真实股票数据 - 增加重试机制
async function loadStockData(retries = 3) {
    for (let i = 0; i < retries; i++) {
        try {
            console.log(`正在加载股票列表... (尝试 ${i + 1}/${retries})`);
            console.log('API地址:', `${API_BASE_URL}/stock_list`);
            
            updateStatus('stockData', `连接中... (${i + 1}/${retries})`, 'checking');
            
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10秒超时
            
            // 添加更详细的fetch配置
            const response = await fetch(`${API_BASE_URL}/stock_list`, {
                method: 'GET',
                mode: 'cors',
                cache: 'no-cache',
                signal: controller.signal,
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
            });
            
            clearTimeout(timeoutId);
            console.log('响应状态:', response.status, response.statusText);
            console.log('响应头:', Object.fromEntries(response.headers.entries()));
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('响应错误内容:', errorText);
                throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
            }
            
            updateStatus('stockData', '解析中...', 'checking');
            
            const data = await response.json();
            console.log('收到数据:', {
                total: data.total,
                codes_count: data.codes?.length,
                names_count: data.names?.length,
                mappings_count: Object.keys(data.mappings || {}).length
            });
            
            // 验证数据完整性
            if (!data.mappings || Object.keys(data.mappings).length === 0) {
                throw new Error('股票映射数据为空');
            }
            
            if (!data.codes || data.codes.length === 0) {
                throw new Error('股票代码数据为空');
            }
            
            // 缓存股票数据
            stockMappings = data.mappings || {};
            stockCodes = data.codes || [];
            stockNames = data.names || [];
            stockDataLoaded = true;
            
            console.log(`股票数据加载成功，共${data.total}只股票`);
            console.log('股票映射示例:', Object.keys(stockMappings).slice(0, 5));
            
            updateStatus('stockData', `已加载 ${data.total} 只股票`, 'success');
            
            return true;
            
        } catch (error) {
            console.error(`加载股票数据失败 (尝试 ${i + 1}):`, error);
            console.error('错误详情:', error.message);
            
            if (i === retries - 1) {
                console.error('错误堆栈:', error.stack);
                updateStatus('stockData', '加载失败', 'error');
                
                // 重置状态
                stockMappings = {};
                stockCodes = [];
                stockNames = [];
                stockDataLoaded = false;
                
                return false;
            }
            
            // 等待2秒后重试
            await sleep(2000);
        }
    }
    return false;
}

// 初始化事件监听器
document.addEventListener('DOMContentLoaded', async function() {
    const pdfInput = document.getElementById('pdfInput');
    const uploadZone = document.getElementById('uploadZone');

    console.log('页面加载完成，开始初始化...');
    console.log('当前URL:', window.location.href);
    console.log('API基础URL:', API_BASE_URL);

    // 等待页面完全加载
    await sleep(500);

    try {
        // 检查后端服务
        console.log('步骤1: 检查后端服务...');
        const backendOk = await checkBackendHealth();
        if (!backendOk) {
            console.error('后端服务检查失败');
            showNotification('后端服务未启动或无法连接，请检查服务状态', 'error');
            return;
        }
        console.log('✅ 后端服务检查通过');

        // 加载股票数据
        console.log('步骤2: 加载股票数据...');
        showLoading(true);
        
        const stockDataOk = await loadStockData();
        
        if (!stockDataOk) {
            console.error('股票数据加载失败');
            showNotification('股票数据加载失败，请检查网络连接或后端服务', 'error');
            return;
        }
        
        console.log('✅ 股票数据加载成功');
        showNotification(`股票数据加载成功，共${stockCodes.length}只股票`);
        console.log('初始化完成，股票数据已就绪');
        
    } catch (error) {
        console.error('初始化过程中发生错误:', error);
        showNotification('初始化失败: ' + error.message, 'error');
        return;
    } finally {
        showLoading(false);
    }

    // PDF文件上传处理
    pdfInput.addEventListener('change', handlePDFUpload);

    // 拖拽上传功能
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0 && files[0].type === 'application/pdf') {
            handlePDFFile(files[0]);
        }
    });

    uploadZone.addEventListener('click', () => {
        pdfInput.click();
    });
});

// 显示通知
function showNotification(message, type = 'info') {
    console.log(`通知 [${type}]: ${message}`);
    
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 5px;
        color: white;
        font-weight: 500;
        z-index: 10000;
        max-width: 300px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        ${type === 'error' ? 'background: #ef4444;' : 'background: #22c55e;'}
    `;
    
    document.body.appendChild(notification);
    
    // 3秒后自动移除
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// 处理PDF上传
async function handlePDFUpload(event) {
    const file = event.target.files[0];
    if (file && file.type === 'application/pdf') {
        await handlePDFFile(file);
    }
}

// 处理PDF文件
async function handlePDFFile(file) {
    showLoading(true);
    
    try {
        const text = await extractTextFromPDF(file);
        document.getElementById('textInput').value = text;
        await processText();
    } catch (error) {
        console.error('PDF处理错误:', error);
        showNotification('PDF文件处理失败，请确保文件格式正确', 'error');
    } finally {
        showLoading(false);
    }
}

// 从PDF提取文本
async function extractTextFromPDF(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = async function(e) {
            try {
                const typedarray = new Uint8Array(e.target.result);
                const pdf = await pdfjsLib.getDocument({data: typedarray}).promise;
                let fullText = '';

                for (let i = 1; i <= pdf.numPages; i++) {
                    const page = await pdf.getPage(i);
                    const textContent = await page.getTextContent();
                    const pageText = textContent.items.map(item => item.str).join(' ');
                    fullText += pageText + '\n';
                }

                resolve(fullText);
            } catch (error) {
                reject(error);
            }
        };
        reader.onerror = () => reject(new Error('文件读取失败'));
        reader.readAsArrayBuffer(file);
    });
}

// 处理文本并识别股票
async function processText() {
    const textInput = document.getElementById('textInput');
    const text = textInput.value.trim();
    
    console.log('开始处理文本，文本长度:', text.length);
    console.log('股票数据加载状态:', stockDataLoaded);
    console.log('股票映射数量:', Object.keys(stockMappings).length);
    
    if (!text) {
        showNotification('请输入或上传包含股票信息的内容', 'error');
        return;
    }

    if (!stockDataLoaded) {
        showNotification('股票数据还未加载完成，请稍候', 'error');
        console.error('股票数据未加载完成，当前状态:', {
            stockDataLoaded,
            stockMappingsCount: Object.keys(stockMappings).length,
            stockCodesCount: stockCodes.length
        });
        return;
    }

    showLoading(true);

    try {
        const processedHTML = await highlightStocks(text);
        displayProcessedText(processedHTML);
        
        document.getElementById('resultSection').style.display = 'block';
        document.getElementById('resultSection').scrollIntoView({ behavior: 'smooth' });
        
        showNotification('股票识别完成，将鼠标悬停在高亮的股票上查看详情');
    } catch (error) {
        console.error('文本处理错误:', error);
        showNotification('文本处理失败，请重试', 'error');
    } finally {
        showLoading(false);
    }
}

// 获取股票最新行情
async function getLatestQuote(stockCode) {
    try {
        const response = await fetch(`${API_BASE_URL}/latest_quote/${stockCode}`, {
            method: 'GET',
            mode: 'cors',
            cache: 'no-cache',
            headers: {
                'Accept': 'application/json',
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error(`获取股票${stockCode}行情失败:`, error);
        return null;
    }
    }

// 修改高亮股票的函数
async function highlightStocks(text) {
    if (!stockDataLoaded) {
        console.warn('股票数据未加载，无法高亮显示');
        return text;
    }

    // 将文本分割成行来处理
    let lines = text.split('\n');

    // 用于存储所有股票的行情数据
    const quoteData = {};
    const stocksToProcess = new Set();
            
    // 第一步：收集所有需要处理的股票
    for (const key in stockMappings) {
        if (text.includes(key)) {
            stocksToProcess.add(key);
        }
    }

    // 第二步：获取所有股票的行情数据
    // 为了提高性能，我们并行获取所有股票的行情数据
    if (stocksToProcess.size > 0) {
        const stockPromises = Array.from(stocksToProcess).map(async (stock) => {
            const stockInfo = stockMappings[stock];
            if (stockInfo) {
                try {
                    const quote = await getLatestQuote(stockInfo.symbol);
                    if (quote) {
                        quoteData[stock] = quote;
            }
                } catch (error) {
                    console.error(`获取${stock}行情失败:`, error);
                }
            }
        });

        // 等待所有请求完成
        await Promise.all(stockPromises);
    }

    // 第三步：处理每一行文本
    const processedLines = lines.map(line => {
        let processedLine = line;

        // 按长度排序处理股票，避免短名称替换长名称的一部分
        const stocksInLine = Array.from(stocksToProcess)
            .filter(stock => line.includes(stock))
            .sort((a, b) => b.length - a.length);

        for (const stock of stocksInLine) {
            const stockInfo = stockMappings[stock];
            const quote = quoteData[stock];
            
            let changeText = '';
            if (quote) {
                const pctChg = quote.pct_chg;
                const changeClass = pctChg >= 0 ? 'stock-up' : 'stock-down';
                changeText = `<span class="stock-change ${changeClass}">${pctChg >= 0 ? '+' : ''}${pctChg.toFixed(2)}%</span>`;
            }

            const replacement = `<span class="stock-highlight" onclick="handleStockClick(this)" 
                                    data-code="${stockInfo.symbol}" 
                                    data-name="${stockInfo.name}">
                                    ${stock}${changeText}
                               </span>`;

            // 使用字符串分割和拼接的方式进行替换，避免正则表达式的问题
            const parts = processedLine.split(stock);
            processedLine = parts.join(replacement);
        }
        
        return processedLine;
    });

    return processedLines.join('\n');
}

// 转义正则表达式特殊字符
function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// 显示处理后的文本
function displayProcessedText(html) {
    const container = document.getElementById('processedText');
    container.innerHTML = html;
    
    // 为所有股票高亮元素添加悬停事件
    const stockElements = container.querySelectorAll('.stock-highlight');
    stockElements.forEach(element => {
        // 鼠标进入事件
        element.addEventListener('mouseenter', (e) => {
            handleStockHover(e.target);
        });
        
        // 鼠标离开事件
        element.addEventListener('mouseleave', () => {
            handleStockLeave();
        });
        
        // 点击事件（备用）
        element.addEventListener('click', (e) => {
            const stockCode = e.target.getAttribute('data-code');
            const stockName = e.target.getAttribute('data-name');
            showStockModal(stockCode, stockName);
        });
    });
}

// 显示股票信息弹窗（点击时）
async function showStockModal(stockCode, stockName) {
    const modal = document.getElementById('stockModal');
    const stockNameElement = document.getElementById('stockName');
    const stockCodeElement = document.getElementById('stockCode');
    const xueqiuLink = document.getElementById('xueqiuLink');

    // 更新标题和代码
    stockNameElement.textContent = stockName || '加载中...';
    stockCodeElement.textContent = stockCode;

    // 更新雪球链接
    const market = stockCode.startsWith('6') ? 'SH' : 'SZ';
    xueqiuLink.href = `https://xueqiu.com/S/${market}${stockCode}`;

    // 显示模态框
    modal.style.display = 'block';
    
    // 加载股票数据
    await loadStockDataForModal(stockCode);
    
    // 设置图表类型切换事件
    setupChartTypeSwitching(stockCode);
}

// 加载股票数据（用于模态框）
async function loadStockDataForModal(stockCode) {
    try {
        const stockData = await fetchStockData(stockCode, 'daily');
        
        if (!stockData) {
            document.getElementById('currentPrice').textContent = '数据加载失败';
            document.getElementById('changePercent').textContent = '--';
            document.getElementById('volume').textContent = '--';
            return;
        }
        
        // 更新股票信息
        document.getElementById('currentPrice').textContent = `¥${stockData.current_price}`;
        
        // 更新涨跌幅并设置样式
        const changeEl = document.getElementById('changePercent');
        changeEl.textContent = `${stockData.change_percent > 0 ? '+' : ''}${stockData.change_percent}%`;
        
        // 使用类名控制颜色
        changeEl.className = 'value ' + (stockData.change_percent >= 0 ? 'up' : 'down');
        
        document.getElementById('volume').textContent = stockData.volume.toLocaleString();
        
        // 绘制K线图
        drawStockChart(stockData.chart_data, 'daily');
        
    } catch (error) {
        console.error('股票数据加载失败:', error);
        document.getElementById('currentPrice').textContent = '数据加载失败';
        document.getElementById('changePercent').textContent = '--';
        document.getElementById('volume').textContent = '--';
    }
}

// 设置图表类型切换
function setupChartTypeSwitching(stockCode) {
    const dailyBtn = document.getElementById('dailyBtn');
    const intradayBtn = document.getElementById('intradayBtn');
    
    // 移除之前的事件监听器
    dailyBtn.replaceWith(dailyBtn.cloneNode(true));
    intradayBtn.replaceWith(intradayBtn.cloneNode(true));
    
    // 重新获取按钮元素
    const newDailyBtn = document.getElementById('dailyBtn');
    const newIntradayBtn = document.getElementById('intradayBtn');
    
    // 添加新的事件监听器
    newDailyBtn.addEventListener('click', async () => {
        newDailyBtn.classList.add('active');
        newIntradayBtn.classList.remove('active');
        const data = await fetchStockData(stockCode, 'daily');
        if (data) {
            drawStockChart(data.chart_data, 'daily');
        }
    });
    
    newIntradayBtn.addEventListener('click', async () => {
        newIntradayBtn.classList.add('active');
        newDailyBtn.classList.remove('active');
        const data = await fetchStockData(stockCode, 'intraday');
        if (data) {
            drawStockChart(data.chart_data, 'intraday');
        }
    });
}

// 绘制股票图表
function drawStockChart(data, type = 'daily') {
    const chartDom = document.getElementById('stockChart');
    
    // 销毁之前的图表
    if (currentChart) {
        currentChart.dispose();
}

    // 初始化ECharts实例
    currentChart = echarts.init(chartDom);
    
    let option;
    
    if (type === 'daily') {
        // 准备日K数据
        const dates = data.map(d => d.date);
        const values = data.map(d => [d.open, d.close, d.low, d.high]);
        
        // 计算每个K线的涨跌幅
        const changePercents = values.map((value, index) => {
            if (index === 0) {
                // 第一个数据点，使用开盘价作为基准
                return ((value[1] - value[0]) / value[0] * 100).toFixed(2);
            } else {
                // 使用前一天收盘价作为基准
                const prevClose = values[index - 1][1];
                return ((value[1] - prevClose) / prevClose * 100).toFixed(2);
    }
        });
        
        option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'cross'
                },
                formatter: function(params) {
                    const data = params[0].data;
                    const changePercent = changePercents[params[0].dataIndex];
                    const color = parseFloat(changePercent) >= 0 ? '#ff333a' : '#00aa3b';
                    return `
                        <div style="font-size: 14px; padding: 4px 8px;">
                            <div style="margin-bottom: 8px;">${params[0].name}</div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span>开盘：</span>
                                <span style="color: ${data[0] >= data[1] ? '#00aa3b' : '#ff333a'}">${data[0]}</span>
        </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span>收盘：</span>
                                <span style="color: ${data[1] >= data[0] ? '#ff333a' : '#00aa3b'}">${data[1]}</span>
                </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span>最低：</span>
                                <span style="color: #00aa3b">${data[2]}</span>
                </div>
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span>最高：</span>
                                <span style="color: #ff333a">${data[3]}</span>
            </div>
                            <div style="display: flex; justify-content: space-between; margin-top: 8px; border-top: 1px solid #eee; padding-top: 8px;">
                                <span>涨跌幅：</span>
                                <span style="color: ${color}">${changePercent}%</span>
            </div>
        </div>
    `;
                }
            },
        grid: {
                left: '10%',
                right: '10%',
                bottom: '15%'
        },
        xAxis: {
            type: 'category',
            data: dates,
            scale: true,
                boundaryGap: false,
                axisLine: { onZero: false },
                splitLine: { show: false },
                min: 'dataMin',
                max: 'dataMax'
        },
        yAxis: {
                scale: true,
                splitArea: {
                    show: true
                }
            },
            dataZoom: [
                {
                    type: 'inside',
                    start: 0,
                    end: 100
                },
                {
                    show: true,
                    type: 'slider',
                    bottom: '5%'
                }
            ],
        series: [
            {
                    name: 'K线',
                type: 'candlestick',
                data: values,
                itemStyle: {
                        color: '#ff333a',     // 涨的颜色（红色）
                        color0: '#00aa3b',    // 跌的颜色（绿色）
                        borderColor: '#ff333a',
                        borderColor0: '#00aa3b'
                }
            }
        ]
    };
    } else {
        // 准备分时数据
        const times = data.map(d => d.time);
        const prices = data.map(d => d.price);
        const basePrice = prices[0]; // 第一个价格作为基准价
        
        option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross'
            }
        },
        grid: {
            left: '10%',
            right: '10%',
            bottom: '15%'
        },
        xAxis: {
            type: 'category',
                data: times,
            scale: true,
            boundaryGap: false,
            axisLine: { onZero: false },
                splitLine: { show: false }
        },
        yAxis: {
            scale: true,
            splitArea: {
                show: true
            }
        },
        dataZoom: [
            {
                type: 'inside',
                start: 0,
                end: 100
            },
            {
                show: true,
                type: 'slider',
                bottom: '5%'
            }
        ],
        series: [
            {
                    name: '分时',
                    type: 'line',
                    data: prices,
                    smooth: true,
                    showSymbol: false,
                    lineStyle: {
                        width: 1,
                        color: '#ff333a'  // 分时图线条颜色（红色）
                    },
                    areaStyle: {
                        color: {
                            type: 'linear',
                            x: 0,
                            y: 0,
                            x2: 0,
                            y2: 1,
                            colorStops: [{
                                offset: 0,
                                color: 'rgba(255, 51, 58, 0.2)'  // 红色半透明
                            }, {
                                offset: 1,
                                color: 'rgba(255, 51, 58, 0)'   // 完全透明
                            }]
                        }
                }
            }
        ]
    };
    }
    
    // 使用配置项显示图表
    currentChart.setOption(option);
    
    // 响应窗口大小变化
    window.addEventListener('resize', function() {
        if (currentChart) {
        currentChart.resize();
        }
    });
}

// 关闭弹窗
function closeModal() {
    document.getElementById('stockModal').style.display = 'none';
}

// 点击弹窗外部关闭
window.onclick = function(event) {
    const modal = document.getElementById('stockModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

// 显示/隐藏加载状态
function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'flex' : 'none';
}

// 处理股票点击
function handleStockClick(element) {
    const stockCode = element.getAttribute('data-code');
    const stockName = element.getAttribute('data-name');
    showStockModal(stockCode, stockName);
}

// 获取股票数据
async function fetchStockData(stockCode, type = 'daily') {
    try {
        const endpoint = type === 'daily' ? 'daily_data' : 'intraday_data';
        const response = await fetch(`${API_BASE_URL}/${endpoint}/${stockCode}`, {
            method: 'GET',
            mode: 'cors',
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        return data;
        
    } catch (error) {
        console.error('获取股票数据失败:', error);
        return null;
    }
} 