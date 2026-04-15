# Zonetic Installation Guide (Android - Termux)

Follow these steps to configure the **Zonetic** command-line interface on Android. This process uses **Termux** and an automated script for a hassle-free setup.

## 0. Install Termux (Read Carefully)

Do not use the Google Play Store version, as it is outdated.

1.  **Download**: Go to the [Official F-Droid Page](https://f-droid.org).
2.  **Install the APK**: Download the latest version that **DOES NOT** have the "(beta)" tag.
3.  **Open**: Launch Termux and wait for the "Installing bootstrap" process to finish.

## 1. Quick Installation

Run the following command inside Termux. It will automatically check for Python/Git and set up the `zon` command:

```bash
curl -sSL https://raw.githubusercontent.com/alve-dev/zonetic-lang-tree-walker-version/refs/heads/main/install.sh | bash
```

> [!TIP]
> **Full Installation**: To download examples and documentation along with the compiler:
> ```bash
> curl -sSL https://raw.githubusercontent.com/alve-dev/zonetic-lang-tree-walker-version/refs/heads/main/install_comple.sh | bash
> ```

## 2. Keep Zonetic Updated

To get the latest improvements directly from the source. The installer ensures only stable commits are downloaded:

```bash
zon update
```

## 3. Verify Installation

Test the installation by checking the version:

```bash
zon vers
```

---

## Troubleshooting

**Command not found**
If the terminal does not recognize the command immediately, run:
```bash
hash -r
```

## Uninstallation

To remove the `zon` command and files:

```bash
rm -rf ~/.zonetic
rm $PREFIX/bin/zon
```

---

## Quick Start: REPL Mode

### How to use `zon repl`

1. **Enter the REPL**:
   ```bash
   zon repl
   ```
2. **Execute**: Type `EOF` on a new line or press `Ctrl+D`.
