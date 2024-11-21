$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]"Administrator")

if (-not $isAdmin) {
    $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    Start-Process powershell -ArgumentList $arguments -Verb RunAs
    exit
}

if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Host "You don't have Chocolatey installed, can't uninstall" -ForegroundColor Yellow
    Read-Host -Prompt "Press Enter to exit"
    exit
}

$userResponse = Read-Host -Prompt "This will uninstall python, nodejs, git, and even chocolatey. Are you sure you want to continue? (Y/N) [N]"

$userResponse = if ([string]::IsNullOrEmpty($userResponse)) { "N" } else { $userResponse.ToUpper() }

if ($userResponse -ne "Y") {
    Write-Host "Uninstallation cancelled" -ForegroundColor Yellow
    Read-Host -Prompt "Press Enter to exit"
    exit
}

$packages = @("python", "nodejs", "git", "chocolatey")

foreach ($package in $packages) {
    Write-Host "Uninstalling $package..." -ForegroundColor Cyan
    choco uninstall $package --remove-dependencies -y
    Write-Host "Uninstallation of $package completed" -ForegroundColor Green
}

Write-Host "Uninstallation complete. Third-party software has been removed, but the NotPixelBot folder needs to be deleted manually." -ForegroundColor YellowGreen
Read-Host -Prompt "Press Enter to exit"
exit