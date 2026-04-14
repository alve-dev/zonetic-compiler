# Zonetic Installation Guide (Windows)

The repository includes a `zon.bat` launcher inside the `src/zonc/` directory. Follow these steps to configure the CLI globally.

## 1. Prerequisites

Ensure **Python 3.10+** is installed. Verify in PowerShell:

```powershell
python --version
```

## 2. Clone the Repository

Clone the source code into a specific directory:

```powershell
git clone https://github.com/YOUR_USERNAME/zonetic-lang-tree-walker-version.git zonetic
```

**WARNING:** Do not modify, move, or delete files inside the `zonetic/` directory after installation.

## 3. Get the Installation Path

Navigate to the compiler directory and get the full path to copy it:

```powershell
cd zonetic/src/zonc
(Get-Item .).FullName
```

*Copy the output of the last command (e.g., C:\Users\Name\zonetic\src\zonc).*

## 4. Add to Environment Variables

1. Open the **Start Menu**, search for "Environment Variables" and select **Edit the system environment variables**.
2. Click **Environment Variables**.
3. Under **User variables**, select **Path** and click **Edit**.
4. Click **New** and paste the path you copied in Step 3.
5. Click **OK** on all windows and **restart your terminal**.

**To reset your terminal, you can do the following:**
```powershell
exit
```
*(And then open a new terminal window).*

## 5. Verify Installation

Open a new PowerShell or CMD window and run:

```powershell
zon vers
```

---

## Troubleshooting

### Command not found
If `zon` is not recognized, ensure you restarted PowerShell after editing the Environment Variables.

### Broken Link
If you move the `zonetic` folder, you must update the Path in Environment Variables with the new location of `src/zonc`.

## Uninstallation

To remove the `zon` command, delete the entry from your Environment Variables Path.