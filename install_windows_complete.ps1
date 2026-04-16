Write-Host '[ ⌐■_■] <("Starting FULL Zonetic setup for WINDOWS... ")'

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
            Write-Host "[ ⌐■_■] <(`"Installing '$CommandName'...`")"
            winget install --exact --id $PackageId --silent --accept-source-agreements --accept-package-agreements | Out-Null
        } else {
            Write-Host "[ X_X] <(`"Error: '$CommandName' is required. Aborting setup.`")" -ForegroundColor Red
            exit 1
        }
    }
}

Check-And-Install "git" "Git.Git"
Check-And-Install "python" "Python.Python.3.12"

$InstallDir = "$HOME\.zonetic"

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
} else {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

Set-Location $InstallDir

if (!(Test-Path ".git")) {
    Write-Host "[ ⌐■_■] <(`"Cloning full repository...`")"
    git clone -q https://github.com/alve-dev/zonetic-lang-tree-walker-version.git . 2>$null
} else {
    Write-Host "[ ⌐■_■] <(`"Updating existing repository...`")"
    git pull origin main -q 2>$null
}

Write-Host "[ ⌐■_■] <(`"Configuring 'zon' global command...`")"
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$NewPath = "$InstallDir\scripts"

if ($UserPath -notlike "*$NewPath*") {
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$NewPath", "User")
    Write-Host "[ ⌐■_■] <(`"Path updated successfully!`")"
} else {
    Write-Host "[ ⌐■_■] <(`"Path already exists. No changes needed.`")"
}

Write-Host "------------------------------------------------"
Write-Host "[ ⌐■_■] <(`"Zonetic installed successfully!`")"
Write-Host "[ ⌐■_■] <(`"IMPORTANT: exit command and run powershell, after try running: zon vers`")"