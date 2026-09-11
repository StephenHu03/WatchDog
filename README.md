# 源码授权保护工具（Source License Protector）


# 1. 项目目标

开发一个 Windows 桌面工具：

```text
LicenseProtector.exe
```

用于厂商内部交付 PHP SaaS 软件。

输入：

- PHP 后端源码目录
- 授权域名
- 授权 IPv4
- 产品版本
- License ID（默认自动生成）

输出：

- 已注入授权保护的 PHP 项目
- 本地签名 License
- 受保护的 Watchdog 核心
- 完整交付 ZIP
- 保护/打包日志

客户拿到交付包后：

1. 可以正常部署 PHP 项目；
2. 可以修改业务源码；
3. 不需要访问厂商服务器；
4. 离线环境也可以运行；
5. 只能在授权域名或授权 IPv4 环境运行；
6. 将源码复制到新的域名和新 IP 后，授权检查失败；
7. 授权核心不能以普通 PHP 明文文件形式直接暴露。

---

# 2. 非目标

V1 不实现：

- 在线 License Server
- 在线激活
- 用户账号系统
- 客户管理后台
- 在线续费
- 在线授权吊销
- 客户服务器定时回连
- Python 运行时依赖
- 强制 Docker
- 强制安装独立守护进程

特别要求：

> 客户服务器不得为了授权检查而访问厂商服务器。

---

# 3. 总体架构

```text
                 厂商电脑
                     |
                     v
        +---------------------------+
        | LicenseProtector.exe      |
        | Python + PySide6          |
        +-------------+-------------+
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
       Scanner    License      Protector
          |       Generator        |
          |           |            |
          +-----------+------------+
                      |
                      v
                Package Builder
                      |
                      v
             Customer Release ZIP
                      |
                      v
               客户 PHP 服务器
                      |
          +-----------+-----------+
          |                       |
          v                       v
   可修改业务源码             Protected Watchdog
                                  |
                         +--------+--------+
                         |                 |
                         v                 v
                   License Verify     Environment Verify
                         |                 |
                         +--------+--------+
                                  |
                         Domain OR IPv4
                                  |
                         +--------+--------+
                         |                 |
                       PASS              FAIL
                         |                 |
                         v                 v
                     正常运行          拒绝运行
```

---

# 4. 核心设计原则

## 4.1 业务源码开放

客户可以修改：

```text
app/
src/
Controller/
Service/
Model/
routes/
resources/
public/
config/
```

具体目录不得硬编码为某一个 PHP Framework。

工具应允许配置保护目录。

---

## 4.2 授权核心保护

以下内容必须受到保护：

```text
License 签名验证
Domain 验证
IPv4 验证
授权逻辑
完整性验证
授权失败处理
```

不能把全部逻辑直接暴露成：

```text
watchdog.php
```

然后允许客户简单删除：

```php
exit;
```

即可绕过授权。

---

## 4.3 不加密整个 PHP 项目

不要对整个 backend 做统一加密。

原因：

```text
客户需要修改业务源码
```

因此采用：

```text
业务源码
    ↓
正常 PHP
    ↓
客户可修改

授权核心
    ↓
保护/加密/混淆
    ↓
客户不可轻易修改
```

---

# 5. 推荐技术栈

## 5.1 Python

```text
Python >= 3.11
PySide6
cryptography
pathlib
hashlib
json
zipfile
shutil
tempfile
logging
uuid
secrets
subprocess
```

GUI：

```text
PySide6
```

EXE：

```text
PyInstaller
```

---

# 6. 项目目录

建议：

