# ==============================================================
# Zonetic Installer — Windows Setup (v2.4)
#
# Default: sparse checkout — downloads only src/zonc/*, scripts/*
#
# Usage:
#   .\install_windows.ps1
#   irm https://raw.githubusercontent.com/alve-dev/zonetic-compiler/refs/heads/main/install_scripts/install_windows.ps1 | iex
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
# Helper: read a y/n answer, retrying until valid input is given
# ------------------------------------------------------------------
function Ask-YN {
    param([string]$Prompt)
    while ($true) {
        Write-Prompt "$Prompt (y/n) "
        $answer = (Read-Host).ToLower()
        if ($answer -eq "y" -or $answer -eq "n") {
            return $answer
        }
        Write-Info "Please answer 'y' or 'n'."
    }
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

function Add-To-UserPath {
    param([string]$PathToAdd)
    if (-not (Test-Path $PathToAdd)) {
        Write-Info "Path '$PathToAdd' does not exist. Skipping."
        return $false
    }
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

# ------------------------------------------------------------------
# Dependency management
# ------------------------------------------------------------------
function Find-GCC {
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
        [string]$InstallHint = ""
    )

    # Check if command exists
    $found = (Get-Command $Cmd -ErrorAction SilentlyContinue) -ne $null
    if ($found) {
        Write-Success "$Cmd is ready."
        return
    }

    Write-Info "'$Cmd' not found."
    if ($InstallHint) { Write-Info "Hint: $InstallHint" }

    # Check if winget is available
    $winget = (Get-Command "winget" -ErrorAction SilentlyContinue) -ne $null
    if (-not $winget) {
        Write-Info "Winget is not available. Please install '$Cmd' manually and add it to your PATH."
        Write-Err "Aborting installation."
    }

    $answer = Ask-YN "'$Cmd' is missing. Install it now?"
    if ($answer -eq "y") {
        Write-Info "Installing $Cmd via winget..."
        try {
            winget install --exact --id $PackageId --accept-source-agreements --accept-package-agreements
            if ($LASTEXITCODE -ne 0) { throw "winget installation failed." }
            Refresh-Env

            # Special handling for g++ (MSYS2)
            if ($Cmd -eq "g++") {
                $gccPath = Find-GCC
                if ($gccPath) {
                    Add-To-UserPath -PathToAdd $gccPath
                    Refresh-Env
                    Write-Success "g++ linked at: $gccPath"
                } else {
                    Write-Info "Could not locate g++ automatically. Please add the MSYS2 bin directory to your PATH manually."
                    Write-Info "Typically: C:\msys64\ucrt64\bin or C:\msys64\mingw64\bin"
                    Write-Info "Also, don't forget to install the toolchain inside MSYS2:"
                    Write-Info "  pacman -S --needed base-devel mingw-w64-ucrt-x86_64-toolchain"
                }
            }

            # Verify again
            $found = (Get-Command $Cmd -ErrorAction SilentlyContinue) -ne $null
            if ($found) {
                Write-Success "$Cmd installed and available."
                return
            } else {
                Write-Err "Installation completed but $Cmd is still not available. Please check your PATH."
            }
        } catch {
            Write-Err "Failed to install $Cmd : $_"
        }
    } else {
        Write-Err "'$Cmd' is required. Aborting."
    }
}

# ------------------------------------------------------------------
# Handle existing installation directory
# ------------------------------------------------------------------
function Check-InstallDir {
    param([string]$Dir)
    if (-not (Test-Path $Dir)) {
        return $true
    }
    $items = Get-ChildItem -Path $Dir -Force -ErrorAction SilentlyContinue
    if ($items.Count -gt 0) {
        Write-Info "$Dir is not empty ($($items.Count) items)."
        $answer = Ask-YN "Overwrite its contents?"
        if ($answer -eq "y") {
            Write-Info "Cleaning directory..."
            Remove-Item -Recurse -Force $Dir -ErrorAction SilentlyContinue
            return $true
        } else {
            Write-Err "Installation cancelled."
        }
    }
    return $true
}

# ------------------------------------------------------------------
# Repository cloning functions
# ------------------------------------------------------------------
function Clone-Or-Update-Sparse {
    param([string]$Url, [string]$Dir, [string]$Name)
    if (Test-Path $Dir) {
        Write-Info "$Name already exists. Updating via sparse checkout..."
        Push-Location $Dir
        try {
            # Ensure sparse checkout is configured
            git config core.sparseCheckout true
            # Update the sparse-checkout patterns
            New-Item -ItemType Directory -Path ".git/info" -Force | Out-Null
            @("src/zonc/*", "scripts/*", ".gitignore") |
                Out-File -FilePath ".git/info/sparse-checkout" -Encoding utf8
            git fetch origin main
            git reset --hard origin/main
            if ($LASTEXITCODE -ne 0) { throw "git reset failed." }
        } catch {
            Write-Err "Failed to update $Name : $_"
        } finally { Pop-Location }
        Write-Success "$Name updated."
    } else {
        Write-Info "Cloning $Name (sparse checkout) from $Url ..."
        try {
            git clone --filter=blob:none --no-checkout $Url $Dir
            if ($LASTEXITCODE -ne 0) { throw "git clone failed." }
            Push-Location $Dir
            git config core.sparseCheckout true
            New-Item -ItemType Directory -Path ".git/info" -Force | Out-Null
            @("src/zonc/*", "scripts/*", ".gitignore") |
                Out-File -FilePath ".git/info/sparse-checkout" -Encoding utf8
            git checkout main 2>$null
            if ($LASTEXITCODE -ne 0) { git pull origin main }
            Pop-Location
        } catch {
            Write-Err "Failed to clone $Name : $_"
        }
        Write-Success "$Name downloaded."
    }
}

function Clone-Or-Update-Full {
    param([string]$Url, [string]$Dir, [string]$Name)
    if (Test-Path $Dir) {
        Write-Info "$Name already exists. Updating..."
        Push-Location $Dir
        try {
            git pull origin main
            if ($LASTEXITCODE -ne 0) { throw "git pull failed." }
        } catch {
            Write-Err "Failed to update $Name : $_"
        } finally { Pop-Location }
        Write-Success "$Name updated."
    } else {
        Write-Info "Cloning $Name from $Url ..."
        try {
            git clone $Url $Dir
            if ($LASTEXITCODE -ne 0) { throw "git clone failed." }
        } catch {
            Write-Err "Failed to clone $Name : $_"
        }
        Write-Success "$Name downloaded."
    }
}

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
function Main {
    Write-Separator
    Write-Host "${CYAN}Zonetic Installer v2.4 — Windows${RESET}" -ForegroundColor Cyan
    Write-Separator

    # Check if running as admin for system PATH updates (not required)
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if (-not $isAdmin) {
        Write-Info "Not running as Administrator. We will update only the User PATH."
        Write-Info "If you want to add to System PATH, run as Administrator."
    }

    Write-Info "Checking dependencies..."
    Require-Tool "git"    "Git.Git"
    Require-Tool "python" "Python.Python.3.12"
    Require-Tool "g++"    "MSYS2.MSYS2" -InstallHint "After installing MSYS2, open MSYS2 and run: pacman -S --needed base-devel mingw-w64-ucrt-x86_64-toolchain"

    $InstallDir = Join-Path $HOME ".zonetic"
    $ZoncDir    = Join-Path $InstallDir ".zonc"
    $ZonvmDir   = Join-Path $InstallDir ".zonvm"

    # Check and clean if needed
    Check-InstallDir -Dir $InstallDir

    # Create directories
    New-Item -ItemType Directory -Path $ZoncDir  -Force | Out-Null
    New-Item -ItemType Directory -Path $ZonvmDir -Force | Out-Null

    # Clone repositories (sparse for compiler, full for VM)
    Clone-Or-Update-Sparse -Url "https://github.com/alve-dev/zonetic-lang-tree-walker-version.git" -Dir $ZoncDir -Name "Compiler"
    Clone-Or-Update-Full  -Url "https://github.com/alve-dev/zonetic-vm.git" -Dir $ZonvmDir -Name "VM"

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