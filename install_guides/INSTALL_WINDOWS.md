# Zonetic Installation Guide (Windows)

Follow these steps to configure the Zonetic CLI on Windows. This process includes setting up the C++ compiler and using a PowerShell script to automate the environment.

## 1. Critical Prerequisite: C++ Compiler (g++)

Zonetic requires a C++ compiler to function. Windows does not include one by default. **Follow these two steps exactly:**

1. **Install MSYS2:** Open PowerShell as **Administrator** and run:
```powershell
winget install --id MSYS2.MSYS2 --exact
```

2. **Install GCC:** Search for "**MSYS2 MSYS**" in your Start Menu, open it, and paste this command:
```bash
pacman -S mingw-w64-ucrt-x86_64-gcc
```
*(Type 'Y' and press Enter when prompted to confirm).*

## 2. Quick Installation (Automated)

Once the compiler is installed, open **PowerShell** and run the installer. This will set up Zonetic in `~/.zonetic` and configure the global `zon` command:

```powershell
irm https://raw.githubusercontent.com/alve-dev/zonetic-compiler/refs/heads/main/install_windows.ps1 | iex
```

> [!IMPORTANT]
> **Restart your Terminal:** Windows needs a fresh session to recognize the new "Path" variables. Close and reopen PowerShell or CMD after installation.

## 3. Full Installation

To download the entire repository, including `examples/` and `docs/`:

```powershell
irm https://raw.githubusercontent.com/alve-dev/zonetic-compiler/refs/heads/main/install_windows_complete.ps1 | iex
```

---

## Troubleshooting

### 'g++' is not recognized
If you installed MSYS2 but the script still can't find `g++`, ensure you ran the `pacman` command in Step 1. The Zonetic installer will attempt to link `C:\msys64\ucrt64\bin` to your Path automatically.

### Script Execution Error
If Windows blocks the installer, run this command once to allow local scripts, then try the installation again:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 'zon' is not recognized
1. **Restart PowerShell:** This is mandatory.
2. **Manual Check:** Ensure `$HOME\.zonetic\.zonc\scripts` is in your Environment Variables Path.

---

## Quick Start

* **Verify Version:** `zon vw --vers`
* **Update Zonetic:** `zon update`
* **REPL Mode:** `zon repl` (Type `EOF` on a new line to execute).

```powershell
>> print("Zonetic is alive!")
>> EOF
```
