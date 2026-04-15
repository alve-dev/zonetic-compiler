@echo off
setlocal enabledelayedexpansion

echo [ ⌐■_■] ^< ( Starting Zonetic setup for WINDOWS... )

:: 1. Check Dependencies
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ ⌐■_■] ^< ( 'git' is missing. Please install Git for Windows first. )
    exit /b 1
)

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ ⌐■_■] ^< ( 'python' is missing. Please install Python 3 first. )
    exit /b 1
)

:: 2. Setup Directory
set "INSTALL_DIR=%USERPROFILE%\.zonetic"

if exist "%INSTALL_DIR%" (
    echo [ ⌐■_■] ^< ( Warning: %INSTALL_DIR% already exists. )
    set /p choice="[ ⌐■_■] < ( Overwrite? (y/n): "
    if /i "!choice!" neq "y" exit /b 0
    rd /s /q "%INSTALL_DIR%"
)

mkdir "%INSTALL_DIR%"
cd /d "%INSTALL_DIR%"

:: 3. Clone (Normal version with Sparse Checkout)
echo [ ⌐■_■] ^< ( Syncing with GitHub... )
git init -q
git remote add origin https://github.com/alve-dev/zonetic-lang-tree-walker-version.git

git pull origin main --rebase -q

:: 4. Add to PATH (The Magic Part)
echo [ ⌐■_■] ^< ( Configuring 'zon' global command... )
:: We add the 'scripts' folder to the User PATH
setx PATH "%PATH%;%INSTALL_DIR%\scripts" >nul

echo ------------------------------------------------
echo [ ⌐■_■] ^< ( Zonetic installed successfully! )
echo [ ⌐■_■] ^< ( IMPORTANT: Restart your terminal to use 'zon' )