```text
license-protector/
│
├── app/
│   ├── main.py
│   │
│   ├── gui/
│   │   ├── main_window.py
│   │   ├── widgets.py
│   │   └── dialogs.py
│   │
│   ├── scanner/
│   │   ├── project_scanner.py
│   │   ├── php_detector.py
│   │   └── framework_detector.py
│   │
│   ├── license/
│   │   ├── generator.py
│   │   ├── signer.py
│   │   ├── schema.py
│   │   └── verifier.py
│   │
│   ├── protector/
│   │   ├── watchdog_builder.py
│   │   ├── source_transformer.py
│   │   ├── integrity_builder.py
│   │   └── package_protector.py
│   │
│   ├── injector/
│   │   ├── bootstrap_injector.py
│   │   └── entry_detector.py
│   │
│   ├── package/
│   │   ├── builder.py
│   │   └── manifest.py
│   │
│   ├── validation/
│   │   ├── domain.py
│   │   ├── ipv4.py
│   │   └── environment.py
│   │
│   └── utils/
│       ├── filesystem.py
│       ├── hashing.py
│       └── logger.py
│
├── resources/
│   ├── watchdog/
│   └── templates/
│
├── tests/
│
├── keys/
│   └── README.md
│
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

# 7. License 数据结构

License 使用：

> Payload + 非对称数字签名

推荐：

```text
Ed25519
```

厂商保存：

```text
private key
```

客户交付包只包含：

```text
public key
```

---

## 7.1 License JSON

逻辑结构：

```json
{
  "version": 1,
  "license_id": "LIC-20260909-XXXXXX",
  "product_id": "PRODUCT-001",
  "product_version": "1.0.0",
  "bind_mode": "DOMAIN_OR_IPV4",
  "domain": "customer.example.com",
  "ipv4": "123.123.123.123",
  "issued_at": "2026-09-09T00:00:00Z",
  "expires_at": null,
  "features": [],
  "signature": "BASE64_SIGNATURE"
}
```

注意：

- `signature` 不参与签名原文；
- 签名对象必须是稳定序列化后的 payload；
- JSON key 顺序必须固定；
- 字符编码统一 UTF-8；
- 签名前不得包含随机字段；
- 签名验证失败必须拒绝运行。

---

# 8. License 签名流程

厂商：

```text
Payload
   ↓
Canonical JSON
   ↓
UTF-8 bytes
   ↓
Ed25519 Sign(private_key)
   ↓
Base64 Signature
   ↓
License
```

客户：

```text
License
   ↓
读取 Payload
   ↓
Canonical JSON
   ↓
Ed25519 Verify(public_key)
   ↓
PASS / FAIL
```

绝对禁止：

- 将私钥放入客户交付包；
- 将私钥写入 Python EXE；
- 将私钥放入 PHP Watchdog；
- 在客户服务器生成签名。

私钥只存在厂商内部安全环境。

---

# 9. Domain 授权验证

## 9.1 目标

授权：

```text
customer.example.com
```

当前访问：

```text
customer.example.com
```

通过。

当前访问：

```text
other.example.com
```

失败。

---

## 9.2 标准化

验证前：

1. 转小写；
2. 去除端口；
3. 去除尾部 `.`；
4. 去除 URL scheme；
5. 不允许通过字符串包含关系匹配；
6. 默认使用精确匹配。

禁止：

```php
strpos($host, $licenseDomain)
```

必须：

```text
normalize(current_host) === normalize(licensed_host)
```

---

## 9.3 Host 获取

优先使用可信 Web Server 提供的 Host 信息。

必须考虑：

- Nginx
- Apache
- PHP-FPM
- 反向代理
- CDN

不要默认信任任意客户端可伪造的 Header。

V1 默认只做：

```text
HTTP_HOST / SERVER_NAME
```

并进行严格格式化。

复杂反向代理环境后续通过配置扩展。

---

# 10. IPv4 授权验证

授权：

```text
123.123.123.123
```

当前服务器满足授权 IP：

```text
PASS
```

否则：

```text
FAIL
```

必须使用服务器本地网络环境判断。

禁止把：

```text
REMOTE_ADDR
```

直接当作服务器 IP。

因为：

```text
REMOTE_ADDR
```

通常代表客户端请求来源。

---

## 10.1 IPv4 获取策略

V1 建议提供环境探测器：

```text
EnvironmentDetector
```

尝试：

1. Server interface addresses；
2. Web Server 配置；
3. PHP 环境；
4. 明确配置的服务器 IP。

如果环境无法可靠判断：

```text
LICENSE_ENVIRONMENT_UNRESOLVED
```

不要误判为授权成功。

同时 GUI 打包测试必须提示：

> IPv4 在 NAT / CDN / 反向代理环境下可能需要人工确认。

---

# 11. Domain OR IPv4 规则

核心逻辑：

```text
domain_match = verify_domain()
ip_match = verify_ipv4()

