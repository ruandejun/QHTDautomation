$shell = New-Object -ComObject Shell.Application
$shell.ShellExecute("d:\Workspace\Python\QHTDautomation\MunAutomationDesktop\MunAutomation.exe", "", "d:\Workspace\Python\QHTDautomation\MunAutomationDesktop", "open", 1)
Start-Sleep -Seconds 3
Get-Process MunAutomation -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, MainWindowHandle, MainWindowTitle
