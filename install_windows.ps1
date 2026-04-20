Write-Host "[ ⌐■_■] <(`"Starting Zonetic setup for WINDOWS...`")"

function Refresh-Env {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

function Check-And-Install {
    param (
        [string]$CommandName,
        [string]$PackageId
    )

    $versionCheck = $null
    if ($CommandName -eq "g++") {
        $versionCheck = g++ --version 2>$null
    } else {
        $versionCheck = Get-Command $CommandName -ErrorAction SilentlyContinue
    }

    if (!$versionCheck) {
        $input = Read-Host "[ ⌐■_■] <(`"Error: '$CommandName' is missing or broken. Install it now? (y/n)`") "
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
            winget install --exact --id $PackageId --accept-source-agreements --accept-package-agreements
            
            Refresh-Env
            
            if ($CommandName -eq "g++") {
                Write-Host "[ ⌐■_■] <(`"Locating GNU compiler...`")"
                $possiblePaths = @(
                    "C:\msys64\ucrt64\bin",
                    "C:\msys64\mingw64\bin",
                    "C:\Program Files\mingw-w64\*\mingw64\bin"
                )
                
                $mingwPath = $null
                foreach ($p in $possiblePaths) {
                    if (Test-Path "$p\g++.exe") { $mingwPath = $p; break }
                }

                if (!$mingwPath) {
                    $mingwPath = Get-ChildItem -Path "C:\Program Files" -Filter "g++.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty DirectoryName
                }

                if ($mingwPath) {
                    $oldPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
                    if ($oldPath -notlike "*$mingwPath*") {
                        [System.Environment]::SetEnvironmentVariable("Path", "$oldPath;$mingwPath", "User")
                        $env:Path += ";$mingwPath"
                        Write-Host "[ ⌐■_■] <(`"g++ linked successfully: $mingwPath`")"
                    }
                }
            }
        } else {
            Write-Host "[ X_X] <(`"Error: '$CommandName' is required. Aborting setup.`")"
            Pause
            exit 1
        }
    } else {
       Write-Host "[ ✓ ] $CommandName is ready." -ForegroundColor Green
    }
}

Check-And-Install "git" "Git.Git"
Check-And-Install "python" "Python.Python.3.12"
Check-And-Install "g++" "MSYS2.MSYS2"

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
            Remove-Item -Recurse -Force $InstallDir | Out-Null
        } else {
            Write-Host "[ ⌐■_■] <(`"Installation cancelled.`")"
            exit 0
        }
    }
}

New-Item -ItemType Directory -Path $ZoncDir -Force | Out-Null
New-Item -ItemType Directory -Path $ZonvmDir -Force | Out-Null

Write-Host "[ ⌐■_■] <(`"Syncing Compiler (Zonc) with GitHub...`")"
Set-Location $ZoncDir
git init
try { git remote add origin https://github.com/alve-dev/zonetic-lang-tree-walker-version.git 2>$null } catch {}

git config core.sparseCheckout true
if (!(Test-Path ".git/info")) { New-Item -ItemType Directory -Path ".git/info" -Force | Out-Null }
"src/zonc/*" | Out-File -FilePath ".git/info/sparse-checkout" -Encoding utf8
"scripts/*" | Add-Content -Path ".git/info/sparse-checkout"
".gitignore" | Add-Content -Path ".git/info/sparse-checkout"

git pull origin main
git checkout main 2>$null

Write-Host "[ ⌐■_■] <(`"Syncing VM (ZonVM) with GitHub...`")"
Set-Location $ZonvmDir
git init
try { git remote add origin https://github.com/alve-dev/zonetic-vm.git 2>$null } catch {}
git pull origin main

Set-Location $HOME
$LauncherPath = Join-Path $ZoncDir "scripts"
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")

if ($UserPath -notlike "*$LauncherPath*") {
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$LauncherPath", "User")
    Write-Host "[ ⌐■_■] <(`"Path updated successfully!`")"
} else {
    Write-Host "[ ⌐■_■] <(`"Path already exists. No changes needed.`")"
}

Write-Host "`n------------------------------------------------"
Write-Host "[ ⌐■_■] <(`"Zonetic v2.0.0 installed successfully!`")"
Write-Host "[ ⌐■_■] <(`"IMPORTANT: Close and restart PowerShell, then try: zon vers`")"
Pause
