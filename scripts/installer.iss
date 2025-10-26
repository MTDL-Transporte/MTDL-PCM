; Inno Setup Script for MTDL-PCM
; Instalador padronizado: Program Files, atalhos com "Iniciar" e "Abrir Login"
; Ajusta working dir e mantem porta padrao 8000; adiciona suporte a inglês e pt-BR

#define MyAppName "MTDL-PCM"
#ifndef MyAppVersion
  #define MyAppVersion "1.0.1"
#endif
#define MyAppPublisher "MTDL Tecnologia"
#define MyAppURL "https://www.mtdl.com.br"

[Setup]
AppId={{38B29B01-2B6C-4A8C-B6B3-PCM202410}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
Compression=lzma
SolidCompression=yes
OutputDir=..\releases
OutputBaseFilename={#MyAppName}-Setup-{#MyAppVersion}
SetupIconFile=..\static\img\app.ico
WizardStyle=modern
ShowLanguageDialog=yes
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Installer
VersionInfoVersion={#MyAppVersion}
UninstallDisplayIcon={app}\MTDL-PCM.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\\BrazilianPortuguese.isl"

[CustomMessages]
english.DesktopIconTask=Create Desktop shortcuts
brazilianportuguese.DesktopIconTask=Criar atalhos na Área de Trabalho
english.GroupShortcuts=Shortcuts:
brazilianportuguese.GroupShortcuts=Atalhos:
english.StartServerPostInstall=Start MTDL-PCM server
brazilianportuguese.StartServerPostInstall=Iniciar servidor MTDL-PCM
english.OpenBrowserPostInstall=Open MTDL-PCM in browser
brazilianportuguese.OpenBrowserPostInstall=Abrir MTDL-PCM no navegador

[Files]
; Binario principal gerado pelo PyInstaller
Source: "..\\dist\\MTDL-PCM.exe"; DestDir: "{app}"; Flags: ignoreversion
; Icone para atalhos
Source: "..\\static\\img\\app.ico"; DestDir: "{app}"; Flags: ignoreversion
; Helper para abrir o login automaticamente
Source: "..\\scripts\\open_login.cmd"; DestDir: "{app}"; Flags: ignoreversion

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIconTask}"; GroupDescription: "{cm:GroupShortcuts}"; Flags: unchecked

[Icons]
; Menu Iniciar: atalho principal (inicia servidor)
Name: "{group}\\MTDL-PCM"; Filename: "{app}\\MTDL-PCM.exe"; WorkingDir: "{app}"; IconFilename: "{app}\\app.ico"
; Menu Iniciar: atalho de login (abre navegador e inicia se necessario)
Name: "{group}\\MTDL-PCM (Login)"; Filename: "{app}\\open_login.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\\app.ico"
; Desktop: atalho principal
Name: "{autodesktop}\\MTDL-PCM"; Filename: "{app}\\MTDL-PCM.exe"; WorkingDir: "{app}"; IconFilename: "{app}\\app.ico"; Tasks: desktopicon
; Desktop: atalho de login
Name: "{autodesktop}\\MTDL-PCM (Login)"; Filename: "{app}\\open_login.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\\app.ico"; Tasks: desktopicon

[Run]
; Oferece iniciar o servidor apos a instalacao
Filename: "{app}\\MTDL-PCM.exe"; Description: "{cm:StartServerPostInstall}"; Flags: postinstall skipifsilent nowait; WorkingDir: "{app}"
; Abre o navegador apontando para a pagina de login (helper garante inicio do servidor ou dominio)
Filename: "{app}\\open_login.cmd"; Description: "{cm:OpenBrowserPostInstall}"; Flags: postinstall skipifsilent

[UninstallDelete]
; Remover dados gerados (opcional)
Type: filesandordirs; Name: "{app}\\data"
Type: files; Name: "{app}\\mtdl_pcm.db"