#!/bin/bash

# Environment Detection
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

echo "[ ⌐■_■] <( Starting FULL Zonetic installation for $ENV... )"

# Dependency check function
check_and_install() {
    if ! command -v $1 &> /dev/null; then
        echo "[ ⌐■_■] <( Installing missing dependency: $1... )"
        $PKG_MANAGER update -y && $PKG_MANAGER install $2 -y
    fi
}

check_and_install "git" "git"
check_and_install "python3" "python3"

INSTALL_DIR="$HOME/.zonetic-full"
mkdir -p "$INSTALL_DIR" && cd "$INSTALL_DIR" || exit

# Clone all content
if [ ! -d ".git" ]; then
    echo "[ ⌐■_■] <( Cloning full repository... )"
    git clone https://github.com .
else
    echo "[ ⌐■_■] <( Updating existing repository... )"
    git pull origin main
fi

# Create Global Command
chmod +x "scripts/zon_launcher.sh"
echo "[ ⌐■_■] <( Setting up global 'zon' command... )"
$SUDO ln -sf "$INSTALL_DIR/scripts/zon_launcher.sh" "$BIN_DIR/zon"

echo "------------------------------------------------"
echo "[ ⌐■_■] <( Full installation finished at $INSTALL_DIR )"
echo "[ ⌐■_■] <( Type 'zon' to start! )"
