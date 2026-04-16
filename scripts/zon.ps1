# [ ⌐■_■] <( Locating Zonetic home... )
$ScriptsDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoDir = (Resolve-Path "$ScriptsDir\..").Path
$MainPy = "$RepoDir\src\zonc\main.py"

# Command: zon update
if ($args[0] -eq "update") {
    Write-Host "[ ⌐■_■] <(`"Checking for updates on GitHub...`")"
    
    if (!(Test-Path "$RepoDir\.git")) {
        Write-Host "[ X_X] <(`"Error: .git directory not found. Cannot update.`")"
        exit 1
    }

    git -C "$RepoDir" fetch origin main -q

    $RemoteMsg = git -C "$RepoDir" log -1 origin/main --pretty=format:%s
    $LocalMsg = git -C "$RepoDir" log -1 --pretty=format:%s

    # 1. Bloqueo de versiones no estables
    if ($RemoteMsg -like "*[NOSTABLE]*") {
        Write-Host "[ X_X] <(`"Error: Remote version is marked as [NOSTABLE].`")"
        Write-Host "[ X_X] <(`"Update aborted to keep your system safe.`")"
        exit 1
    }

    # 2. Verificar si ya está actualizado
    if ($RemoteMsg -eq $LocalMsg) {
        Write-Host "[ ⌐■_■] <(`"You are already up to date!`")"
        Write-Host "[ ⌐■_■] <(`"Current Version: $LocalMsg`")"
        exit 0
    }

    # 3. Realizar el update
    Write-Host "[ ⌐■_■] <(`"New version found: $RemoteMsg`")"
    Write-Host "[ ⌐■_■] <(`"Updating now...`")"
    
    git -C "$RepoDir" reset --hard origin/main -q
    git -C "$RepoDir" clean -fd -q
    
    Write-Host "[ ⌐■_■] <(`"Update complete! You are now on: $RemoteMsg`")"
    exit 0
}

# Run compiler
if (Test-Path $MainPy) {
    # Pasamos todos los argumentos ($args) al script de python
    python "$MainPy" $args
} else {
    Write-Host "[ X_X] <(`"Error: Cannot find main.py at $MainPy`")"
    exit 1
}