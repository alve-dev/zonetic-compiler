#!/bin/bash
# ==============================================================
# Zonetic Installer — Linux / Termux (Android)
#
# Default: sparse checkout — downloads only src/zonc/*, scripts/*
# Complete: in clone_compiler(), comment Clone-Sparse and
#           uncomment Clone-Full to get the entire source tree.
#
# Usage:
#   bash install.sh
#   bash <(curl -s https://raw.githubusercontent.com/.../install.sh)
# ==============================================================

# ------------------------------------------------------------------
# ANSI colors
# ------------------------------------------------------------------
GREEN="\033[32m"
RED="\033[31m"
YELLOW="\033[33m"
CYAN="\033[36m"
RESET="\033[0m"

# ------------------------------------------------------------------
# Zonny faces
#   NEUTRAL  [ o_o]   — working / info
#   SUCCESS  [ ^_^]   — step completed
#   DONE     [ ⌐■_■]b — everything finished
#   ERROR    [ x_x]   — fatal error
#   PROMPT   [ o_0]   — asking the user something
# ------------------------------------------------------------------
FACE_NEUTRAL="[ o_o]"
FACE_SUCCESS="${GREEN}[ ^_^]${RESET}"
FACE_DONE="${CYAN}[ ⌐■_■]b${RESET}"
FACE_ERROR="${RED}[ x_x]${RESET}"
FACE_PROMPT="${YELLOW}[ o_0]${RESET}"

# ------------------------------------------------------------------
# Output helpers
# ------------------------------------------------------------------
info()    { echo -e "$FACE_NEUTRAL $1"; }
success() { echo -e "$FACE_SUCCESS $1"; }
done_()   { echo -e "$FACE_DONE $1"; }
err()     { echo -e "$FACE_ERROR $1"; exit 1; }
separator() { echo ""; echo "------------------------------------------------"; echo ""; }

# ------------------------------------------------------------------
# Platform detection
# ------------------------------------------------------------------
detect_platform() {
    if [ -d "/data/data/com.termux/files/usr" ]; then
        PLATFORM="Termux"
        BIN_DIR="$PREFIX/bin"
        PKG_MANAGER="pkg"
        SUDO=""
    else
        PLATFORM="Linux"
        BIN_DIR="/usr/local/bin"
        PKG_MANAGER="sudo apt"
        SUDO="sudo"
    fi
}

# ------------------------------------------------------------------
# Helper: read a y/n answer, retrying until valid input is given
# ------------------------------------------------------------------
ask_yn() {
    local prompt="$1"
    local answer=""

    read -p "$(echo -e "$FACE_PROMPT $prompt ") " answer </dev/tty
    answer=$(echo "$answer" | tr '[:upper:]' '[:lower:]')

    while [[ "$answer" != "y" && "$answer" != "n" ]]; do
        read -p "$(echo -e "$FACE_PROMPT Are you feeling okay? I need a (y/n), don't fail me now ") " answer </dev/tty
        answer=$(echo "$answer" | tr '[:upper:]' '[:lower:]')
    done

    echo "$answer"
}

# ------------------------------------------------------------------
# Helper: ensure a tool is installed, offering to install it if missing
# ------------------------------------------------------------------
require_tool() {
    local cmd="$1"
    local pkg="$2"

    if command -v "$cmd" &> /dev/null; then
        success "$cmd is ready."
        return 0
    fi

    info "'$cmd' not found."
    local answer
    answer=$(ask_yn "'$cmd' is missing. Install it now? (y/n)")

    if [[ "$answer" == "y" ]]; then
        info "Installing '$cmd'..."
        $PKG_MANAGER update -y > /dev/null 2>&1
        $PKG_MANAGER install "$pkg" -y > /dev/null 2>&1
        success "$cmd installed."
    else
        err "'$cmd' is required. Aborting setup."
    fi
}

# ------------------------------------------------------------------
# Handle existing installation directory
# ------------------------------------------------------------------
check_install_dir() {
    if [ ! -d "$INSTALL_DIR" ]; then
        return 0
    fi

    local file_count
    file_count=$(ls -A "$INSTALL_DIR" 2>/dev/null | wc -l)

    if [ "$file_count" -gt 0 ]; then
        info "$INSTALL_DIR is not empty ($file_count files found)."
        local answer
        answer=$(ask_yn "Overwrite its contents? (y/n)")

        if [[ "$answer" == "y" ]]; then
            info "Cleaning directory..."
            rm -rf "${INSTALL_DIR:?}"/*
        else
            done_ "Installation cancelled."
            exit 0
        fi
    fi
}

# ------------------------------------------------------------------
# Repository cloning
#
# TWO VARIANTS for the compiler:
#   clone_compiler_sparse — downloads only src/zonc/*, scripts/, .gitignore
#   clone_compiler_full   — downloads the entire repository (for contributors)
#
# In clone_compiler(), swap which one is called to switch between modes.
# ------------------------------------------------------------------
clone_compiler_sparse() {
    info "Syncing compiler with GitHub (sparse checkout)..."
    cd "$ZONC_DIR" || err "Could not enter $ZONC_DIR"

    git init -q
    git remote add origin https://github.com/alve-dev/zonetic-lang-tree-walker-version.git 2>/dev/null
    git config core.sparseCheckout true

    {
        echo "src/zonc/*"
        echo "scripts/*"
        echo ".gitignore"
    } > .git/info/sparse-checkout

    git pull origin main --rebase -q
    if [ $? -ne 0 ]; then err "Failed to sync compiler repository."; fi
    success "Compiler downloaded."
}

clone_vm() {
    info "Syncing VM with GitHub..."
    cd "$ZONVM_DIR" || err "Could not enter $ZONVM_DIR"

    git init -q
    git remote add origin https://github.com/alve-dev/zonetic-vm.git 2>/dev/null
    git pull origin main -q
    if [ $? -ne 0 ]; then err "Failed to sync VM repository."; fi
    success "VM downloaded."
}

clone_compiler() {
    clone_compiler_sparse
}

# ------------------------------------------------------------------
# Link the launcher as the global `zon` command
# ------------------------------------------------------------------
link_launcher() {
    if [ ! -f "$LAUNCHER" ]; then
        err "Launcher not found at $LAUNCHER -- The compiler clone may have failed."
    fi

    chmod +x "$LAUNCHER"
    info "Linking 'zon' command to $BIN_DIR..."

    if ! $SUDO ln -sf "$LAUNCHER" "$BIN_DIR/zon" 2>/dev/null; then
        err "Could not create symlink at $BIN_DIR/zon\n-- Try running with sudo, or add $LAUNCHER to your PATH manually."
    fi

    success "'zon' command linked."
}

# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
main() {
    detect_platform

    separator
    echo -e "${CYAN}Zonetic Installer v2.0 — $PLATFORM${RESET}"
    separator

    info "Checking dependencies..."
    require_tool "git"     "git"
    require_tool "python3" "python3"
    require_tool "g++"     "g++"   

    INSTALL_DIR="$HOME/.zonetic"
    ZONC_DIR="$INSTALL_DIR/.zonc"
    ZONVM_DIR="$INSTALL_DIR/.zonvm"
    LAUNCHER="$ZONC_DIR/scripts/zon_launcher.sh"

    check_install_dir

    mkdir -p "$ZONC_DIR" "$ZONVM_DIR"

    clone_compiler
    clone_vm
    link_launcher

    separator
    done_ "Zonetic v2 installed successfully!"
    done_ "Try running: zon vw --vers"
    done_ "If it doesn't work, open a new terminal to apply PATH changes."
    separator
}

main