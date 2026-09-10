from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile
import json
import os
import shutil
import uuid

from app.injector.bootstrap_injector import BootstrapInjector
from app.injector.hyperf_injector import HyperfInjector
from app.license.schema import LicensePayload
from app.license.signer import LicenseSigner
from app.protector.integrity_builder import build_manifest
from app.protector.watchdog_builder import WatchdogBuilder
from app.scanner.project_scanner import ProjectScanner, ProjectInfo
from app.validation.domain import normalize_domain
from app.validation.ipv4 import normalize_ipv4


@dataclass(frozen=True)
class BuildRequest:
    project: Path
    domain: str
    ipv4: str
    product_version: str
    output: Path
    private_key: Path
    public_key: Path
    product_id: str = "PRODUCT-001"
    license_id: str | None = None
    entry: Path | None = None


@dataclass(frozen=True)
class BuildResult:
    release_dir: Path
    zip_path: Path
    license_id: str
    project_info: ProjectInfo


def _extended_path(path: Path) -> str:
    r"""返回 Windows 长路径形式，避免深层 vendor 文件触发 WinError 3。

    Windows 的传统 Win32 API 默认限制路径长度为 260 个字符。客户项目
    常见的 Composer SDK（例如腾讯云 SDK）目录层级很深，历史交付目录再
    叠加时间戳后容易超过该限制。``\\?\`` 前缀会启用 Windows 扩展路径 API；
    非 Windows 平台保持普通路径，便于开发和测试。
    """
    raw = os.path.abspath(os.fspath(path))
    if os.name != "nt" or raw.startswith("\\\\?\\"):
        return raw
    if raw.startswith("\\\\"):
        return "\\\\?\\UNC\\" + raw[2:]
    return "\\\\?\\" + raw


def _normal_path(path: str) -> str:
    """移除扩展路径前缀，仅用于计算 ZIP 内部的相对文件名。"""
    if path.startswith("\\\\?\\UNC\\"):
        return "\\\\" + path[8:]
    if path.startswith("\\\\?\\"):
        return path[4:]
    return path


def _copytree(source: Path, destination: Path) -> None:
    """复制整个项目，并对 Windows 源路径和目标路径启用长路径支持。"""
    shutil.copytree(_extended_path(source), _extended_path(destination))


def _remove_tree(path: Path) -> None:
    """删除可能超过 260 字符的历史目录。"""
    shutil.rmtree(_extended_path(path))


def _iter_files(path: Path):
    """遍历长路径目录，返回可直接交给 ZipFile 的文件路径。"""
    root = _extended_path(path)
    for current, _directories, files in os.walk(root):
        for name in files:
            yield os.path.join(current, name)


class PackageBuilder:
    def __init__(self, logger=None):
        self.log = logger or (lambda message: None)

    def build(self, request: BuildRequest) -> BuildResult:
        project = request.project.resolve()
        domain = normalize_domain(request.domain)
        ipv4 = normalize_ipv4(request.ipv4)
        if not domain and not ipv4:
            raise ValueError("Domain or IPv4 must be provided")
        if not request.private_key.is_file() or not request.public_key.is_file():
            raise FileNotFoundError("Signing key files are required")
        info = ProjectScanner().scan(project, request.entry)
        license_id = request.license_id or f"LIC-{__import__('datetime').datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        payload = LicensePayload.create(license_id, request.product_version, domain or None, ipv4 or None, request.product_id)
        document = LicenseSigner.sign(payload, LicenseSigner.load_private(request.private_key))
        request.output.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix="license-protector-") as temp:
            workspace = Path(temp) / project.name
            _copytree(project, workspace)
            self.log("项目已复制到临时工作区")
            LicenseSigner.write(document, workspace / "license.dat")
            protected = WatchdogBuilder().build(workspace, document, request.public_key)
            BootstrapInjector().inject(workspace, workspace / info.entry.relative_to(project))
            # Hyperf starts the selected entry from CLI. Generate a middleware
            # so the request Host is checked when actual HTTP traffic arrives.
            framework_files = HyperfInjector().inject(workspace) if info.framework == "Hyperf" else []
            protected_files = [p for p in protected + framework_files if p.is_file()]
            manifest = workspace / "MANIFEST"
            build_manifest(workspace, protected_files + [workspace / "license.dat"], manifest)
            (workspace / "VERSION").write_text(request.product_version + "\n", encoding="utf-8")
            (workspace / "INSTALL.md").write_text("Deploy this directory as a normal PHP project. No network connection is required.\n", encoding="utf-8")
            # Every build gets an immutable archive directory. This prevents a
            # later customer build from overwriting an earlier deliverable.
            release_name = f"{project.name}_Release_{request.product_version}"
            history_name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + license_id
            history_dir = request.output / "history" / history_name
            history_dir.mkdir(parents=True, exist_ok=True)
            release_dir = history_dir / release_name
            if release_dir.exists():
                _remove_tree(release_dir)
            _copytree(workspace, release_dir)
            zip_path = history_dir / f"{release_name}.zip"
            with ZipFile(zip_path, "w", ZIP_DEFLATED) as archive:
                for item in _iter_files(release_dir):
                    # item 使用扩展路径打开，归档名则使用普通相对路径。
                    archive_name = os.path.relpath(_normal_path(item), history_dir)
                    archive.write(item, archive_name.replace(os.sep, "/"))
        self.log(f"打包完成: {zip_path}")
        return BuildResult(release_dir, zip_path, license_id, info)
