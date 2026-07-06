# Zonetic Installation Guide (Linux)

Follow these steps to configure the Zonetic command-line interface. This process uses a specialized installer to set up the environment and the global command.

## 1. Quick Installation

Zonetic features an automated installer that handles dependencies and configures the system for you. Run the following command:

```bash
curl -sSL https://raw.githubusercontent.com/alve-dev/zonetic-compiler/refs/heads/main/install_scripts/install.sh | bash
```

> [!TIP]
> **Full Installation**: If you want to download the entire repository (including logos and examples), use this command instead:
> ```bash
> curl -sSL https://raw.githubusercontent.com/alve-dev/zonetic-compiler/refs/heads/main/install_scripts/install_comple.sh | bash
> ```

## 2. Verify Installation

Test the installation by checking the version and Zonny's status:

```bash
zon vers
```

## 3. Keep Zonetic Updated

You can sync your local compiler with the latest stable version from GitHub without reinstalling. The system will check for the [STABLE] flag before updating:

```bash
zon update
```

---

## Troubleshooting
**Command not found**

If the terminal does not recognize the command immediately, refresh your shell configuration:
```bash
source ~/.bashrc
```

**Uninstallation**

To remove the zon command and source files from your system:

```bash
rm -rf ~/.zonetic
sudo rm /usr/local/bin/zon
```

## Quick Start: REPL Mode

Zonetic features a built-in **REPL** (Interactive Mode) that allows you to write and execute code on the fly.

### How to use `zon repl`

1. **Enter the REPL**:
   ```bash
   zon repl
   ```
2. **Execute**: Type `EOF` on a new line or press `Ctrl+D` to trigger execution.
