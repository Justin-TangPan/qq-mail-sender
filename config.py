"""配置管理模块 - 读写 QQ 邮箱发送器的配置信息"""

import json
import os
from pathlib import Path

# 配置文件路径: %APPDATA%\qq-mail-sender\config.json
_config_dir = Path(os.environ.get("APPDATA", Path.home())) / "qq-mail-sender"
_config_file = _config_dir / "config.json"

# 默认配置
DEFAULT_CONFIG = {
    "sender_email": "",        # QQ 邮箱地址，如 123456789@qq.com
    "auth_code": "",           # QQ 邮箱授权码
    "receiver_email": "",      # 收件人邮箱地址
    "subject_prefix": "文件分享: ",  # 邮件主题前缀
    "auto_send": True,         # 拖入后是否自动发送（无需确认）
}


def ensure_config_dir():
    """确保配置目录存在"""
    _config_dir.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    """加载配置，如果文件不存在则返回默认配置"""
    if not _config_file.exists():
        return DEFAULT_CONFIG.copy()
    try:
        with open(_config_file, "r", encoding="utf-8") as f:
            saved = json.load(f)
        # 合并：已保存的值覆盖默认值，新增字段使用默认值
        config = DEFAULT_CONFIG.copy()
        config.update(saved)
        return config
    except (json.JSONDecodeError, IOError):
        return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """保存配置到文件"""
    ensure_config_dir()
    # 只保存非默认值和有意义的字段
    with open(_config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def is_configured(config: dict) -> bool:
    """检查必要配置是否已填写"""
    return bool(
        config.get("sender_email")
        and config.get("auth_code")
        and config.get("receiver_email")
    )


def get_config_path() -> str:
    """返回配置文件路径（用于显示给用户）"""
    return str(_config_file)
