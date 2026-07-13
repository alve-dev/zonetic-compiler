# ==============================================================
# Zonetic Installer — Windows Setup (v2.5)
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
# ------------------------------------------------------------------
$FACE_NEUTRAL = "[ o_o]"
$FACE_SUCCESS = "${GREEN}[ ^_^]${RESET}"
$FACE_DONE    = "${CYAN}[ ⌐■_■]b${RESET}"
$FACE_ERROR   = "${RED}[ x_x]${RESET}"
$FACE_PROMPT  = "${YELLOW}[ o_0]${RESET}"

# ------------------------------------------------------------------
# Output helpers (definidos con function estándar)
# ------------------------------------------------------------------
function Write-Info {
    param([string]$Msg)
    Write-Host "$FACE_NEUTRAL $Msg"
}

function Write-Success {
    param([string]$Msg)
    Write-Host "$FACE_SUCCESS $Msg" -ForegroundColor Green
}

function Write-Done {
    param([string]$Msg)
    Write-Host "$FACE_DONE $Msg" -ForegroundColor Cyan
}

function Write-Err {
    param([string]$Msg)
    Write-Host "$FACE_ERROR $Msg" -ForegroundColor Red
    exit 1
}

function Write-Prompt {
    param([string]$Msg)
    Write-Host "$FACE_PROMPT $Msg" -ForegroundColor Yellow -NoNewline
}

function Write-Separator {
    Write-Host ""
    Write-Host "------------------------------------------------"
    Write-Host ""
}

# ------------------------------------------------------------------
# Helper: leer respuesta y/n (válida)
# ------------------------------------------------------------------
function Ask-YN {
    param([string]$Prompt)
    while ($true) {
        Write-Prompt "$Prompt (y/n) "
        $answer = (Read-Host).ToLower()
        if ($answer -eq "y" -or $answer -eq "n") {
            return $answer
        }
        Write-Info "Por favor, responde 'y' o 'n'."
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
        Write-Info "La ruta '$PathToAdd' no existe. Omitiendo."
        return $false
    }
    $current = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($current -notlike "*$PathToAdd*") {
        try {
            [Environment]::SetEnvironmentVariable("Path", "$current;$PathToAdd", "User")
            Refresh-Env
            Write-Success "PATH de usuario actualizado."
            return $true
        } catch {
            Write-Err "Error al actualizar el PATH de usuario: $_"
        }
    } else {
        Write-Info "El PATH ya contiene esta entrada."
        return $false
    }
}

# ------------------------------------------------------------------
# Gestión de dependencias
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
    # Búsqueda en Program Files
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

    # Verificar si el comando ya existe
    $found = (Get-Command $Cmd -ErrorAction SilentlyContinue) -ne $null
    if ($found) {
        Write-Success "$Cmd está listo."
        return
    }

    Write-Info "'$Cmd' no encontrado."
    if ($InstallHint) { Write-Info "Sugerencia: $InstallHint" }

    # Verificar que winget esté disponible
    $winget = (Get-Command "winget" -ErrorAction SilentlyContinue) -ne $null
    if (-not $winget) {
        Write-Info "No se encontró 'winget'. Por favor, instala '$Cmd' manualmente y añádelo al PATH."
        Write-Err "Instalación abortada."
    }

    $answer = Ask-YN "'$Cmd' falta. ¿Instalarlo ahora?"
    if ($answer -eq "y") {
        Write-Info "Instalando $Cmd vía winget..."
        try {
            winget install --exact --id $PackageId --accept-source-agreements --accept-package-agreements
            if ($LASTEXITCODE -ne 0) { throw "La instalación con winget falló." }
            Refresh-Env

            # Caso especial: g++ (MSYS2)
            if ($Cmd -eq "g++") {
                $gccPath = Find-GCC
                if ($gccPath) {
                    Add-To-UserPath -PathToAdd $gccPath
                    Refresh-Env
                    Write-Success "g++ enlazado en: $gccPath"
                } else {
                    Write-Info "No se pudo localizar g++ automáticamente. Añade la carpeta bin de MSYS2 manualmente."
                    Write-Info "Normalmente: C:\msys64\ucrt64\bin o C:\msys64\mingw64\bin"
                    Write-Info "También recuerda instalar el toolchain dentro de MSYS2:"
                    Write-Info "  pacman -S --needed base-devel mingw-w64-ucrt-x86_64-toolchain"
                }
            }

            # Verificar nuevamente
            $found = (Get-Command $Cmd -ErrorAction SilentlyContinue) -ne $null
            if ($found) {
                Write-Success "$Cmd instalado y disponible."
                return
            } else {
                Write-Err "La instalación se completó pero $Cmd aún no está disponible. Revisa tu PATH."
            }
        } catch {
            Write-Err "Error al instalar $Cmd : $_"
        }
    } else {
        Write-Err "'$Cmd' es necesario. Abortando."
    }
}

# ------------------------------------------------------------------
# Manejo del directorio de instalación existente
# ------------------------------------------------------------------
function Check-InstallDir {
    param([string]$Dir)
    if (-not (Test-Path $Dir)) {
        return $true
    }
    $items = Get-ChildItem -Path $Dir -Force -ErrorAction SilentlyContinue
    if ($items.Count -gt 0) {
        Write-Info "$Dir no está vacío ($($items.Count) elementos)."
        $answer = Ask-YN "¿Sobrescribir su contenido?"
        if ($answer -eq "y") {
            Write-Info "Limpiando directorio..."
            Remove-Item -Recurse -Force $Dir -ErrorAction SilentlyContinue
            return $true
        } else {
            Write-Err "Instalación cancelada."
        }
    }
    return $true
}

