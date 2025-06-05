// 真实股票数据缓存
let stockMappings = {};
let stockCodes = [];
let stockNames = [];
let stockDataLoaded = false;

let currentChart = null;
let hoverTimeout = null;
let currentHoverElement = null;
const API_BASE_URL = 'http://127.0.0.1:5000/api';  // 使用127.0.0.1而不是localhost

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

// 使用真实股票数据识别并高亮股票
async function highlightStocks(text) {
    const stocksFound = new Map(); // 使用Map避免重复
    let processedText = text;

    console.log('开始识别股票，共有', Object.keys(stockMappings).length, '个股票映射');

    // 手动添加一些常见公司名称（特别是核电和科技相关公司）
    const additionalStocks = {
        '国光电气': { symbol: '300447', name: '国光电气', ts_code: '300447.SZ' },
        '合锻智能': { symbol: '603011', name: '合锻智能', ts_code: '603011.SH' },
        '联创光电': { symbol: '600363', name: '联创光电', ts_code: '600363.SH' },
        '西部超导': { symbol: '688122', name: '西部超导', ts_code: '688122.SH' },
        '安泰科技': { symbol: '000969', name: '安泰科技', ts_code: '000969.SZ' },
        '万里石': { symbol: '002785', name: '万里石', ts_code: '002785.SZ' },
        '锡装股份': { symbol: '301093', name: '锡装股份', ts_code: '301093.SZ' },
        '保变电气': { symbol: '600550', name: '保变电气', ts_code: '600550.SH' },
        '精达股份': { symbol: '600577', name: '精达股份', ts_code: '600577.SH' },
        '永鼎股份': { symbol: '600105', name: '永鼎股份', ts_code: '600105.SH' },
        '中钨高新': { symbol: '000657', name: '中钨高新', ts_code: '000657.SZ' },
        '应流股份': { symbol: '603308', name: '应流股份', ts_code: '603308.SH' },
        '中核': { symbol: '000777', name: '中核科技', ts_code: '000777.SZ' },
        '中广核': { symbol: '003816', name: '中广核技', ts_code: '003816.SZ' },
        'META': { symbol: 'META', name: 'Meta Platforms', ts_code: 'META.US' },
        '微软': { symbol: 'MSFT', name: 'Microsoft', ts_code: 'MSFT.US' },
        '亚马逊': { symbol: 'AMZN', name: 'Amazon', ts_code: 'AMZN.US' },
        'Constellation': { symbol: 'CEG', name: 'Constellation Energy', ts_code: 'CEG.US' },
        '王子新材': { symbol: '002735', name: '王子新材', ts_code: '002735.SZ' },
    };

    // 合并额外的股票数据到映射中
    for (const [key, value] of Object.entries(additionalStocks)) {
        if (!stockMappings[key]) {
            stockMappings[key] = value;
        }
    }

    // 按照长度排序，先匹配长的词汇，避免短词汇覆盖长词汇
    const allStockKeys = Object.keys(stockMappings).sort((a, b) => b.length - a.length);

    // 首先处理所有中文股票名称
    for (const stockKey of allStockKeys) {
        if (/[\u4e00-\u9fa5]/.test(stockKey)) {
            const stockInfo = stockMappings[stockKey];
            const escapedKey = escapeRegExp(stockKey);
            
            // 使用更精确的匹配模式
            const pattern = new RegExp(escapedKey, 'g');
            const matches = text.match(pattern);
            
            if (matches) {
                matches.forEach(match => {
                    if (!stocksFound.has(match)) {
                        stocksFound.set(match, {
                            key: stockKey,
                            info: stockInfo,
                            match: match
                        });
                    }
                });
            }
        }
    }

    // 然后处理其他类型的股票代码
    for (const stockKey of allStockKeys) {
        if (!/[\u4e00-\u9fa5]/.test(stockKey)) {
            const stockInfo = stockMappings[stockKey];
            let patterns = [];
            
            // 匹配6位数字股票代码
            if (/^\d{6}$/.test(stockKey)) {
                patterns.push(new RegExp(`(?<!\\d)${escapeRegExp(stockKey)}(?!\\d)`, 'g'));
            }
            // 匹配带括号的股票代码
            patterns.push(new RegExp(`\\(${escapeRegExp(stockKey)}\\)`, 'g'));
            // 匹配英文股票代码
            if (/^[A-Z]+$/.test(stockKey)) {
                patterns.push(new RegExp(`(?<![A-Za-z])${escapeRegExp(stockKey)}(?![A-Za-z])`, 'g'));
            }

            for (const pattern of patterns) {
                const matches = text.match(pattern);
                if (matches) {
                    matches.forEach(match => {
                        const cleanMatch = match.replace(/[()]/g, '');
                        if (!stocksFound.has(cleanMatch)) {
                            stocksFound.set(cleanMatch, {
                                key: stockKey,
                                info: stockInfo,
                                match: match
                            });
                        }
                    });
                }
            }
        }
    }

    console.log('识别到的股票:', Array.from(stocksFound.keys()));

    // 按照匹配长度排序，先替换长的匹配项
    const sortedStocks = Array.from(stocksFound.entries()).sort((a, b) => 
        b[1].match.length - a[1].match.length
    );

    // 替换文本中的股票为高亮链接
    for (const [stockKey, stockData] of sortedStocks) {
        const { info, match } = stockData;
        
        // 使用更简单的替换模式
        const replacement = `<span class="stock-highlight" data-stock-code="${info.symbol}" data-stock-name="${info.name}" data-ts-code="${info.ts_code}">${info.name}(${info.symbol})</span>`;
        
        // 直接替换匹配的文本
        processedText = processedText.replace(match, replacement);
    }

    return processedText;
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
            const stockCode = e.target.getAttribute('data-stock-code');
            const stockName = e.target.getAttribute('data-stock-name');
            showStockModal(stockCode, stockName);
        });
    });
}

