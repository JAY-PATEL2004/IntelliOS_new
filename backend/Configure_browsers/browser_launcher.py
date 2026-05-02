import subprocess
import json
import os
import sys
from pathlib import Path
import psutil
import socket
import shutil
from datetime import datetime, timezone, timedelta

# Constants
BASE_PORT = 9222
MAX_PORT = 9300
PORTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "State", "browser_ports.json")
PROFILE_COPIES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile_copies")
SUPPORTED_BROWSERS = {
    'chrome': {
        'windows': r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        'darwin': '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        'linux': 'google-chrome'
    },
    'edge': {
        'windows': r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
        'darwin': '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
        'linux': 'microsoft-edge'
    }
}

def load_port_data():
    """Load existing port assignments from the JSON file."""
    try:
        if os.path.exists(PORTS_FILE):
            with open(PORTS_FILE, 'r') as f:
                return json.load(f)
        return {"browsers": {}}
    except json.JSONDecodeError:
        print(f"Error: Corrupted {PORTS_FILE} file. Creating new one.")
        return {"browsers": {}}

def save_port_data(data):
    """Save port assignments to the JSON file."""
    try:
        with open(PORTS_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving port data: {e}")

def find_next_available_port(port_data):
    """Find the next available debugging port."""
    used_ports = set()
    for browser_info in port_data["browsers"].values():
        used_ports.update(int(port) for port in browser_info["ports"])
    
    port = BASE_DEBUG_PORT
    while port in used_ports:
        port += 1
    return port

def is_port_in_use(port):
    """Check if a port is already in use."""
    for proc in psutil.process_iter(['connections']):
        try:
            for conn in proc.connections():
                if conn.laddr.port == port:
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

def find_free_port(start_port=BASE_PORT, end_port=MAX_PORT):
    """Find the next available TCP port."""
    for port in range(start_port, end_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) != 0:
                return port
    raise RuntimeError("No free port found in range.")

def is_profile_in_use(profile_path):
    """Check if a browser profile is currently in use."""
    if not profile_path:
        return False
        
    # Create the profile directory if it doesn't exist
    os.makedirs(profile_path, exist_ok=True)
    
    try:
        lock_file = os.path.join(profile_path, "Lock")
        if os.path.exists(lock_file):
            try:
                # Try to delete the lock file - if we can, profile isn't truly locked
                os.remove(lock_file)
                return False
            except (PermissionError, OSError):
                # If we can't delete it, profile is in use
                return True
        
        # Check for running browser processes using this profile
        for proc in psutil.process_iter(['cmdline']):
            try:
                cmdline = proc.cmdline()
                if any(profile_path.lower() in arg.lower() for arg in cmdline if isinstance(arg, str)):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                continue
    except Exception as e:
        print(f"Error checking profile usage: {str(e)}")
        return False
    
    return False

def create_profile_copy(original_profile):
    """Create a copy of the browser profile with a new name."""
    if not original_profile:
        return None
    
    try:
        # Create timestamp-based profile name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        profile_name = f"profile_copy_{timestamp}"
        new_profile_path = os.path.join(PROFILE_COPIES_DIR, profile_name)
        
        # Create the copies directory if it doesn't exist
        os.makedirs(PROFILE_COPIES_DIR, exist_ok=True)
        
        # Create the basic profile structure
        print(f"Creating new profile at {new_profile_path}")
        os.makedirs(new_profile_path, exist_ok=True)
        os.makedirs(os.path.join(new_profile_path, "Default"), exist_ok=True)
        
        # If original profile exists, try to copy essential files
        if os.path.exists(original_profile):
            # List of essential directories to copy
            essential_dirs = [
                "Default/Bookmarks",
                "Default/Preferences",
                "Default/Favicons",
                "Default/History",
                "Default/Login Data",
                "Default/Web Data"
            ]
            
            for item in essential_dirs:
                src = os.path.join(original_profile, item)
                dst = os.path.join(new_profile_path, item)
                dst_dir = os.path.dirname(dst)
                
                if os.path.exists(src):
                    try:
                        # Ensure the destination directory exists
                        os.makedirs(dst_dir, exist_ok=True)
                        # Try to copy the file
                        if os.path.isfile(src):
                            shutil.copy2(src, dst)
                    except (PermissionError, OSError) as e:
                        print(f"Warning: Could not copy {item}: {str(e)}")
                        continue
        
        return new_profile_path
    except Exception as e:
        print(f"Warning: Error while creating profile copy: {str(e)}")
        # Even if we hit some errors, return the new profile path if it was created
        if os.path.exists(new_profile_path):
            return new_profile_path
        return None

def launch_browser(browser_name, profile_name):
    """Launch browser with remote debugging enabled for the specified profile."""
    browser_name = browser_name.lower()
    
    # Validate browser
    if browser_name not in SUPPORTED_BROWSERS:
        print(f"Error: Unsupported browser '{browser_name}'. Supported browsers: {', '.join(SUPPORTED_BROWSERS.keys())}")
        return False

    # Get browser path based on OS
    platform = sys.platform
    if platform.startswith('win'):
        platform = 'windows'
    elif platform.startswith('darwin'):
        platform = 'darwin'
    else:
        platform = 'linux'

    browser_path = SUPPORTED_BROWSERS[browser_name][platform]
    
    # # Load existing port data
    # port_data = load_port_data()
    # if "browsers" not in port_data:
    #     port_data["browsers"] = {}

    # # Initialize browser data if not exists
    # browser_key = f"{browser_name}_{profile_name}"
    # if browser_key not in port_data["browsers"]:
    #     port_data["browsers"][browser_key] = {"ports": []}

    # # Find next available port
    # debug_port = find_next_available_port(port_data)
    
    # # Verify port is not in use
    # while is_port_in_use(debug_port):
    #     debug_port += 1
    debug_port = find_free_port()
    if is_profile_in_use(profile_name):
        profile_name = create_profile_copy(profile_name)

    try:
        # Prepare command line arguments
        args = [
            browser_path,
            f"--remote-debugging-port={debug_port}",
            f"--user-data-dir={profile_name}",
            "--no-first-run",
            "--no-default-browser-check"
        ]

        # Launch browser
        subprocess.Popen(args)
        
        # === Update port data ===
        try:
            with open(PORTS_FILE, 'r', encoding='utf-8') as f:
                browser_ports_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            browser_ports_data = {}

        # Ensure browser section exists
        if browser_name not in browser_ports_data:
            browser_ports_data[browser_name] = {
                "exe": browser_path,
                "profiles": []
            }

        # Ensure profiles array exists
        profiles_list = browser_ports_data[browser_name].get("profiles", [])

        # Mark any existing instances with same debug_port as inactive
        for profile_entry in profiles_list:
            for inst in profile_entry.get("instances", []):
                if str(inst.get("port")) == str(debug_port):
                    inst["status"] = "inactive"

        # Find the current profile entry (or create it)
        profile_entry = next(
            (p for p in profiles_list if p.get("profile") == profile_name),
            None
        )

        if not profile_entry:
            profile_entry = {"profile": profile_name, "instances": []}
            profiles_list.append(profile_entry)

        # Add the new instance data
        profile_entry["instances"].append({
            "port": str(debug_port),
            "launched_at": datetime.now(tz=timezone(timedelta(hours=5, minutes=30))).isoformat(timespec='seconds'),
            "status": "active"
        })

        # Save back to JSON
        browser_ports_data[browser_name]["profiles"] = profiles_list
        with open(PORTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(browser_ports_data, f, indent=4)
        

        # port_data["browsers"][browser_key]["ports"].append(str(debug_port))
        # save_port_data(port_data)
        
        print(f"Successfully launched {browser_name} with profile '{profile_name}' on debug port {debug_port}")
        return True

    except FileNotFoundError:
        print(f"Error: Browser executable not found at {browser_path}")
    except Exception as e:
        print(f"Error launching browser: {e}")
    return False

def main():
    if len(sys.argv) != 3:
        print("Usage: python browser_launcher.py <browser_name> <profile_name>")
        print("Supported browsers:", ", ".join(SUPPORTED_BROWSERS.keys()))
        sys.exit(1)

    browser_name = sys.argv[1]
    profile_name = sys.argv[2]
    
    launch_browser(browser_name, profile_name)

if __name__ == "__main__":
    main()