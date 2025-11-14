# Dir Sorter (Personal Edition)

A lightweight file organization tool that automatically sorts files from a target directory into an organized structure. Two OS-specific scripts (`WIN_Dir_Sorter.py` for Windows and `LIN_Dir_Sorter.py` for Linux/WSL) provide the same functionality, configured through a single JSON file.

## Features

- **Single Configuration File**: One `dir_sorter_config.json` manages all settings
- **Multiple Sort Types**: 
  - **File-Extension**: Groups files by extension (e.g., `.pdf_Files`, `.jpg_Files`)
  - **Date-Created**: Organizes files by creation date (e.g., `2024/03_2024`)
- **Flexible Operation Modes**: Move or copy files to the sorted location
- **Recursive Processing**: Processes all files in subdirectories of the target folder
- **Ignore Lists**: Skip specific files by name or extension
- **Empty Directory Cleanup**: Optional removal of empty directories after moving files
- **Dry-Run Mode**: Preview changes before executing
- **Lock File System**: Prevents concurrent runs and handles stale locks gracefully
- **Interactive Configuration**: Guided setup with validation
- **Quiet Mode**: Suppress output for automation scripts
- **Freeze Mode**: Hold lock for testing RPA integrations

## Requirements

- Python 3.x (latest version recommended)
- Read permissions for the target directory
- Write permissions for the sorted directory location
- The target and sorted directories must be separate (cannot be the same or nested)

## Installation

1. **Download or clone the project** to a convenient location on your system
2. **Ensure Python 3 is installed** and accessible from your command line
3. **Create or download the configuration file** (`dir_sorter_config.json`) in the project directory
4. **Configure the paths** in `dir_sorter_config.json` (see Configuration section below)

### Quick Setup

Run the interactive configuration mode to set up your config file:

```bash
# Windows
python WIN_Dir_Sorter.py -c

# Linux/WSL
python LIN_Dir_Sorter.py -c
```

This will guide you through setting all required configuration values.

## Configuration

The `dir_sorter_config.json` file contains all settings. Here are the available configuration keys:

### Required Fields

- **`Target_Dir`** (string): Absolute path to the folder containing files to be sorted. Supports `~` for home directory expansion.
- **`Sorted_Dir`** (string): Absolute path where organized files will be placed. The directory will be created if it doesn't exist. Must be separate from `Target_Dir`.
- **`Sort_Type`** (string): Sorting method. Options:
  - `"File-Extension"`: Groups files by their extension (e.g., `.pdf_Files`, `.jpg_Files`, `no_extension_Files`)
  - `"Date-Created"`: Organizes by creation date in `YYYY/MM_YYYY` format
- **`Sort_Mode`** (string): Operation mode. Options:
  - `"Move"`: Files are moved from the target directory to the sorted location
  - `"Copy"`: Files are copied, leaving originals in place

### Optional Fields

- **`Delete_Empty_Dirs`** (boolean): If `true`, removes empty directories from `Target_Dir` after sorting. **Only works when `Sort_Mode` is `"Move"`**. Default: `false`
- **`Ignore_Names`** (array of strings): List of filename stems (without extensions) to skip. Example: `["readme", "invoice"]` will ignore `readme.txt` and `invoice.pdf`
- **`Ignore_Types`** (array of strings): List of file extensions (without dots) to skip. Example: `["pdf", "txt"]` will ignore all `.pdf` and `.txt` files. Case-insensitive.

### Internal Fields (Auto-managed)

- **`Lock`** (string): Path to the lock file. Automatically set during script execution.
- **`Lock_PID`** (string): Process ID of the running script. Automatically set during script execution.

### Example Configuration

```json
{
  "Target_Dir": "C:/Users/YourName/Downloads",
  "Sorted_Dir": "C:/Users/YourName/Documents/sorted",
  "Sort_Type": "File-Extension",
  "Sort_Mode": "Move",
  "Delete_Empty_Dirs": true,
  "Ignore_Names": ["readme", "important"],
  "Ignore_Types": ["pdf", "tmp"],
  "Lock": "",
  "Lock_PID": ""
}
```

