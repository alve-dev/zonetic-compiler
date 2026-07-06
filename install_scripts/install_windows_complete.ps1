# ==============================================================
# Zonetic Installer — Windows Setup
#
# Default: sparse checkout — downloads only src/zonc/*, scripts/*
# Complete: swap Clone-Zonc-Sparse for Clone-Zonc-Full in Main()
#
# Usage:
#   .\install_windows.ps1
#   irm https://raw.githubusercontent.com/alve-dev/zonetic-compiler/refs/heads/main/install_windows.ps1 | iex
# ==============================================================

# ------------------------------------------------------------------
# ANSI colors
# ------------------------------------------------------------------
$GREEN  = "$([char]0x1B)[32m"
$RED    = "$([char]0x1B)[31m"
$YELLOW = "$([char]0x1B)[33m"
$CYAN   = "$([char]0x1B)[36m"
$RESET  = "$([char]0x1B)[0m"

# ------------------------------------------------------------------
# Zonny faces
#   NEUTRAL  [ o_o]  — working / info
#   SUCCESS  [ ^_^]  — step completed
#   DONE     [ ⌐■_■]b — everything finished
#   ERROR    [ x_x]  — fatal error
#   PROMPT   [ o_0]  — asking the user something
# ------------------------------------------------------------------
$FACE_NEUTRAL = "[ o_o]"
$FACE_SUCCESS = "${GREEN}[ ^_^]${RESET}"
$FACE_DONE    = "${CYAN}[ ⌐■_■]b${RESET}"
$FACE_ERROR   = "${RED}[ x_x]${RESET}"
$FACE_PROMPT  = "${YELLOW}[ o_0]${RESET}"

# ------------------------------------------------------------------
# Output helpers
# ------------------------------------------------------------------

function Write-Info { param([string]$Msg)
    Write-Host "$FACE_NEUTRAL $Msg"
}

function Write-Success { param([string]$Msg)
    Write-Host "$FACE_SUCCESS $Msg" -ForegroundColor Green
}

function Write-Done { param([string]$Msg)
    Write-Host "$FACE_DONE $Msg" -ForegroundColor Cyan
}

function Write-Err { param([string]$Msg)
    Write-Host "$FACE_ERROR $Msg" -ForegroundColor Red
    exit 1
}

function Write-Prompt { param([string]$Msg)
    Write-Host "$FACE_PROMPT $Msg" -ForegroundColor Yellow -NoNewline
}

function Write-Separator {
    Write-Host ""
    Write-Host "------------------------------------------------"
    Write-Host ""
}

# ------------------------------------------------------------------
# Environment / PATH helpers
# ------------------------------------------------------------------

