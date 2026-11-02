# One-time setup on a new Windows PC: installs Python packages and registers the
# three scheduled tasks (Yad2_Morning, Yad2_Evening, Yad2_Watcher) pointing at
# THIS folder. Safe to re-run — existing tasks with the same names are replaced.
#
# Usage (from a normal, non-admin PowerShell in the project folder):
#   powershell -ExecutionPolicy Bypass -File .\setup_new_pc.ps1

$ErrorActionPreference = "Stop"
$Here = $PSScriptRoot

# ── Python ────────────────────────────────────────────────────────────────────
$Python = (& py -c "import sys; print(sys.executable)" 2>$null)
if (-not $Python) {
    throw "Python not found. Install Python 3.12 from python.org (keep 'py launcher' ticked) and re-run."
}
Write-Host "Python: $Python"
& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $Here "requirements.txt")

# ── Google Chrome (the scraper drives the real installed Chrome, not Playwright's) ──
$ChromePaths = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
if (-not ($ChromePaths | Where-Object { Test-Path $_ })) {
    Write-Warning "Google Chrome not found. Install it from google.com/chrome before the first scrape."
}

# ── Scheduled tasks ───────────────────────────────────────────────────────────
# Interactive logon is required: the scrape is headful (visible Chrome), so it
# cannot run in session 0. See README "Automation Schedule".
$User      = "$env:USERDOMAIN\$env:USERNAME"
$Principal = New-ScheduledTaskPrincipal -UserId $User -LogonType Interactive -RunLevel Limited

function Register-Yad2Task($Name, $Script, $Trigger, [bool]$Wake) {
    $Action   = New-ScheduledTaskAction -Execute $Python `
                    -Argument "`"$(Join-Path $Here $Script)`"" -WorkingDirectory $Here
    $Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun:$Wake `
                    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
                    -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $Name -Action $Action -Trigger $Trigger `
        -Principal $Principal -Settings $Settings -Force | Out-Null
    Write-Host "Registered task $Name"
}

Register-Yad2Task "Yad2_Morning" "yad2_scraper.py" (New-ScheduledTaskTrigger -Daily -At 09:00) $true
Register-Yad2Task "Yad2_Evening" "yad2_scraper.py" (New-ScheduledTaskTrigger -Daily -At 20:00) $true
$Hourly = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddHours((Get-Date).Hour + 1) `
              -RepetitionInterval (New-TimeSpan -Hours 1)
Register-Yad2Task "Yad2_Watcher" "yad2_watcher.py" $Hourly $false

Write-Host ""
Write-Host "Done. Open the dashboard by double-clicking the .bat file in this folder."
