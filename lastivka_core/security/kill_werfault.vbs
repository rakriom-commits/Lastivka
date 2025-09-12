Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File ""C:\Lastivka\lastivka_core\security\kill_werfault.ps1""", 0, False
