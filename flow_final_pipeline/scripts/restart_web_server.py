# -*- coding: utf-8 -*-
import os
import sys
import glob
import time
import subprocess
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORKSPACE = r"c:\Users\ADMIN\Desktop\Python\Veo 3 Tool\AutoVeo3Pro_v6\Auto_Veo_3_Pro\Grok\Skill Video Veo"
FINAL_VIDEOS_DIR = os.path.join(WORKSPACE, "final_videos")
PROJECTS_DIR = os.path.join(WORKSPACE, "projects")

# 1. Kill old process listening on port 8456
out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
pids_to_kill = set()
for line in out.splitlines():
    if ":8456" in line and "LISTENING" in line:
        parts = line.split()
        if parts:
            pids_to_kill.add(parts[-1])

for kpid in pids_to_kill:
    if kpid.isdigit() and int(kpid) > 0:
        print(f"Stopping old server process PID {kpid} on port 8456...")
        subprocess.run(["taskkill", "/F", "/PID", kpid], capture_output=True)

time.sleep(1.0)

# 2. Remove any leftover *-final-30s.mp4 in projects/<pid>/
for leftover in glob.glob(os.path.join(PROJECTS_DIR, "*", "*-final-30s.mp4")):
    try:
        os.remove(leftover)
        print(f"Removed leftover duplicate: {leftover}")
    except OSError as e:
        print(f"Warn removing {leftover}: {e}")

# 3. Sync Web UI state
sys.path.insert(0, os.path.join(WORKSPACE, "flow_final_pipeline", "scripts"))
from sync_web_ui_state import sync_web_ui
sync_web_ui(force=True)

# 4. Start fresh server.py --no-browser in background
server_py = os.path.join(WORKSPACE, "server.py")
subprocess.Popen(
    [sys.executable, server_py, "--no-browser"],
    cwd=WORKSPACE,
    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
)
time.sleep(1.5)

# 5. Verify /api/status and open final_videos folder via /api/open-folder
try:
    with urllib.request.urlopen("http://127.0.0.1:8456/api/status", timeout=5) as r:
        print("Server /api/status HTTP:", r.status)
    req = urllib.request.Request(
        "http://127.0.0.1:8456/api/open-folder",
        data=b'{"path":"final_videos"}',
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as r2:
        print("Opened final_videos folder:", r2.read().decode("utf-8", errors="replace"))
except Exception as e:
    print("Verify err:", e)