if domain_match OR ip_match:
    PASS
else:
    DENY
```

不要实现成：

```text
domain_match AND ip_match
```

---

# 12. Watchdog 生命周期

应用启动时：

```text
Application Bootstrap
        ↓
Watchdog
        ↓
Load License
        ↓
Verify Signature
        ↓
Verify License Metadata
        ↓
Verify Domain
        ↓
Verify IPv4
        ↓
Domain OR IPv4
        ↓
Integrity Check
        ↓
PASS
        ↓
Application Continue
```

失败：

```text
DENY
 ↓
记录错误代码
 ↓
终止应用初始化
```

---

# 13. Watchdog 核心保护

V1 要求：

> 授权核心不能以普通、易读、易修改的 PHP 文件完整呈现。

推荐保护优先级：

### 第一优先级

独立保护模块 + 混淆 + 拆分。

### 第二优先级

加密配置和授权数据。

### 第三优先级

完整性校验。

### 增强模式

如果目标客户环境允许 PHP 扩展，则未来提供：

```text
PHP Extension / Native Module
```

将最关键的授权验证放入原生模块。

但是：

> V1 默认不能要求客户额外安装 PHP 扩展，以保证正常部署兼容性。

---

# 14. “加密”的具体定义

V1 不把“加密”理解为：

```text
整个 PHP 项目 AES 加密
```

而定义为：

```text
授权核心保护
+
License 加密存储
+
核心代码混淆
+
完整性校验
```

原因：

如果整个 PHP 项目加密：

```text
客户无法正常修改源码
```

违背需求。

---

# 15. Watchdog 与业务代码的关系

要求：

```text
业务代码
   ↓
可以自由修改
```

但：

```text
业务代码
   ↓
必须经过授权启动链
```

推荐在项目入口建立：

```text
bootstrap
    ↓
protected watchdog
    ↓
application
```

例如：

```text
public/index.php
      ↓
license bootstrap
      ↓
watchdog
      ↓
vendor/autoload.php
      ↓
application
```

实际注入位置必须根据 Framework 自动判断。

---

# 16. Bootstrap Injector

工具扫描：

```text
Laravel
ThinkPHP
Symfony
原生 PHP
```

寻找：

```text
public/index.php
index.php
bootstrap/app.php
```

如果不能安全自动注入：

```text
停止打包
```

不能盲目修改未知 PHP 文件。

GUI 给出：

```text
无法自动确定项目入口。
请人工指定入口文件。
```

---

# 17. 完整性保护

对保护区域生成：

```text
manifest
```

例如：

```json
{
  "version": 1,
  "files": {
    "protected/watchdog/core.bin": "sha256...",
    "protected/watchdog/loader.php": "sha256...",
    "license.dat": "sha256..."
  }
}
```

运行时：

```text
读取文件
 ↓
SHA-256
 ↓
比较 manifest
 ↓
一致 → PASS
不一致 → DENY
```

注意：

> 完整性校验本身也属于授权核心的一部分，不能完全以明文形式暴露。

---

# 18. 文件保护边界

工具必须允许定义：

```text
editable_paths
protected_paths
```

默认：

```text
editable:
业务源码

protected:
.protected/
watchdog/
license/
```

打包时不得把客户业务目录整体转为保护目录。

---

# 19. Package Builder

最终输出：

```text
Customer_A_Release_1.0.0.zip
```

目录：

```text
Customer_A/
│
├── backend/
│   ├── app/
│   ├── config/
│   ├── public/
│   ├── routes/
│   └── ...
│
├── protected/
│   └── watchdog/
│
├── license.dat
├── VERSION
├── MANIFEST
└── INSTALL.md
```

如果前端和后端是分离项目：

```text
frontend/
backend/
```

保持原项目结构。

---

# 20. GUI 功能

首页必须提供：

```text
项目目录
授权域名
授权 IPv4
授权模式
License ID
产品版本
输出目录
```

按钮：

```text
[扫描项目]
[生成 License]
[开始保护]
[测试授权]
[生成交付包]
```

---

# 21. GUI 工作状态

状态机：

```text
IDLE
 ↓
