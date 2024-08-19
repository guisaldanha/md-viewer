; Script gerado pelo Inno Setup Script Wizard.
; ESTE É UM EXEMPLO. LEIA A DOCUMENTAÇÃO PARA DETALHES SOBRE A CRIAÇÃO DE SCRIPTS DO INNO SETUP!

; Definições de constantes para o aplicativo
#define MyAppName "MD Viewer"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Guilherme Saldanha"
#define MyAppURL "https://www.guisaldanha.com/"
#define MyAppExeName "MDViewer.exe"
#define MyAppAssocName "Markdown File"
#define MyAppAssocExt ".md"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

; Configurações gerais do instalador
[Setup]
AppId={{FE3DDCED-675E-4D77-BF43-5CF84BC6F902}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes
DisableProgramGroupPage=yes
LicenseFile=D:\Python\MDViewer\LICENSE
PrivilegesRequired=lowest
OutputDir=D:\Python\MDViewer\distribuition
OutputBaseFilename=MDViewerSetup{#MyAppVersion}
SetupIconFile=D:\Python\MDViewer\assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
AlwaysRestart=no
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
RestartIfNeededByRun=no
CloseApplications=yes

; Definição dos idiomas suportados pelo instalador
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; Definição das tarefas adicionais que o usuário pode escolher durante a instalação
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

; Arquivos que serão incluídos no instalador
[Files]
Source: "D:\Python\MDViewer\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion restartreplace
Source: "D:\Python\MDViewer\dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Configurações de registro para associar o aplicativo com arquivos .md
[Registry]
; HKCU: HKEY_CURRENT_USER (Para o usuário atual), HKLM: HKEY_LOCAL_MACHINE (Para todos os usuários)
Root: HKCU; Subkey: "Software\Classes\{#MyAppAssocExt}\OpenWithProgids"; ValueType: string; ValueName: "{#MyAppAssocKey}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\{#MyAppAssocKey}"; ValueType: string; ValueName: ""; ValueData: "{#MyAppAssocName}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\{#MyAppAssocKey}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\{#MyAppAssocKey}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".myp"; ValueData: ""; Flags: uninsdeletevalue

; Ícones que serão criados pelo instalador
[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; Comandos que serão executados após a instalação
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove todos os arquivos e pastas criados no diretório de instalação
Type: filesandordirs; Name: "{app}"
; Remover logs e arquivos temporários, caso tenham sido criados
Type: filesandordirs; Name: "{localappdata}\MD Viewer\Logs"
; Remove a pasta de dados do usuário, caso vazia
Type: dirifempty; Name: "{userappdata}\MD Viewer"

[Code]
var
  PreviousVersion: string;

procedure InitializeWizard;
{ Executa código personalizado durante a fase inicial da instalação, antes que o assistente de instalação mostre suas telas e inicie o processo de instalação propriamente dito.}
var
  Response: Integer;
begin
  { Verificar se uma versão anterior está instalada }
  if RegQueryStringValue(HKCU, 'Software\{#MyAppPublisher}\{#MyAppName}', 'Version', PreviousVersion) then
  begin
    if CompareStr(PreviousVersion, '{#MyAppVersion}') = 0 then
    begin
      { Perguntar se deseja reparar a instalação }
      Response := MsgBox('A versão ' + PreviousVersion + ' já está instalada. Deseja reparar a instalação e substituir todos os arquivos?', mbConfirmation, MB_YESNO);
      if Response = IDNO then
      begin
        Abort; { Se o usuário não quiser reparar, cancelar a instalação }
      end
    end
    else if CompareStr(PreviousVersion, '{#MyAppVersion}') < 0 then
    begin
      MsgBox('Uma versão anterior foi detectada: ' + PreviousVersion + '. Ela será atualizada para a versão ' + '{#MyAppVersion}' + '.', mbInformation, MB_OK);
    end
    else if CompareStr(PreviousVersion, '{#MyAppVersion}') > 0 then
    begin
      MsgBox('Uma versão mais recente foi detectada: ' + PreviousVersion + '. A instalação será cancelada.', mbError, MB_OK);
      Abort;
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
{ Executa código personalizado durante a desinstalação, após cada etapa de desinstalação.}
begin
  if CurUninstallStep = usPostUninstall then
  begin
    { Remover todas as informações do registro relacionadas à versão anterior }
    RegDeleteKeyIncludingSubkeys(HKCU, 'Software\{#MyAppPublisher}\{#MyAppName}');
    RegDeleteKeyIncludingSubkeys(HKCU, 'Software\Classes\{#MyAppAssocExt}\OpenWithProgids');
    RegDeleteKeyIncludingSubkeys(HKCU, 'Software\Classes\{#MyAppAssocKey}');

    { Verificar e remover as chaves do MuiCache, se existirem }
    if RegKeyExists(HKCU, 'Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache') then
    begin
      RegDeleteKeyIncludingSubkeys(HKCU, 'Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache');
    end;

    { Verificar e remover as chaves relacionadas ao histórico de atalhos (UFH\SHC), se existirem }
    if RegKeyExists(HKCU, 'Software\Microsoft\Windows\CurrentVersion\UFH\SHC') then
    begin
      RegDeleteKeyIncludingSubkeys(HKCU, 'Software\Microsoft\Windows\CurrentVersion\UFH\SHC');
    end;

    { Verificar e remover as chaves relacionadas à compatibilidade, se existirem }
    if RegKeyExists(HKCU, 'Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Compatibility Assistant\Store') then
    begin
      RegDeleteKeyIncludingSubkeys(HKCU, 'Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Compatibility Assistant\Store');
    end;

  end;
end;

procedure RegisterPreviousVersion;
{ Registra a versão anterior no registro após a instalação. Isso é útil para futuras atualizações.}
begin
  { Registrar a nova versão no registro }
  RegWriteStringValue(HKCU, 'Software\{#MyAppPublisher}\{#MyAppName}', 'Version', '{#MyAppVersion}');
end;

procedure CurStepChanged(CurStep: TSetupStep);
{ Executa código personalizado durante a instalação, após cada etapa de instalação. }
begin
  if CurStep = ssPostInstall then
  begin
    { Após a instalação, registrar a nova versão }
    RegisterPreviousVersion;
  end;
end;
