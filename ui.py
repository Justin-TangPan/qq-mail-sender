"""GUI 界面模块 - 主界面和配置界面"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from io import BytesIO

from config import load_config, save_config, is_configured, get_config_path
from sender import send_email, send_content_email, build_subject, build_body

# 尝试导入 tkinterdnd2 以支持拖放
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

# 尝试导入 Pillow 以支持剪贴板图片
try:
    from PIL import Image, ImageGrab, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


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
            main_frame, text="发送前不弹出确认对话框", variable=self.auto_send_var
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


class ContentTab:
    """图文内容发送标签页"""

    def __init__(self, parent, app: "MainApp"):
        self.app = app
        self.frame = ttk.Frame(parent)
        self.pasted_image = None  # PIL.Image 对象
        self._photo = None  # 保持 PhotoImage 引用防止被回收

        self._build_ui()

    def _build_ui(self):
        """构建图文内容标签页界面"""
        # 按钮工具栏
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill=tk.X, padx=8, pady=(8, 4))

        ttk.Button(toolbar, text="📋 粘贴图片", command=self._paste_image, width=12).pack(
            side=tk.LEFT
        )
        ttk.Button(toolbar, text="❌ 清空", command=self._clear_all, width=10).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(toolbar, text="📤 发送", command=self._send, width=10).pack(
            side=tk.RIGHT
        )

        # 反馈提示条
        self.feedback_var = tk.StringVar(value="")
        self.feedback_label = tk.Label(self.frame, textvariable=self.feedback_var, font=("", 10), fg="#333333")
        self.feedback_label.pack(fill=tk.X, padx=8, pady=(0, 2))

        # 图文输入区
        text_frame = ttk.LabelFrame(self.frame, text="图文内容（可粘贴文字）", padding=4)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self.text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("", 11), undo=True)
        text_scroll = ttk.Scrollbar(text_frame, command=self.text_widget.yview)
        self.text_widget.configure(yscrollcommand=text_scroll.set)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_widget.pack(fill=tk.BOTH, expand=True)

        # 绑定粘贴事件：Ctrl+V 时先检查剪贴板是否有图片
        self.text_widget.bind("<<Paste>>", self._on_paste)
        self.text_widget.bind("<Control-v>", self._on_paste)

        # 图片预览区（固定高度，防止图片无法显示）
        img_frame = ttk.LabelFrame(self.frame, text="图片预览", padding=4, height=180)
        img_frame.pack(fill=tk.X, padx=8, pady=(4, 8))
        img_frame.pack_propagate(False)

        self.img_label = tk.Label(
            img_frame,
            text="（无图片）\n截图后按 Ctrl+V 粘贴，或点击「粘贴图片」按钮",
            fg="#999999",
            justify=tk.CENTER,
        )
        self.img_label.pack(fill=tk.BOTH, expand=True)

        if not HAS_PIL:
            self.img_label.config(
                text="⚠ 未安装 Pillow，无法粘贴图片\n请运行: pip install Pillow",
                fg="#CC0000",
            )

    def _on_paste(self, event):
        """Ctrl+V 粘贴：优先检查剪贴板图片，无图片则正常粘贴文本"""
        if HAS_PIL:
            try:
                img = ImageGrab.grabclipboard()
                if img is not None and isinstance(img, Image.Image):
                    self._set_image(img)
                    return "break"  # 阻止默认文本粘贴
            except Exception:
                pass
        # 没有图片，正常粘贴文本（不阻止默认行为）
        return None

    def _paste_image(self):
        """从剪贴板粘贴图片"""
        if not HAS_PIL:
            messagebox.showwarning("提示", "未安装 Pillow，无法读取剪贴板图片。\n请运行: pip install Pillow")
            return

        try:
            img = ImageGrab.grabclipboard()
        except Exception as e:
            messagebox.showerror("错误", f"读取剪贴板失败: {e}")
            return

        if img is None:
            messagebox.showinfo("提示", "剪贴板中没有图片。\n请先截图（Win+Shift+S）或复制图片。")
            return

        if not isinstance(img, Image.Image):
            messagebox.showinfo("提示", "剪贴板中的内容不是图片。")
            return

        self._set_image(img)

    def _set_image(self, img: "Image.Image"):
        """设置当前图片并显示预览"""
        self.pasted_image = img
        w, h = img.size

        # 等比缩放生成预览（最大 480x150）
        max_w, max_h = 480, 150
        ratio = min(max_w / w, max_h / h, 1.0)
        preview = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(preview)

        self.img_label.config(
            image=self._photo,
            text=f"✅ 已粘贴图片 ({w}x{h})",
            compound=tk.TOP,
            fg="#008800",
        )
        self.app.status_var.set(f"已粘贴图片 ({w}x{h})，可输入文本后点击发送")

    def _clear_all(self):
        """清空文本和图片"""
        self.text_widget.delete("1.0", tk.END)
        self.pasted_image = None
        self._photo = None
        self.img_label.config(
            image="",
            text="（无图片）\n截图后按 Ctrl+V 粘贴，或点击「粘贴图片」按钮",
            fg="#999999",
            compound=tk.NONE,
        )
        self.app.status_var.set("已清空")
        self.feedback_var.set("")

    def _send(self):
        """发送图文内容"""
        config = load_config()

        if not is_configured(config):
            messagebox.showwarning("提示", "请先配置邮箱信息！", parent=self.app.root)
            self.app._show_config()
            return

        text_content = self.text_widget.get("1.0", tk.END).strip()
        has_image = self.pasted_image is not None

        if not text_content and not has_image:
            messagebox.showinfo("提示", "请输入文本或粘贴图片后再发送！", parent=self.app.root)
            return

        # 构建主题
        prefix = config.get("subject_prefix", "文件分享: ")
        if has_image and text_content:
            subject = f"{prefix}文本及图片"
        elif has_image:
            subject = f"{prefix}图片分享"
        else:
            subject = f"{prefix}文本分享"

        # 图片转 bytes
        image_bytes = None
        if has_image:
            buf = BytesIO()
            self.pasted_image.save(buf, format="PNG")
            image_bytes = buf.getvalue()

        # 如果不自动发送，弹出确认
        if not config.get("auto_send", True):
            parts = []
            if text_content:
                preview_text = text_content[:50] + "..." if len(text_content) > 50 else text_content
                parts.append(f"文本: {preview_text}")
            if has_image:
                parts.append(f"图片: {self.pasted_image.size[0]}x{self.pasted_image.size[1]}")
            confirm = messagebox.askyesno(
                "确认发送",
                f"将发送以下内容到 {config['receiver_email']}:\n\n" + "\n".join(parts) + "\n\n确认发送？",
                parent=self.app.root,
            )
            if not confirm:
                return

        # 设置发送中状态
        self.app._set_status_sending_content(text_content, has_image)
        self.feedback_var.set("⏳ 正在发送...")
        self.feedback_label.config(fg="#CC8800")

        # 在后台线程中发送
        thread = threading.Thread(
            target=self._send_in_thread,
            args=(config, subject, text_content, image_bytes),
            daemon=True,
        )
        thread.start()

    def _send_in_thread(self, config: dict, subject: str, text_content: str, image_bytes: bytes | None):
        """在后台线程中发送内容邮件"""
        result = send_content_email(
            sender_email=config["sender_email"],
            auth_code=config["auth_code"],
            receiver_email=config["receiver_email"],
            subject=subject,
            text_content=text_content,
            image_bytes=image_bytes,
        )
        self.app.root.after(0, self._on_content_send_complete, result)

    def _on_content_send_complete(self, result: dict):
        """图文内容发送完成回调"""
        if result["success"]:
            msg = f"✅ {result['message']} ({result['time']:.1f}s)"
            self.feedback_var.set(msg)
            self.feedback_label.config(fg="#008800")
            self.app.status_var.set(msg)
            self.app.status_label.config(foreground="#008800")
            messagebox.showinfo("发送成功", result["message"], parent=self.app.root)
        else:
            msg = f"❌ {result['message']}"
            self.feedback_var.set(msg)
            self.feedback_label.config(fg="#CC0000")
            self.app.status_var.set(msg)
            self.app.status_label.config(foreground="#CC0000")
            messagebox.showerror("发送失败", result["message"], parent=self.app.root)

        # 5秒后清空反馈提示
        self.app.root.after(5000, lambda: self.feedback_var.set(""))


class MainApp:
    """主应用窗口"""

    def __init__(self):
        # 根据是否支持拖放选择 Tk 基类
        if HAS_DND:
            self.root = TkinterDnD.Tk()
        else:
            self.root = tk.Tk()

        self.root.title("QQ邮箱一键发送")
        self.root.geometry("560x460")
        self.root.resizable(True, True)

        # 居中显示
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - 560) // 2
        y = (sh - 460) // 2
        self.root.geometry(f"+{x}+{y}")

        self.queued_files: list[str] = []

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

        # 选项卡
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- 标签页 1: 文件发送 ---
        file_tab = ttk.Frame(self.notebook)
        self.notebook.add(file_tab, text="📁 文件发送")

        # 拖放提示
        self.drop_label = tk.Label(
            file_tab,
            text="📁 拖入文件到下方列表，或点击「选择文件」按钮添加",
            font=("", 10),
            fg="#666666",
            justify=tk.CENTER,
            cursor="hand2",
            height=2,
        )
        self.drop_label.pack(fill=tk.X, padx=4, pady=(4, 2))
        self.drop_label.bind("<Button-1>", lambda e: self._select_files())

        # 文件列表
        list_frame = ttk.Frame(file_tab)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)

        self.file_listbox = tk.Listbox(
            list_frame, font=("", 10), selectmode=tk.EXTENDED, activestyle="underline"
        )
        list_scroll = ttk.Scrollbar(list_frame, command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=list_scroll.set)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_listbox.pack(fill=tk.BOTH, expand=True)

        # 空列表提示
        self._update_file_listbox()

        # 文件操作按钮
        file_btn_frame = ttk.Frame(file_tab)
        file_btn_frame.pack(fill=tk.X, padx=4, pady=(2, 4))

        ttk.Button(file_btn_frame, text="📂 选择文件", command=self._select_files, width=12).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(file_btn_frame, text="➖ 移除选中", command=self._remove_selected_files, width=12).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(file_btn_frame, text="❌ 清空列表", command=self._clear_file_queue, width=12).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(file_btn_frame, text="📤 发送", command=self._send_queued_files, width=10).pack(
            side=tk.RIGHT, padx=2
        )

        # --- 标签页 2: 图文内容 ---
        self.content_tab = ContentTab(self.notebook, self)
        self.notebook.add(self.content_tab.frame, text="📝 图文内容")

        # 状态栏
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10, pady=(0, 8))

        self.status_var = tk.StringVar(value="就绪 - 请拖入文件或切换到图文内容标签页")
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
            self.file_listbox.drop_target_register(DND_FILES)
            self.file_listbox.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event):
        """处理拖放事件"""
        raw = event.data
        file_paths = self._parse_dnd_files(raw)
        if file_paths:
            self._add_files(file_paths)

    def _parse_dnd_files(self, raw: str) -> list[str]:
        """解析拖放的文件路径"""
        paths = []
        i = 0
        while i < len(raw):
            if raw[i] == "{":
                end = raw.index("}", i)
                paths.append(raw[i + 1 : end])
                i = end + 2
            else:
                end = raw.find(" ", i)
                if end == -1:
                    end = len(raw)
                path = raw[i:end]
                if path:
                    paths.append(path)
                i = end + 1

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
            self._add_files(list(file_paths))

    def _add_files(self, file_paths: list[str]):
        """添加文件到发送队列"""
        added = 0
        for p in file_paths:
            if p not in self.queued_files:
                self.queued_files.append(p)
                added += 1
        self._update_file_listbox()
        if added:
            self.status_var.set(f"已添加 {added} 个文件到列表（共 {len(self.queued_files)} 个）")
            self.status_label.config(foreground="#333333")

    def _remove_selected_files(self):
        """移除列表中选中的文件"""
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showinfo("提示", "请先在列表中选中要移除的文件", parent=self.root)
            return
        # 从后往前删，避免索引错位
        for idx in sorted(selection, reverse=True):
            del self.queued_files[idx]
        self._update_file_listbox()
        self.status_var.set(f"已移除，列表剩余 {len(self.queued_files)} 个文件")

    def _clear_file_queue(self):
        """清空文件列表"""
        if not self.queued_files:
            return
        self.queued_files.clear()
        self._update_file_listbox()
        self.status_var.set("已清空文件列表")

    def _update_file_listbox(self):
        """刷新文件列表显示"""
        self.file_listbox.delete(0, tk.END)
        if not self.queued_files:
            self.file_listbox.insert(tk.END, "（列表为空，拖入文件或点击「选择文件」添加）")
            self.file_listbox.config(fg="#999999")
        else:
            self.file_listbox.config(fg="#333333")
            for i, p in enumerate(self.queued_files, 1):
                self.file_listbox.insert(tk.END, f"{i}. {Path(p).name}")

    def _send_queued_files(self):
        """发送列表中所有文件"""
        config = load_config()

        if not is_configured(config):
            messagebox.showwarning("提示", "请先配置邮箱信息！", parent=self.root)
            self._show_config()
            return

        if not self.queued_files:
            messagebox.showinfo("提示", "文件列表为空，请先添加文件！", parent=self.root)
            return

        file_paths = list(self.queued_files)

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
        self.root.after(0, self._on_send_complete, result)

    def _set_status_sending(self, file_paths: list[str]):
        """设置发送中状态"""
        count = len(file_paths)
        names = ", ".join(Path(p).name for p in file_paths[:3])
        if count > 3:
            names += f" 等{count}个文件"
        self.status_var.set(f"⏳ 正在发送: {names} ...")
        self.status_label.config(foreground="#CC8800")

    def _set_status_sending_content(self, text_content: str, has_image: bool):
        """设置图文内容发送中状态"""
        parts = []
        if text_content:
            parts.append("文本")
        if has_image:
            parts.append("图片")
        desc = " + ".join(parts)
        self.status_var.set(f"⏳ 正在发送{desc} ...")
        self.status_label.config(foreground="#CC8800")

    def _on_send_complete(self, result: dict):
        """发送完成回调"""
        if result["success"]:
            msg = f"✅ {result['message']} ({result['time']:.1f}s)"
            self.status_var.set(msg)
            self.status_label.config(foreground="#008800")
            # 发送成功后清空文件列表
            if self.queued_files:
                self.queued_files.clear()
                self._update_file_listbox()
            messagebox.showinfo("发送成功", result["message"], parent=self.root)
        else:
            msg = f"❌ {result['message']}"
            self.status_var.set(msg)
            self.status_label.config(foreground="#CC0000")
            messagebox.showerror("发送失败", result["message"], parent=self.root)

        # 5秒后恢复默认状态
        self.root.after(
            5000,
            lambda: (
                self.status_var.set("就绪 - 请拖入文件或切换到图文内容标签页"),
                self.status_label.config(foreground="#333333"),
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