SCANNING
 ↓
SCAN_SUCCESS
 ↓
GENERATING_LICENSE
 ↓
PROTECTING
 ↓
INJECTING
 ↓
VERIFYING
 ↓
PACKAGING
 ↓
COMPLETED
```

任何失败：

```text
FAILED
```

不得生成半成品交付包。

---

# 22. GUI 日志

必须显示：

```text
[15:30:01] 开始扫描项目
[15:30:02] 检测到 PHP 项目
[15:30:02] 检测 Framework: Laravel
[15:30:03] 项目入口: public/index.php
[15:30:03] License 创建完成
[15:30:03] License 签名完成
[15:30:04] Watchdog 注入完成
[15:30:04] 完整性检查完成
[15:30:05] 打包完成
```

失败必须显示：

```text
错误代码
原因
建议解决方案
```

---

# 23. 打包前检查

必须检查：

```text
[ ] 项目目录存在
[ ] PHP 文件存在
[ ] 项目入口存在
[ ] 未重复注入
[ ] Domain 合法
[ ] IPv4 合法
[ ] License 生成成功
[ ] License 签名成功
[ ] Watchdog 文件完整
[ ] Protected 文件完整
```

任意失败：

```text
禁止输出 Release
```

---

# 24. 打包后自动测试

生成临时测试环境：

```text
Temporary Release
        ↓
读取 License
        ↓
测试授权数据
        ↓
测试签名
        ↓
测试 Domain
        ↓
测试 IPv4
        ↓
