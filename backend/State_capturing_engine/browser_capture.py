"""
browser_capture.py - Module for capturing browser states
"""
import os
import json
import requests
from datetime import datetime, timezone, timedelta
# requires: pip install websocket-client
import time
# from websocket import create_connection
import subprocess
import pychrome

IST = timezone(timedelta(hours=5, minutes=30))

# def _safe_recv_loop(self):
#     try:
#         while self._ws:
#             message_json = self._ws.recv()
#             if not message_json:  # Empty message received
#                 continue
#             try:
#                 message = json.loads(message_json)
#             except json.JSONDecodeError:
#                 print("[WARN] Received malformed or empty message, ignoring...")
#                 continue
#             self._handle_message(message)
#     except Exception as e:
#         print(f"[ERROR] WebSocket loop ended: {e}")

# pychrome.tab.Tab._recv_loop = _safe_recv_loop

def get_tab_launch_time(base_url, ws_url):
    """
    Connects to a Chrome tab using pychrome and retrieves performance.timeOrigin.
    Returns ISO timestamp string (UTC) or None.
    """

    try:
        # Connect to the specific tab via its WebSocketDebuggerUrl
        browser = pychrome.Browser(url=base_url)
        tab_id = ws_url.split("/")[-1]
        tabs = browser.list_tab()
        tab = None
        for i in tabs:
            if i.id==tab_id:
                tab = i

        # tab = pychrome.Tab(browser=None)
        # tab._wsurl = ws_url  # manually set the websocket
        # if tab is None:
        #     print(f"[WARN] Tab with ID {tab_id} not found.")
        #     return None
        tab.start()
        tab.Runtime.enable()

        # Evaluate JavaScript expression
        result = tab.Runtime.evaluate(
            expression="performance.timeOrigin", returnByValue=True
        )

        tab.stop()
        val = result.get("result", {}).get("value")
        if val is not None:
            dt = datetime.fromtimestamp(val / 1000.0, tz=IST)
            print(f"[SUCCESS] Launch time found: {dt.isoformat(timespec='seconds')}")
            return dt.isoformat()
        else:
            print("[WARN] performance.timeOrigin returned None or undefined.")
            return None

    except Exception as e:
        print(f"[ERROR] Failed to get timeOrigin: {e}")
        return None

# def get_tab_launch_time(ws_url, timeout=5.0):
#     """
#     Connects to a single tab via WebSocket and retrieves performance.timeOrigin.
#     Returns an ISO timestamp string (UTC) or None on failure.
#     """
#     if not ws_url:
#         print("[ERROR] WebSocket URL is empty or invalid")
#         return None
        
#     print(f"\n[INFO] Connecting to WebSocket: {ws_url}")
#     try:
#         # Add additional headers that might be required for authentication
#         headers = {
#             "Origin": "http://localhost",
#             "Pragma": "no-cache",
#             "Cache-Control": "no-cache"
#         }
#         ws = create_connection(ws_url, timeout=timeout, header=["Origin: http://localhost"])
#         print("[DEBUG] WebSocket connection established.")

#         # Enable Runtime domain
#         ws.send(json.dumps({"id": 1, "method": "Runtime.enable"}))
#         print("[DEBUG] Sent Runtime.enable command.")
#         time.sleep(0.5)  # wait briefly for the context to initialize

#         # Evaluate JS expression
#         request = {
#             "id": 2,
#             "method": "Runtime.evaluate",
#             "params": {
#                 "expression": "performance.timeOrigin",
#                 "returnByValue": True
#             }
#         }
#         ws.send(json.dumps(request))
#         print("[DEBUG] Sent Runtime.evaluate command for performance.timeOrigin.")

#         # Wait for result
#         while True:
#             msg = ws.recv()
#             data = json.loads(msg)
#             # Uncomment for detailed debugging:
#             # print("[RAW MESSAGE]", json.dumps(data, indent=2))

#             if data.get("id") == 2:
#                 val = data.get("result", {}).get("result", {}).get("value")
#                 if val is not None:
#                     ts = float(val)
#                     dt = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc)
#                     print(f"[SUCCESS] Launch time found: {dt.isoformat()}")
#                     return dt.isoformat()
#                 else:
#                     print("[WARN] performance.timeOrigin returned None or undefined.")
#                     return None

#     except Exception as e:
#         print(f"[ERROR] Failed to get timeOrigin: {e}")
#         return None
#     finally:
#         try:
#             ws.close()
#             print("[DEBUG] WebSocket connection closed.")
#         except Exception:
#             pass

