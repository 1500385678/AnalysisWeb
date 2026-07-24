' AnalysisWeb 自动启动(用相对路径,跟 vbs 所在目录)
' 2026-07-24 v1.0.0:从 PictureWeb 拆出,env 重命名为 ANALYSISWEB_TEST_PORT
Option Explicit

Sub LaunchServer()
    On Error Resume Next
    Dim WshShell, fso, scriptDir, logFile, ts

    Set WshShell = CreateObject("WScript.Shell")
    Set fso = CreateObject("Scripting.FileSystemObject")
    scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
    logFile = scriptDir & "\logs\start_hidden.err.log"

    ' 确保 logs 目录存在
    fso.CreateFolder(scriptDir & "\logs")

    ' 默认 8082;若需 dev 端口,自行改这里(ANALYSISWEB_TEST_PORT=9082)
    ' 2026-07-24 v1.0.0:不再强制设 dev 端口,直接走默认 8082

    WshShell.CurrentDirectory = scriptDir
    WshShell.Run "python.exe -X utf8 """ & scriptDir & "\server.py""", 0, False

    If Err.Number <> 0 Then
        Set ts = fso.OpenTextFile(logFile, 8, True)  ' 8 = ForAppending
        ts.WriteLine Now() & " [ERR " & Err.Number & "] " & Err.Description
        ts.Close
        MsgBox "启动失败,日志见 " & logFile, vbExclamation, "AnalysisWeb"
    End If

    Set ts = Nothing
    Set fso = Nothing
    Set WshShell = Nothing
End Sub

LaunchServer

