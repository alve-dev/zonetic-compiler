# ============================================================
# Zonetic Installer v2.0 — Windows Setup (Complete Version)
# ============================================================
# 
# Installs the Zonetic compiler and VM, checks dependencies,
# clones repositories, and updates the system PATH.
# This version uses git init + pull instead of clone for
# maximum compatibility.
#
# Usage: .\install_windows_complete.ps1
# Usage with irm: irm https://raw.githubusercontent.com/alve-dev/zonetic-compiler/refs/heads/main/install_windows_complete.ps1 | iex
# ============================================================

# ------------------------------
# ANSI Colors
# ------------------------------
$GREEN  = "$([char]0x1B)[32m"
$RED    = "$([char]0x1B)[31m"
$YELLOW = "$([char]0x1B)[33m"
$CYAN   = "$([char]0x1B)[36m"
$RESET  = "$([char])0x1B)[0m]"

# ------------------------------
# Fun little faces for visual feedback
# ------------------------------
$FRAMES = @("[ o_o]", "[ o_-]", "[ -_-]", "[ -_o]")

$FACE_SUCCESS = "${GREEN}[ ^_^]${RESET}"
$FACE_DONE    = "${CYAN}[ ⌐■_■]b${RESET}"
$FACE_ERROR   = "${RED}[ x_x]${RESET}"
$FACE_PROMPT  = "${YELLOW}[ o_0]${RESET}"
$FACE_STATIC  = "[ o_o]"

# ------------------------------
# Logging helper functions
# ------------------------------

function Write-Success {
    param([string]$Message)
    Write-Host "$FACE_SUCCESS $Message" -ForegroundColor Green
}

function Write-Done {
    param([string]$Message)
    Write-Host "$FACE_DONE $Message" -ForegroundColor Cyan
}

function Write-Error {
    param([string]$Message)
    Write-Host "$FACE_ERROR $Message" -ForegroundColor Red
    exit 1
}

function Write-Prompt {
    param([string]$Message)
    Write-Host "$FACE_PROMPT $Message" -ForegroundColor Yellow -NoNewline
}

function Write-Static {
    param([string]$Message)
    Write-Host "$FACE_STATIC $Message"
}

function Write-Animated {
    param(
        [string]$Message,
        [scriptblock]$JobScript
    )
    
    $job = Start-Job -ScriptBlock $JobScript
    
    $frameIndex = 0
    do {
        $frame = $FRAMES[$frameIndex % $FRAMES.Count]
        Write-Host "`r$frame $Message " -NoNewline
        $frameIndex++
        Start-Sleep -Milliseconds 150
    } until ($job.State -ne 'Running')
    
    Write-Host "`r[ o_o] $Message " -NoNewline
    Write-Host ""
    
    $result = Receive-Job -Job $job -Wait -AutoRemoveJob
    if ($job.State -eq 'Failed') {
        Write-Host "$FACE_ERROR The job failed. Check the error above." -ForegroundColor Red
        exit 1
    }
    return $result
}

function Write-Separator {
    Write-Host ""
    Write-Host "------------------------------------------------"
    Write-Host ""
}

# ------------------------------
# System utilities
# ------------------------------

function Refresh-Env {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

function Add-To-UserPath {
    param([string]$PathToAdd)
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -notlike "*$PathToAdd*") {
        [Environment]::SetEnvironmentVariable("Path", "$userPath;$PathToAdd", "User")
        Refresh-Env
        Write-Success "Path updated successfully."
        return $true
    }
    Write-Static "The PATH already contains this path. No changes needed."
    return $false
}

function Add-To-SystemPath {
    param([string]$PathToAdd)
    $systemPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    if ($systemPath -notlike "*$PathToAdd*") {
        [Environment]::SetEnvironmentVariable("Path", "$systemPath;$PathToAdd", "Machine")
        Refresh-Env
        Write-Success "System PATH updated successfully."
        return $true
    }
    return $false
}

# ------------------------------
# Dependency management
# ------------------------------

function Install-With-Winget {
    param(
        [string]$CommandName,
        [string]$PackageId
    )
    
    Write-Animated "Installing $CommandName..." {
        winget install --exact --id $PackageId --accept-source-agreements --accept-package-agreements
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install $CommandName with winget."
        }
    }
    Refresh-Env
}

function Locate-GCC {
    Write-Static "Looking for GNU compiler..."
    $possiblePaths = @(
        "C:\msys64\ucrt64\bin",
        "C:\msys64\mingw64\bin",
        "C:\Program Files\mingw-w64\*\mingw64\bin"
    )
    foreach ($p in $possiblePaths) {
        if (Test-Path "$p\g++.exe") {
            return $p
        }
    }
    $found = Get-ChildItem -Path "C:\Program Files" -Filter "g++.exe" -Recurse -ErrorAction SilentlyContinue |
             Select-Object -First 1 -ExpandProperty DirectoryName
    return $found
}

