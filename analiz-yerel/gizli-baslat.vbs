' Toplayiciyi konsol penceresi acmadan calistirir (Gorev Zamanlayici bunu cagirir). Node kapaninca cikis koduyla biter.
Set kabuk = CreateObject("WScript.Shell")
kabuk.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WScript.Quit kabuk.Run("node --env-file=.env sunucu.js", 0, True)