// 处理股票悬停
function handleStockHover(element) {
    // 清除之前的超时
    if (hoverTimeout) {
        clearTimeout(hoverTimeout);
    }
    
    currentHoverElement = element;
    
    // 设置延迟，避免鼠标快速移动时频繁触发
    hoverTimeout = setTimeout(() => {
        if (currentHoverElement === element) {
            const stockCode = element.getAttribute('data-stock-code');
            const stockName = element.getAttribute('data-stock-name');
            showStockTooltip(element, stockCode, stockName);
        }
    }, 500); // 500ms延迟
}

// 处理股票悬停离开
function handleStockLeave() {
    // 清除超时
    if (hoverTimeout) {
        clearTimeout(hoverTimeout);
        hoverTimeout = null;
    }
    
    // 延迟隐藏tooltip，给用户时间移动到tooltip上
    setTimeout(() => {
        const tooltip = document.getElementById('stock-tooltip');
        if (tooltip && !tooltip.matches(':hover') && !currentHoverElement) {
            hideStockTooltip();
        }
    }, 300);
}

// 显示股票提示框
async function showStockTooltip(element, stockCode, stockName) {
    try {
        // 检查是否已存在tooltip
        let tooltip = document.getElementById('stock-tooltip');
        if (!tooltip) {
            tooltip = createStockTooltip();
        }
        
        // 显示加载状态
        tooltip.innerHTML = `
            <div class="tooltip-header">
                <h3>${stockName}</h3>
                <p>${stockCode}</p>
            </div>
            <div class="tooltip-body">
                <div class="loading-small">
                    <div class="spinner-small"></div>
                    <p>加载中...</p>
                </div>
            </div>
        `;
        
        // 定位tooltip
        positionTooltip(tooltip, element);
        tooltip.style.display = 'block';
        
        // 获取股票数据
        const stockData = await fetchStockData(stockCode);
        
        // 更新tooltip内容
        if (stockData && currentHoverElement === element) {
            updateTooltipContent(tooltip, stockName, stockCode, stockData);
        }
        
    } catch (error) {
        console.error('显示股票提示框失败:', error);
    }
}

