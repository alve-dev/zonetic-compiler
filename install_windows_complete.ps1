Write-Host "[ ⌐■_■] <(`"Starting FULL Zonetic setup for WINDOWS...`")"

function Refresh-Env {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

function Check-And-Install {
    param (
        [string]$CommandName,
        [string]$PackageId
    )

    if (!(Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        $input = Read-Host "[ ⌐■_■] <(`"Error: '$CommandName' is missing. Install it now? (y/n)`") "
        $answer = $input.ToLower()

        if ($answer -ne "y" -and $answer -ne "n") {
            while ($true) {
                $input = Read-Host "[ o_0] <(`"Are you feeling okay?, I need a (y/n), don't fail me now`") "
                $answer = $input.ToLower()
                if ($answer -eq "y" -or $answer -eq "n") { break }
            }
        }

        if ($answer -eq "y") {
            Write-Host "[ ⌐■_■] <(`"Installing '$CommandName' via winget...`")"
            winget install --exact --id $PackageId --silent --accept-source-agreements --accept-package-agreements | Out-Null
            
            Refresh-Env
            
            if ($CommandName -eq "g++" -and !(Get-Command "g++" -ErrorAction SilentlyContinue)) {
                Write-Host "[ ⌐■_■] <(`"Searching for g++ location...`")"
                $mingwPath = Get-ChildItem -Path "C:\", "C:\Program Files" -Filter "g++.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty DirectoryName
                if ($mingwPath) {
                    $oldPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
                    if ($oldPath -notlike "*$mingwPath*") {
                        [System.Environment]::SetEnvironmentVariable("Path", "$oldPath;$mingwPath", "User")
                        $env:Path += ";$mingwPath"
                        Write-Host "[ ⌐■_■] <(`"g++ found and added to PATH: $mingwPath`")"
                    }
                }
            }
        } else {
            Write-Host "[ X_X] <(`"Error: '$CommandName' is required. Aborting setup.`")" -ForegroundColor Red
            exit 1
        }
    }
}

Check-And-Install "git" "Git.Git"
Check-And-Install "python" "Python.Python.3.12"
Check-And-Install "g++" "GNU.MinGW-w64"

$InstallDir = Join-Path $HOME ".zonetic"
$ZoncDir    = Join-Path $InstallDir ".zonc"
$ZonvmDir   = Join-Path $InstallDir ".zonvm"

if (Test-Path $InstallDir) {
    $FileCount = (Get-ChildItem -Path $InstallDir -Force).Count
    if ($FileCount -gt 0) {
        Write-Host "[ ⌐■_■] <(`"Warning: $InstallDir is not empty ($FileCount files found).`")"
        $choiceIn = Read-Host "[ ⌐■_■] <(`"Do you want to OVERWRITE its contents? (y/n)`")"
        $choice = $choiceIn.ToLower()

        if ($choice -ne "y" -and $choice -ne "n") {
            while ($true) {
                $choiceIn = Read-Host "[ o_0] <(`"Are you feeling okay?, I need a (y/n), don't fail me now`")"
                $choice = $choiceIn.ToLower()
                if ($choice -eq "y" -or $choice -eq "n") { break }
            }
        }

        if ($choice -eq "y") {
            Write-Host "[ ⌐■_■] <(`"Cleaning directory...`")"
            Get-ChildItem -Path $InstallDir -Force | Remove-Item -Recurse -Force | Out-Null
        } else {
            Write-Host "[ ⌐■_■] <(`"Installation cancelled by user.`")"
            exit 0
        }
    }
}

New-Item -ItemType Directory -Path $ZoncDir -Force | Out-Null
New-Item -ItemType Directory -Path $ZonvmDir -Force | Out-Null

Write-Host "[ ⌐■_■] <(`"Downloading Zonetic Compiler (Full)...`")"
Set-Location $ZoncDir
git init -q
try { git remote add origin https://github.com/alve-dev/zonetic-lang-tree-walker-version.git 2>$null } catch {}
git pull origin main -q
git checkout main -f -q 2>$null

Write-Host "[ ⌐■_■] <(`"Downloading Zonetic VM (Full)...`")"
Set-Location $ZonvmDir
git init -q
try { git remote add origin https://github.com/alve-dev/zonetic-vm.git 2>$null } catch {}
git pull origin main -q
git checkout main -f -q 2>$null

Set-Location $HOME

Write-Host "[ ⌐■_■] <(`"Configuring 'zon' global command...`")"
$LauncherPath = Join-Path $ZoncDir "scripts"
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")

if ($UserPath -notlike "*$LauncherPath*") {
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$LauncherPath", "User")
    Write-Host "[ ⌐■_■] <(`"Path updated successfully!`")"
} else {
    Write-Host "[ ⌐■_■] <(`"Path already exists. No changes needed.`")"
}

Write-Host "------------------------------------------------"
Write-Host "[ ⌐■_■] <(`"Zonetic v2.0.0 COMPLETE installed successfully!`")"
Write-Host "[ ⌐■_■] <(`"IMPORTANT: Close and restart PowerShell, then try: zon vw --vers`")"