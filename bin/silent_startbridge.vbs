Set oShell = CreateObject("Wscript.Shell")
cmd = "powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File ""C:\Lastivka\bin\Start-Bridge.ps1"""
oShell.Run cmd, 0, False
