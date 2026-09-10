"""LicenseProtector 图形界面。

界面只负责收集参数和展示进度，实际的扫描、签名、注入和打包逻辑由
项目中的业务模块完成。这样可以保证 GUI 和命令行入口使用同一套核心逻辑。

开发者：Stephen Hu <stephenhu031028@gmail.com>
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.package.builder import BuildRequest, PackageBuilder


class MainWindow:
    """LicenseProtector 的主窗口。"""

    COLORS = {
        "navy": "#14213D",
        "blue": "#2563EB",
        "blue_dark": "#1D4ED8",
        "page": "#F4F7FB",
        "card": "#FFFFFF",
        "border": "#D8E0EC",
        "text": "#172033",
        "muted": "#667085",
        "log": "#101827",
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.values = {key: tk.StringVar() for key in ("project", "domain", "ipv4", "version", "private", "public", "output")}
        self.key_status = tk.StringVar()
        self.status = tk.StringVar(value="就绪，可以开始配置")
        self._configure_window()
        self._configure_style()
        self._set_defaults()
        self._build_layout()
        self._refresh_key_status()

    def _configure_window(self) -> None:
        """设置窗口尺寸和背景。"""
        self.root.title("LicenseProtector | 源码授权保护工具")
        self.root.geometry("940x700")
        self.root.minsize(820, 600)
        self.root.configure(bg=self.COLORS["page"])

    def _configure_style(self) -> None:
        """集中配置 ttk 样式，保持各区域视觉一致。"""
        style = ttk.Style(self.root)
        try:
            style.theme_use("vista")
        except tk.TclError:
            style.theme_use("clam")
        style.configure("Page.TFrame", background=self.COLORS["page"])
        style.configure("Title.TLabel", background=self.COLORS["navy"], foreground="white", font=("Segoe UI", 22, "bold"))
        style.configure("Section.TLabel", background=self.COLORS["card"], foreground=self.COLORS["text"], font=("Segoe UI", 11, "bold"))
        style.configure("Hint.TLabel", background=self.COLORS["card"], foreground=self.COLORS["muted"], font=("Segoe UI", 9))
        style.configure("Field.TLabel", background=self.COLORS["card"], foreground=self.COLORS["text"], font=("Segoe UI", 9))
        style.configure("Status.TLabel", background=self.COLORS["page"], foreground=self.COLORS["muted"], font=("Segoe UI", 9))
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), foreground="white", background=self.COLORS["blue"], padding=(18, 8))
        style.map("Primary.TButton", background=[("active", self.COLORS["blue_dark"]), ("disabled", "#A8B8D1")])
        style.configure("Action.TButton", font=("Segoe UI", 9), padding=(11, 6))
        style.configure("TLabelframe", background=self.COLORS["card"], bordercolor=self.COLORS["border"])
        style.configure("TLabelframe.Label", background=self.COLORS["card"], foreground=self.COLORS["text"], font=("Segoe UI", 10, "bold"))
        style.configure("TEntry", padding=6)

    @staticmethod
    def _application_dir() -> Path:
        """返回程序目录：exe 所在目录，源码运行时的项目根目录。"""
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parents[2]

    def _set_defaults(self) -> None:
        """初始化表单，密钥默认放在软件安装目录的 keys 文件夹。"""
        key_dir = self._application_dir() / "keys"
        # 安装目录可能位于 Program Files，交付包默认放在用户文档目录，避免权限错误。
        delivery_dir = Path.home() / "Documents" / "LicenseProtector" / "deliveries"
        self.values["version"].set("1.0.0")
        self.values["private"].set(str(key_dir / "vendor_private.pem"))
        self.values["public"].set(str(key_dir / "vendor_public.pem"))
        self.values["output"].set(str(delivery_dir))

    def _build_layout(self) -> None:
        """构建标题区、配置区、操作区、日志区和开发者信息。"""
        header = tk.Frame(self.root, bg=self.COLORS["navy"], height=108)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="LicenseProtector", bg=self.COLORS["navy"], fg="white", font=("Segoe UI", 22, "bold"), anchor="w").place(x=30, y=16)
        tk.Label(header, text="离线 PHP 源码授权保护工具  ·  安全、可追溯、无需联网", bg=self.COLORS["navy"], fg="#D9E5FF", font=("Segoe UI", 10), anchor="w").place(x=32, y=58)

        page = ttk.Frame(self.root, style="Page.TFrame", padding=(24, 18, 24, 12))
        page.pack(fill="both", expand=True)
        config = ttk.Frame(page, style="Page.TFrame")
        config.pack(fill="x")
        config.columnconfigure(0, weight=1)
        config.columnconfigure(1, weight=1)
        self._project_card(config).grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._license_card(config).grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self._key_card(page).pack(fill="x", pady=(12, 0))

        actions = ttk.Frame(page, style="Page.TFrame")
        actions.pack(fill="x", pady=(14, 8))
        ttk.Button(actions, text="生成厂商密钥", style="Action.TButton", command=self.generate_keys).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="扫描项目", style="Action.TButton", command=self.scan).pack(side="left", padx=8)
        # ttk 的 Vista 原生主题会忽略自定义前景色，主操作使用 tk.Button 保证蓝底白字。
        self.build_button = tk.Button(
            actions,
            text="生成交付包  ▶",
            command=self.build,
            bg=self.COLORS["blue"],
            fg="white",
            activebackground=self.COLORS["blue_dark"],
            activeforeground="white",
            disabledforeground="#E5E7EB",
            relief="flat",
            borderwidth=0,
            padx=18,
            pady=8,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
        )
        self.build_button.pack(side="right")

        log_frame = ttk.LabelFrame(page, text="运行日志", padding=(10, 8))
        log_frame.pack(fill="both", expand=True)
        self.log = tk.Text(log_frame, height=8, state="disabled", wrap="word", bg=self.COLORS["log"], fg="#D8E4F5", insertbackground="white", relief="flat", padx=10, pady=8, font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        footer = ttk.Frame(self.root, style="Page.TFrame", padding=(24, 0, 24, 12))
        footer.pack(fill="x")
        ttk.Label(footer, textvariable=self.status, style="Status.TLabel").pack(side="left")
        ttk.Label(footer, text="开发者：Stephen Hu  |  stephenhu031028@gmail.com", style="Status.TLabel").pack(side="right")

    def _card(self, parent: ttk.Frame, title: str, hint: str) -> ttk.Frame:
        """创建统一风格的配置分组。"""
        card = ttk.LabelFrame(parent, text=title, padding=(14, 10, 14, 12))
        # 卡片内部统一使用 grid；不能在同一个父容器中混用 pack 和 grid。
        ttk.Label(card, text=hint, style="Hint.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        return card

    def _field(self, parent: ttk.Frame, row: int, label: str, key: str, browse: str | None = None) -> None:
        """添加带标签、输入框和可选浏览按钮的表单项。"""
        # 第 0 行由分组说明占用，表单字段从第 1 行开始。
        field_row = row + 1
        ttk.Label(parent, text=label, style="Field.TLabel", width=12).grid(row=field_row, column=0, sticky="w", pady=4)
        entry = ttk.Entry(parent, textvariable=self.values[key])
        entry.grid(row=field_row, column=1, sticky="ew", pady=4, padx=(0, 6))
        if browse:
            ttk.Button(parent, text="浏览…", style="Action.TButton", command=lambda: self._browse(key, browse)).grid(row=field_row, column=2, sticky="e", pady=2)
        parent.columnconfigure(1, weight=1)

    def _project_card(self, parent: ttk.Frame) -> ttk.Frame:
        card = self._card(parent, "项目配置", "选择待保护的 PHP 项目，并指定交付包保存位置。")
        self._field(card, 0, "项目目录", "project", "project")
        self._field(card, 1, "输出目录", "output", "output")
        return card

    def _license_card(self, parent: ttk.Frame) -> ttk.Frame:
        card = self._card(parent, "授权配置", "域名和 IPv4 至少填写一项；同时填写时支持任一项匹配。")
        self._field(card, 0, "授权域名", "domain")
        self._field(card, 1, "授权 IPv4", "ipv4")
        self._field(card, 2, "产品版本", "version")
        return card

    def _key_card(self, parent: ttk.Frame) -> ttk.Frame:
        card = self._card(parent, "密钥配置", "厂商签发工具：私钥保存在安装目录 keys 中，绝不能把本工具或私钥发给客户。")
        self._field(card, 0, "厂商私钥", "private", "private")
        self._field(card, 1, "厂商公钥", "public", "public")
        ttk.Label(card, textvariable=self.key_status, style="Hint.TLabel").grid(row=3, column=1, sticky="w", pady=(5, 0))
        return card

    def _browse(self, key: str, kind: str) -> None:
        """根据字段类型打开目录或文件选择器。"""
        if kind == "project":
            selected = filedialog.askdirectory(title="选择 PHP 项目目录")
        elif kind == "output":
            selected = filedialog.askdirectory(title="选择交付包输出目录")
        else:
            selected = filedialog.askopenfilename(title="选择密钥文件", filetypes=[("PEM 密钥", "*.pem"), ("所有文件", "*.*")])
        if selected:
            self.values[key].set(selected)
            if key in ("private", "public"):
                self._refresh_key_status()

    def _refresh_key_status(self) -> None:
        """根据两个密钥文件的存在情况更新提示。"""
        private = Path(self.values["private"].get())
        public = Path(self.values["public"].get())
        if private.is_file() and public.is_file():
            self.key_status.set("● 密钥对已就绪")
        elif private.exists() or public.exists():
            self.key_status.set("● 密钥文件不完整，请重新生成或选择完整密钥对")
        else:
            self.key_status.set("● 尚未生成密钥对，请点击“生成厂商密钥”")

    def choose_project(self) -> None:
        """兼容旧代码调用的项目目录选择入口。"""
        self._browse("project", "project")

    def generate_keys(self) -> None:
        """生成厂商密钥，并明确提醒私钥不能交付给客户。"""
        from app.license.signer import LicenseSigner

        private = Path(self.values["private"].get())
        public = Path(self.values["public"].get())
        if private.exists() and not messagebox.askyesno("密钥已存在", "覆盖现有密钥会使旧 License 无法验证，确定继续吗？"):
            return
        try:
            private.parent.mkdir(parents=True, exist_ok=True)
            public.parent.mkdir(parents=True, exist_ok=True)
            LicenseSigner.generate_keypair(private, public)
            self._refresh_key_status()
            self.write_log(f"厂商密钥已生成：{private.parent}")
            self.status.set("密钥生成成功")
            messagebox.showinfo("完成", "密钥生成成功。请妥善备份私钥，绝不要把私钥发给客户。")
        except Exception as exc:
            messagebox.showerror("生成失败", str(exc))

    def write_log(self, message: str) -> None:
        """线程安全地把消息追加到日志区。"""
        self.root.after(0, self._append_log, message)

    def _append_log(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def scan(self) -> None:
        """扫描项目并在日志中显示框架和入口文件。"""
        project = Path(self.values["project"].get())
        if not project.is_dir():
            messagebox.showwarning("需要选择项目", "请先选择有效的 PHP 项目目录。")
            return
        try:
            from app.scanner.project_scanner import ProjectScanner

            info = ProjectScanner().scan(project)
            self.write_log(f"检测到 {info.framework}，入口：{info.entry}")
            self.status.set("项目扫描完成")
        except Exception as exc:
            messagebox.showerror("扫描失败", str(exc))

    def build(self) -> None:
        """校验输入后启动后台打包线程，避免大项目导致界面卡顿。"""
        values = self.values
        project = Path(values["project"].get())
        if not project.is_dir():
            messagebox.showwarning("需要选择项目", "请先选择有效的 PHP 项目目录。")
            return
        if not values["domain"].get().strip() and not values["ipv4"].get().strip():
            messagebox.showwarning("缺少授权范围", "授权域名和授权 IPv4 至少填写一项。")
            return
        request = BuildRequest(project, values["domain"].get(), values["ipv4"].get(), values["version"].get(), Path(values["output"].get()), Path(values["private"].get()), Path(values["public"].get()))
        self.build_button.configure(state="disabled")
        self.status.set("正在生成交付包，请稍候…")
        self.write_log("开始后台打包，界面保持响应…")
        threading.Thread(target=self._build_worker, args=(request,), daemon=True).start()

    def _build_worker(self, request: BuildRequest) -> None:
        """在后台线程运行文件复制、签名、注入和归档。"""
        try:
            result = PackageBuilder(self.write_log).build(request)
            self.root.after(0, self._build_finished, result.zip_path)
        except Exception as exc:
            self.root.after(0, self._build_failed, str(exc))

    def _build_finished(self, zip_path: Path) -> None:
        self.build_button.configure(state="normal")
        self.status.set("交付包生成完成")
        messagebox.showinfo("打包完成", f"交付包已生成：\n{zip_path}")

    def _build_failed(self, error: str) -> None:
        self.build_button.configure(state="normal")
        self.status.set("打包失败，请查看错误提示")
        messagebox.showerror("打包失败", error)
