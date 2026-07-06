# ------------------------------------------------------------------
# Resolve script location and derive ZONC_DIR (the compiler root)
# ------------------------------------------------------------------
$ScriptsDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ZoncDir    = (Resolve-Path "$ScriptsDir\..").Path
$MainPy     = "$ZoncDir\src\zonc\main.py"

# ------------------------------------------------------------------
# VM paths
# ------------------------------------------------------------------
$VmDir        = "$HOME\.zonetic\.zonvm"
$BinaryVm     = "$VmDir\zonvm.exe"
$IncludeVmDir = "$VmDir\include"
$SrcVmDir     = "$VmDir\src"

# ------------------------------------------------------------------
# Build the VM binary if it does not exist yet
# ------------------------------------------------------------------
function Build-VmIfNeeded {
    if (!(Test-Path $BinaryVm)) {
        Write-Host "[ ⌐■_■] <(`"Building the VM engine at $VmDir...`")"
        if (!(Test-Path $SrcVmDir)) {
            Write-Host "[zon error]: VM source not found at $SrcVmDir"
            Write-Host "-- Run 'zon update' to sync the VM repository."
            exit 1
        }
        g++ -g -std=c++20 -I"$IncludeVmDir" "$SrcVmDir\*.cpp" -o "$BinaryVm"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[zon error]: Failed to build the VM."
            Write-Host "-- Check that g++ is installed and the source at $SrcVmDir is intact."
            exit 1
        }
    }
}

# ------------------------------------------------------------------
# update — sync compiler and VM from GitHub
# ------------------------------------------------------------------
if ($args[0] -eq "update") {
    Write-Host "[ ⌐■_■] <(`"Checking for updates on GitHub...`")"
    $CompilerUpdated = $false

    if (Test-Path "$ZoncDir\.git") {
        git -C "$ZoncDir" fetch origin main -q
        $RemoteMsg = ([string](git -C "$ZoncDir" log -1 origin/main --pretty=format:%s)).Trim()
        $LocalMsg  = ([string](git -C "$ZoncDir" log -1 --pretty=format:%s)).Trim()

        if ($RemoteMsg -notmatch "\[NOSTABLE\]" -and $RemoteMsg -ne $LocalMsg) {
            git -C "$ZoncDir" reset --hard origin/main -q
            Write-Host "[ ⌐■_■] <(`"Compiler updated: $RemoteMsg`")"
            $CompilerUpdated = $true
        } else {
            Write-Host "[ ⌐■_■] <(`"Compiler is already up to date.`")"
        }
    }

    if (Test-Path "$VmDir\.git") {
        git -C "$VmDir" fetch origin main -q
        $VmRemote = ([string](git -C "$VmDir" log -1 origin/main --pretty=format:%H)).Trim()
        $VmLocal  = ([string](git -C "$VmDir" log -1 --pretty=format:%H)).Trim()

        if ($CompilerUpdated -eq $true -or $VmRemote -ne $VmLocal) {
            git -C "$VmDir" reset --hard origin/main -q
            if (Test-Path $BinaryVm) {
                Remove-Item $BinaryVm -Force
                Write-Host "[ ⌐■_■] <(`"Old binary removed.`")"
            }
            Write-Host "[ ⌐■_■] <(`"VM synchronized and marked for rebuild.`")"
        } else {
            Write-Host "[ ⌐■_■] <(`"VM is already up to date.`")"
        }
    }
    exit 0
}

# ------------------------------------------------------------------
# clr --his — clear the REPL history file
# ------------------------------------------------------------------
if ($args[0] -eq "clr" -and $args[1] -eq "--his") {
    $HistoryFile = "$HOME\.zonhistoryrepl"
    if (Test-Path $HistoryFile) {
        Clear-Content $HistoryFile
        Write-Host "[ ⌐■_■] <(`"History cleared!`")"
    } else {
        Write-Host "[zon error]: No history file found at $HistoryFile"
    }
    exit 0
}

# ------------------------------------------------------------------
# vw --file — print a source or bytecode file to stdout
# ------------------------------------------------------------------
if ($args[0] -eq "vw" -and $args[1] -eq "--file") {
    $Target = $args[2]
    if (!$Target) {
        Write-Host "[zon error]: No path provided for 'vw --file'."
        Write-Host "-- Usage: zon vw --file <path>"
        exit 1
    }
    if (Test-Path $Target) { Get-Content $Target ; exit 0 }
    else { Write-Host "[zon error]: File '$Target' not found." ; exit 1 }
}

# ------------------------------------------------------------------
# vw --zonasm — disassemble a .zbc file (compiling first if .zon)
# ------------------------------------------------------------------
if ($args[0] -eq "vw" -and $args[1] -eq "--zonasm") {
    $File = $args[2]
    if (!$File) {
        Write-Host "[zon error]: No file specified for 'vw --zonasm'."
        Write-Host "-- Usage: zon vw --zonasm <file>.zon|.zbc"
        exit 1
    }
    if (!(Test-Path $File)) {
        Write-Host "[zon error]: File '$File' not found."
        exit 1
    }

    Build-VmIfNeeded
    $Extension = [System.IO.Path]::GetExtension($File)

    switch ($Extension) {
        ".zbc" {
            python "$MainPy" vw --zonasm "$File"
        }
        ".zon" {
            python "$MainPy" c "$File"
            if ($LASTEXITCODE -eq 0) {
                $Bytecode = $File -replace '\.zon$', '.zbc'
                if (Test-Path $Bytecode) {
                    python "$MainPy" vw --zonasm "$Bytecode"
                } else {
                    Write-Host "[zon error]: Expected bytecode at '$Bytecode' but it was not created."
                    exit 1
                }
            } else { exit 1 }
        }
        Default {
            Write-Host "[zon error]: '$File' has an unsupported extension."
            Write-Host "-- Only .zon and .zbc files are accepted."
            exit 1
        }
    }
    exit 0
}

