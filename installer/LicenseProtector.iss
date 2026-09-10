; LicenseProtector installer
; Developer: Stephen Hu <stephenhu031028@gmail.com>
[Setup]
AppId={{B1E3D6C8-1F0D-4E0D-9E2C-5E0D1A5F2D11}
AppName=LicenseProtector
AppVersion=1.1.0
AppPublisher=Stephen Hu
AppPublisherURL=mailto:stephenhu031028@gmail.com
DefaultDirName={autopf}\LicenseProtector
DefaultGroupName=LicenseProtector
OutputDir=..\installer_dist
OutputBaseFilename=LicenseProtector-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayName=LicenseProtector

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："

[Files]
Source: "..\final_dist\LicenseProtector.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; 程序安装在 Program Files 时，允许普通用户在 keys 中生成和更新厂商密钥。
Name: "{app}\keys"; Permissions: users-modify

[Icons]
Name: "{group}\LicenseProtector"; Filename: "{app}\LicenseProtector.exe"
Name: "{autodesktop}\LicenseProtector"; Filename: "{app}\LicenseProtector.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\LicenseProtector.exe"; Description: "启动 LicenseProtector"; Flags: nowait postinstall skipifsilent
