#!/usr/bin/env bash

# ------------------------------------------------------------------
# Resolve the real path of this script even through symlinks,
# then derive ZONC_DIR (the compiler root) from it.
# ------------------------------------------------------------------
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"

ZONC_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MAIN_PY="$ZONC_DIR/src/zonc/main.py"
LAUNCHER_FILE="$SOURCE"

# ------------------------------------------------------------------
# VM paths
# ------------------------------------------------------------------
VM_DIR="$HOME/.zonetic/.zonvm"
BINARY_VM="$VM_DIR/zonvm"
INCLUDE_VM_DIR="$VM_DIR/include"
SRC_VM_DIR="$VM_DIR/src"

# ------------------------------------------------------------------
# Build the VM binary if it does not exist yet
# ------------------------------------------------------------------
build_vm_if_needed() {
    if [ ! -f "$BINARY_VM" ]; then
        echo "[ ⌐■_■] <(\"Building the VM engine at $VM_DIR...\")"
        if [ ! -d "$SRC_VM_DIR" ]; then
            echo "[zon error]: VM source not found at $SRC_VM_DIR"
            echo "-- Run 'zon update' to sync the VM repository."
            exit 1
        fi
        g++ -std=c++20 -I"$INCLUDE_VM_DIR" "$SRC_VM_DIR"/*.cpp -o "$BINARY_VM"
        if [ $? -ne 0 ]; then
            echo "[zon error]: Failed to build the VM."
            echo "-- Check that g++ is installed and the source at $SRC_VM_DIR is intact."
            exit 1
        fi
    fi
}

# ------------------------------------------------------------------
# update — sync compiler and VM from GitHub
# ------------------------------------------------------------------
if [ "$1" == "update" ]; then
    echo "[ ⌐■_■] <(\"Checking for updates on GitHub...\")"
    COMPILER_UPDATED=false

    if [ -d "$ZONC_DIR/.git" ]; then
        git -C "$ZONC_DIR" fetch origin main -q
        REMOTE_MSG=$(git -C "$ZONC_DIR" log -1 origin/main --pretty=format:%s)
        LOCAL_MSG=$(git  -C "$ZONC_DIR" log -1 --pretty=format:%s)

        if [[ "$REMOTE_MSG" != *"[NOSTABLE]"* && "$REMOTE_MSG" != "$LOCAL_MSG" ]]; then
            git -C "$ZONC_DIR" reset --hard origin/main -q
            chmod +x "$LAUNCHER_FILE"
            echo "[ ⌐■_■] <(\"Compiler updated: $REMOTE_MSG\")"
            COMPILER_UPDATED=true
        else
            echo "[ ⌐■_■] <(\"Compiler is already up to date.\")"
        fi
    fi

    if [ -d "$VM_DIR/.git" ]; then
        git -C "$VM_DIR" fetch origin main -q
        VM_REMOTE=$(git -C "$VM_DIR" log -1 origin/main --pretty=format:%H)
        VM_LOCAL=$(git  -C "$VM_DIR" log -1 --pretty=format:%H)

        if [[ "$COMPILER_UPDATED" == true || "$VM_REMOTE" != "$VM_LOCAL" ]]; then
            git -C "$VM_DIR" reset --hard origin/main -q
            rm -f "$BINARY_VM"
            echo "[ ⌐■_■] <(\"VM synchronized and marked for rebuild.\")"
        else
            echo "[ ⌐■_■] <(\"VM is already up to date.\")"
        fi
    fi
    exit 0
fi

# ------------------------------------------------------------------
# clr --his — clear the REPL history file
# ------------------------------------------------------------------
if [[ "$1" == "clr" && "$2" == "--his" ]]; then
    HISTORY_FILE="$HOME/.zonhistoryrepl"
    if [ -f "$HISTORY_FILE" ]; then
        : > "$HISTORY_FILE"
        echo "[ ⌐■_■] <(\"History cleared!\")"
    else
        echo "[zon error]: No history file found at $HISTORY_FILE"
    fi
    exit 0
fi

# ------------------------------------------------------------------
# vw --file — print a source or bytecode file to stdout
# ------------------------------------------------------------------
if [[ "$1" == "vw" && "$2" == "--file" ]]; then
    if [ -z "$3" ]; then
        echo "[zon error]: No path provided for 'vw --file'."
        echo "-- Usage: zon vw --file <path>"
        exit 1
    fi
    if [ -f "$3" ]; then
        cat "$3"
        exit 0
    else
        echo "[zon error]: File '$3' not found."
        exit 1
    fi
fi

# ------------------------------------------------------------------
# vw --zonasm — disassemble a .zbc file (compiling first if .zon)
# ------------------------------------------------------------------
if [[ "$1" == "vw" && "$2" == "--zonasm" ]]; then
    if [ -z "$3" ]; then
        echo "[zon error]: No file specified for 'vw --zonasm'."
        echo "-- Usage: zon vw --zonasm <file>.zon|.zbc"
        exit 1
    fi

    FILE="$3"
    if [ ! -f "$FILE" ]; then
        echo "[zon error]: File '$FILE' not found."
        exit 1
    fi

    case "$FILE" in
        *.zbc)
            python3 "$MAIN_PY" vw --zonasm "$FILE"
            ;;
        *.zon)
            python3 "$MAIN_PY" c "$FILE"
            if [ $? -eq 0 ]; then
                BYTECODE="${FILE%.zon}.zbc"
                if [ -f "$BYTECODE" ]; then
                    python3 "$MAIN_PY" vw --zonasm "$BYTECODE"
                else
                    echo "[zon error]: Expected bytecode at '$BYTECODE' but it was not created."
                    exit 1
                fi
            else
                exit 1
            fi
            ;;
        *)
            echo "[zon error]: '$FILE' has an unsupported extension."
            echo "-- Only .zon and .zbc files are accepted."
            exit 1
            ;;
    esac
    exit 0
fi

# ------------------------------------------------------------------
# repl — read code interactively, compile to a temp .zbc, then run
# ------------------------------------------------------------------
if [ "$1" == "repl" ]; then
    build_vm_if_needed
    TEMP_ZBC=$(mktemp --suffix=.zbc)
    trap 'rm -f "$TEMP_ZBC"' EXIT

    END_KEY="${2:-EOF}"
    python3 "$MAIN_PY" repl "$TEMP_ZBC" "$END_KEY"

    if [ $? -ne 0 ]; then
        exit 1
    fi

    VM_EXIT=0
    if [ -s "$TEMP_ZBC" ]; then
        "$BINARY_VM" "$TEMP_ZBC"
        VM_EXIT=$?
    fi
    exit $VM_EXIT
fi

# ------------------------------------------------------------------
# r — run a .zon or .zbc file
# ------------------------------------------------------------------
if [ "$1" == "r" ]; then
    if [ -z "$2" ]; then
        echo "[zon error]: No file specified for 'r'."
        echo "-- Usage: zon r <file>.zon|.zbc"
        exit 1
    fi

    FILE="$2"
    if [ ! -f "$FILE" ]; then
        echo "[zon error]: File '$FILE' not found."
        echo "-- Double-check your spelling and ensure the file exists."
        exit 1
    fi

    build_vm_if_needed

    VM_EXIT=0
    case "$FILE" in
        *.zbc)
            "$BINARY_VM" "$FILE"
            VM_EXIT=$?
            ;;
        *.zon)
            python3 "$MAIN_PY" c "$FILE"
            if [ $? -eq 0 ]; then
                BYTECODE="${FILE%.zon}.zbc"
                if [ -f "$BYTECODE" ]; then
                    "$BINARY_VM" "$BYTECODE"
                    VM_EXIT=$?
                else
                    echo "[zon error]: Expected bytecode at '$BYTECODE' but it was not created."
                    exit 1
                fi
            else
                exit 1
            fi
            ;;
        *)
            echo "[zon error]: '$FILE' has an unsupported extension."
            echo "-- Only .zon and .zbc files are accepted."
            exit 1
            ;;
    esac
    exit $VM_EXIT
fi

# ------------------------------------------------------------------
# st --zbc — read code interactively, compile directly to a .zbc file
# ------------------------------------------------------------------
if [[ "$1" == "st" && "$2" == "--zbc" ]]; then
    if [ -z "$3" ]; then
        echo "[zon error]: No output path specified for 'st --zbc'."
        echo "-- Usage: zon st --zbc <output>.zbc [endkey]"
        exit 1
    fi

    TARGET="$3"
    END_KEY="${4:-EOF}"

    python3 "$MAIN_PY" st --zbc "$TARGET" "$END_KEY"

    if [ -f "$TARGET" ]; then
        read -p "Do you want to run $(basename "$TARGET") now? (y/n): " answer </dev/tty
        answer=$(echo "$answer" | tr '[:upper:]' '[:lower:]')
        if [[ "$answer" == "y" || "$answer" == "yes" ]]; then
            build_vm_if_needed
            "$BINARY_VM" "$TARGET"
        fi
    fi
    exit 0
fi

# ------------------------------------------------------------------
# rebuild — recompile the VM binary
# ------------------------------------------------------------------
if [ "$1" == "rebuild" ]; then
    COMPILE_FLAGS="-O3 -std=c++20"
    MODE_NAME="RELEASE"

    if [ "$2" == "--debug" ]; then
        COMPILE_FLAGS="-g -O0 -std=c++20 -DDEBUG_MODE"
        MODE_NAME="DEBUG"
    fi

    echo "[ ⌐■_■] <(\"Rebuilding VM engine in $MODE_NAME mode...\")"

    if [ -f "$BINARY_VM" ]; then
        rm -f "$BINARY_VM"
        echo "[ ⌐■_■] <(\"Old binary removed.\")"
    fi

    g++ $COMPILE_FLAGS -I"$INCLUDE_VM_DIR" "$SRC_VM_DIR"/*.cpp -o "$BINARY_VM"

    if [ $? -ne 0 ]; then
        echo "[zon error]: Failed to rebuild the VM."
        echo "-- Check that g++ is installed and the source at $SRC_VM_DIR is intact."
        exit 1
    else
        echo "[ ⌐■_■] <(\"VM rebuilt successfully!\")"
        exit 0
    fi
fi

# ------------------------------------------------------------------
# fallback — pass everything else directly to main.py
# ------------------------------------------------------------------
if [ -f "$MAIN_PY" ]; then
    python3 "$MAIN_PY" "$@"
else
    echo "[zon error]: Cannot find main.py at $MAIN_PY"
    echo "-- Try running 'zon update' to restore the compiler files."
    exit 1
fi