function Refresh-Env {
    $env:Path = (
        [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
        [System.Environment]::GetEnvironmentVariable("Path", "User")
    )
}

function Add-To-UserPath { param([string]$PathToAdd)
    $current = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($current -notlike "*$PathToAdd*") {
        [Environment]::SetEnvironmentVariable("Path", "$current;$PathToAdd", "User")
        Refresh-Env
        Write-Success "PATH updated."
        return $true
    }
    Write-Info "PATH already contains this entry. No changes needed."
    return $false
}

function Add-To-SystemPath { param([string]$PathToAdd)
    $current = [Environment]::GetEnvironmentVariable("Path", "Machine")
    if ($current -notlike "*$PathToAdd*") {
        [Environment]::SetEnvironmentVariable("Path", "$current;$PathToAdd", "Machine")
        Refresh-Env
        Write-Success "System PATH updated."
        return $true
    }
    return $false
}

# ------------------------------------------------------------------
# Dependency management
# ------------------------------------------------------------------

function Find-GCC {
    $candidates = @(
        "C:\msys64\ucrt64\bin",
        "C:\msys64\mingw64\bin",
        "C:\Program Files\mingw-w64\*\mingw64\bin"
    )
    foreach ($p in $candidates) {
        if (Test-Path "$p\g++.exe") { return $p }
    }
    return Get-ChildItem -Path "C:\Program Files" -Filter "g++.exe" -Recurse -ErrorAction SilentlyContinue |
           Select-Object -First 1 -ExpandProperty DirectoryName
}

function Require-Tool { param([string]$Cmd, [string]$PackageId)
    $found = if ($Cmd -eq "g++") {
        (g++ --version 2>$null) -ne $null
    } else {
        (Get-Command $Cmd -ErrorAction SilentlyContinue) -ne $null
    }

    if ($found) { Write-Success "$Cmd is ready." ; return }

    Write-Info "'$Cmd' not found."
    while ($true) {
        Write-Prompt "Install it now? (y/n) "
        $answer = (Read-Host).ToLower()

        if ($answer -eq "y") {
            Write-Info "Installing $Cmd via winget..."
            winget install --exact --id $PackageId --accept-source-agreements --accept-package-agreements
            if ($LASTEXITCODE -ne 0) { Write-Err "Failed to install $Cmd." }
            Refresh-Env

            if ($Cmd -eq "g++") {
                $path = Find-GCC
                if ($path) {
                    Add-To-SystemPath -PathToAdd $path
                    Write-Success "g++ linked at: $path"
                } else {
                    Write-Info "Could not locate g++ automatically. Add it to PATH manually."
                }
            }
            return

        } elseif ($answer -eq "n") {
            Write-Err "'$Cmd' is required. Aborting."
        }
    }
}

# ------------------------------------------------------------------
# Repository cloning
# ------------------------------------------------------------------

function Clone-Zonc-Full { param([string]$Url, [string]$Dir)
    if (Test-Path $Dir) {
        Write-Info "Compiler already exists. Updating..."
        Push-Location $Dir
        try {
            git pull origin main
            if ($LASTEXITCODE -ne 0) { Write-Err "Failed to update compiler." }
        } finally { Pop-Location }
        Write-Success "Compiler updated."
        return
    }

    Write-Info "Cloning full compiler..."
    git clone $Url $Dir
    if ($LASTEXITCODE -ne 0) { Write-Err "Failed to clone compiler repository." }
    Write-Success "Compiler downloaded."
}

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

function Main {
    Write-Separator
    Write-Host "${CYAN}Zonetic Installer v2.0 — Windows${RESET}" -ForegroundColor Cyan
    Write-Separator

    Write-Info "Checking dependencies..."
    Require-Tool "git"    "Git.Git"
    Require-Tool "python" "Python.Python.3.12"
    Require-Tool "g++"    "MSYS2.MSYS2"

    $InstallDir = Join-Path $HOME ".zonetic"
    $ZoncDir    = Join-Path $InstallDir ".zonc"
    $ZonvmDir   = Join-Path $InstallDir ".zonvm"

    if (Test-Path $InstallDir) {
        $count = (Get-ChildItem -Path $InstallDir -Force).Count
        if ($count -gt 0) {
            Write-Info "$InstallDir is not empty ($count items)."
            while ($true) {
                Write-Prompt "Overwrite its contents? (y/n) "
                $answer = (Read-Host).ToLower()
                if ($answer -eq "y") {
                    Write-Info "Cleaning directory..."
                    Remove-Item -Recurse -Force $InstallDir | Out-Null
                    break
                } elseif ($answer -eq "n") {
                    Write-Err "Installation cancelled."
                }
            }
        }
    }

    New-Item -ItemType Directory -Path $ZoncDir  -Force | Out-Null
    New-Item -ItemType Directory -Path $ZonvmDir -Force | Out-Null

    Clone-Zonc-Full "https://github.com/alve-dev/zonetic-lang-tree-walker-version.git" $ZoncDir

    Clone-Zonvm "https://github.com/alve-dev/zonetic-vm.git" $ZonvmDir

    Add-To-UserPath -PathToAdd (Join-Path $ZoncDir "scripts")

    Write-Separator
    Write-Done "Zonetic v2 installed successfully!"
    Write-Done "Open a new terminal and run: zon vw --vers"
    Write-Done "If it doesn't work, close and reopen your terminal to apply PATH changes."
    Write-Separator

    Read-Host "Press Enter to exit"
}

# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------
if ($PSVersionTable.PSVersion.Major -lt 5) {
    Write-Err "This script requires PowerShell 5.0 or higher."
}

Main