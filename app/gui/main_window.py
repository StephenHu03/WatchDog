"""Human-centered desktop workflow for PHP + Hyperf license deliveries.

The GUI owns only interaction state. Target normalization, runtime validation,
signing and packaging remain in dedicated domain modules so CLI and GUI builds
always follow the same policy.

Developer: Stephen Hu <stephenhu031028@gmail.com>
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.license.targets import LicenseTargets
from app.package.builder import BuildRequest, PackageBuilder
from app.runtime.profile import PHP_HYPERF


class Tooltip:
    """Small hover label for compact icon-only target controls."""

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show, add=True)
        widget.bind("<Leave>", self._hide, add=True)

    def _show(self, _event=None) -> None:
        if self.window is not None:
            return
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.geometry(f"+{self.widget.winfo_rootx()}+{self.widget.winfo_rooty() + self.widget.winfo_height() + 4}")
        tk.Label(self.window, text=self.text, bg="#202124", fg="white", padx=7, pady=3, font=("Segoe UI", 8)).pack()

    def _hide(self, _event=None) -> None:
        if self.window is not None:
            self.window.destroy()
            self.window = None


class MainWindow:
    """Collect build inputs while keeping the primary delivery workflow focused."""

    COLORS = {
        "accent": "#1A73E8",
        "accent_dark": "#185ABC",
        "page": "#F8F9FA",
        "surface": "#FFFFFF",
        "border": "#DADCE0",
        "text": "#202124",
        "muted": "#5F6368",
        "success": "#137333",
        "chip": "#E8F0FE",
        "chip_text": "#174EA6",
        "log": "#202124",
    }

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.values = {key: tk.StringVar() for key in ("project", "version", "private", "public", "output")}
        self.php_version = tk.StringVar(value="8.1+")
        self.target_inputs = {"domains": tk.StringVar(), "ipv4s": tk.StringVar()}
        self.target_items: dict[str, list[str]] = {"domains": [], "ipv4s": []}
        # Each target group renders compact rows instead of a fixed-height
        # Listbox. Empty groups therefore stay small and readable.
        self.target_lists: dict[str, tk.Frame] = {}
        self.target_counts: dict[str, tk.StringVar] = {}
        self.key_status = tk.StringVar()
        self.status = tk.StringVar(value="就绪")
        self._compact_layout: bool | None = None
        self._configure_window()
        self._configure_style()
        self._set_defaults()
        self._build_layout()
        self._refresh_key_status()

    def _configure_window(self) -> None:
        self.root.title("LicenseProtector | PHP + Hyperf 授权交付")
        self.root.geometry("1040x800")
        self.root.minsize(900, 680)
        self.root.configure(bg=self.COLORS["page"])

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("vista")
        except tk.TclError:
            style.theme_use("clam")
        style.configure("Page.TFrame", background=self.COLORS["page"])
        style.configure("Card.TLabelframe", background=self.COLORS["surface"], bordercolor=self.COLORS["border"], relief="solid")
        style.configure("Card.TLabelframe.Label", background=self.COLORS["surface"], foreground=self.COLORS["text"], font=("Segoe UI", 10, "bold"))
        style.configure("Field.TLabel", background=self.COLORS["surface"], foreground=self.COLORS["text"], font=("Segoe UI", 9))
        style.configure("Hint.TLabel", background=self.COLORS["surface"], foreground=self.COLORS["muted"], font=("Segoe UI", 9))
        style.configure("Status.TLabel", background=self.COLORS["page"], foreground=self.COLORS["muted"], font=("Segoe UI", 9))
        style.configure("TEntry", padding=6)
        style.configure("TCombobox", padding=5)
        style.configure("Action.TButton", font=("Segoe UI", 9), padding=(10, 6))

    @staticmethod
    def _application_dir() -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parents[2]

    def _set_defaults(self) -> None:
        key_dir = self._application_dir() / "keys"
        self.values["version"].set("1.1.0")
        self.values["private"].set(str(key_dir / "vendor_private.pem"))
        self.values["public"].set(str(key_dir / "vendor_public.pem"))
        self.values["output"].set(str(Path.home() / "Documents" / "LicenseProtector" / "deliveries"))

    def _build_layout(self) -> None:
        header = tk.Frame(self.root, bg=self.COLORS["surface"], height=88)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Frame(header, bg=self.COLORS["accent"], height=4).pack(fill="x", side="top")
        tk.Label(header, text="LicenseProtector", bg=self.COLORS["surface"], fg=self.COLORS["text"], font=("Segoe UI", 20, "bold"), anchor="w").place(x=28, y=24)
        tk.Label(header, text="授权交付工作台", bg=self.COLORS["surface"], fg=self.COLORS["muted"], font=("Segoe UI", 10), anchor="w").place(x=30, y=55)
        tk.Label(header, text="PHP  ·  Hyperf", bg=self.COLORS["chip"], fg=self.COLORS["chip_text"], padx=12, pady=5, font=("Segoe UI", 9, "bold")).place(relx=1.0, x=-30, y=30, anchor="ne")

        # Keep commands visible while the configuration canvas grows with the
        # number of license targets. No section is forced to shrink vertically.
        scroll_shell = ttk.Frame(self.root, style="Page.TFrame")
        scroll_shell.pack(fill="both", expand=True)
        self.scroll_canvas = tk.Canvas(scroll_shell, bg=self.COLORS["page"], highlightthickness=0, borderwidth=0)
        scroll_bar = ttk.Scrollbar(scroll_shell, orient="vertical", command=self.scroll_canvas.yview)
        self.scroll_canvas.configure(yscrollcommand=scroll_bar.set)
        self.scroll_canvas.pack(side="left", fill="both", expand=True)
        scroll_bar.pack(side="right", fill="y")
        page = ttk.Frame(self.scroll_canvas, style="Page.TFrame", padding=(24, 18, 24, 12))
        self._scroll_window = self.scroll_canvas.create_window((0, 0), window=page, anchor="nw")
        page.bind("<Configure>", self._sync_scroll_region)
        self.scroll_canvas.bind("<Configure>", self._resize_scroll_content)
        self.root.bind_all("<MouseWheel>", self._scroll_with_mouse, add=True)
        self.root.bind_all("<Button-4>", lambda _event: self.scroll_canvas.yview_scroll(-3, "units"), add=True)
        self.root.bind_all("<Button-5>", lambda _event: self.scroll_canvas.yview_scroll(3, "units"), add=True)

        config = ttk.Frame(page, style="Page.TFrame")
        config.pack(fill="x")
        config.columnconfigure(0, weight=1)
        config.columnconfigure(1, weight=1)
        self.config = config
        self.project_card = self._project_card(config)
        self.runtime_card = self._runtime_card(config)
        self.license_card = self._license_card(config)
        self._apply_responsive_layout(False)
        self._key_card(page).pack(fill="x", pady=(12, 0))

        log_frame = ttk.LabelFrame(page, text="运行日志", style="Card.TLabelframe", padding=(10, 8))
        log_frame.pack(fill="x", pady=(12, 0))
        self.log = tk.Text(log_frame, height=7, state="disabled", wrap="word", bg=self.COLORS["log"], fg="#E8EAED", insertbackground="white", relief="flat", padx=10, pady=8, font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        actions = ttk.Frame(self.root, style="Page.TFrame", padding=(24, 8, 24, 4))
        actions.pack(fill="x")
        ttk.Button(actions, text="生成厂商密钥", style="Action.TButton", command=self.generate_keys).pack(side="left")
        ttk.Button(actions, text="扫描项目", style="Action.TButton", command=self.scan).pack(side="left", padx=8)
        self.build_button = tk.Button(actions, text="生成交付包", command=self.build, bg=self.COLORS["accent"], fg="white", activebackground=self.COLORS["accent_dark"], activeforeground="white", disabledforeground="#E8EAED", relief="flat", borderwidth=0, padx=20, pady=8, font=("Segoe UI", 10, "bold"), cursor="hand2")
        self.build_button.pack(side="right")

        footer = ttk.Frame(self.root, style="Page.TFrame", padding=(24, 0, 24, 12))
        footer.pack(fill="x")
        ttk.Label(footer, textvariable=self.status, style="Status.TLabel").pack(side="left")
        ttk.Label(footer, text="Stephen Hu  |  stephenhu031028@gmail.com", style="Status.TLabel").pack(side="right")

    def _sync_scroll_region(self, _event=None) -> None:
        """Make the canvas height follow dynamic authorization target rows."""
        self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))

    def _resize_scroll_content(self, event) -> None:
        """Stretch content horizontally and switch card layout at narrow widths."""
        self.scroll_canvas.itemconfigure(self._scroll_window, width=event.width)
        self._apply_responsive_layout(event.width < 940)

    def _apply_responsive_layout(self, compact: bool) -> None:
        """Use two columns on desktop and one readable column on narrow windows."""
        if compact == self._compact_layout:
            return
        self._compact_layout = compact
        if compact:
            self.project_card.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
            self.runtime_card.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 12))
            self.license_card.grid(row=2, column=0, columnspan=2, sticky="ew")
        else:
            self.project_card.grid(row=0, column=0, sticky="new", padx=(0, 8), pady=(0, 12))
            self.runtime_card.grid(row=1, column=0, sticky="new", padx=(0, 8))
            self.license_card.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(8, 0))

    def _scroll_with_mouse(self, event) -> str | None:
        """Scroll configuration without stealing the dedicated log widget wheel."""
        if event.widget == self.log:
            return None
        if event.delta:
            self.scroll_canvas.yview_scroll(-int(event.delta / 120), "units")
            return "break"
        return None

    def _card(self, parent: ttk.Frame, title: str, hint: str) -> ttk.LabelFrame:
        card = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe", padding=(14, 10, 14, 12))
        ttk.Label(card, text=hint, style="Hint.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
        card.columnconfigure(1, weight=1)
        return card

    def _field(self, parent: ttk.LabelFrame, row: int, label: str, key: str, browse: str | None = None) -> None:
        field_row = row + 1
        ttk.Label(parent, text=label, style="Field.TLabel", width=12).grid(row=field_row, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=self.values[key]).grid(row=field_row, column=1, sticky="ew", pady=4, padx=(0, 6))
        if browse:
            ttk.Button(parent, text="浏览...", style="Action.TButton", command=lambda: self._browse(key, browse)).grid(row=field_row, column=2, sticky="e", pady=2)

    def _project_card(self, parent: ttk.Frame) -> ttk.LabelFrame:
        card = self._card(parent, "项目", "选择待交付的 Hyperf 项目与归档位置。")
        self._field(card, 0, "项目目录", "project", "project")
        self._field(card, 1, "输出目录", "output", "output")
        return card

    def _runtime_card(self, parent: ttk.Frame) -> ttk.LabelFrame:
        card = self._card(parent, "运行环境", "签名记录目标服务器运行环境。")
        ttk.Label(card, text="语言", style="Field.TLabel", width=12).grid(row=1, column=0, sticky="w", pady=4)
        language = ttk.Combobox(card, values=(PHP_HYPERF.language,), state="readonly")
        language.set(PHP_HYPERF.language)
        language.grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(card, text="框架", style="Field.TLabel", width=12).grid(row=2, column=0, sticky="w", pady=4)
        framework = ttk.Combobox(card, values=(PHP_HYPERF.framework,), state="readonly")
        framework.set(PHP_HYPERF.framework)
        framework.grid(row=2, column=1, sticky="ew", pady=4)
        ttk.Label(card, text="最低 PHP", style="Field.TLabel", width=12).grid(row=3, column=0, sticky="w", pady=4)
        versions = tuple(f"{version}+" for version in PHP_HYPERF.minimum_versions)
        ttk.Combobox(card, textvariable=self.php_version, values=versions, state="readonly").grid(row=3, column=1, sticky="ew", pady=4)
        return card

    def _license_card(self, parent: ttk.Frame) -> ttk.LabelFrame:
        card = self._card(parent, "授权目标", "任意一个域名或服务器 IPv4 匹配即可通过。")
        self._target_editor(card, 1, "授权域名", "domains", "例如 api.example.com")
        self._target_editor(card, 5, "服务器 IPv4", "ipv4s", "例如 10.0.3.6")
        ttk.Label(card, text="产品版本", style="Field.TLabel", width=12).grid(row=9, column=0, sticky="w", pady=(8, 4))
        ttk.Entry(card, textvariable=self.values["version"]).grid(row=9, column=1, columnspan=2, sticky="ew", pady=(8, 4))
        return card

    def _target_editor(self, parent: ttk.LabelFrame, row: int, title: str, key: str, placeholder: str) -> None:
        heading = tk.Frame(parent, bg=self.COLORS["surface"])
        heading.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(2, 4))
        heading.columnconfigure(1, weight=1)
        tk.Label(heading, text=title, bg=self.COLORS["surface"], fg=self.COLORS["text"], font=("Segoe UI", 9, "bold"), anchor="w").grid(row=0, column=0, sticky="w")
        count = tk.StringVar(value="0 个")
        self.target_counts[key] = count
        tk.Label(heading, textvariable=count, bg=self.COLORS["surface"], fg=self.COLORS["muted"], font=("Segoe UI", 8), anchor="e").grid(row=0, column=1, sticky="e")
        entry = ttk.Entry(parent, textvariable=self.target_inputs[key])
        entry.grid(row=row + 1, column=0, columnspan=2, sticky="ew", pady=(0, 2), padx=(0, 6))
        entry.bind("<Return>", lambda _event, kind=key: self._add_target(kind))
        add = tk.Button(parent, text="+", command=lambda kind=key: self._add_target(kind), bg=self.COLORS["accent"], fg="white", activebackground=self.COLORS["accent_dark"], activeforeground="white", relief="flat", width=3, cursor="hand2", font=("Segoe UI", 10, "bold"))
        add.grid(row=row + 1, column=2, sticky="e", pady=(0, 2))
        Tooltip(add, f"添加{title}")
        ttk.Label(parent, text=placeholder, style="Hint.TLabel").grid(row=row + 2, column=0, columnspan=3, sticky="w", pady=(0, 3))
        rows = tk.Frame(parent, bg=self.COLORS["surface"])
        rows.grid(row=row + 3, column=0, columnspan=3, sticky="ew", pady=(0, 3))
        self.target_lists[key] = rows

    def _add_target(self, kind: str) -> None:
        raw = self.target_inputs[kind].get().strip()
        if not raw:
            return
        values = [item.strip() for item in raw.replace(";", ",").replace("\n", ",").split(",") if item.strip()]
        self.target_items[kind].extend(item for item in values if item not in self.target_items[kind])
        self.target_inputs[kind].set("")
        self._refresh_target_list(kind)

    def _remove_target(self, kind: str, index: int) -> None:
        """Remove one visible target row; the row owns its own action."""
        if 0 <= index < len(self.target_items[kind]):
            del self.target_items[kind][index]
            self._refresh_target_list(kind)

    def _refresh_target_list(self, kind: str) -> None:
        rows = self.target_lists[kind]
        for child in rows.winfo_children():
            child.destroy()
        items = self.target_items[kind]
        self.target_counts[kind].set(f"{len(items)} 个")
        if not items:
            tk.Label(rows, text="尚未添加，打包时至少填写一项授权目标", bg=self.COLORS["surface"], fg=self.COLORS["muted"], font=("Segoe UI", 8), anchor="w").pack(fill="x", pady=(1, 2))
            return
        for index, item in enumerate(items):
            item_row = tk.Frame(rows, bg=self.COLORS["chip"], highlightbackground="#D2E3FC", highlightthickness=1)
            item_row.pack(fill="x", pady=(0, 3))
            tk.Label(item_row, text=item, bg=self.COLORS["chip"], fg=self.COLORS["chip_text"], font=("Segoe UI", 9), anchor="w", padx=9, pady=4).pack(side="left", fill="x", expand=True)
            remove = tk.Button(item_row, text="×", command=lambda target=kind, target_index=index: self._remove_target(target, target_index), bg=self.COLORS["chip"], fg=self.COLORS["muted"], activebackground="#FCE8E6", activeforeground="#C5221F", relief="flat", borderwidth=0, width=3, cursor="hand2", font=("Segoe UI", 10))
            remove.pack(side="right", padx=(0, 3))
            Tooltip(remove, "移除该授权目标")

    def _key_card(self, parent: ttk.Frame) -> ttk.LabelFrame:
        card = self._card(parent, "厂商密钥", "私钥仅保存在厂商设备；客户交付包不包含私钥。")
        self._field(card, 0, "厂商私钥", "private", "private")
        self._field(card, 1, "厂商公钥", "public", "public")
        ttk.Label(card, textvariable=self.key_status, style="Hint.TLabel").grid(row=3, column=1, sticky="w", pady=(5, 0))
        return card

    def _browse(self, key: str, kind: str) -> None:
        if kind in ("project", "output"):
            selected = filedialog.askdirectory(title="选择项目目录" if kind == "project" else "选择输出目录")
        else:
            selected = filedialog.askopenfilename(title="选择密钥文件", filetypes=[("PEM 密钥", "*.pem"), ("所有文件", "*.*")])
        if selected:
            self.values[key].set(selected)
            if key in ("private", "public"):
                self._refresh_key_status()

    def _refresh_key_status(self) -> None:
        private, public = Path(self.values["private"].get()), Path(self.values["public"].get())
        if private.is_file() and public.is_file():
            self.key_status.set("密钥对已就绪")
        elif private.exists() or public.exists():
            self.key_status.set("密钥文件不完整")
        else:
            self.key_status.set("尚未生成厂商密钥")

    def generate_keys(self) -> None:
        from app.license.signer import LicenseSigner

        private, public = Path(self.values["private"].get()), Path(self.values["public"].get())
        if private.exists() and not messagebox.askyesno("密钥已存在", "覆盖私钥会使旧 License 无法验证，确定继续吗？"):
            return
        try:
            private.parent.mkdir(parents=True, exist_ok=True)
            public.parent.mkdir(parents=True, exist_ok=True)
            LicenseSigner.generate_keypair(private, public)
            self._refresh_key_status()
            self.write_log(f"厂商密钥已生成：{private.parent}")
            self.status.set("密钥已生成")
        except Exception as exc:
            messagebox.showerror("生成失败", str(exc))

    def write_log(self, message: str) -> None:
        self.root.after(0, self._append_log, message)

    def _append_log(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def scan(self) -> None:
        project = Path(self.values["project"].get())
        if not project.is_dir():
            messagebox.showwarning("需要选择项目", "请先选择有效的 Hyperf 项目目录。")
            return
        try:
            from app.scanner.project_scanner import ProjectScanner

            info = ProjectScanner().scan(project)
            PHP_HYPERF.validate_project_framework(info.framework)
            self.write_log(f"检测到 PHP · {info.framework}，入口：{info.entry}")
            self.status.set("项目扫描完成")
        except Exception as exc:
            messagebox.showerror("扫描失败", str(exc))

    def build(self) -> None:
        project = Path(self.values["project"].get())
        if not project.is_dir():
            messagebox.showwarning("需要选择项目", "请先选择有效的 Hyperf 项目目录。")
            return
        try:
            targets = LicenseTargets.create(self.target_items["domains"], self.target_items["ipv4s"])
            request = BuildRequest(
                project=project,
                domains=targets.domains,
                ipv4s=targets.ipv4s,
                php_min_version=self.php_version.get(),
                product_version=self.values["version"].get().strip(),
                output=Path(self.values["output"].get()),
                private_key=Path(self.values["private"].get()),
                public_key=Path(self.values["public"].get()),
            )
        except ValueError as exc:
            messagebox.showwarning("授权配置无效", str(exc))
            return
        self.build_button.configure(state="disabled")
        self.status.set("正在生成交付包")
        self.write_log("开始后台打包，界面保持响应…")
        threading.Thread(target=self._build_worker, args=(request,), daemon=True).start()

    def _build_worker(self, request: BuildRequest) -> None:
        try:
            result = PackageBuilder(self.write_log).build(request)
            self.root.after(0, self._build_finished, result.zip_path)
        except Exception as exc:
            self.root.after(0, self._build_failed, str(exc))

    def _build_finished(self, zip_path: Path) -> None:
        self.build_button.configure(state="normal")
        self.status.set("交付包已生成")
        messagebox.showinfo("打包完成", f"交付包已生成：\n{zip_path}")

    def _build_failed(self, error: str) -> None:
        self.build_button.configure(state="normal")
        self.status.set("打包失败")
        messagebox.showerror("打包失败", error)
