#!/usr/bin/env bash 

SOURCE="${BASH_SOURCE[0]}" 
while [ -L "$SOURCE" ]; do 
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )" 
  SOURCE="$(readlink "$SOURCE")" 
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" 
done 
DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )" 

ZONC_DIR="$(cd "$DIR/.." && pwd)" 
MAIN_PY="$ZONC_DIR/src/zonc/main.py"
LAUNCHER_FILE="$SOURCE"

VM_DIR="$HOME/.zonetic/.zonvm"
BINARY_VM="$VM_DIR/zonvm"
INCLUDE_VM_DIR="$VM_DIR/include"
SRC_VM_DIR="$VM_DIR/src"

build_vm_if_needed() {
    if [ ! -f "$BINARY_VM" ]; then
        echo "[ ⌐■_■] <(\"Building the VM engine at $VM_DIR...\")"
        if [ ! -d "$SRC_VM_DIR" ]; then
            echo "[ X_X] <(\"Error: VM source not found at $SRC_VM_DIR\")"
            exit 1
        fi
        g++ -std=c++20 -I"$INCLUDE_VM_DIR" "$SRC_VM_DIR"/*.cpp -o "$BINARY_VM"
        if [ $? -ne 0 ]; then
            echo "[ X_X] <(\"Error: Failed to build VM.\")"
            exit 1
        fi
    fi
}

if [ "$1" == "update" ]; then 
    echo "[ ⌐■_■] <(\"Checking for updates on GitHub...\")" 
    
    UPDATED=false

    if [ -d "$ZONC_DIR/.git" ]; then 
        git -C "$ZONC_DIR" fetch origin main -q 
        REMOTE_MSG=$(git -C "$ZONC_DIR" log -1 origin/main --pretty=format:%s) 
        LOCAL_MSG=$(git -C "$ZONC_DIR" log -1 --pretty=format:%s) 

        if [[ "$REMOTE_MSG" != *"[NOSTABLE]"* && "$REMOTE_MSG" != "$LOCAL_MSG" ]]; then 
            git -C "$ZONC_DIR" reset --hard origin/main -q 
            chmod +x "$LAUNCHER_FILE"
            echo "[ ⌐■_■] <(\"Compiler updated: $REMOTE_MSG\")" 
            UPDATED=true
        else
            echo "[ ⌐■_■] <(\"Compiler is already up to date.\")"
        fi
    fi

    if [ -d "$VM_DIR/.git" ]; then
        git -C "$VM_DIR" fetch origin main -q
        VM_REMOTE=$(git -C "$VM_DIR" log -1 origin/main --pretty=format:%H)
        VM_LOCAL=$(git -C "$VM_DIR" log -1 --pretty=format:%H)

        if [[ "$UPDATED" == true || "$VM_REMOTE" != "$VM_LOCAL" ]]; then
            git -C "$VM_DIR" reset --hard origin/main -q
            rm -f "$BINARY_VM"
            echo "[ ⌐■_■] <(\"VM synchronized and marked for rebuild.\")"
        else
            echo "[ ⌐■_■] <(\"VM is already up to date.\")"
        fi
    fi

    exit 0 
fi

if [[ "$1" == "clr" && "$2" == "--his" ]]; then
    HISTORY_FILE="$HOME/.zonhistoryrepl"
    if [ -f "$HISTORY_FILE" ]; then
        : > "$HISTORY_FILE"
        echo "[ ⌐■_■] <(\"History cleared!\")"
    else
        echo "[ X_X] <(\"No history found.\")"
    fi
    exit 0
fi

if [[ "$1" == "vw" && "$2" == "--file" ]]; then
    [ -z "$3" ] && echo "[zon error]: Missing path." && exit 1
    if [ -f "$3" ]; then cat "$3"; exit 0; else echo "[zon error]: File not found."; exit 1; fi
fi

if [[ "$1" == "repl" && "$2" != "--in" ]]; then
    build_vm_if_needed
    TEMP_ZBC=$(mktemp --suffix=.zbc)
    trap 'rm -f "$TEMP_ZBC"' EXIT

    if [ -z "$2" ]; then
        python3 "$MAIN_PY" repl "$TEMP_ZBC"
    else
        python3 "$MAIN_PY" repl "$TEMP_ZBC" "$2"
    fi
    
    if [[ $? -eq 0 && -s "$TEMP_ZBC" ]]; then
        "$BINARY_VM" "$TEMP_ZBC"
    fi
    exit 0
fi

CONFIG_FILE="$HOME/.zonetic_config"

if [ "$1" == "r" ]; then
    FILE=$2
    TARGET_PATH=""
    if [ -f "$FILE" ]; then
        TARGET_PATH="$FILE"
    elif [ -f "$CONFIG_FILE" ]; then
        GLOBAL_DIR=$(cat "$CONFIG_FILE" | xargs)
        if [ -f "$GLOBAL_DIR/$FILE" ]; then
            TARGET_PATH="$GLOBAL_DIR/$FILE"
        fi
    fi

    if [ -z "$TARGET_PATH" ]; then
        echo "[ X_X] <(\"Error: File '$FILE' not found locally or in PATH.\")"
        exit 1
    fi
    
    build_vm_if_needed
    case "$TARGET_PATH" in
        *.zbc) "$BINARY_VM" "$TARGET_PATH" ;;
        *.zon)
            python3 "$MAIN_PY" c "$TARGET_PATH"
            if [ $? -eq 0 ]; then
                BYTECODE="${TARGET_PATH%.zon}.zbc"
                [ -f "$BYTECODE" ] && "$BINARY_VM" "$BYTECODE" || exit 1
            fi
            ;;
        *) echo "[ X_X] <(\"Invalid extension.\")"; exit 1 ;;
    esac
    exit 0
fi

if [[ "$1" == "st" && "$2" == "--zbc" ]]; then
    TARGET_PATH="$3"
    KEYEND=""
    if [[ -z "$TARGET_PATH" ]]; then
        python3 "$MAIN_PY" st --zbc
        exit 1
    fi

    if [ -z "$4" ]; then
        KEYEND="EOF"
    else
        KEYEND="$4"
    fi

    python3 "$MAIN_PY" st --zbc "$TARGET_PATH" "$KEYEND"

    if [ -f "$TARGET_PATH" ]; then
        read -p "Do you want to run $(basename "$TARGET_PATH") now? (y/n): " input </dev/tty
        answer=$(echo "$input" | tr '[:upper:]' '[:lower:]')
        if [[ "$answer" == "y" || "$answer" == "yes" ]]; then
            build_vm_if_needed
            "$BINARY_VM" "$TARGET_PATH"
        fi
    fi
    exit 0
fi

if [ "$1" == "rebuild" ]; then
    BUILD_FLAGS="-O3 -std=c++20"
    MODE_NAME="RELEASE"

    if [ "$2" == "--debug" ]; then
        BUILD_FLAGS="-g -O0 -std=c++20 -DDEBUG_MODE"
        MODE_NAME="DEBUG"
    fi

    echo "[ ⌐■_■] <(\"Rebuilding VM engine in $MODE_NAME mode...\")"

    if [ -f "$BINARY_VM" ]; then
        rm -f "$BINARY_VM"
        echo "[ ⌐■_■] <(\"Old binary removed.\")"
    fi

    g++ $BUILD_FLAGS -I"$IncludeVmDir" "$SrcVmDir"/*.cpp -o "$BinaryVm"

    if [ $? -ne 0 ]; then
        echo -e "[ X_X] <(\"Error: Failed to build VM.\")"
        exit 1
    else
        echo "[ ⌐■_■] <(\"VM rebuilt successfully!\")"
        exit 0
    fi
fi


if [ -f "$MAIN_PY" ]; then 
    python3 "$MAIN_PY" "$@" 
else 
    echo "[ X_X] <(\"Error: Cannot find main.py at $MAIN_PY\")" 
    exit 1 
fi