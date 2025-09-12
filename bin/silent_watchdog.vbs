Set oShell = CreateObject("Wscript.Shell")
cmd = "powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File ""C:\Lastivka\lastivka_core\security\watchdog_wrapper.ps1"""
oShell.Run cmd, 0, False  ' 0 = ????????, False = ?? ??????
