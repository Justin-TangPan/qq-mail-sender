# QQ邮箱一键发送 📬

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)](https://github.com/your-repo)

> 一个小巧的 Windows 桌面应用，拖入文件即可自动通过 QQ 邮箱发送邮件。

简体中文 | [English](README_EN.md)

## 🖼️ 界面预览

*（截图待补充）*

## ✨ 功能特点

- 🖱️ **拖放发送** — 将文件拖入窗口即可自动发送，无需额外操作
- 📎 **多文件支持** — 可同时拖入多个文件作为附件
- 📝 **粘贴发送** — 支持粘贴文本或图片（截图后 Ctrl+V），直接作为邮件内容发送
- ⚙️ **应用内配置** — 图形界面配置邮箱信息，无需手动编辑文件
- 📌 **窗口置顶** — 可选保持窗口在最前面，方便反复拖入
- 🔒 **本地存储** — 配置信息保存在本地，不上传任何数据
- 🚀 **免 Python 运行** — 提供编译好的 exe 直接运行

## 🚀 快速开始

### 方法一：直接运行 exe

从 [Releases](https://github.com/your-repo/qq-mail-sender/releases) 页面下载 `QQ邮箱一键发送.exe`，双击运行即可。

### 方法二：源码运行

#### 1. 获取 QQ 邮箱授权码

> ⚠️ QQ 邮箱不能使用登录密码发送邮件，必须使用**授权码**。

1. 登录 [QQ邮箱](https://mail.qq.com)
2. 点击 **设置** → **账户**
3. 找到 **POP3/SMTP服务**，点击 **开启**
4. 按提示用手机发送短信验证
5. 验证成功后会得到一个 **16位授权码**，复制保存

#### 2. 运行应用

```bash
# 确保已安装 Python 3.8+
pip install tkinterdnd2  # 可选，用于拖放支持
pip install Pillow       # 可选，用于粘贴图片支持
python main.py
```

#### 3. 首次配置

首次启动会自动弹出设置界面，填入：
- **QQ 邮箱地址** — 你的 QQ 邮箱，如 `123456789@qq.com`
- **授权码** — 上一步获取的 16 位授权码
- **收件人邮箱** — 接收文件的邮箱地址
- **主题前缀** — 邮件主题前缀，默认 `文件分享: `

#### 4. 使用

- 将文件拖放到窗口区域 → 自动发送
- 或点击 **选择文件** 按钮手动选择
- 切换到 **文本/图片** 标签页，可粘贴文字或截图（Ctrl+V）直接发送
- 发送成功后窗口会显示绿色提示，5秒后自动恢复

## 📦 自行打包

使用 PyInstaller 打包为独立的 exe 文件：

```bash
pip install pyinstaller

# 打包为单文件 exe
pyinstaller --onefile --windowed --name "QQ邮箱一键发送" \
    --hidden-import tkinterdnd2 \
    --hidden-import PIL.ImageGrab \
    main.py
```

打包后的 exe 在 `dist/` 目录下。

## ⚙️ 配置文件

配置保存在: `%APPDATA%\qq-mail-sender\config.json`

```json
{
  "sender_email": "123456789@qq.com",
  "auth_code": "abcdefghijklmnop",
  "receiver_email": "someone@example.com",
  "subject_prefix": "文件分享: ",
  "auto_send": true
}
```

## 📁 项目结构

```
qq-mail-sender/
├── main.py          # 程序入口
├── ui.py            # GUI 界面（Tkinter）
├── sender.py        # 邮件发送模块（SMTP）
├── config.py        # 配置读写模块
├── README.md        # 本文件
└── .gitignore
```

## ❓ 常见问题

### 发送失败：认证失败
- 检查授权码是否正确（不是 QQ 密码）
- 确认 QQ 邮箱已开启 SMTP 服务

### 发送失败：连接失败
- 检查网络连接
- 公司网络可能屏蔽了 465 端口

### 拖放不生效
- 安装 `tkinterdnd2`: `pip install tkinterdnd2`
- 或使用 **选择文件** 按钮代替拖放

### 粘贴图片不生效
- 安装 Pillow: `pip install Pillow`
- 确保剪贴板中有图片（如用 Win+Shift+S 截图）
- 或点击「粘贴图片」按钮手动粘贴

### 附件过大
- QQ 邮箱单封邮件附件上限约 50MB
- 超大文件建议使用网盘分享

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request
