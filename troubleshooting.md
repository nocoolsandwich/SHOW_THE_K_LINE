# 股票信息查看器 - 故障排除指南

## 常见问题及解决方案

### 1. "股票数据加载失败，请检查网络连接或后端服务"

**可能原因：**
- 后端服务未启动
- 端口被占用
- CORS配置问题
- 网络连接问题

**解决步骤：**

#### 步骤1: 检查后端服务
```powershell
# 检查端口5000是否被占用
netstat -an | findstr ":5000"

# 如果没有输出，说明后端服务未启动
# 启动后端服务
python backend.py
```

#### 步骤2: 检查前端服务
```powershell
# 检查端口8080是否被占用
netstat -an | findstr ":8080"

# 如果没有输出，启动前端服务
python -m http.server 8080
```

#### 步骤3: 测试API连接
```powershell
# 测试健康检查
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/health" -Method Get

# 测试股票列表
$response = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/stock_list" -Method Get
Write-Host "股票总数: $($response.total)"
```

### 2. "股票数据还未加载完成，请稍候"

**可能原因：**
- 股票数据加载失败
- JavaScript执行错误
- API响应格式问题

**解决步骤：**

#### 步骤1: 打开浏览器开发者工具
1. 按F12打开开发者工具
2. 切换到Console标签
3. 刷新页面，查看错误信息

#### 步骤2: 检查网络请求
1. 切换到Network标签
2. 刷新页面
3. 查看是否有失败的请求（红色标记）

#### 步骤3: 使用测试页面
访问 `http://127.0.0.1:8080/simple_test.html` 进行基础测试

### 3. 鼠标悬停无反应

**可能原因：**
- 股票识别失败
- 事件监听器未正确绑定
- CSS样式问题

**解决步骤：**

#### 步骤1: 检查股票是否被识别
1. 在文本框中输入测试文本：`平安银行(000001)上涨2%`
2. 点击"分析文本"
3. 查看是否有高亮显示

#### 步骤2: 检查控制台错误
1. 打开开发者工具
2. 查看Console中是否有JavaScript错误

### 4. PDF上传失败

**可能原因：**
- PDF文件损坏
- PDF.js库加载失败
- 文件大小过大

**解决步骤：**

#### 步骤1: 检查PDF文件
- 确保PDF文件可以正常打开
- 文件大小不超过10MB

#### 步骤2: 检查网络连接
- 确保可以访问CDN资源
- 检查防火墙设置

## 完整的重启流程

如果遇到问题，可以按以下步骤完全重启：

### 1. 停止所有服务
```powershell
# 停止所有Python进程
taskkill /f /im python.exe

# 等待几秒钟
Start-Sleep -Seconds 3
```

### 2. 重新启动后端服务
```powershell
# 在项目目录中启动后端
cd C:\Users\admin\Desktop\vv
python backend.py
```

### 3. 重新启动前端服务（新的PowerShell窗口）
```powershell
# 在项目目录中启动前端
cd C:\Users\admin\Desktop\vv
python -m http.server 8080
```

### 4. 验证服务状态
```powershell
# 测试后端
Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/health"

# 测试前端
Invoke-RestMethod -Uri "http://127.0.0.1:8080" | Select-String "股票信息查看器"
```

### 5. 打开浏览器测试
```powershell
Start-Process "http://127.0.0.1:8080"
```

## 系统要求检查

### Python环境
```powershell
# 检查Python版本
python --version

# 检查必要的包
python -c "import tushare, flask, flask_cors, pandas; print('所有包已安装')"
```

### 网络连接
```powershell
# 测试本地连接
Test-NetConnection -ComputerName 127.0.0.1 -Port 5000
Test-NetConnection -ComputerName 127.0.0.1 -Port 8080
```

## 日志分析

### 后端日志
后端服务运行时会在控制台输出详细日志：
- `股票列表缓存加载成功` - 缓存正常
- `收到请求: GET http://127.0.0.1:5000/api/stock_list` - API请求正常
- `返回股票数据，共 5413 只股票` - 数据返回正常

### 前端日志
在浏览器开发者工具Console中查看：
- `页面加载完成，开始初始化...` - 页面初始化开始
- `✅ 后端服务检查通过` - 后端连接正常
- `✅ 股票数据加载成功` - 数据加载完成

## 联系支持

如果以上步骤都无法解决问题，请提供以下信息：
1. 操作系统版本
2. Python版本
3. 浏览器版本
4. 完整的错误信息
5. 控制台日志截图 