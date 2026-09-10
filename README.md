# LicenseProtector

离线 PHP 源码授权保护工具（V1）。

开发者：**Stephen Hu**（stephenhu031028@gmail.com）。

工具只修改临时复制的项目，业务源码仍可编辑；交付包使用 Ed25519 签名 License、域名或 IPv4 二选一校验、保护目录完整性清单，并且运行时不访问网络。

Hyperf 项目会额外生成授权中间件，在每个 HTTP 请求中校验真实 Host；不会在 Hyperf 的 CLI 启动阶段误判域名。

## CLI

```powershell
& .\.venv\Scripts\python.exe -m app.cli keygen --private keys\vendor_private.pem --public keys\vendor_public.pem
& .\.venv\Scripts\python.exe -m app.cli build --project D:\Project\Backend --domain customer.example.com --ipv4 123.123.123.123 --version 1.0.0 --private-key keys\vendor_private.pem --public-key keys\vendor_public.pem --output dist
```

私钥仅保存在厂商电脑，绝不能放进客户交付包或代码仓库。

注意：`LicenseProtector-Setup.exe` 是厂商签发工具，不要把它发给客户。客户只需要拿到生成后的 PHP 交付包；交付包只包含公钥和签名后的 `license.dat`，不包含厂商私钥。

每次打包结果自动归档到：

```text
<输出目录>/history/<UTC时间戳>_<LicenseID>/
├── <项目名>_Release_<版本>/
└── <项目名>_Release_<版本>.zip
```

Windows 图形化安装包位于 `installer_dist/LicenseProtector-Setup.exe`。安装向导允许自选安装目录，并默认创建桌面快捷方式；安装后不需要 Python 或 Qt 运行时。

图形界面默认把厂商密钥保存到软件安装目录下的 `keys` 文件夹：

```text
<安装目录>\keys\vendor_private.pem
<安装目录>\keys\vendor_public.pem
```

详细流程和运行时校验原理见 `docs/打包原理说明.md`。
