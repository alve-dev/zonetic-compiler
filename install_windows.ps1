Write-Host "[ ⌐■_■] < ( Starting Zonetic setup for WINDOWS... )"

# 1. Check Dependencies
if (!(Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "[ ⌐■_■] < ( Error: 'git' is missing. Please install Git. )" -ForegroundColor Red
    exit 1
}
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ ⌐■_■] < ( Error: 'python' is missing. Please install Python. )" -ForegroundColor Red
    exit 1
}

# 2. Setup Directory
$InstallDir = "$HOME\.zonetic"

if (Test-Path $InstallDir) {
    Write-Host "[ ⌐■_■] < ( Warning: $InstallDir already exists. )"
    $Choice = Read-Host "[ ⌐■_■] < ( Overwrite its contents? (y/n)"
    if ($Choice -ne "y") { Write-Host "Aborted."; exit 0 }
    Remove-Item -Recurse -Force $InstallDir
}

New-Item -ItemType Directory -Path $InstallDir | Out-Null
Set-Location $InstallDir

# 3. Clone (Sparse Checkout)
Write-Host "[ ⌐■_■] < ( Syncing with GitHub... )"
git init -q
git remote add origin https://github.com/alve-dev/zonetic-lang-tree-walker-version.git
git config core.sparseCheckout true
@("src/zonc/*", "scripts/*", ".gitignore") | Out-File -FilePath .git/info/sparse-checkout -Encoding utf8

git pull origin main --rebase -q

# 4. PATH Configuration
Write-Host "[ ⌐■_■] < ( Configuring 'zon' global command... )"
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$NewPath = "$InstallDir\scripts"

if ($UserPath -notlike "*$NewPath*") {
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$NewPath", "User")
    Write-Host "[ ⌐■_■] < ( Path updated successfully! )"
}

Write-Host "------------------------------------------------"
Write-Host "[ ⌐■_■] < ( Zonetic installed successfully! )"
Write-Host "[ ⌐■_■] < ( IMPORTANT: Restart your terminal to use 'zon' )"

