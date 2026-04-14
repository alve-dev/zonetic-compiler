# Zonetic Installation Guide (Linux)

Follow these steps to configure the Zonetic command-line interface. This process creates a global symbolic link to the compiler source.

## 1. Prerequisites

Zonetic requires Python 3.10 or higher. Verify your environment:

```bash
python3 --version
```

## 2. Clone the Repository

Clone the source code into a specific directory named 'zonetic':

```bash
git clone https://github.com/YOUR_USERNAME/zonetic-lang-tree-walker-version.git zonetic
```
>[!CAUTION]
>**WARNING**: Do not modify, move, or delete files inside the `zonetic/` directory after installation. Doing so will break the compiler and the global command.

## 3. Navigate and Set Permissions

Move to the compiler source directory and grant execution permissions to the entry point:

```bash
cd zonetic/src/zonc
chmod +x main.py
```
## 4. Create the System Link

Create a symbolic link in `/usr/local/bin` to make `zon` a global command:

```bash
sudo ln -s $(pwd)/main.py /usr/local/bin/zon
```
## 5. Verify Installation

Test the installation by checking the version and Zonny's status:

```bash
zon vers
```

---

## Troubleshooting
**Command not found**

If the terminal does not recognize the command immediately, refresh your shell configuration:
```bash
source ~/.bashrc
```

**Broken Link**

The symbolic link depends on the absolute path of the source file. If you move the zonetic folder, you must recreate the link:
```bash
sudo rm /usr/local/bin/zon
cd new/path/to/zonetic/src/zonc
sudo ln -s $(pwd)/main.py /usr/local/bin/zon
```

**Uninstallation**

To remove the zon command from your system:

```bash
sudo rm /usr/local/bin/zon
```
