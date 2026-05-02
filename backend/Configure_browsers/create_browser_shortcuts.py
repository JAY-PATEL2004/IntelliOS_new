import os
import sys
from pathlib import Path
import win32com.client

# Path to your main launcher
LAUNCHER_PATH = os.path.dirname(os.path.abspath(__file__)) + "\\browser_launcher.py"
PYTHONW_PATH = sys.executable  # or hardcode path to pythonw.exe if preferred

# Define browser info
BROWSERS = {
    "chrome": {
        "name": "Google Chrome",
        "exe": r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        "profile_root": Path(os.getenv("LOCALAPPDATA")) / "Google" / "Chrome" / "User Data"
    },
    "msedge": {
        "name": "Microsoft Edge",
        "exe": r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
        "profile_root": Path(os.getenv("LOCALAPPDATA")) / "Microsoft" / "Edge" / "User Data"
    }
}

DESKTOP = Path(os.path.join(os.environ["USERPROFILE"], "OneDrive", "Desktop"))

def create_shortcut(shortcut_path, target, args, icon_path, working_dir=None):
    """Create a Windows .lnk shortcut."""
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.TargetPath = target
    shortcut.Arguments = args
    shortcut.IconLocation = icon_path
    if working_dir:
        shortcut.WorkingDirectory = working_dir
    shortcut.Save()

def detect_profiles(profile_root):
    """Detect available browser profiles (Default, Profile 1, etc.)."""
    if not profile_root.exists():
        return []
    profiles = []
    for entry in profile_root.iterdir():
        if entry.is_dir() and (entry.name == "Default" or entry.name.startswith("Profile")):
            profiles.append(entry)
    return profiles

def create_browser_shortcuts():
    for browser_key, info in BROWSERS.items():
        exe_path = info["exe"]
        profile_root = info["profile_root"]
        browser_name = info["name"]

        if not os.path.exists(exe_path):
            print(f"⚠️ {browser_name} not found, skipping.")
            continue

        profiles = detect_profiles(profile_root)
        if not profiles:
            print(f"❌ No profiles found for {browser_name}.")
            continue

        for profile_dir in profiles:
            profile_name = profile_dir.name
            shortcut_name = f"{browser_name} - {profile_name} (Debug).lnk"
            shortcut_path = DESKTOP / shortcut_name

            args = f"\"{LAUNCHER_PATH}\" {browser_key} \"{profile_dir}\""

            create_shortcut(
                shortcut_path=shortcut_path,
                target=PYTHONW_PATH,
                args=args,
                icon_path=exe_path,
                working_dir=str(Path(LAUNCHER_PATH).parent)
            )

            print(f"✅ Shortcut created: {shortcut_name}")

    print("\n🎉 All shortcuts created successfully on your Desktop!")
