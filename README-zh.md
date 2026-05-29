# FudanWebTool

[English README](README.md)

FudanWebTool 是一个轻量级 Windows 托盘工具，用于监测复旦校园网的真实外网连通性，并在断线时自动重新认证。

托盘程序在后台运行，不保留持续占用的控制台窗口。它会先检测真实外网是否可达，只有需要恢复网络时才访问复旦认证门户。如果门户显示已经认证成功，但外网实际不可达，工具会先注销当前假在线状态，再重新选择校园网出口登录。

## 功能

- Windows 任务栏右下角托盘图标，支持状态、立即检查、暂停/继续、设置和退出
- 可在设置窗口勾选当前用户开机自启动
- 显示当前联网网卡的上传/下载速度、今日总量和本月总量
- 周期性网络健康检查
- 校园网网关登录请求
- 非敏感设置保存到 `%APPDATA%\FudanWebTool\config.json`
- 流量累计保存到 `%APPDATA%\FudanWebTool\traffic.json`
- 密码通过 Windows 凭据管理器保存，不写入配置文件
- 输出重连尝试和失败原因日志
- 针对“门户已认证但外网不可用”的假在线状态，自动注销后重连

## 配置

推荐通过托盘图标里的设置窗口配置。设置窗口会把非敏感设置保存到 `%APPDATA%\FudanWebTool\config.json`，把密码保存到 Windows 凭据管理器。

“开机自启动”只会在当前用户的 Windows Startup 文件夹中创建或删除启动脚本；不会安装系统服务，不会创建计划任务，也不会写入注册表 Run 项。

`.env` 仍然保留，用于命令行使用或从旧版本迁移。只有在你希望继续使用环境变量配置时，才需要复制 `.env.example`：

```powershell
Copy-Item .env.example .env
```

不要提交 `.env`；它已经被 Git 忽略。

可用配置项：

- `FUDAN_NET_USERNAME`：校园网用户名
- `FUDAN_NET_PASSWORD`：`.env` 模式下的校园网密码
- `FUDAN_NET_BASE_URL`：认证门户地址，默认 `http://10.102.250.36`
- `FUDAN_NET_CHANNEL_NAME`：网络出口名称，默认校园网
- `FUDAN_NET_INTERVAL`：监测间隔秒数，默认 `5`
- `FUDAN_NET_CHECK_TIMEOUT`：单个外网目标的检测超时时间，默认 `3`
- `FUDAN_NET_CHECK_URLS`：用于检测真实外网连通性的 URL 列表，使用英文逗号分隔

配置优先级：托盘设置高于 `.env`，`.env` 高于内置默认值。

## 流量统计

托盘程序每秒采样一次当前活跃的非虚拟网卡，显示实时上传/下载速度，以及今日和本月累计流量。这些数据来自 Windows 本机网卡计数器，是本地近似统计，不是校园网门户侧的账单或计费数据。

如果 Windows 重置了网卡计数器，程序会忽略负增量，避免累计值被倒扣。如果同时存在 VPN、热点或多个网卡，第一版会选择流量最高的非虚拟网卡。

## 开发环境

推荐使用 Anaconda/Miniconda 环境进行本地开发和测试：

```powershell
conda env create -f environment.yml
conda activate fudan-web-tool
python -m pytest
```

如果环境已经存在，依赖变更后可以更新环境：

```powershell
conda env update -f environment.yml --prune
conda activate fudan-web-tool
```

也可以使用普通 Python 虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev,build]
python -m pytest
```

## 使用方法

### 预打包 EXE

`dist\FudanWebTool.exe` 是 PyInstaller 打包出的独立 Windows 可执行文件。它已经包含 Python 运行时、项目代码、托盘图标、Qt 库以及托盘程序运行需要的其它依赖，所以运行时不需要源码目录，也不需要 Conda 环境或已安装的 `fudan-web-tool` 命令。

你可以只复制 `FudanWebTool.exe` 到同一台 Windows 电脑上的其它文件夹中运行。用户设置、保存的凭据和流量累计仍然会写入 Windows 用户目录中的标准位置：`%APPDATA%\FudanWebTool\config.json`、`%APPDATA%\FudanWebTool\traffic.json` 和 Windows 凭据管理器。

源码目录只在开发、测试、修改代码或重新打包 EXE 时需要。被 Git 忽略的 `build\` 目录只是可删除的构建缓存；被 Git 忽略的 `dist\` 目录保存生成好的可执行文件。

以 Windows 托盘程序运行：

```powershell
fudan-web-tool tray
```

这个命令会启动独立的后台托盘进程，然后把控制权还给终端。关闭终端不会关闭托盘程序。需要停止时，请使用托盘菜单里的退出。

仅调试时，可以让托盘循环留在当前终端：

```powershell
fudan-web-tool tray --foreground
```

只检查当前状态，不执行登录：

```powershell
fudan-web-tool status
```

执行一次网络恢复流程：

```powershell
fudan-web-tool once
```

以前台进程持续监测并自动恢复网络：

```powershell
fudan-web-tool watch
```

## 打包 EXE

安装构建依赖后，运行：

```powershell
.\scripts\build-windows.ps1
```

PyInstaller 配置使用 `console=False`，打包后的程序会作为后台托盘程序启动，而不是保留持续控制台窗口。

## 文档维护

修改面向用户的安装、配置或使用说明时，请保持 `README.md` 和 `README-zh.md` 同步。
