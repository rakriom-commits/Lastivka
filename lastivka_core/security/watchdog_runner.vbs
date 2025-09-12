Set sh = CreateObject("WScript.Shell")
sh.Run "powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File ""C:\Lastivka\lastivka_core\security\watchdog_wrapper.ps1""", 0, False