## Usage

### Basic Commands

```bash
# Windows - Run the sorter
python WIN_Dir_Sorter.py

# Linux/WSL - Run the sorter
python LIN_Dir_Sorter.py
```

### Command-Line Options

- **`--dry-run`** or **`--d-r`**: Preview mode. Shows what would be moved/copied without making changes. Prompts for confirmation if files would be affected.
- **`--quiet`** or **`-q`**: Silent mode. Suppresses all output except errors and lock warnings.
- **`--configure`** or **`-c`**: Interactive configuration editor. Opens a menu to edit all configuration fields.
- **`--freeze`** or **`-f`**: Freeze mode. Holds the lock file and sleeps until interrupted (useful for testing RPA integrations).

### Common Usage Examples

```bash
# Preview changes before running
python WIN_Dir_Sorter.py --dry-run

# Run silently (for automation)
python WIN_Dir_Sorter.py --quiet

# Edit configuration interactively
python WIN_Dir_Sorter.py -c

# Preview and confirm in one step
python WIN_Dir_Sorter.py --dry-run
# (Then type 'y' when prompted)

# Hold lock for testing
python WIN_Dir_Sorter.py --freeze
```

## How It Works

1. **Lock Check**: The script checks for existing lock files to prevent concurrent runs
2. **Configuration Validation**: Validates all paths and settings
3. **File Discovery**: Recursively scans the target directory for all files
4. **Filtering**: Applies ignore lists (names and types)
5. **Destination Planning**: Determines destination folders based on sort type
6. **Execution**: Moves or copies files to their destinations
7. **Cleanup**: Optionally removes empty directories (if enabled and in Move mode)
8. **Lock Release**: Removes the lock file when finished

### Sort Type Details

**File-Extension Mode:**
- Files are grouped into folders named by their extension
- Format: `.{extension}_Files` (e.g., `.pdf_Files`, `.jpg_Files`)
- Files without extensions go into `no_extension_Files`

**Date-Created Mode:**
- Files are organized by creation date
- Structure: `YYYY/MM_YYYY` (e.g., `2024/03_2024`)
- Uses file creation time (birthtime) when available, falls back to modification time

## Troubleshooting

### Lock File Issues

If you see a lock file warning:

**Windows:**
```bash
# Check if the process is still running
tasklist | findstr <PID>

# Force kill if needed
taskkill /PID <PID> /F

# Then delete the lock file manually
del dir_sorter.lock
```

**Linux/WSL:**
```bash
# Check if the process is still running
ps -p <PID>

# Force kill if needed
kill -9 <PID>

# Then delete the lock file manually
rm dir_sorter.lock
```

### Common Errors

- **"Target_Dir must be a real folder"**: The target directory path doesn't exist or isn't a directory
- **"Target_Dir and Sorted_Dir cannot be the same place"**: Both paths point to the same location
- **"Sorted_Dir cannot live inside Target_Dir"**: The sorted directory is nested within the target (or vice versa)
- **"Permission problem"**: Insufficient permissions to read/write files or directories
- **"File no longer exists"**: File was deleted or moved between discovery and processing

### Configuration Validation

The script validates configuration on every run. If validation fails:
1. Check error messages for specific issues
2. Run `python WIN_Dir_Sorter.py -c` (or `LIN_Dir_Sorter.py -c`) to fix interactively
3. Ensure all paths are absolute and valid
4. Verify that `Sort_Type` and `Sort_Mode` use exact values: `"File-Extension"`, `"Date-Created"`, `"Move"`, `"Copy"`

## Notes

- The script processes files recursively through all subdirectories
- Paths support `~` for home directory expansion (e.g., `~/Downloads`)
- Extensions in `Ignore_Types` are case-insensitive and dots are automatically stripped
- Filename matching in `Ignore_Names` is exact (case-sensitive) and matches the stem only
- Empty directory cleanup only runs when `Delete_Empty_Dirs` is `true` and `Sort_Mode` is `"Move"`
- The lock file system prevents accidental concurrent runs and helps identify stuck processes
