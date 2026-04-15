#!/usr/bin/env bash

# [ ⌐■_■] <( Finding my real home... )
# Este truco sigue el symlink hasta la carpeta real
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
  DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
DIR="$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )"

# Ahora REPO_DIR será correctamente /home/usuario/.zonetic
REPO_DIR="$(cd "$DIR/.." && pwd)"
MAIN_PY="$REPO_DIR/src/zonc/main.py"

if [ "$1" == "update" ]; then
    echo "[ ⌐■_■] <( Checking for updates on GitHub... )"
    git -C "$REPO_DIR" fetch origin main -q

    REMOTE_MSG=$(git -C "$REPO_DIR" log -1 origin/main --pretty=format:%s)
    LOCAL_MSG=$(git -C "$REPO_DIR" log -1 --pretty=format:%s)

    if [[ "$REMOTE_MSG" == *"[NOSTABLE]"* ]]; then
        echo "[ ⌐■_■] <( Error: Remote version is marked as [NOSTABLE]. )"
        echo "[ ⌐■_■] <( Update aborted to keep your system safe. )"
        exit 1
    fi
    
    if [[ "$REMOTE_MSG" == "$LOCAL_MSG" ]]; then
        echo "[ ⌐■_■] <( You are already up to date! )"
        echo "[ ⌐■_■] <( Version: $LOCAL_MSG )"
        exit 0
    fi

    # 5. Perform the update
    echo "[ ⌐■_■] <( New version found: $REMOTE_MSG )"
    echo "[ ⌐■_■] <( Updating now... )"
    
    git -C "$REPO_DIR" reset --hard origin/main -q
    git -C "$REPO_DIR" clean -fd -q
    
    echo "[ ⌐■_■] <( Update complete! You are now on $REMOTE_MSG )"
    exit 0
fi

if [ -f "$MAIN_PY" ]; then
    python3 "$MAIN_PY" "$@"
else
    echo "[ ⌐■_■] <( Error: Cannot find main.py at $MAIN_PY )"
    exit 1
fi
