# [ ⌐■_■] <( Locating Zonetic home... )
$ScriptsDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RepoDir = Resolve-Path "$ScriptsDir\.."
$MainPy = "$RepoDir\src\zonc\main.py"

# Command: zon update
if ($args[0] -eq "update") {
    Write-Host "[ ⌐■_■] < ( Checking for updates on GitHub... )"
    git -C "$RepoDir" fetch origin main -q

    $RemoteMsg = git -C "$RepoDir" log -1 origin/main --pretty=format:%s
    $LocalMsg = git -C "$RepoDir" log -1 --pretty=format:%s

    if ($RemoteMsg -like "*[NOSTABLE]*") {
        Write-Host "[ ⌐■_■] < ( Error: Remote version is [NOSTABLE]. Aborting... )" -ForegroundColor Red
        exit 1
    }

    if ($RemoteMsg -eq $LocalMsg) {
        Write-Host "[ ⌐■_■] < ( Already up to date: $LocalMsg )"
        exit 0
    }

    Write-Host "[ ⌐■_■] < ( Updating to: $RemoteMsg )"
    git -C "$RepoDir" reset --hard origin/main -q
    git -C "$RepoDir" clean -fd -q
    Write-Host "[ ⌐■_■] < ( Update complete! )" -ForegroundColor Green
    exit 0
}

# Run compiler
if (Test-Path $MainPy) {
    python "$MainPy" $args
} else {
    Write-Host "[ ⌐■_■] < ( Error: main.py not found at $MainPy )" -ForegroundColor Red
    exit 1
}