function Check-And-Install-Dependency {
    param(
        [string]$CommandName,
        [string]$PackageId
    )
    
    $exists = $false
    if ($CommandName -eq "g++") {
        $exists = (g++ --version 2>$null) -ne $null
    } else {
        $exists = (Get-Command $CommandName -ErrorAction SilentlyContinue) -ne $null
    }
    
    if ($exists) {
        Write-Success "$CommandName is ready."
        return
    }
    
    Write-Static "Warning: '$CommandName' not found or broken."
    
    while ($true) {
        Write-Prompt "Install it now? (y/n) "
        $answer = Read-Host
        $answer = $answer.ToLower()
        
        if ($answer -eq "y") {
            Install-With-Winget -CommandName $CommandName -PackageId $PackageId
            
            if ($CommandName -eq "g++") {
                $gccPath = Locate-GCC
                if ($gccPath) {
                    Add-To-SystemPath -PathToAdd $gccPath
                    Write-Success "g++ linked successfully at: $gccPath"
                } else {
                    Write-Static "Could not locate g++ after installation."
                }
            }
            return
        } elseif ($answer -eq "n") {
            Write-Error "Error: '$CommandName' is required. Installation cancelled."
        }
    }
}

# ------------------------------
# Clone or update repositories (Complete version uses init + pull)
# ------------------------------

function Init-And-Pull-Repo {
    param(
        [string]$RepoUrl,
        [string]$TargetDir
    )
    
    if (Test-Path $TargetDir) {
        Write-Static "Repository already exists at: $TargetDir"
        Write-Animated "Updating repository..." {
            Set-Location $TargetDir
            git pull origin main
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to pull in $TargetDir."
            }
            Set-Location $HOME
        }
    } else {
        Write-Animated "Initializing and pulling repository: $RepoUrl" {
            Set-Location $TargetDir
            git init
            try { git remote add origin $RepoUrl 2>$null } catch {}
            git pull origin main
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to pull from $RepoUrl."
            }
            Set-Location $HOME
        }
    }
}

# ------------------------------
# Main installation routine
# ------------------------------

function Main {
    Write-Separator
    Write-Host "${CYAN}Zonetic Installer v2.0 (Complete)${RESET}" -ForegroundColor Cyan
    Write-Separator
    
    Write-Static "Checking dependencies..."
    Check-And-Install-Dependency "git" "Git.Git"
    Check-And-Install-Dependency "python" "Python.Python.3.12"
    Check-And-Install-Dependency "g++" "MSYS2.MSYS2"
    
    $InstallDir = Join-Path $HOME ".zonetic"
    $ZoncDir    = Join-Path $InstallDir ".zonc"
    $ZonvmDir   = Join-Path $InstallDir ".zonvm"
    
    if (Test-Path $InstallDir) {
        $FileCount = (Get-ChildItem -Path $InstallDir -Force).Count
        if ($FileCount -gt 0) {
            Write-Static "The directory $InstallDir is not empty ($FileCount items)."
            while ($true) {
                Write-Prompt "Overwrite its contents? (y/n) "
                $choice = Read-Host
                $choice = $choice.ToLower()
                if ($choice -eq "y") {
                    Write-Static "Cleaning directory..."
                    Remove-Item -Recurse -Force $InstallDir | Out-Null
                    break
                } elseif ($choice -eq "n") {
                    Write-Error "Installation cancelled by user."
                }
            }
        }
    }
    
    Write-Static "Creating directories..."
    New-Item -ItemType Directory -Path $ZoncDir -Force | Out-Null
    New-Item -ItemType Directory -Path $ZonvmDir -Force | Out-Null
    
    Write-Static "Downloading Zonetic Compiler (Complete)..."
    Init-And-Pull-Repo "https://github.com/alve-dev/zonetic-lang-tree-walker-version.git" $ZoncDir
    
    Write-Static "Downloading Zonetic VM (Complete)..."
    Init-And-Pull-Repo "https://github.com/alve-dev/zonetic-vm.git" $ZonvmDir
    
    Write-Static "Updating user PATH..."
    $LauncherPath = Join-Path $ZoncDir "scripts"
    Add-To-UserPath -PathToAdd $LauncherPath
    
    Write-Separator
    Write-Done "Zonetic v2.0.0 installed successfully!"
    Write-Done "To test the installation, open a new terminal and run:"
    Write-Done "    zon repl"
    Write-Done "If it doesn't work, close and reopen your terminal to apply PATH changes."
    Write-Separator
    
    Read-Host "Press Enter to exit"
}

# ------------------------------
# Entry point
# ------------------------------

if ($PSVersionTable.PSVersion.Major -lt 5) {
    Write-Error "This script requires PowerShell 5.0 or higher."
}

Main