// 创建股票提示框
function createStockTooltip() {
    const tooltip = document.createElement('div');
    tooltip.id = 'stock-tooltip';
    tooltip.className = 'stock-tooltip';
    tooltip.style.cssText = `
        position: absolute;
        background: white;
        border-radius: 10px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        padding: 0;
        z-index: 1000;
        max-width: 400px;
        width: 350px;
        display: none;
        font-size: 14px;
        border: 1px solid #e2e8f0;
    `;
    
    // 添加鼠标事件，保持tooltip显示
    tooltip.addEventListener('mouseenter', () => {
        if (hoverTimeout) {
            clearTimeout(hoverTimeout);
        }
    });
    
    tooltip.addEventListener('mouseleave', () => {
        currentHoverElement = null;
        setTimeout(() => {
            if (!tooltip.matches(':hover')) {
                hideStockTooltip();
            }
        }, 300);
    });
    
    document.body.appendChild(tooltip);
    return tooltip;
}

// 定位提示框
function positionTooltip(tooltip, element) {
    const rect = element.getBoundingClientRect();
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
    
    let left = rect.left + scrollLeft + rect.width / 2 - 175; // 居中对齐
    let top;
    
    // 计算元素在视口中的位置
    const elementTop = rect.top;
    const elementBottom = rect.bottom;
    const viewportHeight = window.innerHeight;
    const tooltipHeight = 250; // 预估tooltip高度
    
    // 优先显示在元素上方
    if (elementTop > tooltipHeight + 20) {
        // 如果元素上方有足够空间，显示在上方
        top = elementTop + scrollTop - tooltipHeight - 10;
    } else if (viewportHeight - elementBottom > tooltipHeight + 20) {
        // 如果元素下方有足够空间，显示在下方
        top = elementBottom + scrollTop + 10;
    } else {
        // 如果上下空间都不够，显示在元素上方，但确保不超出视口顶部
        top = Math.max(10, elementTop + scrollTop - tooltipHeight - 10);
    }
    
    // 水平方向边界检查
    if (left < 10) left = 10;
    if (left + 350 > window.innerWidth) left = window.innerWidth - 360;
    
    tooltip.style.left = left + 'px';
    tooltip.style.top = top + 'px';
}

// 隐藏股票提示框
function hideStockTooltip() {
    const tooltip = document.getElementById('stock-tooltip');
    if (tooltip) {
        tooltip.style.display = 'none';
    }
}

