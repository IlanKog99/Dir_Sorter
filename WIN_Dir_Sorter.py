from json import dumps, loads  # read and write config file
from shutil import copy2, move  # move and copy files
from time import localtime, sleep  # get creation dates and sleep for freeze mode
from sys import argv  # read CLI args
from os import getpid, system  # specific OS functions we need
from pathlib import Path  # path objects
from typing import Dict, List, Optional, Set, Tuple  # type and return hints

ROOT_DIR = Path(__file__).resolve().parent # get the root directory of the script
FILE_INFO: Dict[str, Dict[str, object]] = { # object can be type str or path
    "config": {
        "filename": "dir_sorter_config.json",
        "path": ROOT_DIR / "dir_sorter_config.json",
    },
    "lock": {
        "filename": "dir_sorter.lock",
        "path": ROOT_DIR / "dir_sorter.lock",
    },
}


def parse_cli_args() -> Dict[str, bool]:  # return dict of args values as bools
    args = argv[1:] # get args from CLI
    return {
        "dry_run": ("--dry-run" in args) or ("--d-r" in args), # Reutn bool based on string in args
        "quiet": ("--quiet" in args) or ("-q" in args), # Reutn bool based on string in args
        "configure": ("--configure" in args) or ("-c" in args), # Reutn bool based on string in args
        "freeze": ("--freeze" in args) or ("-f" in args), # Reutn bool based on string in args
    }


def require_config_file(path: Path) -> None:
    if path.exists(): # if cfg exists return
        return
    print(f"Config file not found: {path}") # else print message and exit
    print("Create the file manually or run the script with -c to set it up interactively.")
    exit(1) # exit code 1 because error


def load_raw_config(path: Path) -> Dict[str, object]:
    # load cfg from ascii text file to dict
    return loads(path.read_text(encoding="utf-8")) # utf-8 to work with one cfg for both OSes


def save_raw_config(path: Path, data: Dict[str, object]) -> None:
    path.write_text(dumps(data, indent=2) + "\n", encoding="utf-8") # utf-8 to work with one cfg for both OSes


def validate_config(raw: Dict[str, object], abort_on_error: bool = True) -> Optional[Dict[str, object]]:
    def report(message: str) -> Optional[Dict[str, object]]:
        print(message)
        if abort_on_error:
            exit(1)
        return None

    try:
        target = Path(str(raw["Target_Dir"])).expanduser().resolve()
        sorted_home = Path(str(raw["Sorted_Dir"])).expanduser().resolve()
        sort_type = str(raw["Sort_Type"])
        sort_mode = str(raw["Sort_Mode"])
    except KeyError as missing:
        return report(f"Config is missing the '{missing.args[0]}' field.")

    if not target.exists() or not target.is_dir(): # make sure both are valid dirs
        return report("Target_Dir must be a real folder.")
    if target == sorted_home: # make sure they are not the same dir
        return report("Target_Dir and Sorted_Dir cannot be the same place.")
    if target in sorted_home.parents: # make sure sorted_home is not a subdir of target
        return report("Sorted_Dir cannot live inside Target_Dir.")
    if sorted_home in target.parents: # make sure target is not a subdir of sorted_home
        return report("Target_Dir cannot live inside Sorted_Dir.")

    if not sorted_home.exists(): # make sure sorted_home exists
        sorted_home.mkdir(parents=True, exist_ok=True)

    if sort_type not in {"File-Extension", "Date-Created"}: # make sure sort_type is valid
        return report("Sort_Type must be 'File-Extension' or 'Date-Created'.")
    if sort_mode not in {"Move", "Copy"}: # make sure sort_mode is valid
        return report("Sort_Mode must be 'Move' or 'Copy'.")

    ignore_names = {str(item).strip() for item in raw.get("Ignore_Names", []) if str(item).strip()} # teke each value, turn into str, remove whitespace and save into a set
    ignore_types = {str(item).strip().lower().lstrip(".") for item in raw.get("Ignore_Types", []) if str(item).strip()} # teke each value, turn into str, remove whitespace, lower case, remove dot and save into a set

    # Get Delete_Empty_Dirs boolean, default to False
    delete_empty_dirs = bool(raw.get("Delete_Empty_Dirs", False))

    # save the values to the raw var later to be used by save_raw_config
    raw["Target_Dir"] = str(target)
    raw["Sorted_Dir"] = str(sorted_home)
    raw["Ignore_Names"] = sorted(ignore_names)
    raw["Ignore_Types"] = sorted(ignore_types)
    raw["Delete_Empty_Dirs"] = delete_empty_dirs
    raw["Lock"] = str(raw.get("Lock", "") or "")
    raw["Lock_PID"] = str(raw.get("Lock_PID", "") or "")

    return {
        "target_dir": target,
        "sorted_dir": sorted_home,
        "sort_type": sort_type,
        "sort_mode": sort_mode,
        "ignore_names": ignore_names,
        "ignore_types": ignore_types,
        "delete_empty_dirs": delete_empty_dirs,
        "lock_entry": str(raw["Lock"]),
        "lock_pid": str(raw["Lock_PID"]),
    }