测试完整性
```

至少验证：

### 测试 A

正确 Domain：

```text
PASS
```

### 测试 B

错误 Domain + 正确 IP：

```text
PASS
```

### 测试 C

正确 Domain + 错误 IP：

```text
PASS
```

### 测试 D

错误 Domain + 错误 IP：

```text
FAIL
```

### 测试 E

修改 License：

```text
FAIL
```

### 测试 F

修改 Protected 文件：

```text
FAIL
```

---

# 25. 错误代码

统一：

```text
LIC-1001 License missing
LIC-1002 License signature invalid
LIC-1003 Domain mismatch
LIC-1004 IPv4 mismatch
LIC-1005 License expired
LIC-1006 License malformed
LIC-1007 Environment unresolved
LIC-1008 Protected file integrity failed
LIC-1009 Watchdog unavailable
LIC-1010 Bootstrap initialization failed
```

---

# 26. 安全要求

## 私钥

绝对禁止：

```text
Git
源码仓库
客户服务器
PHP 源码
客户 License
```

出现私钥。

---

## 公钥

可以放入：

```text
Watchdog
```

因为公钥本身不能生成合法 License。

---

# 27. License 生成器安全

Python 工具中：

```text
PrivateKeyProvider
```

负责读取厂商私钥。

V1 可以从：

```text
本地受保护目录
```

读取。

推荐支持：

```text
环境变量
```

或后续：

```text
Windows Credential Manager
```

不要把私钥硬编码到 Python 源码。

---

# 28. 防重复授权

每一个客户交付生成：

```text
unique license_id
```

例如：

```text
LIC-20260909-8A73F2
```

License ID 不参与业务运行逻辑，但用于：

- 交付追踪
- 客户识别
- 内部售后
- 问题排查

---

# 29. 版本控制

License：

```text
product_version
```

Watchdog：

```text
watchdog_version
```

Release：

```text
release_version
```

三者独立。

示例：

```text
Product: 1.5.0
Watchdog: 1.0.3
Release: 2026.09.09
```

---

# 30. 不允许联网

客户 Watchdog 中禁止：

```text
curl
file_get_contents(http://...)
Guzzle HTTP
fsockopen
socket
```

向厂商授权服务器发起验证。

授权系统只能使用：

```text
本地 License
本地文件
本地服务器环境
```

---

# 31. 部署兼容性原则

授权系统不得要求：

```text
Python
Node
Docker
独立 License Server
常驻进程
外部 API
```

客户原有部署方式不变。

---

# 32. 日志原则

客户侧只记录必要信息：

```text
license_id
error_code
timestamp
```

不得记录：

```text
敏感业务数据
用户密码
数据库内容
完整请求 Body
```

---

# 33. 开发阶段建议

按照以下顺序实现。

## Phase 1：License

先完成：

```text
License Schema
Ed25519 Sign
Ed25519 Verify
License Generator
License Validator
```

先不要做 GUI。

---

## Phase 2：Watchdog

实现：

```text
Watchdog
Domain Validator
IPv4 Validator
Integrity Validator
Error Code
```

完成纯本地测试。

---

## Phase 3：项目注入

实现：

```text
PHP Project Scanner
Framework Detector
Entry Detector
Bootstrap Injector
```

先支持：

```text
原生 PHP
Laravel
```

其他 Framework 后续增加。

---

## Phase 4：Protector

实现：

```text
Protected Core
License Protection
Code Obfuscation
Manifest
Integrity
```

目标：

> 授权核心不能被普通文本编辑器直接修改后继续运行。

---

## Phase 5：Package Builder

实现：

```text
Copy Project
Inject
Protect
Generate License
Generate Manifest
Verify
ZIP
```

---

## Phase 6：GUI

最后再做：

```text
PySide6
```

不要一开始把所有业务逻辑写进 GUI。

GUI 只调用 Service。

---

# 34. Service 层

推荐：

```text
ProjectService
LicenseService
ProtectionService
InjectionService
ValidationService
PackageService
```

GUI：

```text
MainWindow
   ↓
Service
   ↓
Core
```

禁止：

```text
GUI → 直接修改 PHP 文件
```

---

# 35. 测试要求

必须有单元测试：

```text
tests/
├── test_license.py
├── test_signature.py
├── test_domain.py
├── test_ipv4.py
├── test_integrity.py
├── test_injector.py
├── test_packager.py
└── test_e2e.py
```

---

# 36. 必须通过的核心测试

```text
Test 01
正确 License → PASS

Test 02
错误签名 → FAIL

Test 03
错误 Domain + 正确 IPv4 → PASS

Test 04
正确 Domain + 错误 IPv4 → PASS

Test 05
错误 Domain + 错误 IPv4 → FAIL

Test 06
修改 License Payload → FAIL

Test 07
修改 Protected Core → FAIL

Test 08
复制项目到不同 Domain + 不同 IP → FAIL

Test 09
客户修改业务 Controller → PASS

Test 10
客户修改业务 Service → PASS

Test 11
客户修改前端 → PASS

Test 12
完全断网 → 正常授权运行
```

---

# 37. 关键安全边界

必须明确：

> 本系统不是不可破解 DRM。

如果攻击者拥有：

```text
服务器 root
+
完整源码
+
完整运行环境
```

理论上最终可以修改运行环境或补丁绕过保护。

因此 V1 的目标是：

```text
普通复制
    ↓
换域名
    ↓
换 IP
    ↓
直接重新部署
```

无法直接成功。

同时提高：

```text
修改授权逻辑
重新打包
绕过 Watchdog
```

的技术成本。

---

# 38. Codex 执行要求

Codex 必须按照以下规则开发：

1. 先建立完整项目目录；
2. 先实现核心 Service，再实现 GUI；
3. 所有模块必须有类型标注；
4. 所有核心逻辑必须有单元测试；
5. 不允许把私钥写入代码；
6. 不允许硬编码客户 Domain/IP；
7. 不允许整个 PHP 项目加密；
8. 不允许 Watchdog 核心以完整明文形式暴露；
9. 不允许运行时访问厂商服务器；
10. 不允许为了授权增加 Python 运行时依赖；
11. 打包前必须创建临时工作目录；
12. 原始源码不得直接修改，必须复制到输出工作区后再处理；
13. 任意步骤失败必须自动清理临时目录；
14. 输出 ZIP 前必须完成 Release 自检；
15. GUI 只负责交互，不负责业务核心逻辑。

---

# 39. 原始源码保护

用户选择：

```text
D:\Project\Backend
```

绝对不能直接修改原目录。

必须：

```text
Original
   ↓
Temporary Workspace
   ↓
Transform
   ↓
Verify
   ↓
Output
```

即：

```text
原始项目
   ↓
只读
   ↓
复制
   ↓
保护处理
   ↓
生成交付项目
```

这样即使工具异常，也不能破坏开发人员原项目。

---

# 40. CLI 模式

虽然主要使用 GUI，但建议同时实现 CLI：

```bash
license-protector build \
  --project ./backend \
  --domain customer.example.com \
  --ipv4 123.123.123.123 \
  --version 1.0.0 \
  --output ./dist
```

这样方便 Codex、CI 和自动化测试。

GUI 最终只是 CLI/Core 的图形化封装。

---

# 41. 最终验收标准

完成 V1 后，执行：

```text
原始 PHP 项目
      ↓
LicenseProtector.exe
      ↓
Customer_A_Release.zip
      ↓
部署到授权 Domain
      ↓
PASS
```

修改业务：

```text
Controller
Service
Model
Frontend
```

仍：

```text
PASS
```

复制到：

```text
new-domain.com
new-ip
```

结果：

```text
FAIL
```

修改：

```text
license.dat
```

结果：

```text
FAIL
```

修改：

```text
protected watchdog
```

结果：

```text
FAIL
```

完全断网：

```text
PASS
```

---

# 42. V1 完成定义

只有同时满足以下条件，才认为 V1 完成：

```text
[✓] Windows EXE 可以启动
[✓] GUI 可以选择 PHP 项目
[✓] 自动扫描项目
[✓] 输入 Domain
[✓] 输入 IPv4
[✓] 生成唯一 License
[✓] Ed25519 签名
[✓] 自动注入 Watchdog
[✓] Watchdog 核心受到保护
[✓] Domain OR IPv4 验证
[✓] License 签名验证
[✓] 完整性验证
[✓] 客户业务源码可修改
[✓] 客户无需联网
[✓] 客户正常 PHP 部署
[✓] 自动生成 ZIP
[✓] 自动执行 Release 测试
[✓] 原始项目不会被修改
[✓] 完整测试通过
```

---

# 43. Codex 第一条执行指令

实现时不要一次性生成所有代码。

按照：

```text
Step 1
建立项目骨架

Step 2
实现 License Schema + Ed25519

Step 3
实现 Domain / IPv4 Validator

Step 4
实现 Watchdog

Step 5
实现 Integrity

Step 6
实现 PHP Scanner / Injector

Step 7
实现 Protector

Step 8
实现 Package Builder

Step 9
实现 CLI

Step 10
实现 PySide6 GUI

Step 11
实现 EXE 构建

Step 12
执行完整 E2E Test
```

每完成一个 Step：

```text
运行测试
 ↓
修复问题
 ↓
再进入下一阶段
```

不要跳过测试直接进入下一阶段。

---

# 44. 最终产品模型

```text
             LicenseProtector.exe
                     │
                     ▼
             ┌───────────────┐
             │ PHP Project   │
             └───────┬───────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
      License      Watchdog     Integrity
        │            │            │
        └────────────┼────────────┘
                     ▼
               Customer Release
                     │
                     ▼
               客户正常部署
                     │
          ┌──────────┴──────────┐
          │                     │
     业务源码可修改         授权核心受保护
          │                     │
          └──────────┬──────────┘
                     ▼
              Domain OR IPv4
                     │
              ┌──────┴──────┐
              ▼             ▼
             PASS          FAIL
              │             │
              ▼             ▼
            正常运行       拒绝运行
```

**最终原则：**

> **开放业务源码，保护授权核心；本地离线验证，域名/IP 二选一匹配；正常部署不变；核心目标是阻止“复制源码 → 换域名/IP → 二次销售”的低成本行为。**
