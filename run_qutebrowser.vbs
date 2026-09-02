Set WshShell = CreateObject("WScript.Shell")

WshShell.CurrentDirectory = "D:\study\Git_Start\qutebrowser"

WshShell.Run ".venv\Scripts\python.exe qutebrowser.py", 0, False