def say(message: str, quiet: bool) -> None:
    if not quiet:
        print(message)


def check_lock(config: Dict[str, object], quiet: bool) -> None:
    lock_entry = str(config["lock_entry"])
    if not lock_entry:
        return
    recorded = Path(lock_entry).expanduser().resolve() # file path for the lock written in cfg
    if recorded.exists():
        pid_text = recorded.read_text(encoding="utf-8").strip() or "Unknown"
        print(f"""
Another sorter run left a lock behind.
Lock file: {recorded}
Recorded PID: {pid_text}
If that run is stuck, close it with: taskkill /PID <PID> /F
Then delete the lock file and run this script again.
""")
        exit(1)
    lock_pid = str(config.get("lock_pid", "") or "")
    if lock_pid:
        print(f"""
Config mentioned a lock, but the lock file is gone.
Previously recorded PID: {lock_pid}
If that process is still stuck, close it with: taskkill /PID {lock_pid} /F
""")
    say("Clearing stale lock entry from config.", quiet)
    # remove fake lock if present in cfg
    config["lock_entry"] = ""
    raw_config = load_raw_config(FILE_INFO["config"]["path"])
    raw_config["Lock"] = ""
    raw_config["Lock_PID"] = ""
    save_raw_config(FILE_INFO["config"]["path"], raw_config)


def grab_lock(raw: Dict[str, object]) -> Path:
    # creat a lock file with the PID of the current process
    path = FILE_INFO["lock"]["path"]
    pid = str(getpid())
    path.write_text(pid, encoding="utf-8") # Creates file and writes in it
    raw["Lock"] = str(path)
    raw["Lock_PID"] = pid
    save_raw_config(FILE_INFO["config"]["path"], raw)
    return path


def drop_lock(raw: Dict[str, object], path: Path) -> None:
    if path.exists():
        path.unlink()
    raw["Lock"] = ""
    raw["Lock_PID"] = ""
    save_raw_config(FILE_INFO["config"]["path"], raw)


def should_skip_file(path: Path, config: Dict[str, object]) -> bool:
    ignore_names = config["ignore_names"]
    ignore_types = config["ignore_types"]
    return path.stem in ignore_names or path.suffix.lower().lstrip(".") in ignore_types # Return bool value based on file name or extension


def extension_folder(extension: str) -> str:
    return f".{extension}_Files" if extension else "no_extension_Files"


def date_folder(base: Path, path: Path) -> Path:
    stats = path.stat()
    if hasattr(stats, "st_birthtime"):
        created_timestamp = stats.st_birthtime
    else:
        created_timestamp = stats.st_mtime
    created = localtime(created_timestamp)
    return base / f"{created.tm_year}" / f"{created.tm_mon:02d}_{created.tm_year}"