# ------------------------------------------------------------------
# Clonación de repositorios (sparse y full)
# ------------------------------------------------------------------
function Clone-Or-Update-Sparse {
    param([string]$Url, [string]$Dir, [string]$Name)
    if (Test-Path $Dir) {
        Write-Info "$Name ya existe. Actualizando (sparse checkout)..."
        Push-Location $Dir
        try {
            git config core.sparseCheckout true
            # Asegurar que el directorio .git/info existe
            New-Item -ItemType Directory -Path ".git/info" -Force | Out-Null
            # Definir los patrones de sparse checkout
            @("src/zonc/*", "scripts/*", ".gitignore") | Out-File -FilePath ".git/info/sparse-checkout" -Encoding utf8
            git fetch origin main
            git reset --hard origin/main
            if ($LASTEXITCODE -ne 0) { throw "git reset falló." }
        } catch {
            Write-Err "Error al actualizar $Name : $_"
        } finally { Pop-Location }
        Write-Success "$Name actualizado."
    } else {
        Write-Info "Clonando $Name (sparse checkout) desde $Url ..."
        try {
            git clone --filter=blob:none --no-checkout $Url $Dir
            if ($LASTEXITCODE -ne 0) { throw "git clone falló." }
            Push-Location $Dir
            git config core.sparseCheckout true
            New-Item -ItemType Directory -Path ".git/info" -Force | Out-Null
            @("src/zonc/*", "scripts/*", ".gitignore") | Out-File -FilePath ".git/info/sparse-checkout" -Encoding utf8
            git checkout main 2>$null
            if ($LASTEXITCODE -ne 0) { git pull origin main }
            Pop-Location
        } catch {
            Write-Err "Error al clonar $Name : $_"
        }
        Write-Success "$Name descargado."
    }
}

function Clone-Or-Update-Full {
    param([string]$Url, [string]$Dir, [string]$Name)
    if (Test-Path $Dir) {
        Write-Info "$Name ya existe. Actualizando..."
        Push-Location $Dir
        try {
            git pull origin main
            if ($LASTEXITCODE -ne 0) { throw "git pull falló." }
        } catch {
            Write-Err "Error al actualizar $Name : $_"
        } finally { Pop-Location }
        Write-Success "$Name actualizado."
    } else {
        Write-Info "Clonando $Name desde $Url ..."
        try {
            git clone $Url $Dir
            if ($LASTEXITCODE -ne 0) { throw "git clone falló." }
        } catch {
            Write-Err "Error al clonar $Name : $_"
        }
        Write-Success "$Name descargado."
    }
}

# ------------------------------------------------------------------
# Función principal
# ------------------------------------------------------------------
function Main {
    Write-Separator
    Write-Host "${CYAN}Zonetic Installer v2.5 — Windows${RESET}" -ForegroundColor Cyan
    Write-Separator

    # Comprobar si se ejecuta como admin (no obligatorio, pero se avisa)
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if (-not $isAdmin) {
        Write-Info "No se ejecuta como Administrador. Solo se actualizará el PATH de usuario."
        Write-Info "Si quieres añadir al PATH del sistema, ejecuta como Administrador."
    }

    Write-Info "Verificando dependencias..."
    Require-Tool "git"    "Git.Git"
    Require-Tool "python" "Python.Python.3.12"
    Require-Tool "g++"    "MSYS2.MSYS2" -InstallHint "Después de instalar MSYS2, abre MSYS2 y ejecuta: pacman -S --needed base-devel mingw-w64-ucrt-x86_64-toolchain"

    $InstallDir = Join-Path $HOME ".zonetic"
    $ZoncDir    = Join-Path $InstallDir ".zonc"
    $ZonvmDir   = Join-Path $InstallDir ".zonvm"

    # Verificar y limpiar si es necesario
    Check-InstallDir -Dir $InstallDir

    # Crear directorios
    New-Item -ItemType Directory -Path $ZoncDir  -Force | Out-Null
    New-Item -ItemType Directory -Path $ZonvmDir -Force | Out-Null

    # Clonar repositorios (sparse para compilador, full para VM)
    Clone-Or-Update-Sparse -Url "https://github.com/alve-dev/zonetic-lang-tree-walker-version.git" -Dir $ZoncDir -Name "Compiler"
    Clone-Or-Update-Full  -Url "https://github.com/alve-dev/zonetic-vm.git" -Dir $ZonvmDir -Name "VM"

    # Añadir carpeta scripts al PATH de usuario
    $scriptsPath = Join-Path $ZoncDir "scripts"
    Add-To-UserPath -PathToAdd $scriptsPath

    Write-Separator
    Write-Done "¡Zonetic v2 instalado con éxito!"
    Write-Done "Abre una nueva terminal y ejecuta: zon vw --vers"
    Write-Done "Si no funciona, cierra y vuelve a abrir la terminal para aplicar los cambios de PATH."
    Write-Separator

    Read-Host "Presiona Enter para salir"
}

# ------------------------------------------------------------------
# Punto de entrada
# ------------------------------------------------------------------
if ($PSVersionTable.PSVersion.Major -lt 5) {
    Write-Err "Este script requiere PowerShell 5.0 o superior."
}

Main