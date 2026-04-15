#!/bin/bash

if [ -d "/data/data/com.termux/files/usr" ]; then
    ENV="TERMUX"
    BIN_DIR="$PREFIX/bin"
    PKG_MANAGER="pkg"
    SUDO=""
else
    ENV="LINUX"
    BIN_DIR="/usr/local/bin"
    PKG_MANAGER="sudo apt"
    SUDO="sudo"
fi

echo "[ ⌐■_■] <( Starting Zonetic setup for $ENV... )"

check_and_install() {
    if ! command -v $1 &> /dev/null; then
        echo "[ ⌐■_■] <( '$1' is missing. Install it now? (y/n) )"
        read -r answer </dev/tty
        if [[ "$answer" =~ ^[Yy]$ ]]; then
            echo "[ ⌐■_■] <( Installing $1... )"
            $PKG_MANAGER update -y && $PKG_MANAGER install $2 -y
        else
            echo "[ ⌐■_■] <( Error: $1 is required. Aborting setup. )"
            exit 1
        fi
    fi
}

check_and_install "git" "git"
check_and_install "python3" "python3"

INSTALL_DIR="$HOME/.zonetic"

if [ -d "$INSTALL_DIR" ]; then
    FILE_COUNT=$(ls -A "$INSTALL_DIR" 2>/dev/null | wc -l)
    if [ "$FILE_COUNT" -gt 0 ]; then
        echo "[ ⌐■_■] <( Warning: $INSTALL_DIR is not empty ($FILE_COUNT files found). )"
        echo "[ ⌐■_■] <( Do you want to OVERWRITE its contents? (y/n) )"
        read -r choice </dev/tty
        if [[ "$choice" =~ ^[Yy]$ ]]; then
            echo "[ ⌐■_■] <( Cleaning directory... )"
            rm -rf "${INSTALL_DIR:?}"/*
            rm -rf "${INSTALL_DIR:?}"/.* 2>/dev/null
        else
            echo "[ ⌐■_■] <( Installation cancelled by user. )"
            exit 0
        fi
    fi
else
    mkdir -p "$INSTALL_DIR"
fi

cd "$INSTALL_DIR" || exit

if [ ! -d ".git" ]; then
    git init -q
    git remote add origin https://github.com/alve-dev/zonetic-lang-tree-walker-version.git 2>/dev/null || \
    git remote set-url origin https://github.com/alve-dev/zonetic-lang-tree-walker-version.git
    
    git config core.sparseCheckout true
    echo "src/zonc/*" > .git/info/sparse-checkout
    echo "scripts/*" >> .git/info/sparse-checkout
    echo ".gitignore" >> .git/info/sparse-checkout
fi

echo "[ ⌐■_■] <( Syncing with GitHub repository... )"
git pull origin main --rebase -q

LAUNCHER_PATH="$INSTALL_DIR/scripts/zon_launcher.sh"

if [ -f "$LAUNCHER_PATH" ]; then
    chmod +x "$LAUNCHER_PATH"
    echo "[ ⌐■_■] <( Configuring 'zon' global command... )"
    $SUDO ln -sf "$LAUNCHER_PATH" "$BIN_DIR/zon"
else
    echo "[ ⌐■_■] <( Error: Launcher script not found at $LAUNCHER_PATH )"
    exit 1
fi

echo "------------------------------------------------"
echo "[ ⌐■_■] <( Zonetic installed successfully! )"
echo "[ ⌐■_■] <( Try running: zon vers )"
