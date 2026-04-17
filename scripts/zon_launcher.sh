#!/usr/bin/env bash 

SOURCE="${BASH_SOURCE[0]}" 
while [ -L "$SOURCE" ]; do 
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )" 
  SOURCE="$(readlink "$SOURCE")" 
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" 
done 
DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )" 

REPO_DIR="$(cd "$DIR/.." && pwd)" 
MAIN_PY="$REPO_DIR/src/zonc/main.py"
LAUNCHER_FILE="$SOURCE"

if [ "$1" == "update" ]; then 
    echo "[ ⌐■_■] <(\"Checking for updates on GitHub...\")" 

    if [ ! -d "$REPO_DIR/.git" ]; then 
        echo "[ X_X] <(\"Error: .git directory not found. Cannot update.\")" 
        exit 1 
    fi 

    git -C "$REPO_DIR" fetch origin main -q 

    REMOTE_MSG=$(git -C "$REPO_DIR" log -1 origin/main --pretty=format:%s) 
    LOCAL_MSG=$(git -C "$REPO_DIR" log -1 --pretty=format:%s) 

    if [[ "$REMOTE_MSG" == *"[NOSTABLE]"* ]]; then 
        echo "[ X_X] <(\"Error: Remote version is marked as [NOSTABLE].\")" 
        echo "[ X_X] <(\"Update aborted to keep your system safe.\")" 
        exit 1 
    fi 

    if [[ "$REMOTE_MSG" == "$LOCAL_MSG" ]]; then 
        echo "[ ⌐■_■] <(\"You are already up to date!\")" 
        echo "[ ⌐■_■] <(\"Current Version: $LOCAL_MSG\")" 
        exit 0 
    fi 

    echo "[ ⌐■_■] <(\"New version found: $REMOTE_MSG\")" 
    echo "[ ⌐■_■] <(\"Updating now...\")" 

    git -C "$REPO_DIR" reset --hard origin/main -q 
    chmod +x "$LAUNCHER_FILE"

    echo "[ ⌐■_■] <(\"Update complete! You are now on: $REMOTE_MSG\")" 
    exit 0 
fi 

if [ -f "$MAIN_PY" ]; then 
    python3 "$MAIN_PY" "$@" 
else 
    echo "[ X_X] <(\"Error: Cannot find main.py at $MAIN_PY\")" 
    exit 1 
fi