Set sh = CreateObject("WScript.Shell")
sh.Run "powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File ""C:\Lastivka\lastivka_core\security\cleanup_logs.ps1""", 0, False
