# FudanWebTool

[English README](README.md)

FudanWebTool 是一个轻量级命令行工具，用于监测复旦校园网的真实外网连通性，并在断线时自动重新认证。

它以前台命令行守护进程的形式运行。工具会先检测真实外网是否可达，只有需要恢复网络时才访问复旦认证门户。如果门户页面显示“认证成功”，但外网实际不可达，工具会先注销当前假在线状态，再重新选择校园网出口登录。

## 功能

- 周期性网络健康检查
- 校园网网关登录请求
- 通过环境变量安全配置
- 输出重连尝试和失败原因日志
- 针对“门户已认证但外网不可用”的假在线状态，自动注销后重连

## 配置

先复制 `.env.example` 为本地 `.env`，再填写你的本地账号信息。真实账号和密码只应保存在 `.env` 中。

```powershell
Copy-Item .env.example .env
```

不要提交 `.env`；它已经被 Git 忽略。

可用配置项：

- `FUDAN_NET_USERNAME`：校园网用户名
- `FUDAN_NET_PASSWORD`：校园网密码
- `FUDAN_NET_BASE_URL`：认证门户地址，默认 `http://10.102.250.36`
- `FUDAN_NET_CHANNEL_NAME`：网络出口名称，默认 `校园网`
- `FUDAN_NET_INTERVAL`：watch 模式两次检测之间的间隔秒数，默认 `5`
- `FUDAN_NET_CHECK_TIMEOUT`：单个外网目标的检测超时时间，默认 `3`
- `FUDAN_NET_CHECK_URLS`：用于检测真实外网连通性的 URL 列表，使用英文逗号分隔

## 文档维护

修改面向用户的安装、配置或使用说明时，请保持 `README.md` 和 `README-zh.md` 同步。

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

如果 PowerShell 中无法使用 `conda activate`，先初始化 Conda，然后重启终端：

```powershell
conda init powershell
```

命令行入口会安装到这个 Conda 环境中，所以运行工具前请先激活环境：

```powershell
conda activate fudan-web-tool
fudan-web-tool status
```

也可以使用普通 Python 虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python -m pytest
```

## 使用方法

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
