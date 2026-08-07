"""邮件发送模块 - 通过 QQ 邮箱 SMTP 服务器发送带附件的邮件"""

import smtplib
import os
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

# QQ 邮箱 SMTP 服务器配置
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465  # SSL 端口


def send_email(
    sender_email: str,
    auth_code: str,
    receiver_email: str,
    subject: str,
    body: str,
    file_paths: list[str],
) -> dict:
    """
    发送带附件的邮件。

    参数:
        sender_email: 发件人 QQ 邮箱地址
        auth_code: QQ 邮箱授权码
        receiver_email: 收件人邮箱地址
        subject: 邮件主题
        body: 邮件正文
        file_paths: 附件文件路径列表

    返回:
        dict: {"success": bool, "message": str, "time": float}
    """
    start_time = time.time()

    try:
        # 构建邮件
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = subject

        # 添加正文
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # 添加附件
        for file_path in file_paths:
            file_path = Path(file_path)
            if not file_path.exists():
                return {
                    "success": False,
                    "message": f"文件不存在: {file_path}",
                    "time": time.time() - start_time,
                }

            with open(file_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())

            encoders.encode_base64(part)
            # 处理中文文件名
            filename = file_path.name
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=("utf-8", "", filename),
            )
            msg.attach(part)

        # 连接 SMTP 服务器并发送
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(sender_email, auth_code)
            server.sendmail(sender_email, [receiver_email], msg.as_string())

        elapsed = time.time() - start_time
        file_names = [Path(p).name for p in file_paths]
        return {
            "success": True,
            "message": f"发送成功! 附件: {', '.join(file_names)}",
            "time": elapsed,
        }

    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "message": "认证失败: 请检查邮箱地址和授权码是否正确",
            "time": time.time() - start_time,
        }
    except smtplib.SMTPConnectError:
        return {
            "success": False,
            "message": "连接失败: 无法连接到 QQ 邮箱服务器，请检查网络",
            "time": time.time() - start_time,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"发送失败: {str(e)}",
            "time": time.time() - start_time,
        }


def build_subject(prefix: str, file_paths: list[str]) -> str:
    """根据文件名自动生成邮件主题"""
    if not file_paths:
        return f"{prefix}无附件"

    names = [Path(p).name for p in file_paths]
    if len(names) == 1:
        return f"{prefix}{names[0]}"
    else:
        # 多文件: 列出第一个 + 等共N个文件
        return f"{prefix}{names[0]} 等共{len(names)}个文件"


def build_body(file_paths: list[str]) -> str:
    """自动生成邮件正文"""
    if not file_paths:
        return "无附件内容。"

    names = [Path(p).name for p in file_paths]
    if len(names) == 1:
        return f"附件为发送的文件: {names[0]}\n\n请查收。"
    else:
        file_list = "\n".join(f"  - {n}" for n in names)
        return f"附件为发送的 {len(names)} 个文件:\n{file_list}\n\n请查收。"
