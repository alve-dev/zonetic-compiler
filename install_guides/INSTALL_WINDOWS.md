# Zonetic Installation Guide (Windows)

Follow these steps to configure the Zonetic command-line interface on Windows. This process uses an automated batch script to handle dependencies, directory setup, and environment variables.

## 1. Prerequisites

Before installing, ensure you have **Git** and **Python 3** available in your system.
Verify them by running these commands in CMD or PowerShell:

```batch
git --version
python --version
```

## 2. Quick Installation (Automated)

Open **Command Prompt (CMD)** and run the following command. This will download the installer, execute it to set up Zonetic in `~/.zonetic`, and then clean up the temporary installer file:

```batch
curl -sSL https://raw.githubusercontent.com/alve-dev/zonetic-lang-tree-walker-version/refs/heads/main/install_windows.bat -o install_zon.bat && install_zon.bat
```

> [!IMPORTANT]
> **Restart your Terminal:** Windows requires a new terminal session to recognize the changes made to the "Path" environment variable. Please close and reopen your CMD or PowerShell window.

## 3. Full Installation

To download the entire repository, including the `examples/` and `docs/` folders:

```batch
curl -sSL https://raw.githubusercontent.com/alve-dev/zonetic-lang-tree-walker-version/refs/heads/main/install_windows_complete.bat -o install_zon.bat && install_zon.bat
```

## 4. Keep Zonetic Updated

The new CLI handles updates automatically. You don't need to download the installer again; just run:

```bash
zon update
```

## 5. Verify Installation

Check if Zonny is ready to help you:

```bash
zon vers
```

---

## Troubleshooting

### 'zon' is not recognized
1. **Restart your Terminal:** This is the most common fix. 
2. **Manual Path Check:** If it still fails, ensure that `C:\Users\<YourUser>\.zonetic\scripts` is listed in your User Environment Variables (Path).

### Python App Execution Aliases
If typing `python` opens the Microsoft Store, search for **"Manage app execution aliases"** in the Windows Start Menu and turn off the aliases for "Python".

## Uninstallation

To completely remove Zonetic from your system:

1. Delete the installation folder:
   ```batch
   rd /s /q "%USERPROFILE%\.zonetic"
   ```
2. Remove the `%USERPROFILE%\.zonetic\scripts` entry from your **Environment Variables** (Path) manually.

## Quick Start: REPL Mode

How to use `zon repl`:

1. **Enter the REPL**:
   ```bash
   zon repl
   ```
2. **Write your code**: You can type multiple lines.
3. **Execute**: Type `EOF` on a new line or press `Ctrl+Z and Enter`.

```bash
>> mut x = 100
>> print("Value: ", x)
>> EOF
```

> [!TIP]
> This mode is perfect for testing logic or syntax quickly. Once the output is displayed, the temporary environment is wiped clean.