def plan_moves(config: Dict[str, object]) -> Tuple[List[Tuple[Path, Path]], Set[Path]]:
    moves: List[Tuple[Path, Path]] = []
    folders: Set[Path] = set()
    target_dir = config["target_dir"]
    sorted_dir = config["sorted_dir"]
    sort_type = config["sort_type"]
    for entry in target_dir.rglob("*"):
        if not entry.is_file():
            continue
        if should_skip_file(entry, config):
            continue
        if sort_type == "File-Extension":
            folder = sorted_dir / extension_folder(entry.suffix.lower().lstrip("."))
        else:
            folder = date_folder(sorted_dir, entry)
        folders.add(folder)
        moves.append((entry, folder / entry.name))
    return moves, folders


def show_plan(moves: List[Tuple[Path, Path]], folders: Set[Path]) -> None:
    if not moves:
        print("Dry run: nothing needs to move.")
        return
    print("Dry run plan:")
    for folder in sorted(folders, key=str):
        print(f"  make sure this folder exists: {folder}")
    for source, target in moves:
        print(f"  {source} -> {target}")


def confirm_plan() -> bool:
    answer = input("Run these moves now? [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def run_moves(moves: List[Tuple[Path, Path]], mode: str, quiet: bool) -> None:
    for source, target in moves:
        if not source.exists(): # skip if file gone
            say(f"Skipping {source}: file no longer exists", quiet)
            continue
        
        target_dir = target.parent
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            if mode == "Copy":
                copy2(str(source), str(target))
                say(f"Copied {source.name} to {target}", quiet)
            else:
                move(str(source), str(target))
                say(f"Moved {source.name} to {target}", quiet)
        except PermissionError as error:
            say(f"Skipping {source}: permission problem ({error})")
            try:
                if target_dir.exists() and not any(target_dir.iterdir()):
                    target_dir.rmdir() # remove empty dir if move failed
            except OSError:
                pass
        except OSError as error: # incase file is in use or moved befor the script (general os error)
            say(f"Skipping {source}: {error}")
            try:
                if target_dir.exists() and not any(target_dir.iterdir()):
                    target_dir.rmdir() # remove empty dir if move failed
            except OSError:
                pass


def delete_empty_dirs(target_dir: Path, quiet: bool) -> None:
    deleted_count = 0
    all_dirs = []
    for root, dirs, files in target_dir.walk():
        all_dirs.append(Path(root))
    all_dirs.sort(key=lambda p: len(p.parts), reverse=True) # deepest first
    
    for dir_path in all_dirs:
        if dir_path == target_dir:
            continue
        try:
            has_files = any(item.is_file() for item in dir_path.iterdir())
            if not has_files:
                items = list(dir_path.iterdir())
                if not items:
                    dir_path.rmdir()
                    say(f"Deleted empty directory: {dir_path}", quiet)
                    deleted_count += 1
        except PermissionError as error:
            say(f"Skipping {dir_path}: permission problem ({error})", quiet)
        except OSError as error:
            say(f"Skipping {dir_path}: {error}", quiet)
    
    if deleted_count > 0:
        say(f"Deleted {deleted_count} empty director{'y' if deleted_count == 1 else 'ies'}.", quiet)


def freeze_loop(quiet: bool) -> None:
    say("Freeze mode: sleeping until you press CTRL+C.", quiet)
    try:
        while True:
            sleep(300.0)
    except KeyboardInterrupt:
        say("Freeze ended by user.", quiet)


def configure_interactively(path: Path) -> None:
    if not path.exists():
        # tell the user to download deafult cfg from repo and also where it should be
        print(f"Config file not found: {path}")
        print("Download the config file from the repo before running configure mode.")
        return
    data = load_raw_config(path)
    fields = ["Target_Dir", "Sorted_Dir", "Sort_Type", "Sort_Mode", "Delete_Empty_Dirs", "Ignore_Names", "Ignore_Types"]

    while True:
        system("cls")
        print("Interactive config editor (names without extensions, types without dots)")
        print("Press Enter without typing anything to save and exit.\n")

        while True:
            for index, field in enumerate(fields, start=1):
                print(f"{index}. {field}: {data.get(field)}")
            choice = input("Pick a number to edit (Enter to finish): ").strip()
            if not choice:  # break on empty input
                break
            if not choice.isdigit() or not 1 <= int(choice) <= len(fields):  # check if choice is a number and within range
                input("Please choose a valid number. Press Enter to continue.")
                continue
            field = fields[int(choice) - 1]  # account for 0 index
            if field in {"Ignore_Names", "Ignore_Types"}:
                print("Enter comma-separated values (e.g. item1, item2, item3). Leave blank to clear.")
            if field == "Sort_Type":
                print("Options: File-Extension or Date-Created.") # the options for that field
            if field == "Sort_Mode":
                print("Options: Move or Copy.") # the options for that field
            if field == "Delete_Empty_Dirs":
                print("Options: true/false, yes/no, or 1/0.")
            new_value = input(f"New value for {field}: ").strip()
            if field in {"Sort_Type", "Sort_Mode"}:
                new_value = new_value.title().replace(" ", "-")  # capitalize and replace spaces with dashes
            if field == "Delete_Empty_Dirs":
                new_value_lower = new_value.lower()
                if new_value_lower in {"true", "yes", "1", "y"}:
                    data[field] = True
                elif new_value_lower in {"false", "no", "0", "n", ""}:
                    data[field] = False
                else:
                    print(f"Invalid value '{new_value}'. Setting to False.")
                    data[field] = False
                    input("Press Enter to continue.")
            elif field in {"Ignore_Names", "Ignore_Types"}:
                data[field] = [item.strip() for item in new_value.split(",") if item.strip()]
            else:
                data[field] = new_value
            
            system("cls")  # Clear screen after editing before showing menu again

        if validate_config(data, abort_on_error=False) is None:
            print("Config not saved: fix the issues above.")
            input("Press Enter to return to the editor.")
            continue

        save_raw_config(path, data)
        print("Config saved. Run the sorter when you are ready!")
        break


def run(flags: Dict[str, bool]) -> None:
    if flags["configure"]: # if configure is True in dict flags
        configure_interactively(FILE_INFO["config"]["path"])
        return

    require_config_file(FILE_INFO["config"]["path"]) # verify cfg exists if not exit in func

    raw = load_raw_config(FILE_INFO["config"]["path"]) # raw is mutable dict 
    config = validate_config(raw) # verify no errors during validation of cfg
    if config is None:
        print("Run 'python WIN_Dir_Sorter.py -c' to fix the config interactively.")
        exit(1)

    check_lock(config, flags["quiet"])
    current_lock = grab_lock(raw)
    try:
        if flags["freeze"]:
            freeze_loop(flags["quiet"])
            return

        moves, folders = plan_moves(config)
        sort_mode = config["sort_mode"]
        if flags["dry_run"]:
            show_plan(moves, folders)
            if moves and confirm_plan():
                run_moves(moves, sort_mode, flags["quiet"])
                if config.get("delete_empty_dirs", False) and sort_mode == "Move":
                    delete_empty_dirs(config["target_dir"], flags["quiet"])
            else:
                say("Dry run only. No files were touched.", flags["quiet"])
            return

        if not moves:
            say("All caught up. Nothing to move.", flags["quiet"])
            return

        run_moves(moves, sort_mode, flags["quiet"])
        if config.get("delete_empty_dirs", False) and sort_mode == "Move":
            delete_empty_dirs(config["target_dir"], flags["quiet"])
    finally:
        drop_lock(raw, current_lock)


def main() -> None:
    run(parse_cli_args())


if __name__ == "__main__":
    main()
 