# ------------------------------------------------------------------
# repl — read code interactively, compile to a temp .zbc, then run
# ------------------------------------------------------------------
if ($args[0] -eq "repl") {
    Build-VmIfNeeded
    $TempZbc = (New-TemporaryFile).FullName + ".zbc"

    $EndKey = if ($args[1]) { $args[1] } else { "EOF" }
    python "$MainPy" repl "$TempZbc" $EndKey

    $VmExit = 0
    if ($LASTEXITCODE -eq 0 -and (Test-Path $TempZbc)) {
        & "$BinaryVm" "$TempZbc"
        $VmExit = $LASTEXITCODE
        Remove-Item $TempZbc -ErrorAction SilentlyContinue
    }
    exit $VmExit
}

# ------------------------------------------------------------------
# r — run a .zon or .zbc file
# ------------------------------------------------------------------
if ($args[0] -eq "r") {
    $File = $args[1]
    if (!$File) {
        Write-Host "[zon error]: No file specified for 'r'."
        Write-Host "-- Usage: zon r <file>.zon|.zbc"
        exit 1
    }
    if (!(Test-Path $File)) {
        Write-Host "[zon error]: File '$File' not found."
        Write-Host "-- Double-check your spelling and ensure the file exists."
        exit 1
    }

    Build-VmIfNeeded
    $Extension = [System.IO.Path]::GetExtension($File)
    $VmExit = 0

    switch ($Extension) {
        ".zbc" {
            & "$BinaryVm" "$File"
            $VmExit = $LASTEXITCODE
        }
        ".zon" {
            python "$MainPy" c "$File"
            if ($LASTEXITCODE -eq 0) {
                $Bytecode = $File -replace '\.zon$', '.zbc'
                if (Test-Path $Bytecode) {
                    & "$BinaryVm" "$Bytecode"
                    $VmExit = $LASTEXITCODE
                } else {
                    Write-Host "[zon error]: Expected bytecode at '$Bytecode' but it was not created."
                    exit 1
                }
            } else { exit 1 }
        }
        Default {
            Write-Host "[zon error]: '$File' has an unsupported extension."
            Write-Host "-- Only .zon and .zbc files are accepted."
            exit 1
        }
    }
    exit $VmExit
}

# ------------------------------------------------------------------
# st --zbc — read code interactively, compile directly to a .zbc file
# ------------------------------------------------------------------
if ($args[0] -eq "st" -and $args[1] -eq "--zbc") {
    $Target = $args[2]
    if (!$Target) {
        Write-Host "[zon error]: No output path specified for 'st --zbc'."
        Write-Host "-- Usage: zon st --zbc <output>.zbc [endkey]"
        exit 1
    }

    $EndKey = if ($args[3]) { $args[3] } else { "EOF" }
    python "$MainPy" st --zbc "$Target" $EndKey

    if (Test-Path -Path "$Target" -PathType Leaf) {
        $Answer = Read-Host "Do you want to run $(Split-Path $Target -Leaf) now? (y/n)"
        if ($Answer.ToLower() -eq "y" -or $Answer.ToLower() -eq "yes") {
            Build-VmIfNeeded
            & "$BinaryVm" "$Target"
        }
    }
    exit 0
}

# ------------------------------------------------------------------
# rebuild — recompile the VM binary
# ------------------------------------------------------------------
if ($args[0] -eq "rebuild") {
    $CompileFlags = "-O3 -std=c++20"
    $ModeName     = "RELEASE"

    if ($args[1] -eq "--debug") {
        $CompileFlags = "-g -O0 -std=c++20 -DDEBUG_MODE"
        $ModeName     = "DEBUG"
    }

    Write-Host "[ ⌐■_■] <(`"Rebuilding VM engine in $ModeName mode...`")"

    if (Test-Path $BinaryVm) {
        Remove-Item $BinaryVm -Force
        Write-Host "[ ⌐■_■] <(`"Old binary removed.`")"
    }

    g++ $CompileFlags.Split(" ") -I"$IncludeVmDir" "$SrcVmDir\*.cpp" -o "$BinaryVm"

    if ($LASTEXITCODE -ne 0) {
        Write-Host "[zon error]: Failed to rebuild the VM."
        Write-Host "-- Check that g++ is installed and the source at $SrcVmDir is intact."
        exit 1
    } else {
        Write-Host "[ ⌐■_■] <(`"VM rebuilt successfully!`")"
        exit 0
    }
}

# ------------------------------------------------------------------
# fallback — pass everything else directly to main.py
# ------------------------------------------------------------------
if (Test-Path $MainPy) {
    python "$MainPy" $args
} else {
    Write-Host "[zon error]: Cannot find main.py at $MainPy"
    Write-Host "-- Try running 'zon update' to restore the compiler files."
    exit 1
}