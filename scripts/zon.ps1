$ScriptsDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ZoncDir = (Resolve-Path "$ScriptsDir\..").Path
$MainPy = "$ZoncDir\src\zonc\main.py"

$VmDir = "$HOME\.zonetic\.zonvm"
$BinaryVm = "$VmDir\zonvm.exe"
$IncludeVmDir = "$VmDir\include"
$SrcVmDir = "$VmDir\src"

function Build-VmIfNeeded {
    if (!(Test-Path $BinaryVm)) {
        Write-Host "[ ⌐■_■] <(`"Building the VM engine at $VmDir...`")"
        if (!(Test-Path $SrcVmDir)) {
            Write-Host "[ X_X] <(`"Error: VM source not found at $SrcVmDir`")" -ForegroundColor Red
            exit 1
        }
        
        g++ -g -std=c++20 -I"$IncludeVmDir" "$SrcVmDir\*.cpp" -o "$BinaryVm"
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ X_X] <(`"Error: Failed to build VM.`")" -ForegroundColor Red
            exit 1
        }
    }
}

if ($args[0] -eq "update") {
    Write-Host "[ ⌐■_■] <(`"Checking for updates on GitHub...`")"
    $Updated = $false
    
    if (Test-Path "$ZoncDir\.git") {
        git -C "$ZoncDir" fetch origin main -q
        $RemoteMsg = git -C "$ZoncDir" log -1 origin/main --pretty=format:%s
        $LocalMsg = git -C "$ZoncDir" log -1 --pretty=format:%s

        if ($RemoteMsg -notlike "*[NOSTABLE]*" -and $RemoteMsg -ne $LocalMsg) {
            git -C "$ZoncDir" reset --hard origin/main -q
            Write-Host "[ ⌐■_■] <(`"Compiler updated: $RemoteMsg`")"
            $Updated = $true
        } else {
            Write-Host "[ ⌐■_■] <(`"Compiler is already up to date.`")"
        }
    }

    if (Test-Path "$VmDir\.git") {
        git -C "$VmDir" fetch origin main -q
        $VmRemote = git -C "$VmDir" log -1 origin/main --pretty=format:%H
        $VmLocal = git -C "$VmDir" log -1 --pretty=format:%H

        if ($Updated -eq $true -or $VmRemote -ne $VmLocal) {
            git -C "$VmDir" reset --hard origin/main -q
            if (Test-Path $BinaryVm) { Remove-Item $BinaryVm -Force }
            Write-Host "[ ⌐■_■] <(`"VM synchronized and marked for rebuild.`")"
        } else {
            Write-Host "[ ⌐■_■] <(`"VM is already up to date.`")"
        }
    }
    exit 0
}

if ($args[0] -eq "clr" -and $args[1] -eq "--his") {
    $HistoryFile = "$HOME\.zonhistoryrepl"
    if (Test-Path $HistoryFile) {
        Clear-Content $HistoryFile
        Write-Host "[ ⌐■_■] <(`"History cleared!`")"
    } else {
        Write-Host "[ X_X] <(`"No history found.`")"
    }
    exit 0
}

if ($args[0] -eq "vw" -and $args[1] -eq "--file") {
    $Target = $args[2]
    if (!$Target) { Write-Host "[zon error]: Missing path." ; exit 1 }
    if (Test-Path $Target) { Get-Content $Target ; exit 0 }
    else { Write-Host "[zon error]: File not found." ; exit 1 }
}

if ($args[0] -eq "repl" -and $args[1] -ne "--in") {
    Build-VmIfNeeded
    $TempZbc = New-TemporaryFile
    $TempZbcPath = $TempZbc.FullName + ".zbc"
    
    if (!$args[1]) {
        python "$MainPy" repl "$TempZbcPath"
    } else {
        python "$MainPy" repl "$TempZbcPath" $args[1]
    }

    if ($LASTEXITCODE -eq 0 -and (Test-Path $TempZbcPath)) {
        & "$BinaryVm" "$TempZbcPath"
        Remove-Item $TempZbcPath -ErrorAction SilentlyContinue
    }
    exit 0
}

if ($args[0] -eq "r") {
    $File = $args[1]
    $ConfigFile = "$HOME\.zonetic_config"
    $TargetPath = ""

    if (Test-Path $File) {
        $TargetPath = (Resolve-Path $File).Path
    } elseif (Test-Path $ConfigFile) {
        $GlobalDir = Get-Content $ConfigFile
        if (Test-Path "$GlobalDir\$File") {
            $TargetPath = "$GlobalDir\$File"
        }
    }

    if (!$TargetPath) {
        Write-Host "[ X_X] <(`"Error: File '$File' not found locally or in PATH.`")"
        exit 1
    }

    Build-VmIfNeeded
    $Extension = [System.IO.Path]::GetExtension($TargetPath)

    switch ($Extension) {
        ".zbc" { & "$BinaryVm" "$TargetPath" }
        ".zon" {
            python "$MainPy" c "$TargetPath"
            if ($LASTEXITCODE -eq 0) {
                $Bytecode = $TargetPath -replace '\.zon$', '.zbc'
                if (Test-Path $Bytecode) { & "$BinaryVm" "$Bytecode" }
            }
        }
        Default { Write-Host "[ X_X] <(`"Invalid extension.`")" ; exit 1 }
    }
    exit 0
}

if ($args[0] -eq "st" -and $args[1] -eq "--zbc") {
    $TargetPath = $args[2]
    if (!$TargetPath) {
        python "$MainPy" st --zbc
        exit 1
    }

    python "$MainPy" st --zbc $args[2..$args.Count]
    
    if ($LASTEXITCODE -eq 0) {
        $Ans = Read-Host "Do you want to run $(Split-Path $TargetPath -Leaf) now? (y/n)"
        if ($Ans.ToLower() -eq "y" -or $Ans.ToLower() -eq "yes") {
            Build-VmIfNeeded
            & "$BinaryVm" "$TargetPath"
        }
    }
    exit 0
}

if ($args[0] -eq "rebuild") {
    Write-Host "[ ⌐■_■] <(`"Forcing VM rebuild...`")"
    if (Test-Path $BinaryVm) { 
        Remove-Item $BinaryVm -Force 
        Write-Host "[ ⌐■_■] <(`"Old binary removed.`")"
    }
    Build-VmIfNeeded
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[ ⌐■_■] <(`"VM rebuilt successfully!`")"
    }
    exit 0
}

if (Test-Path $MainPy) {
    python "$MainPy" $args
} else {
    Write-Host "[ X_X] <(`"Error: Cannot find main.py at $MainPy`")"
    exit 1
}