#!/usr/bin/env python3

import os
import subprocess
import time
import sys
import psutil
import shutil
from datetime import datetime
import socket

# Directory to store profile copies
BASE_PORT = 9222
MAX_PORT = 9300
PROFILE_COPIES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile_copies")

# Default browser paths
EXE_PATHS = {
    "chrome": "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "msedge": "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "opera": "C:\\Users\\jaypa\\AppData\\Local\\Programs\\Opera\\opera.exe"
}

def is_port_in_use(port):
    """Check if a port is already in use."""
    if not port:
        return False
    try:
        port = int(port)
        for proc in psutil.process_iter(['connections']):
            try:
                for conn in proc.connections():
                    if conn.laddr.port == port:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except (ValueError, TypeError):
        return False
    return False

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

def find_free_port(start_port=BASE_PORT, end_port=MAX_PORT):
    """Find the next available TCP port."""
    for port in range(start_port, end_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) != 0:
                return port
    raise RuntimeError("No free port found in range.")

def restore_browser(browser, windows, exe):
    """Restore browser windows and their tabs"""
    print(exe)
    if not windows or len(windows) == 0:
        return

    # Open each window as a separate browser window and pass URLs
    for window in windows:
        urls = []
        for tab in window['tabs']:
            if (tab.get('url') and 
                any(tab['url'].startswith(prefix) for prefix in ['https://', 'http://', 'file://', 'chrome://', 'edge://']) and
                not any(tab.get('title', '').startswith(prefix) for prefix in ['https://', 'http://'])):
                urls.append(tab['url'])
        
        if len(urls) == 0:
            continue
        
        # Check if debugging port is in use
        debugging_port = window.get('debuggingPort')
        if debugging_port is None:
            debugging_port = find_free_port()
        if is_port_in_use(debugging_port):
            print(f"Error: Debugging port {debugging_port} is already in use", file=sys.stderr)
            continue
            
        # Handle profile path
        original_profile = window.get('profile')
        profile_path = original_profile
        
        print(f"Checking profile: {original_profile}")
        if original_profile:
            if is_profile_in_use(original_profile):
                print(f"Profile {original_profile} is in use, creating a copy...")
                new_profile = create_profile_copy(original_profile)
                if new_profile:
                    profile_path = new_profile
                    print(f"Successfully created new profile copy at: {profile_path}")
                else:
                    print(f"Error: Could not create profile copy for {original_profile}", file=sys.stderr)
                    continue
            else:
                print(f"Profile {original_profile} is not in use, using it directly")
        
        # Start a new window with multiple tabs
        try:
            args = [
                exe,
                f"--remote-debugging-port={debugging_port}",
                f"--user-data-dir={profile_path}",
                "--args",
                "--new-window",
                "--no-first-run",
                "--no-default-browser-check",
            ]
            subprocess.Popen(args + urls)
            time.sleep(0.3)
        except Exception as e:
            print(f"Error launching {browser}: {str(e)}", file=sys.stderr)

def restore_browsers(state):
    """Main function to restore all browsers from state"""
    for browser in state.get('browsers', []):
        exe = browser.get('exe')
        if exe in [None, ""]:
            if not browser.get('browser') in EXE_PATHS.keys():
                print("Can't find the executable path for ", browser.get('browser'))
                continue
            else:
                exe = EXE_PATHS.get(browser.get('browser'))
        
        restore_browser(browser.get('browser'), browser.get('windows', []), exe)