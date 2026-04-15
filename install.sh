#!/bin/bash

# 1. Environment Detection
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

# Dependency check function
check_and_install() {
    if ! command -v $1 &> /dev/null; then
        echo "[ ⌐■_■] <( '$1' is missing. Install it now? (y/n) )"
        read -r answer </dev/tty
        if [ "$answer" != "${answer#[Yy]}" ]; then
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

# 2. Setup Directory with safety check
INSTALL_DIR="$HOME/.zonetic"

if [ -d "$INSTALL_DIR" ]; then
    # Contamos cuántos archivos hay (incluyendo ocultos)
    FILE_COUNT=$(ls -A "$INSTALL_DIR" | wc -l)
    
    if [ "$FILE_COUNT" -gt 0 ]; then
        echo "[ ⌐■_■] <( Warning: $INSTALL_DIR is not empty ($FILE_COUNT files found). )"
        echo "[ ⌐■_■] <( Do you want to OVERWRITE its contents? (y/n) )"
        read -r choice </dev/tty
        if [[ "$choice" =~ ^[Yy]$ ]]; then
            echo "[ ⌐■_■] <( Cleaning directory... )"
            rm -rf "${INSTALL_DIR:?}"/*
        else
            echo "[ ⌐■_■] <( Installation cancelled by user. )"
            exit 0
        fi
    fi
else
    mkdir -p "$INSTALL_DIR"
fi


cd "$INSTALL_DIR" || exit

# 3. Sparse Checkout (Light installation)
if [ ! -d ".git" ]; then
    git init -q
    git remote add origin https://github.com
    git config core.sparseCheckout true
    echo "src/zonc/*" > .git/info/sparse-checkout
    echo "scripts/*" >> .git/info/sparse-checkout
    echo ".gitignore" >> .git/info/sparse-checkout
fi

echo "[ ⌐■_■] <( Syncing with GitHub repository... )"
git pull origin main -q

# 4. Create Global Command
chmod +x "$INSTALL_DIR/scripts/zon_launcher.sh"
echo "[ ⌐■_■] <( Configuring 'zon' global command... )"
$SUDO ln -sf "$INSTALL_DIR/scripts/zon_launcher.sh" "$BIN_DIR/zon"

echo "------------------------------------------------"
echo "[ ⌐■_■] <( Zonetic installed successfully! )"
echo "[ ⌐■_■] <( Try running: zon vers )"
