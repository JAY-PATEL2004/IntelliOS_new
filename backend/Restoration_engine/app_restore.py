#!/usr/bin/env python3

import os
import subprocess
import time
import sys
import win32gui
import win32con
import win32process

def restore_app_files(exe, items, name, window_info=None):
    """Restore applications and their associated files"""
    if not exe or not os.path.exists(exe):
        # Try just the process name if exe missing
        exe = name
    
    if not items or len(items) == 0:
        # If no files, just open the app
        try:
            subprocess.Popen([exe])
            return
        except Exception as e:
            print(f"Error launching {name}: {str(e)}", file=sys.stderr)
            return

    # Some apps prefer one process with multiple args (Word/Excel), others prefer separate instances
    one_shot_apps = ["WINWORD.EXE", "EXCEL.EXE", "POWERPNT.EXE", "Acrobat.exe", "AcroRd32.exe"]
    process = None
    try:
        if name in one_shot_apps:
            process = subprocess.Popen([exe] + items)
        else:
            for item in items:
                subprocess.Popen([exe, item])
                time.sleep(0.1)

        # Wait briefly for the window to appear
        time.sleep(1)
        
    except Exception as e:
        print(f"Error launching {name} with items: {str(e)}", file=sys.stderr)

def restore_apps(state):
    """Main function to restore all apps from state"""
    for app in state.get('apps', []):
        # Filter out non-existing files (moved/deleted)
        existing_items = [f for f in app.get('items', []) if os.path.exists(f)]
        restore_app_files(app.get('exe'), existing_items, app.get('name'), app.get('mainWindow'))