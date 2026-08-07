"""GUI 界面模块 - 主界面和配置界面"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

from config import load_config, save_config, is_configured, get_config_path
from sender import send_email, build_subject, build_body

# 尝试导入 tkinterdnd2 以支持拖放
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False


class ConfigDialog:
    """配置对话框"""

    def __init__(self, parent):
        self.result = False  # 是否保存了配置

        self.win = tk.Toplevel(parent)
        self.win.title("邮件发送设置")
        self.win.resizable(False, False)
        self.win.grab_set()  # 模态窗口

        # 居中显示
        self.win.geometry("460x340")
        self.win.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 460) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 340) // 2
        self.win.geometry(f"+{x}+{y}")

        config = load_config()

        main_frame = ttk.Frame(self.win, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # QQ 邮箱地址
        ttk.Label(main_frame, text="QQ 邮箱地址:").grid(row=0, column=0, sticky=tk.W, pady=6)
        self.sender_var = tk.StringVar(value=config.get("sender_email", ""))
        ttk.Entry(main_frame, textvariable=self.sender_var, width=35).grid(
            row=0, column=1, pady=6, padx=(10, 0)
        )

        # 授权码
        ttk.Label(main_frame, text="授权码:").grid(row=1, column=0, sticky=tk.W, pady=6)
        self.auth_var = tk.StringVar(value=config.get("auth_code", ""))
        ttk.Entry(main_frame, textvariable=self.auth_var, width=35, show="*").grid(
            row=1, column=1, pady=6, padx=(10, 0)
        )

        # 收件人
        ttk.Label(main_frame, text="收件人邮箱:").grid(row=2, column=0, sticky=tk.W, pady=6)
        self.receiver_var = tk.StringVar(value=config.get("receiver_email", ""))
        ttk.Entry(main_frame, textvariable=self.receiver_var, width=35).grid(
            row=2, column=1, pady=6, padx=(10, 0)
        )

        # 主题前缀
        ttk.Label(main_frame, text="主题前缀:").grid(row=3, column=0, sticky=tk.W, pady=6)
        self.prefix_var = tk.StringVar(value=config.get("subject_prefix", "文件分享: "))
        ttk.Entry(main_frame, textvariable=self.prefix_var, width=35).grid(
            row=3, column=1, pady=6, padx=(10, 0)
        )

        # 自动发送选项
        self.auto_send_var = tk.BooleanVar(value=config.get("auto_send", True))
        ttk.Checkbutton(
            main_frame, text="拖入文件后自动发送（无需确认）", variable=self.auto_send_var
        ).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=10)

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=(15, 0))

        ttk.Button(btn_frame, text="保存", command=self._save, width=10).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="取消", command=self.win.destroy, width=10).pack(
            side=tk.LEFT, padx=5
        )

        # 提示文字
        hint = ttk.Label(
            main_frame,
            text="提示: 授权码在 QQ邮箱 → 设置 → 账户 → POP3/SMTP服务 中获取",
            foreground="gray",
            font=("", 8),
        )
        hint.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

    def _save(self):
        sender = self.sender_var.get().strip()
        auth = self.auth_var.get().strip()
        receiver = self.receiver_var.get().strip()

        if not sender or not auth or not receiver:
            messagebox.showwarning("提示", "请填写邮箱地址和授权码！", parent=self.win)
            return

        if "@qq.com" not in sender.lower():
            messagebox.showwarning("提示", "发件人邮箱应为 QQ 邮箱（xxx@qq.com）", parent=self.win)
            return

        config = {
            "sender_email": sender,
            "auth_code": auth,
            "receiver_email": receiver,
            "subject_prefix": self.prefix_var.get().strip(),
            "auto_send": self.auto_send_var.get(),
        }
        save_config(config)
        self.result = True
        self.win.destroy()


class MainApp:
    """主应用窗口"""

    def __init__(self):
        # 根据是否支持拖放选择 Tk 基类
        if HAS_DND:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()

        self.root.title("QQ邮箱一键发送")
        self.root.geometry("500x320")
        self.root.resizable(True, True)

        # 居中显示
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - 500) // 2
        y = (sh - 320) // 2
        self.root.geometry(f"+{x}+{y}")

        self._build_ui()
        self._setup_dnd()

        # 首次启动检查配置
        if not is_configured(load_config()):
            self.root.after(100, self._show_config)

    def _build_ui(self):
        """构建界面"""
        # 顶部工具栏
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=10, pady=(10, 0))

        ttk.Button(toolbar, text="⚙ 设置", command=self._show_config, width=8).pack(
            side=tk.LEFT
        )

        self.topmost_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            toolbar, text="窗口置顶", variable=self.topmost_var, command=self._toggle_topmost
        ).pack(side=tk.LEFT, padx=10)

        ttk.Button(toolbar, text="选择文件", command=self._select_files, width=10).pack(
            side=tk.RIGHT
        )

        # 拖放区域
        drop_frame = ttk.LabelFrame(self.root, text="拖入文件发送", padding=10)
        drop_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.drop_label = tk.Label(
            drop_frame,
            text="📁\n\n将文件拖放到此处\n即可自动发送邮件\n\n（也支持点击上方「选择文件」按钮）",
            font=("", 14),
            fg="#666666",
            justify=tk.CENTER,
            cursor="hand2",
        )
        self.drop_label.pack(fill=tk.BOTH, expand=True)
        self.drop_label.bind("<Button-1>", lambda e: self._select_files())

        # 状态栏
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10, pady=(0, 8))

        self.status_var = tk.StringVar(value="就绪 - 请拖入文件或点击选择文件")
        self.status_label = ttk.Label(
            status_frame, textvariable=self.status_var, foreground="#333333"
        )
        self.status_label.pack(side=tk.LEFT)

        self.config_path_var = tk.StringVar()
        ttk.Label(
            status_frame, textvariable=self.config_path_var, foreground="gray", font=("", 7)
        ).pack(side=tk.RIGHT)

        # 显示配置路径
        self.config_path_var.set(f"配置: {get_config_path()}")

    def _setup_dnd(self):
        """设置拖放支持"""
        if HAS_DND:
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind("<<Drop>>", self._on_drop)
        else:
            # 无拖放支持时更新提示文字
            current_text = self.drop_label.cget("text")
            self.drop_label.config(
                text=current_text.replace("将文件拖放到此处\n即可自动发送邮件\n\n", "")
                + "\n\n（拖放支持未启用，请点击选择文件）"
            )

    def _on_drop(self, event):
        """处理拖放事件"""
        # tkinterdnd2 返回的文件路径格式: 多文件用空格分隔，路径有空格时用 {} 包裹
        raw = event.data
        file_paths = self._parse_dnd_files(raw)
        if file_paths:
            self._process_files(file_paths)

    def _parse_dnd_files(self, raw: str) -> list[str]:
        """解析拖放的文件路径"""
        paths = []
        # 处理 Windows 路径格式
        i = 0
        while i < len(raw):
            if raw[i] == "{":
                # 找到对应的 }
                end = raw.index("}", i)
                paths.append(raw[i + 1 : end])
                i = end + 2  # 跳过 } 和空格
            else:
                # 找到下一个空格或结尾
                end = raw.find(" ", i)
                if end == -1:
                    end = len(raw)
                path = raw[i:end]
                if path:
                    paths.append(path)
                i = end + 1

        # 过滤：只保留存在的文件
        valid = []
        for p in paths:
            p = p.strip()
            if p and Path(p).is_file():
                valid.append(p)

        return valid

    def _select_files(self):
        """通过文件选择对话框选择文件"""
        file_paths = filedialog.askopenfilenames(
            title="选择要发送的文件",
            parent=self.root,
        )
        if file_paths:
            self._process_files(list(file_paths))

    def _process_files(self, file_paths: list[str]):
        """处理文件：发送邮件"""
        config = load_config()

        if not is_configured(config):
            messagebox.showwarning("提示", "请先配置邮箱信息！", parent=self.root)
            self._show_config()
            return

        # 构建邮件内容
        subject = build_subject(config["subject_prefix"], file_paths)
        body = build_body(file_paths)

        # 如果不自动发送，弹出确认
        if not config.get("auto_send", True):
            file_names = "\n".join(Path(p).name for p in file_paths)
            confirm = messagebox.askyesno(
                "确认发送",
                f"将发送以下文件到 {config['receiver_email']}:\n\n{file_names}\n\n确认发送？",
                parent=self.root,
            )
            if not confirm:
                return

        # 在后台线程中发送
        self._set_status_sending(file_paths)
        thread = threading.Thread(
            target=self._send_in_thread,
            args=(config, subject, body, file_paths),
            daemon=True,
        )
        thread.start()

    def _send_in_thread(self, config: dict, subject: str, body: str, file_paths: list[str]):
        """在后台线程中发送邮件"""
        result = send_email(
            sender_email=config["sender_email"],
            auth_code=config["auth_code"],
            receiver_email=config["receiver_email"],
            subject=subject,
            body=body,
            file_paths=file_paths,
        )
        # 在主线程中更新状态
        self.root.after(0, self._on_send_complete, result)

    def _set_status_sending(self, file_paths: list[str]):
        """设置发送中状态"""
        count = len(file_paths)
        names = ", ".join(Path(p).name for p in file_paths[:3])
        if count > 3:
            names += f" 等{count}个文件"
        self.status_var.set(f"⏳ 正在发送: {names} ...")
        self.status_label.config(foreground="#CC8800")
        self.drop_label.config(fg="#CC8800", text="⏳\n\n正在发送中...\n请稍候")

    def _on_send_complete(self, result: dict):
        """发送完成回调"""
        if result["success"]:
            self.status_var.set(f"✅ {result['message']} ({result['time']:.1f}s)")
            self.status_label.config(foreground="#008800")
            self.drop_label.config(
                fg="#008800",
                text=f"✅\n\n发送成功!\n{result['message']}\n\n继续拖入文件发送",
            )
        else:
            self.status_var.set(f"❌ {result['message']}")
            self.status_label.config(foreground="#CC0000")
            self.drop_label.config(
                fg="#CC0000",
                text=f"❌\n\n发送失败\n{result['message']}\n\n拖入文件重试",
            )

        # 5秒后恢复默认状态
        self.root.after(
            5000,
            lambda: (
                self.status_var.set("就绪 - 请拖入文件或点击选择文件"),
                self.status_label.config(foreground="#333333"),
                self.drop_label.config(
                    fg="#666666",
                    text="📁\n\n将文件拖放到此处\n即可自动发送邮件\n\n（也支持点击上方「选择文件」按钮）",
                ),
            ),
        )

    def _show_config(self):
        """显示配置对话框"""
        dialog = ConfigDialog(self.root)
        self.root.wait_window(dialog.win)
        if dialog.result:
            self.status_var.set("✅ 配置已保存，可以拖入文件发送了")
            self.status_label.config(foreground="#008800")

    def _toggle_topmost(self):
        """切换窗口置顶"""
        self.root.attributes("-topmost", self.topmost_var.get())

    def run(self):
        """启动应用"""
        self.root.mainloop()
