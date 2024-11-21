$minPythonVersion = [version]"3.10.0"
$minNodeJSVersion = [version]"20.18.0"
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]"Administrator")

if (-not $isAdmin) {
    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

function Install-RequiredPackage {
    param(
        [string]$PackageName,
        [string]$CommandName = $PackageName,
        [scriptblock]$VersionCheck = $null,
        [version]$MinVersion = $null
    )
    
    try {
        $command = Get-Command $CommandName -ErrorAction SilentlyContinue
        
        if ($command -and -not $VersionCheck) {
            Write-Host "Found $PackageName, skipping installation" -ForegroundColor Green
            return
        }
        
        if ($command -and $VersionCheck) {
            $versionString = & $VersionCheck
            if ($versionString) {
                $version = [version]($versionString -replace '^[vV]|Python\s+')
                if ($version -ge $MinVersion) {
                    Write-Host "Current version of $PackageName is suitable" -ForegroundColor Green
                    return
                }
                Write-Host "Your current version of $PackageName ($version) is not supported. Installing a new one..." -ForegroundColor Yellow
            }
        } elseif (-not $command) {
            Write-Host "You don't have $PackageName installed, installing..." -ForegroundColor Yellow
        }
        
        choco install $PackageName --force -y
    } catch {
        Write-Host "Couldn't verify/install $PackageName. Error: $_" -ForegroundColor Red
        Read-Host -Prompt "Press Enter to exit"
        exit
    }
}

try {
    if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
        iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    }
} catch {
    Write-Host "Couldn't install Chocolatey. Error: $_" -ForegroundColor Red
    Read-Host -Prompt "Press Enter to exit"
    exit
}

Install-RequiredPackage -PackageName "python" -VersionCheck { python --version } -MinVersion $minPythonVersion
Install-RequiredPackage -PackageName "nodejs" -CommandName "node" -VersionCheck { node --version } -MinVersion $minNodeJSVersion
Install-RequiredPackage -PackageName "git"

Import-Module $env:ChocolateyInstall\helpers\chocolateyProfile.psm1
refreshenv

try {
    $gitClonePath = Read-Host "Specify the path to git clone the NotPixelBot repository"
    if (-not (Test-Path $gitClonePath)) {
        New-Item -ItemType Directory -Path $gitClonePath | Out-Null
    }
    
    Write-Host "Cloning NotPixelBot repository..." -ForegroundColor Cyan
    git clone https://github.com/asish1346/NotPixelBot $gitClonePath
    git config --global --add safe.directory $gitClonePath
    Set-Location $gitClonePath
} catch {
    Write-Host "Couldn't git clone NotPixelBot repository. Error: $_" -ForegroundColor Red
    Read-Host -Prompt "Press Enter to exit"
    exit
}

try {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
    .\.venv\Scripts\activate

    Write-Host "Installing poetry..." -ForegroundColor Cyan
    pip install poetry

    Write-Host "Installing dependencies using poetry..." -ForegroundColor Cyan
    poetry install --only main

    Write-Host "Congratulations, you can now run NotPixelBot via start.bat or manually. Check the 'Run the script' section in README.md for details." -ForegroundColor Green
    Read-Host -Prompt "Press Enter to exit"
} catch {
    Write-Host "Couldn't install NotPixelBot dependencies. Error: $_" -ForegroundColor Red
    Read-Host -Prompt "Press Enter to exit"
    exit
}