# 中国用户pip安装加速指南

由于网络原因，在中国使用pip安装Python包可能会很慢。以下是几种加速方案：

## 1. 使用国内镜像源

### 临时使用镜像源
```bash
# 使用清华镜像源
pip install persist-queue -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 使用阿里云镜像源
pip install persist-queue -i https://mirrors.aliyun.com/pypi/simple/

# 使用豆瓣镜像源
pip install persist-queue -i https://pypi.douban.com/simple/

# 使用中科大镜像源
pip install persist-queue -i https://pypi.mirrors.ustc.edu.cn/simple/
```

### 永久配置镜像源

#### Windows系统
在用户目录下创建或编辑 `pip.ini` 文件：
```
%APPDATA%\pip\pip.ini
```
或
```
%USERPROFILE%\pip\pip.ini
```

文件内容：
```ini
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple/
trusted-host = pypi.tuna.tsinghua.edu.cn
```

#### Linux/macOS系统
创建或编辑 `~/.pip/pip.conf` 文件：
```ini
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple/
trusted-host = pypi.tuna.tsinghua.edu.cn
```

## 2. 使用conda镜像源

如果您使用Anaconda或Miniconda：

```bash
# 添加清华conda镜像源
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
conda config --set show_channel_urls yes

# 安装包
conda install persist-queue
```

## 3. 使用pipx安装（推荐用于工具类包）

```bash
# 安装pipx
pip install pipx -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 使用pipx安装
pipx install persist-queue
```

## 4. 离线安装方案

### 下载wheel文件
```bash
# 下载wheel文件到本地
pip download persist-queue -d ./packages -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 从本地安装
pip install ./packages/persist-queue-*.whl
```

### 使用pip-tools
```bash
# 安装pip-tools
pip install pip-tools -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 生成requirements.txt
pip-compile requirements.txt

# 下载所有依赖
pip download -r requirements.txt -d ./packages -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

## 5. 使用代理

如果您有代理服务器：
```bash
pip install persist-queue --proxy http://proxy-server:port
```

## 6. 加速pip本身

```bash
# 升级pip到最新版本
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 使用并行下载
pip install persist-queue --use-feature=fast-deps -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

## 7. 针对persist-queue的安装建议

由于persist-queue包含异步功能，需要安装额外的依赖：

```bash
# 安装基础版本
pip install persist-queue -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 安装包含异步功能的完整版本
pip install persist-queue[async] -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 或者手动安装异步依赖
pip install aiofiles aiosqlite -i https://pypi.tuna.tsinghua.edu.cn/simple/
pip install persist-queue -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

## 8. 常见问题解决

### SSL证书问题
```bash
pip install persist-queue --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org
```

### 超时问题
```bash
pip install persist-queue --timeout 1000 -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 缓存问题
```bash
# 清除pip缓存
pip cache purge

# 重新安装
pip install persist-queue -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

## 推荐配置

对于中国用户，推荐使用以下配置：

1. **首选方案**：使用清华镜像源
2. **备选方案**：阿里云或中科大镜像源
3. **离线环境**：提前下载wheel文件
4. **开发环境**：配置永久镜像源

选择最适合您网络环境的方案即可显著提升安装速度。 