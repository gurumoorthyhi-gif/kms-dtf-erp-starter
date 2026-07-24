Option Explicit

Dim shell, fileSystem, projectRoot, pythonExe, runScript, command
Set shell = CreateObject("WScript.Shell")
Set fileSystem = CreateObject("Scripting.FileSystemObject")

projectRoot = fileSystem.GetParentFolderName( _
    fileSystem.GetParentFolderName(WScript.ScriptFullName))
pythonExe = projectRoot & "\.venv\Scripts\python.exe"
runScript = projectRoot & "\run.py"

If Not fileSystem.FileExists(pythonExe) Then
    MsgBox "Python environment not found: " & pythonExe, vbCritical, "KMS DTF ERP"
    WScript.Quit 1
End If

shell.CurrentDirectory = projectRoot
command = """" & pythonExe & """ """ & runScript & """"
shell.Run command, 0, False