# def get_tab_launch_time(ws_url):
#     print(f"[INFO] Using WebSocket URL: {ws_url}")
#     try:
#         # JSON command to send to CDP
#         cmd = '{"id":1,"method":"Runtime.evaluate","params":{"expression":"performance.timeOrigin","returnByValue":true}}'
#         WSCAT_PATH = r"C:\\Users\\jaypa\AppData\\Roaming\\npm\\wscat.cmd"

#         # Run wscat in non-interactive mode and capture output
#         process = subprocess.Popen(
#             [WSCAT_PATH, "-c", ws_url],
#             stdin=subprocess.PIPE,
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             text=True
#         )

#         # Send the command to stdin and close it (forces wscat to exit after response)
#         out, err = process.communicate(input=cmd, timeout=8)

#         if err:
#             print(f"[DEBUG] stderr: {err.strip()}")
#         if not out.strip():
#             print("[ERROR] No output received from wscat.")
#             return None

#         print(f"[DEBUG] Raw wscat output:\n{out.strip()}")

#         # Parse JSON line containing "value"
#         for line in out.splitlines():
#             if '"value"' in line:
#                 try:
#                     data = json.loads(line.strip())
#                     val = data["result"]["result"]["value"]
#                     ts = float(val) / 1000.0
#                     iso_time = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
#                     print(f"[SUCCESS] Launch time (UTC): {iso_time}")
#                     return iso_time
#                 except Exception as e:
#                     print(f"[WARN] Failed to parse JSON: {e}")
#                     print(f"[DEBUG] Problematic line: {line}")

#         print("[WARN] Could not extract performance.timeOrigin value from response.")
#         return None

#     except subprocess.TimeoutExpired:
#         print("[ERROR] wscat timed out waiting for response.")
#     except Exception as e:
#         print(f"[ERROR] Exception while running wscat: {e}")


def get_devtools_tabs(base_url, last_captured):
    """Get tabs information from browser's devtools API"""
    try:

        resp = requests.get(f"{base_url}/json", timeout=1)
        tabs = resp.json()
        formatted_tabs = []
        # browser = pychrome.Browser(url=base_url)
        for tab in tabs:
            if (tab.get('url') and 
                any(tab['url'].startswith(prefix) for prefix in ['https://', 'http://', 'file://', 'chrome://', 'edge://']) and
                not any(tab.get('title', '').startswith(prefix) for prefix in ['https://', 'http://']) and tab.get('type') == 'page'):
                launch_time = get_tab_launch_time(base_url, tab.get("webSocketDebuggerUrl"))
                if not (launch_time>last_captured):
                    continue
                formatted_tabs.append({
                    "id": tab.get("id"),
                    "url": tab.get("url"),
                    "title": tab.get("title"),
                    "description": tab.get("description", ""),
                    "tab_launched_at": launch_time
                })
        return formatted_tabs
    except Exception:
        return []



def capture_browser_states(browser_data, last_captured):
    print("Last Captured at",last_captured)
    """Capture states of all browsers.

    If the environment variable `LAST_CAPTURED` is set (ISO or epoch), only
    instances with `launched_at` > LAST_CAPTURED will be included. If
    `launched_at` is missing for an instance, it will be included.
    """



    browsers = []

    # Process all browser types
    for browser_name, browser_info in browser_data.items():
        browser_windows = []
        browser_exe = browser_info.get("exe")

        # Process all profiles for this browser
        for profile_info in browser_info.get("profiles", []):
            # Handle both profile name formats
            profile_path = profile_info.get("profile")
            if not profile_path:
                continue

            # Process all instances of this profile
            for instance in profile_info.get("instances", []):
                if instance.get("status") != "active":
                    continue

                launched_at_raw = instance.get("launched_at")

                # If LAST_CAPTURED is set and we have a launched_at, include only newer instances

                port = instance.get("port")
                try:
                    port_int = int(port)
                except Exception:
                    port_int = None

                tabs = get_devtools_tabs(f"http://localhost:{port_int}", last_captured) if port_int else []

                if tabs:
                    window = {
                        "profile": profile_path,
                        "debuggingPort": int(port_int) if port_int else None,
                        "tabs": tabs,
                        "window_launched_at": launched_at_raw
                    }
                    browser_windows.append(window)

        # Add browser to list if it has active windows
        if browser_windows:
            browsers.append({
                "browser": browser_name,
                "exe": browser_exe,
                "windows": browser_windows
            })

    return browsers

# if __name__ == "__main__":
#     print(os.environ.get('LAST_CAPTURED'))
#     get_tab_launch_time("http://localhost:9222","ws://localhost:9222/devtools/page/BECE40E16C0D9B0461032448CDF2CB6B")
get_tab_launch_time("http://localhost:9223","ws://localhost:9223/devtools/page/62EBBB6DDB54320069BE19F3C518591A")