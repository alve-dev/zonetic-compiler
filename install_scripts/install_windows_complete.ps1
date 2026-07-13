# ==============================================================
# Zonetic Installer — Windows Setup (v2.2)
#
# Usage:
#   .\install_windows.ps1
#   irm https://raw.githubusercontent.com/alve-dev/zonetic-compiler/refs/heads/main/install_scripts/install_windows_complete.ps1 | iex
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
function Write-Info   { param([string]$Msg) { Write-Host "$FACE_NEUTRAL $Msg" } }
function Write-Success { param([string]$Msg) { Write-Host "$FACE_SUCCESS $Msg" -ForegroundColor Green } }
function Write-Done    { param([string]$Msg) { Write-Host "$FACE_DONE $Msg" -ForegroundColor Cyan } }
function Write-Err     { param([string]$Msg) { Write-Host "$FACE_ERROR $Msg" -ForegroundColor Red; exit 1 } }
function Write-Prompt  { param([string]$Msg) { Write-Host "$FACE_PROMPT $Msg" -ForegroundColor Yellow -NoNewline } }
function Write-Separator { Write-Host ""; Write-Host "------------------------------------------------"; Write-Host "" }

# ------------------------------------------------------------------
# Environment / PATH helpers
# ------------------------------------------------------------------
function Refresh-Env {
    $env:Path = (
        [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
        [System.Environment]::GetEnvironmentVariable("Path", "User")
    )
}

function Add-To-UserPath {
    param([string]$PathToAdd)
    $current = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($current -notlike "*$PathToAdd*") {
        try {
            [Environment]::SetEnvironmentVariable("Path", "$current;$PathToAdd", "User")
            Refresh-Env
            Write-Success "User PATH updated."
            return $true
        } catch {
            Write-Err "Failed to update user PATH: $_"
        }
    } else {
        Write-Info "PATH already contains this entry."
        return $false
    }
}

function Add-To-SystemPath {
    param([string]$PathToAdd)
    # Check if running as admin (required for system PATH)
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if (-not $isAdmin) {
        Write-Info "System PATH modification requires administrator privileges. Skipping system PATH."
        return $false
    }
    $current = [Environment]::GetEnvironmentVariable("Path", "Machine")
    if ($current -notlike "*$PathToAdd*") {
        try {
            [Environment]::SetEnvironmentVariable("Path", "$current;$PathToAdd", "Machine")
            Refresh-Env
            Write-Success "System PATH updated."
            return $true
        } catch {
            Write-Err "Failed to update system PATH: $_"
        }
    }
    return $false
}

# ------------------------------------------------------------------
# Dependency management
# ------------------------------------------------------------------
function Find-GCC {
    # Common locations for MSYS2 / MinGW
    $candidates = @(
        "C:\msys64\ucrt64\bin",
        "C:\msys64\mingw64\bin",
        "C:\msys64\clang64\bin",
        "C:\Program Files\mingw-w64\*\mingw64\bin"
    )
    foreach ($p in $candidates) {
        if (Test-Path "$p\g++.exe") { return $p }
    }
    # Fallback: search in Program Files
    $found = Get-ChildItem -Path "C:\Program Files" -Filter "g++.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { return $found.DirectoryName }
    return $null
}

function Require-Tool {
    param(
        [string]$Cmd,
        [string]$PackageId,
        [string]$InstallHint = ""  # Optional extra hint
    )

    # Special case for g++ because we need to check both command and existence
    if ($Cmd -eq "g++") {
        $found = (Get-Command "g++" -ErrorAction SilentlyContinue) -ne $null
        if (-not $found) {
            # Try to find it in common paths even if not in PATH
            $gccPath = Find-GCC
            if ($gccPath) {
                Add-To-UserPath -PathToAdd $gccPath
                Refresh-Env
                $found = (Get-Command "g++" -ErrorAction SilentlyContinue) -ne $null
            }
        }
        if ($found) {
            Write-Success "g++ is ready."
            return
        }
    } else {
        $found = (Get-Command $Cmd -ErrorAction SilentlyContinue) -ne $null
        if ($found) {
            Write-Success "$Cmd is ready."
            return
        }
    }

    Write-Info "'$Cmd' not found."
    if ($InstallHint) { Write-Info "Hint: $InstallHint" }

    while ($true) {
        Write-Prompt "Install it now? (y/n) "
        $answer = (Read-Host).ToLower()

        if ($answer -eq "y") {
            Write-Info "Installing $Cmd via winget..."
            try {
                winget install --exact --id $PackageId --accept-source-agreements --accept-package-agreements
                if ($LASTEXITCODE -ne 0) { throw "winget installation failed." }

                # After installation, refresh and verify
                Refresh-Env
                if ($Cmd -eq "g++") {
                    # For MSYS2, we need to find the bin folder and add it to PATH
                    $gccPath = Find-GCC
                    if ($gccPath) {
                        Add-To-UserPath -PathToAdd $gccPath
                        Refresh-Env
                        Write-Success "g++ linked at: $gccPath"
                    } else {
                        Write-Info "Could not locate g++ automatically. Please add the MSYS2 bin directory to your PATH manually."
                        Write-Info "Typically: C:\msys64\ucrt64\bin or C:\msys64\mingw64\bin"
                    }
                }
                # Verify again
                $found = if ($Cmd -eq "g++") { (Get-Command "g++" -ErrorAction SilentlyContinue) -ne $null } else { (Get-Command $Cmd -ErrorAction SilentlyContinue) -ne $null }
                if ($found) {
                    Write-Success "$Cmd installed and available."
                    return
                } else {
                    Write-Err "Installation completed but $Cmd is still not available. Please check your PATH."
                }
            } catch {
                Write-Err "Failed to install $Cmd : $_"
            }
        } elseif ($answer -eq "n") {
            Write-Err "'$Cmd' is required. Aborting."
        }
    }
}

# ------------------------------------------------------------------
# Repository cloning functions
# ------------------------------------------------------------------
function Clone-Zonc-Full {
    param([string]$Url, [string]$Dir)
    if (Test-Path $Dir) {
        Write-Info "Compiler already exists. Updating..."
        Push-Location $Dir
        try {
            git init -q
            git remote add origin $Url 2>/dev/null
            git pull origin main
            if ($LASTEXITCODE -ne 0) { throw "git pull failed." }
        } catch {
            Write-Err "Failed to update compiler: $_"
        } finally { Pop-Location }
        Write-Success "Compiler updated."
        return
    }

    Write-Info "Cloning full compiler from $Url ..."
    try {
        git clone $Url $Dir
        if ($LASTEXITCODE -ne 0) { throw "git clone failed." }
    } catch {
        Write-Err "Failed to clone compiler repository: $_"
    }
    Write-Success "Compiler downloaded."
}

function Clone-Zonvm {
    param([string]$Url, [string]$Dir)
    if (Test-Path $Dir) {
        Write-Info "VM already exists. Updating..."
        Push-Location $Dir
        try {
            git init -q
            git remote add origin $Url 2>/dev/null
            git pull origin main
            if ($LASTEXITCODE -ne 0) { throw "git pull failed." }
        } catch {
            Write-Err "Failed to update VM: $_"
        } finally { Pop-Location }
        Write-Success "VM updated."
        return
    }

    Write-Info "Cloning VM from $Url ..."
    try {
        git clone $Url $Dir
        if ($LASTEXITCODE -ne 0) { throw "git clone failed." }
    } catch {
        Write-Err "Failed to clone VM repository: $_"
    }
    Write-Success "VM downloaded."
}

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
function Main {
    Write-Separator
    Write-Host "${CYAN}Zonetic Installer v2.2 — Windows${RESET}" -ForegroundColor Cyan
    Write-Separator

    # Check if running as admin for system PATH updates
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if (-not $isAdmin) {
        Write-Info "Not running as Administrator. System PATH modifications will be skipped."
        Write-Info "If you want the installer to add to System PATH, run as Administrator."
    }

    Write-Info "Checking dependencies..."
    Require-Tool "git"    "Git.Git"
    Require-Tool "python" "Python.Python.3.12"
    Require-Tool "g++"    "MSYS2.MSYS2" -InstallHint "After installing MSYS2, open MSYS2 and run: pacman -S --needed base-devel mingw-w64-ucrt-x86_64-toolchain"

    $InstallDir = Join-Path $HOME ".zonetic"
    $ZoncDir    = Join-Path $InstallDir ".zonc"
    $ZonvmDir   = Join-Path $InstallDir ".zonvm"

    if (Test-Path $InstallDir) {
        $count = (Get-ChildItem -Path $InstallDir -Force -ErrorAction SilentlyContinue).Count
        if ($count -gt 0) {
            Write-Info "$InstallDir is not empty ($count items)."
            while ($true) {
                Write-Prompt "Overwrite its contents? (y/n) "
                $answer = (Read-Host).ToLower()
                if ($answer -eq "y") {
                    Write-Info "Cleaning directory..."
                    Remove-Item -Recurse -Force $InstallDir -ErrorAction SilentlyContinue | Out-Null
                    break
                } elseif ($answer -eq "n") {
                    Write-Err "Installation cancelled."
                }
            }
        }
    }

    # Create directories
    New-Item -ItemType Directory -Path $ZoncDir  -Force | Out-Null
    New-Item -ItemType Directory -Path $ZonvmDir -Force | Out-Null

    # Clone repositories (full for compiler)
    Clone-Zonc-Full   "https://github.com/alve-dev/zonetic-lang-tree-walker-version.git" $ZoncDir

    Clone-Zonvm "https://github.com/alve-dev/zonetic-vm.git" $ZonvmDir

    # Add scripts folder to user PATH
    $scriptsPath = Join-Path $ZoncDir "scripts"
    Add-To-UserPath -PathToAdd $scriptsPath

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
