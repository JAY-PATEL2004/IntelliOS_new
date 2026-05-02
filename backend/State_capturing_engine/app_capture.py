"""
app_capture.py - Module for capturing application states
"""
import json
import os
import psutil
import win32com.client
import pythoncom
import win32process
import win32gui
import urllib.parse
import pathlib

VSCODE_DATADIR = os.path.join(r"C:\Users", os.environ.get("USERNAME", ""), r"AppData\Roaming\Code\User\globalStorage\storage.json")

def get_main_window_info(pid):
    """Get window information for a process"""
    def callback(hwnd, window_info):
        try:
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
            if found_pid == pid and win32gui.IsWindowVisible(hwnd):
                # Get window title
                title = win32gui.GetWindowText(hwnd)
                
                # Get window rect (position and size)
                rect = win32gui.GetWindowRect(hwnd)
                left, top, right, bottom = rect
                
                # Get window state
                style = win32gui.GetWindowLong(hwnd, -16)  # GWL_STYLE
                state = "minimized" if style & 0x20000000 else "maximized" if style & 0x01000000 else "normal"
                
                window_info.append({
                    "title": title,
                    "position": {
                        "x": left,
                        "y": top
                    },
                    "size": {
                        "width": right - left,
                        "height": bottom - top
                    },
                    "state": state
                })
        except Exception:
            pass
        return True
    
    window_info = []
    win32gui.EnumWindows(lambda hwnd, _: callback(hwnd, window_info), None)
    return window_info[0] if window_info else None

def get_word_docs():
    try:
        pythoncom.CoInitialize()
        try:
            word = win32com.client.GetActiveObject("Word.Application")
            return [doc.FullName for doc in word.Documents]
        finally:
            pythoncom.CoUninitialize()
    except Exception:
        return []

def get_excel_books():
    try:
        print("Getting Excel books")
        pythoncom.CoInitialize()
        try:
            xl = win32com.client.GetActiveObject("Excel.Application")
            print("Workbooks :", xl.Workbooks)
            return [wb.FullName for wb in xl.Workbooks]
        finally:
            pythoncom.CoUninitialize()
    except Exception as e:
        print("Error :", str(e))
        return []

def get_powerpoint_pres():
    try:
        pythoncom.CoInitialize()
        try:
            pp = win32com.client.GetActiveObject("PowerPoint.Application")
            return [pres.FullName for pres in pp.Presentations]
        finally:
            pythoncom.CoUninitialize()
    except Exception:
        return []
    
def get_visio_drawings():
    try:
        pythoncom.CoInitialize()
        try:
            visio = win32com.client.GetActiveObject("Visio.Application")
            return [doc.FullName for doc in visio.Documents]
        finally:
            pythoncom.CoUninitialize()
    except Exception:
        return []

def get_publisher_docs():
    try:
        pythoncom.CoInitialize()
        try:
            pub = win32com.client.GetActiveObject("Publisher.Application")
            return [doc.FullName for doc in pub.Documents]
        finally:
            pythoncom.CoUninitialize()
    except Exception:
        return []

def get_project_files():
    try:
        pythoncom.CoInitialize()
        try:
            proj = win32com.client.GetActiveObject("MSProject.Application")
            return [proj.FullName for proj in proj.Projects]
        finally:
            pythoncom.CoUninitialize()
    except Exception:
        return []

def get_access_dbs():
    try:
        pythoncom.CoInitialize()
        try:
            access = win32com.client.GetActiveObject("Access.Application")
            return [access.CurrentProject.FullName] if access.CurrentProject else []
        finally:
            pythoncom.CoUninitialize()
    except Exception:
        return []

def get_onenote_files():
    try:
        pythoncom.CoInitialize()
        try:
            onenote = win32com.client.GetActiveObject("OneNote.Application")
            hierarchy = onenote.GetHierarchy("", 3)  # 3 = hsPages
            return [page.Path for page in hierarchy.PageNodes]
        finally:
            pythoncom.CoUninitialize()
    except Exception:
        return []
    
def get_vscode_workspaces():
    try:
        data={}
        with open(VSCODE_DATADIR, 'r', encoding='utf-8') as f:
            data = json.load(f)
        workspaces = []
        data = data.get("windowsState")
        print("Loaded data : ",data)
        lastActiveWindow = str(urllib.parse.unquote(data.get("lastActiveWindow").get("folder")))[8:]
        print("Last active window folder : ",lastActiveWindow)
        workspaces.append(lastActiveWindow)
        for window in data.get("openedWindows", []):
            folder = str(urllib.parse.unquote(window.get("folder")))[8:]
            if folder:
                print("Found folder : ",folder)
                workspaces.append(folder)
        return workspaces


    except Exception as e:
        print("Error loading VSCode workspaces :", str(e))

def capture_app_states():
    """Capture states of all supported applications"""
    whitelist = [
        "WINWORD.EXE","EXCEL.EXE","POWERPNT.EXE","VISIO.EXE", "MSPUB.EXE",
        "MSACCESS.EXE","WINPROJ.EXE","ONENOTE.EXE","notepad.exe","notepad++.exe",
        "code.exe","Code.exe","devenv.exe","sublime_text.exe","Acrobat.exe",
        "AcroRd32.exe","vlc.exe","obs64.exe","photoshop.exe","idea64.exe","pycharm64.exe"
    ]

    handlers = {
        "WINWORD.EXE": get_word_docs,
        "EXCEL.EXE": get_excel_books,
        "POWERPNT.EXE": get_powerpoint_pres,
        "VISIO.EXE": get_visio_drawings,
        "MSPUB.EXE": get_publisher_docs,
        "MSACCESS.EXE": get_access_dbs,
        "WINPROJ.EXE": get_project_files,
        "ONENOTE.EXE": get_onenote_files,
        "Code.exe": get_vscode_workspaces
    }

    apps = []
    handled = set()
    for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
        name = proc.info['name']
        if name not in whitelist:
            continue
        
        if name in handlers.keys() and name not in handled:
            files = handlers[name]()
            apps.append({
                "name": name,
                "pid": proc.info['pid'],
                "exe": proc.info['exe'],
                "cmdline": ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else '',
                "items": list(set(files)),
                "windowInfo": get_main_window_info(proc.info['pid'])
            })
            handled.add(name)

    return sorted(apps, key=lambda x: x["name"])
# print(capture_app_states())