// 获取股票数据
async function fetchStockData(stockCode) {
    try {
        const response = await fetch(`${API_BASE_URL}/daily_data/${stockCode}?days=30`, {
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

// 更新提示框内容
function updateTooltipContent(tooltip, stockName, stockCode, stockData) {
    const changeColor = stockData.change_percent >= 0 ? '#22c55e' : '#ef4444';
    const changeSign = stockData.change_percent >= 0 ? '+' : '';
    
    tooltip.innerHTML = `
        <div class="tooltip-header" style="background: linear-gradient(45deg, #667eea, #764ba2); color: white; padding: 15px; border-radius: 10px 10px 0 0;">
            <h3 style="margin: 0; font-size: 16px;">${stockName}</h3>
            <p style="margin: 5px 0 0 0; opacity: 0.9;">${stockCode}</p>
        </div>
        <div class="tooltip-body" style="padding: 15px;">
            <div class="stock-info-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px;">
                <div class="info-item" style="background: #f7fafc; padding: 8px; border-radius: 5px;">
                    <span style="font-size: 12px; color: #666;">当前价格</span><br>
                    <span style="font-weight: bold; color: #333;">¥${stockData.current_price}</span>
                </div>
                <div class="info-item" style="background: #f7fafc; padding: 8px; border-radius: 5px;">
                    <span style="font-size: 12px; color: #666;">涨跌幅</span><br>
                    <span style="font-weight: bold; color: ${changeColor};">${changeSign}${stockData.change_percent}%</span>
                </div>
            </div>
            <div class="mini-chart" style="height: 100px; position: relative;">
                <div id="tooltip-chart" style="width: 320px; height: 100px;"></div>
            </div>
            <div style="text-align: center; margin-top: 10px; font-size: 12px; color: #666;">
                点击查看完整信息
            </div>
        </div>
    `;
    
    // 绘制迷你图表
    setTimeout(() => {
        drawMiniChart(stockData.chart_data);
    }, 50);
}

// 绘制迷你图表
function drawMiniChart(chartData) {
    const chartDom = document.getElementById('tooltip-chart');
    if (!chartDom || !chartData || chartData.length === 0) return;
    
    // 初始化ECharts实例
    const chart = echarts.init(chartDom);
    
    // 准备数据
    const dates = chartData.map(d => d.date);
    const values = chartData.map(d => [d.open, d.close, d.low, d.high]);
    
    // 配置项
    const option = {
        animation: false,
        grid: {
            left: 0,
            right: 0,
            top: 0,
            bottom: 0
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross'
            },
            formatter: function(params) {
                const data = params[0].data;
                return `日期：${params[0].axisValue}<br/>
                        开盘：${data[0]}<br/>
                        收盘：${data[1]}<br/>
                        最低：${data[2]}<br/>
                        最高：${data[3]}`;
            }
        },
        xAxis: {
            type: 'category',
            data: dates,
            show: false,
            scale: true,
            boundaryGap: false
        },
        yAxis: {
            type: 'value',
            show: false,
            scale: true
        },
        series: [
            {
                type: 'candlestick',
                data: values,
                itemStyle: {
                    color: '#ec0000',
                    color0: '#00da3c',
                    borderColor: '#8A0000',
                    borderColor0: '#008F28'
                }
            }
        ]
    };
    
    // 使用配置项显示图表
    chart.setOption(option);
    
    // 响应窗口大小变化
    window.addEventListener('resize', function() {
        chart.resize();
    });
}

// 显示股票信息弹窗（点击时）
async function showStockModal(stockCode, stockName) {
    const modal = document.getElementById('stockModal');
    const stockNameEl = document.getElementById('stockName');
    const stockCodeEl = document.getElementById('stockCode');
    
    stockNameEl.textContent = stockName;
    stockCodeEl.textContent = stockCode;
    
    modal.style.display = 'block';
    
    // 隐藏tooltip
    hideStockTooltip();
    
    // 加载股票数据
    await loadStockDataForModal(stockCode);
}

// 加载股票数据（用于模态框）
async function loadStockDataForModal(stockCode) {
    try {
        const stockData = await fetchStockData(stockCode);
        
        if (!stockData) {
            document.getElementById('currentPrice').textContent = '数据加载失败';
            document.getElementById('changePercent').textContent = '--';
            document.getElementById('volume').textContent = '--';
            return;
        }
        
        // 更新股票信息
        document.getElementById('currentPrice').textContent = `¥${stockData.current_price}`;
        document.getElementById('changePercent').textContent = `${stockData.change_percent > 0 ? '+' : ''}${stockData.change_percent}%`;
        document.getElementById('volume').textContent = stockData.volume.toLocaleString();
        
        // 设置涨跌颜色
        const changeEl = document.getElementById('changePercent');
        changeEl.style.color = stockData.change_percent >= 0 ? '#22c55e' : '#ef4444';
        
        // 绘制K线图
        drawStockChart(stockData.chart_data);
        
    } catch (error) {
        console.error('股票数据加载失败:', error);
        document.getElementById('currentPrice').textContent = '数据加载失败';
        document.getElementById('changePercent').textContent = '--';
        document.getElementById('volume').textContent = '--';
    }
}

// 绘制股票K线图
function drawStockChart(data) {
    const chartDom = document.getElementById('stockChart');
    
    // 销毁之前的图表
    if (currentChart) {
        currentChart.dispose();
    }
    
    // 初始化ECharts实例
    currentChart = echarts.init(chartDom);
    
    // 准备数据
    const dates = data.map(d => d.date);
    const values = data.map(d => [d.open, d.close, d.low, d.high]);
    
    // 配置项
    const option = {
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
                    color: '#ec0000',
                    color0: '#00da3c',
                    borderColor: '#8A0000',
                    borderColor0: '#008F28'
                }
            }
        ]
    };
    
    // 使用配置项显示图表
    currentChart.setOption(option);
    
    // 响应窗口大小变化
    window.addEventListener('resize', function() {
        currentChart.resize();
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
    
    // 点击其他地方时隐藏tooltip
    if (!event.target.closest('.stock-highlight') && !event.target.closest('#stock-tooltip')) {
        hideStockTooltip();
    }
}

// 显示/隐藏加载状态
function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'flex' : 'none';
} 