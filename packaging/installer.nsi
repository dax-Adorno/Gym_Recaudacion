Unicode True
!include "MUI2.nsh"
!include "x64.nsh"
!include "WinVer.nsh"
!define APP_LABEL "MOOVE RECOVERY - Version 2.0.1"
!define UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\MooveRecovery"
Name "${APP_LABEL}"
OutFile "..\dist\installer\MOOVE_RECOVERY_2.0.1_Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\MooveRecovery"
RequestExecutionLevel user
SetCompressor zlib
VIProductVersion "2.0.1.0"
VIAddVersionKey /LANG=1034 "ProductName" "${APP_LABEL}"
VIAddVersionKey /LANG=1034 "FileDescription" "Instalador MOOVE RECOVERY 2.0.1"
VIAddVersionKey /LANG=1034 "FileVersion" "2.0.1.0"
VIAddVersionKey /LANG=1034 "LegalCopyright" "DAX"
!define MUI_WELCOMEPAGE_TEXT "Instalacion de MOOVE RECOVERY - Version 2.0.1. Los datos y la activacion se guardan separados del programa."
!define MUI_FINISHPAGE_RUN "$INSTDIR\MooveRecovery.exe"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Spanish"

Function .onInit
  SetShellVarContext current
  SetRegView 64
  ${IfNot} ${RunningX64}
    MessageBox MB_OK|MB_ICONSTOP "Se necesita Windows de 64 bits."
    Abort
  ${EndIf}
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_OK|MB_ICONSTOP "Se necesita Windows 10 o posterior."
    Abort
  ${EndIf}
  IfFileExists "$INSTDIR\MooveRecovery.exe" 0 ready
  ClearErrors
  FileOpen $0 "$INSTDIR\MooveRecovery.exe" a
  IfErrors blocked
  FileClose $0
  Goto ready
  blocked:
    MessageBox MB_OK|MB_ICONSTOP "Cierra MOOVE RECOVERY antes de actualizar."
    Abort
  ready:
FunctionEnd

Section "Programa"
  SetOutPath "$INSTDIR"
  SetOverwrite on
  ClearErrors
  File /r "..\dist\MooveRecovery\*"
  IfErrors failed
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateDirectory "$SMPROGRAMS\MOOVE RECOVERY"
  CreateShortcut "$SMPROGRAMS\MOOVE RECOVERY\MOOVE RECOVERY.lnk" "$INSTDIR\MooveRecovery.exe"
  CreateShortcut "$DESKTOP\MOOVE RECOVERY.lnk" "$INSTDIR\MooveRecovery.exe"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayName" "${APP_LABEL}"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "DisplayVersion" "2.0.1"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "Publisher" "DAX"
  WriteRegStr HKCU "${UNINSTALL_KEY}" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegStr HKCU "${UNINSTALL_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINSTALL_KEY}" "NoRepair" 1
  Goto done
  failed:
    MessageBox MB_OK|MB_ICONSTOP "No se pudo completar la instalacion. Cierra el programa y revisa permisos."
    Abort
  done:
SectionEnd

Function un.onInit
  SetShellVarContext current
  SetRegView 64
  IfFileExists "$INSTDIR\MooveRecovery.exe" 0 ready
  ClearErrors
  FileOpen $0 "$INSTDIR\MooveRecovery.exe" a
  IfErrors blocked
  FileClose $0
  Goto ready
  blocked:
    MessageBox MB_OK|MB_ICONSTOP "Cierra MOOVE RECOVERY antes de desinstalar."
    Abort
  ready:
FunctionEnd

Section "Uninstall"
  !include "..\build\uninstall-files.nsh"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  Delete "$DESKTOP\MOOVE RECOVERY.lnk"
  Delete "$SMPROGRAMS\MOOVE RECOVERY\MOOVE RECOVERY.lnk"
  RMDir "$SMPROGRAMS\MOOVE RECOVERY"
  DeleteRegKey HKCU "${UNINSTALL_KEY}"
SectionEnd
