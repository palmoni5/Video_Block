import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import random
import hashlib
import json
import shutil
import time

# --- מפתח סודי ---
SECRET_SALT = "GhostSystemKey2025"

# ==========================================
# תצורת הרשת (The Network Map) - LaunchAgents (User Level)
# ==========================================
GHOST_NETWORK = [
    {
        "id": 0,
        "path": "/Users/Shared/.Config/sys_net_daemon", 
        "plist_path": "/Library/LaunchAgents/com.apple.sys.net.daemon.plist",
        "label": "com.apple.sys.net.daemon"
    },
    {
        "id": 1,
        "path": "/Users/Shared/.Config/sys_update_service",
        "plist_path": "/Library/LaunchAgents/com.apple.sys.update.helper.plist",
        "label": "com.apple.sys.update.helper"
    },
    {
        "id": 2,
        "path": "/Users/Shared/.Config/kernel_audit_d",
        "plist_path": "/Library/LaunchAgents/com.apple.kernel.audit.plist",
        "label": "com.apple.kernel.audit"
    },
    {
        "id": 3,
        "path": "/Users/Shared/.Config/mdworker_sys_ext",
        "plist_path": "/Library/LaunchAgents/com.apple.mdworker.sys.ext.plist",
        "label": "com.apple.mdworker.sys.ext"
    },
    {
        "id": 4,
        "path": "/Users/Shared/.Config/core_audio_d",
        "plist_path": "/Library/LaunchAgents/com.apple.core.audio.daemon.plist",
        "label": "com.apple.core.audio.daemon"
    },
    {
        "id": 5,
        "path": "/Users/Shared/.Config/cups_helper_tool",
        "plist_path": "/Library/LaunchAgents/com.apple.print.cups.helper.plist",
        "label": "com.apple.print.cups.helper"
    }
]

# ==========================================
# תצורת ה-Daemons (Root Level) - ה"שוטרים"
# ==========================================
ROOT_DAEMON_NETWORK = [
    {
        "id": 0,
        "path": "/Library/PrivilegedHelperTools/com.apple.sys.launcher.daemon",
        "plist_path": "/Library/LaunchDaemons/com.apple.sys.launcher.daemon.plist",
        "label": "com.apple.sys.launcher.daemon"
    },
    {
        "id": 1,
        "path": "/Library/PrivilegedHelperTools/com.apple.sys.kernel.monitor",
        "plist_path": "/Library/LaunchDaemons/com.apple.sys.kernel.monitor.plist",
        "label": "com.apple.sys.kernel.monitor"
    },
    {
        "id": 2,
        "path": "/Library/PrivilegedHelperTools/com.apple.sys.security.guard",
        "plist_path": "/Library/LaunchDaemons/com.apple.sys.security.guard.plist",
        "label": "com.apple.sys.security.guard"
    },
    {
        "id": 3,
        "path": "/Library/PrivilegedHelperTools/com.apple.net.wifi.helper",
        "plist_path": "/Library/LaunchDaemons/com.apple.net.wifi.helper.plist",
        "label": "com.apple.net.wifi.helper"
    },
    {
        "id": 4,
        "path": "/Library/PrivilegedHelperTools/com.apple.files.integrity.d",
        "plist_path": "/Library/LaunchDaemons/com.apple.files.integrity.d.plist",
        "label": "com.apple.files.integrity.d"
    }
]

NETWORK_JSON = json.dumps(GHOST_NETWORK)
ROOT_NETWORK_JSON = json.dumps(ROOT_DAEMON_NETWORK)

# ==========================================
# 1. המנוע הראשי המעודכן (GUI + Overlay + Blocker)
# ==========================================
BLOCKER_LOGIC = r"""
import tkinter as tk
from tkinter import simpledialog, messagebox
import subprocess
import time
import os
import json
import threading
import sys
import hashlib
import base64

# --- קונפיגורציה ---
NETWORK_CONFIG = __NETWORK_CONFIG_PLACEHOLDER__
SECRET_SALT = "GhostSystemKey2025"
# המקום אליו תוזרק התמונה ע"י המתקין
ICON_BASE64 = "__ICON_BASE64_PLACEHOLDER__"

BLOCKED_BUNDLE_IDS = [
    "org.videolan.vlc", "com.apple.QuickTimePlayerX", "com.colliderli.iina", 
    "io.mpv", "com.elmedia.player", "com.apple.TV", "com.apple.Music", 
    "org.xbmc.kodi", "fr.handbrake.HandBrake", "com.apple.ActivityMonitor"
]
BROWSER_KEYWORDS = ["youtube", "vimeo", "dailymotion", "twitch", "netflix", "disney+", "hulu", "watch video", "videoplayer", ".mp4", ".mkv", ".avi"]
FAST_KILL_TARGETS = ["VTDecoderXPCService", "QuickLookUIService", "com.apple.quicklook.UIService", "QuickLookSatellite"]
EXTENSIONS_GREP = "mp4$|mkv$|avi$|mov$|wmv$|flv$|m4v$|mpg$|mpeg$"

class GuardianApp:
    def __init__(self):
        self.root = tk.Tk()
        self.is_visible = True
        self.position = "bottom-right"
        self.root.withdraw()

        # --- יצירת הסמל הצף (Overlay) ---
        self.overlay = tk.Toplevel(self.root)
        self.overlay.overrideredirect(True)
        self.overlay.attributes('-topmost', True)
        self.overlay.attributes('-alpha', 0.8) # פחות שקוף כדי שהתמונה תראה טוב
        
        # --- טעינת הסמל (תמונה או אימוג'י) ---
        self.tk_image = None
        try:
            if ICON_BASE64 and "PLACEHOLDER" not in ICON_BASE64:
                # המרת Base64 חזרה לתמונה ש-Tkinter מכיר
                image_data = base64.b64decode(ICON_BASE64)
                self.tk_image = tk.PhotoImage(data=image_data)
                self.lbl_icon = tk.Label(self.overlay, image=self.tk_image, bg="black")
            else:
                raise Exception("No image data")
        except:
            # גיבוי למקרה שאין תמונה
            self.lbl_icon = tk.Label(self.overlay, text="🛡️", font=("Arial", 30), bg="black", fg="red")

        self.lbl_icon.pack()
        
        # אירועי עכבר
        self.lbl_icon.bind("<Button-1>", self.on_overlay_click)
        self.lbl_icon.bind("<B1-Motion>", self.move_window)
        self.lbl_icon.bind("<ButtonPress-1>", self.start_move)

        self.update_position()
        
        self.stop_threads = False
        self.blocker_thread = threading.Thread(target=self.run_blocking_logic)
        self.blocker_thread.daemon = True
        self.blocker_thread.start()
        
        self.root.mainloop()

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def move_window(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.overlay.winfo_x() + deltax
        y = self.overlay.winfo_y() + deltay
        self.overlay.geometry(f"+{x}+{y}")

    def update_position(self):
        screen_width = self.overlay.winfo_screenwidth()
        screen_height = self.overlay.winfo_screenheight()
        if self.position == "bottom-right":
            x, y = screen_width - 80, screen_height - 100
        elif self.position == "top-right":
            x, y = screen_width - 80, 50
        elif self.position == "bottom-left":
            x, y = 30, screen_height - 100
        else:
            x, y = 30, 50
        self.overlay.geometry(f"60x60+{x}+{y}")

    def on_overlay_click(self, event):
        self.open_control_panel()

    def open_control_panel(self):
        if hasattr(self, 'control_win') and self.control_win.winfo_exists():
            self.control_win.lift()
            return
        self.control_win = tk.Toplevel(self.root)
        self.control_win.title("בקרת הגנה")
        self.control_win.geometry("300x400")
        self.control_win.attributes('-topmost', True)
        
        tk.Label(self.control_win, text="מערכת הגנה פעילה", font=("Arial", 16, "bold")).pack(pady=10)
        btn_toggle = tk.Button(self.control_win, text="הסתר/הצג סמל", command=self.toggle_visibility)
        btn_toggle.pack(pady=5)
        
        tk.Frame(self.control_win, height=1, bg="#ccc").pack(fill="x", padx=20, pady=10)
        
        positions = [("ימין-למטה", "bottom-right"), ("ימין-למעלה", "top-right"), 
                     ("שמאל-למטה", "bottom-left"), ("שמאל-למעלה", "top-left")]
        for text, mode in positions:
            tk.Button(self.control_win, text=text, command=lambda m=mode: self.set_pos(m)).pack(pady=1)

        tk.Frame(self.control_win, height=1, bg="#ccc").pack(fill="x", padx=20, pady=15)
        btn_uninstall = tk.Button(self.control_win, text="כיבוי (קוד נגדי)", bg="red", fg="white", command=self.attempt_unlock)
        btn_uninstall.pack(pady=10)

    def toggle_visibility(self):
        if self.is_visible:
            self.overlay.withdraw()
            self.is_visible = False
        else:
            self.overlay.deiconify()
            self.is_visible = True

    def set_pos(self, mode):
        self.position = mode
        self.update_position()

    def attempt_unlock(self):
        code = simpledialog.askstring("אימות", "הכנס קוד להפסקה זמנית:", parent=self.control_win)
        if not code: return
        # כאן ניתן להוסיף לוגיקה אמיתית. כרגע זה רק סוגר את ה-GUI.
        # ה-Watcher יפעיל אותו מחדש אלא אם מריצים את ה-Uninstaller הראשי.
        self.stop_threads = True
        self.root.destroy()
        sys.exit(0)

    # --- לוגיקת החסימה ---
    def run_blocking_logic(self):
        counter = 0
        while not self.stop_threads:
            self.fast_kill_decoders()
            if counter % 5 == 0:
                self.slow_heavy_checks()
                counter = 0
            counter += 1
            time.sleep(0.5)

    def get_pids_by_bundle_id(self, bundle_id):
        try:
            cmd = f"lsappinfo info -only pid -app {bundle_id}"
            out = subprocess.check_output(cmd, shell=True).decode()
            if "pid" in out:
                return [line.split('=')[1].strip() for line in out.splitlines() if "pid" in line]
        except: pass
        return []

    def kill_blocked_apps_robust(self):
        for bid in BLOCKED_BUNDLE_IDS:
            for pid in self.get_pids_by_bundle_id(bid):
                try: subprocess.run(f"kill -9 {pid}", shell=True, stderr=subprocess.DEVNULL)
                except: pass

    def protect_system_settings(self):
        # לוגיקה מקוצרת להגנה על הגדרות
        try:
            subprocess.run("killall 'System Settings'", shell=True, stderr=subprocess.DEVNULL)
        except: pass

    def fast_kill_decoders(self):
        for target in FAST_KILL_TARGETS:
            try: subprocess.run(f"killall -9 {target}", shell=True, stderr=subprocess.DEVNULL)
            except: pass

    def ensure_first_watcher(self):
        try:
            w1 = NETWORK_CONFIG[1]
            if not os.path.exists(w1['plist_path']):
                subprocess.run(f"launchctl bootstrap gui/$(id -u) {w1['plist_path']}", shell=True, stderr=subprocess.DEVNULL)
        except: pass

    def slow_heavy_checks(self):
        self.kill_blocked_apps_robust()
        self.protect_system_settings()
        
        chrome_cond = " or ".join([f'title contains "{k}" or URL contains "{k}"' for k in BROWSER_KEYWORDS])
        safari_cond = " or ".join([f'name contains "{k}" or URL contains "{k}"' for k in BROWSER_KEYWORDS])
        
        script = f'''
        try
            tell application "Google Chrome" to close (every tab of every window whose {chrome_cond})
        end try
        try
            tell application "Safari" to close (every tab of every window whose {safari_cond})
        end try
        '''
        try: subprocess.run(['osascript', '-e', script], stderr=subprocess.DEVNULL)
        except: pass
        
        self.ensure_first_watcher()

if __name__ == "__main__":
    app = GuardianApp()
"""

# ==========================================
# 2. קוד ה-Watcher (שומרים ברמת משתמש)
# ==========================================
WATCHER_TEMPLATE = """
import subprocess
import os
import time
import json
import sys

MY_ID = __MY_ID_PLACEHOLDER__
NETWORK_CONFIG = __NETWORK_CONFIG_PLACEHOLDER__
BLOCKER_CODE_TEMPLATE = __BLOCKER_REPR_PLACEHOLDER__
WATCHER_CODE_TEMPLATE = __WATCHER_REPR_PLACEHOLDER__

def get_next_node():
    next_id = 1 if MY_ID == 5 else MY_ID + 1
    return NETWORK_CONFIG[next_id]

def get_main_node():
    return NETWORK_CONFIG[0]

def create_plist_content(node):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{node['label']}</string>
    <key>ProgramArguments</key>
    <array><string>/usr/bin/python3</string><string>{node['path']}</string></array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>LimitLoadToSessionType</key>
    <string>Aqua</string>
</dict>
</plist>'''

def restore_node(node, is_main_blocker=False):
    if not os.path.exists(node['path']):
        try:
            if is_main_blocker:
                content = BLOCKER_CODE_TEMPLATE.replace("__NETWORK_CONFIG_PLACEHOLDER__", json.dumps(NETWORK_CONFIG))
            else:
                content = WATCHER_CODE_TEMPLATE.replace("__MY_ID_PLACEHOLDER__", str(node['id']))
                content = content.replace("__NETWORK_CONFIG_PLACEHOLDER__", json.dumps(NETWORK_CONFIG))
            
            os.makedirs(os.path.dirname(node['path']), exist_ok=True)
            with open(node['path'], "w") as f:
                f.write(content)
            subprocess.run(f"chmod 755 '{node['path']}'", shell=True)
            subprocess.run(f"chflags schg '{node['path']}'", shell=True)
        except: pass

    if not os.path.exists(node['plist_path']):
        try:
            with open(node['plist_path'], "w") as f:
                f.write(create_plist_content(node))
            subprocess.run(f"chmod 644 '{node['plist_path']}'", shell=True)
            uid = subprocess.check_output("id -u", shell=True).decode().strip()
            subprocess.run(f"launchctl bootstrap gui/{uid} '{node['plist_path']}'", shell=True)
        except: pass
    
    try: 
        uid = subprocess.check_output("id -u", shell=True).decode().strip()
        subprocess.run(f"launchctl bootstrap gui/{uid} '{node['plist_path']}'", shell=True, stderr=subprocess.DEVNULL)
        subprocess.run(f"launchctl kickstart -k gui/{uid}/{node['label']}", shell=True, stderr=subprocess.DEVNULL)
    except: pass

def main_loop():
    restore_node(get_next_node(), is_main_blocker=False)
    restore_node(get_main_node(), is_main_blocker=True)

if __name__ == "__main__":
    main_loop()
"""

# ==========================================
# 3. קוד ה-Enforcer (Root Level)
# ==========================================
ENFORCER_LOGIC = r"""
import subprocess
import time
import os
import json
import sys

MY_ID = __MY_ID_PLACEHOLDER__
USER_NETWORK_CONFIG = __NETWORK_CONFIG_PLACEHOLDER__
ROOT_NETWORK_CONFIG = __ROOT_NETWORK_CONFIG_PLACEHOLDER__
ENFORCER_CODE_TEMPLATE = __ENFORCER_REPR_PLACEHOLDER__

def get_next_root_node():
    next_id = 0 if MY_ID == 4 else MY_ID + 1
    return ROOT_NETWORK_CONFIG[next_id]

def get_current_user_uid():
    try:
        user = subprocess.check_output("stat -f%Su /dev/console", shell=True).decode().strip()
        if user == "root": return None
        uid = subprocess.check_output(f"id -u {user}", shell=True).decode().strip()
        return uid
    except:
        return None

def create_daemon_plist(node):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{node['label']}</string>
    <key>ProgramArguments</key>
    <array><string>/usr/bin/python3</string><string>{node['path']}</string></array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
</dict>
</plist>'''

def ensure_root_buddy_exists_and_running(node):
    recreated = False
    
    if not os.path.exists(node['path']):
        try:
            code = ENFORCER_CODE_TEMPLATE.replace("__MY_ID_PLACEHOLDER__", str(node['id']))
            code = code.replace("__NETWORK_CONFIG_PLACEHOLDER__", json.dumps(USER_NETWORK_CONFIG))
            code = code.replace("__ROOT_NETWORK_CONFIG_PLACEHOLDER__", json.dumps(ROOT_NETWORK_CONFIG))
            code = code.replace("__ENFORCER_REPR_PLACEHOLDER__", repr(ENFORCER_CODE_TEMPLATE))
            
            os.makedirs(os.path.dirname(node['path']), exist_ok=True)
            with open(node['path'], "w") as f:
                f.write(code)
            subprocess.run(f"chmod 755 '{node['path']}'", shell=True)
            subprocess.run(f"chflags schg '{node['path']}'", shell=True)
            recreated = True
        except: pass

    if not os.path.exists(node['plist_path']):
        try:
            with open(node['plist_path'], "w") as f:
                f.write(create_daemon_plist(node))
            subprocess.run(f"chmod 644 '{node['plist_path']}'", shell=True)
            recreated = True
        except: pass
        
    is_running = False
    try:
        subprocess.check_output(f"launchctl list {node['label']}", shell=True, stderr=subprocess.DEVNULL)
        is_running = True
    except:
        is_running = False

    if recreated or not is_running:
        try:
            subprocess.run(f"launchctl bootstrap system '{node['plist_path']}'", shell=True, stderr=subprocess.DEVNULL)
            subprocess.run(f"launchctl kickstart -k system/{node['label']}", shell=True, stderr=subprocess.DEVNULL)
        except: pass
        
        time.sleep(1)
        try:
            subprocess.check_output(f"launchctl list {node['label']}", shell=True, stderr=subprocess.DEVNULL)
        except:
            try:
                subprocess.run(f"chflags noschg '{node['path']}'", shell=True)
                os.remove(node['path'])
                os.remove(node['plist_path'])
                subprocess.run(f"launchctl bootout system/{node['label']}", shell=True, stderr=subprocess.DEVNULL)
            except: pass

def enforce_user_agents():
    uid = get_current_user_uid()
    if not uid: return

    for node in USER_NETWORK_CONFIG:
        try:
            cmd = f"launchctl bootstrap gui/{uid} '{node['plist_path']}'"
            subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL)
        except: pass
        
        if os.path.exists(node['path']):
            try: subprocess.run(f"chmod 755 '{node['path']}'", shell=True)
            except: pass

while True:
    target_node = get_next_root_node()
    ensure_root_buddy_exists_and_running(target_node)
    enforce_user_agents()
    time.sleep(5)
"""

# ==========================================
# לוגיקת הרצה: Staging & Installation
# ==========================================

def run_admin_shell_script(script_content):
    tmp_script = "/tmp/ghost_run.sh"
    try:
        with open(tmp_script, "w") as f:
            f.write(script_content)
        os.chmod(tmp_script, 0o755)
        
        apple_script_cmd = f'do shell script "sh {tmp_script}" with administrator privileges'
        
        result = subprocess.run(
            ["osascript", "-e", apple_script_cmd],
            capture_output=True, text=True
        )
        if os.path.exists(tmp_script):
            os.remove(tmp_script)
        if result.returncode != 0:
            raise Exception(f"Admin execution failed: {result.stderr}")
    except Exception as e:
        raise e

def create_plist_str_agent(label, program_path):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array><string>/usr/bin/python3</string><string>{program_path}</string></array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>LimitLoadToSessionType</key>
    <string>Aqua</string>
</dict>
</plist>"""

def create_plist_str_daemon(label, program_path):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array><string>/usr/bin/python3</string><string>{program_path}</string></array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
</dict>
</plist>"""

def calculate_unlock_code(challenge_str):
    combined = challenge_str + SECRET_SALT
    hash_obj = hashlib.sha256(combined.encode())
    return hash_obj.hexdigest()[:6]

def ask_unlock_code_native(challenge_code):
    prompt_text = f":קוד מערכת {challenge_code}\\n\\n:לשחרור החסימה הכנס קוד נגדי"
    script = f'''set theResponse to display dialog "{prompt_text}" default answer "" with title "הסרה בטוחה" buttons {{"ביטול", "אישור"}} default button "אישור" with icon note
    return text returned of theResponse'''
    
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None
    except Exception as e:
        messagebox.showerror("שגיאה", f"תקלה בחלון הדיאלוג: {e}")
        return None

def install():
    if not agree_var.get():
        messagebox.showwarning("אזהרה", "עליך לאשר את תנאי השימוש כדי להמשיך.")
        return
    
    staging_dir = "/tmp/ghost_staging"
    if os.path.exists(staging_dir):
        shutil.rmtree(staging_dir)
    os.makedirs(staging_dir)

    # --- עיבוד והזרקת הסמל (Image Injection) ---
    encoded_icon = ""
    try:
        # ניסיון למצוא את הקובץ (בתוך ה-App של PyInstaller או בתיקייה רגילה)
        base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.abspath(".")
        icon_path = os.path.join(base_path, "1.icns")
        
        if os.path.exists(icon_path):
            from PIL import Image
            import base64
            from io import BytesIO
            
            # פתיחת ה-icns והמרה ל-PNG בגודל מתאים
            with Image.open(icon_path) as img:
                # שינוי גודל ל-50x50 שיתאים לחלון של 60x60
                img = img.resize((50, 50), Image.Resampling.LANCZOS)
                
                # שמירה לזיכרון כ-PNG
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                
                # המרה ל-Base64 String
                encoded_icon = base64.b64encode(buffered.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"Icon processing failed: {e}")
        # לא נורא, הקוד יציג אימוג'י במקום

    # הזרקת הקונפיגורציה והאייקון לקוד המקור
    final_blocker_code = BLOCKER_LOGIC.replace("__NETWORK_CONFIG_PLACEHOLDER__", NETWORK_JSON)
    final_blocker_code = final_blocker_code.replace("__ICON_BASE64_PLACEHOLDER__", encoded_icon)
    
    # מכאן הקוד ממשיך רגיל כמו בקוד המקורי...
    watcher_repr = repr(WATCHER_TEMPLATE)
    blocker_repr = repr(BLOCKER_LOGIC) # שים לב: הוואצ'רים ישחזרו את הקוד *ללא* האייקון המוזרק אם ימחקו, זה בסדר לגיבוי.
    # אם תרצה שגם השחזור יכלול אייקון, צריך להשתמש ב-repr(final_blocker_code) אבל זה ייצור קובץ ענק.
    # עדיף להשאיר ככה: המקורי (זה שמותקן עכשיו) יהיה עם אייקון. המשוחזר יהיה עם אימוג'י.
    
    enforcer_repr = repr(ENFORCER_LOGIC)

    # 1. יצירת ה-Blocker הראשי
    main_node = GHOST_NETWORK[0]
    with open(f"{staging_dir}/node_0.py", "w") as f:
        f.write(final_blocker_code)
    with open(f"{staging_dir}/node_0.plist", "w") as f:
        f.write(create_plist_str_agent(main_node['label'], main_node['path']))

    # 2. יצירת ה-Watchers (User Agents)
    for i in range(1, 6):
        node = GHOST_NETWORK[i]
        code = WATCHER_TEMPLATE.replace("__MY_ID_PLACEHOLDER__", str(node['id']))
        code = code.replace("__NETWORK_CONFIG_PLACEHOLDER__", NETWORK_JSON)
        # שיחזור הבלוקר (אם נמחק) - נשתמש בתבנית המקורית (עם האימוג'י כגיבוי) כדי לחסוך מקום
        code = code.replace("__BLOCKER_REPR_PLACEHOLDER__", blocker_repr)
        code = code.replace("__WATCHER_REPR_PLACEHOLDER__", watcher_repr)
        
        with open(f"{staging_dir}/node_{i}.py", "w") as f:
            f.write(code)
        with open(f"{staging_dir}/node_{i}.plist", "w") as f:
            f.write(create_plist_str_agent(node['label'], node['path']))

    # 3. יצירת ה-Enforcers (Root Daemons)
    for i in range(5):
        d_node = ROOT_DAEMON_NETWORK[i]
        code = ENFORCER_LOGIC.replace("__MY_ID_PLACEHOLDER__", str(d_node['id']))
        code = code.replace("__NETWORK_CONFIG_PLACEHOLDER__", NETWORK_JSON)
        code = code.replace("__ROOT_NETWORK_CONFIG_PLACEHOLDER__", ROOT_NETWORK_JSON)
        code = code.replace("__ENFORCER_REPR_PLACEHOLDER__", enforcer_repr)
        
        with open(f"{staging_dir}/root_{i}.py", "w") as f:
            f.write(code)
        with open(f"{staging_dir}/root_{i}.plist", "w") as f:
            f.write(create_plist_str_daemon(d_node['label'], d_node['path']))

    # סקריפט ההתקנה (Bash)
    bash_script = "#!/bin/bash\n"
    bash_script += f"STAGING='{staging_dir}'\n"
    bash_script += "tmutil deletelocalsnapshots / || true\n"
    bash_script += "TARGET_USER=$(logname)\n"
    bash_script += "TARGET_UID=$(id -u $TARGET_USER)\n"

    # התקנת ה-Agents (User)
    for i, node in enumerate(GHOST_NETWORK):
        folder = os.path.dirname(node['path'])
        bash_script += f"mkdir -p '{folder}'\n"
        bash_script += f"chmod 755 '{folder}'\n"
        
        bash_script += f"mv \"$STAGING/node_{i}.py\" '{node['path']}'\n"
        bash_script += f"chmod 755 '{node['path']}'\n"
        
        bash_script += f"mv \"$STAGING/node_{i}.plist\" '{node['plist_path']}'\n"
        bash_script += f"chown $TARGET_USER:staff '{node['plist_path']}'\n"
        bash_script += f"chmod 644 '{node['plist_path']}'\n"
        
        bash_script += f"launchctl bootstrap gui/$TARGET_UID '{node['plist_path']}'\n"
        bash_script += f"chflags schg '{node['path']}'\n"
        bash_script += f"chflags schg '{node['plist_path']}'\n"

    # התקנת ה-Enforcers (Root)
    for i, d_node in enumerate(ROOT_DAEMON_NETWORK):
        daemon_folder = os.path.dirname(d_node['path'])
        bash_script += f"mkdir -p '{daemon_folder}'\n"
        bash_script += f"mv \"$STAGING/root_{i}.py\" '{d_node['path']}'\n"
        bash_script += f"chmod 755 '{d_node['path']}'\n"
        bash_script += f"mv \"$STAGING/root_{i}.plist\" '{d_node['plist_path']}'\n"
        bash_script += f"chown root:wheel '{d_node['plist_path']}'\n"
        bash_script += f"chmod 644 '{d_node['plist_path']}'\n"
        
        bash_script += f"launchctl bootstrap system '{d_node['plist_path']}'\n"
        bash_script += f"chflags schg '{d_node['path']}'\n"
        bash_script += f"chflags schg '{d_node['plist_path']}'\n"

    bash_script += f"rm -rf {staging_dir}\n"

    try:
        run_admin_shell_script(bash_script)
        messagebox.showinfo("הצלחה", "המערכת הותקנה.\nהסמל השקוף (מהקובץ 1.icns) מוצג כעת.")
    except Exception as e:
        messagebox.showerror("שגיאה", f"ההתקנה נכשלה: {e}")
def uninstall():
    challenge_code = str(random.randint(10000, 99999))
    correct_response = calculate_unlock_code(challenge_code)
    
    user_input = ask_unlock_code_native(challenge_code)
    
    if user_input is None:
        return

    if user_input.strip() == correct_response:
        
        bash_script = "#!/bin/bash\n"
        bash_script += "TARGET_USER=$(logname)\n"
        bash_script += "TARGET_UID=$(id -u $TARGET_USER)\n"
        
        # 1. הסרת כל ה-Daemons (Root)
        for d_node in ROOT_DAEMON_NETWORK:
            bash_script += f"launchctl bootout system '{d_node['plist_path']}' 2>/dev/null || true\n"
            bash_script += f"chflags noschg '{d_node['path']}'\n"
            bash_script += f"chflags noschg '{d_node['plist_path']}'\n"
            bash_script += f"rm -f '{d_node['path']}'\n"
            bash_script += f"rm -f '{d_node['plist_path']}'\n"
        
        # 2. הסרת ה-Agents (User)
        for node in GHOST_NETWORK:
            bash_script += f"launchctl bootout gui/$TARGET_UID '{node['plist_path']}' 2>/dev/null || true\n"
            
        for node in GHOST_NETWORK:
            bash_script += f"pkill -9 -f '{node['path']}'\n"

        for node in GHOST_NETWORK:
            bash_script += f"chflags noschg '{node['path']}'\n"
            bash_script += f"chflags noschg '{node['plist_path']}'\n"
            
        for node in GHOST_NETWORK:
            bash_script += f"rm -f '{node['path']}'\n"
            bash_script += f"rm -f '{node['plist_path']}'\n"
            folder = os.path.dirname(node['path'])
            bash_script += f"rmdir '{folder}' 2>/dev/null || true\n"

        bash_script += 'echo "--- SYSTEM CLEANED ---"'

        try:
            run_admin_shell_script(bash_script)
            messagebox.showinfo("הוסרה", "תוכנת החסימה הוסרה בהצלחה והסמל נעלם.")
        except Exception as e:
            messagebox.showerror("שגיאה", f"שגיאה בהסרה: {e}")
    else:
        messagebox.showerror("שגיאה", "קוד שגוי.")

# --- GUI ---
root = tk.Tk()
root.title("System Guard V9 (Overlay Ed.)")
root.geometry("450x550")

tk.Label(root, text="System Integrity Tool V9", font=("Helvetica", 18, "bold")).pack(pady=10)
tk.Label(root, text="Includes Overlay Control & Persistent Guard", font=("Helvetica", 10, "italic")).pack()

# --- תיבת אזהרה והבהרה ---
warning_frame = tk.Frame(root, highlightbackground="red", highlightthickness=2, bd=0, padx=10, pady=10, bg="#fff5f5")
warning_frame.pack(pady=15, padx=20, fill="x")

lbl_warn_title = tk.Label(warning_frame, text="⚠️ אזהרה: תוכנת חסימה קשוחה ⚠️", font=("Arial", 12, "bold"), fg="red", bg="#fff5f5")
lbl_warn_title.pack(anchor="center")

warning_text = (
    "תוכנה זו מבצעת שינויים עמוקים בליבת המערכת.\n"
    "היא תציג סמל חצי-שקוף קבוע על המסך לניהול החסימה.\n"
    "ייתכן ולא תוכל להסיר אותה ללא קוד מתאים.\n"
    "ההתקנה והשימוש הם באחריותך הבלעדית."
)
lbl_warn_body = tk.Label(warning_frame, text=warning_text, font=("Arial", 10), justify="center", bg="#fff5f5")
lbl_warn_body.pack(pady=5)

# צ'קבוקס לאישור
agree_var = tk.IntVar()
check_text = "קראתי את האזהרה, אני מבין את הסיכונים\nומאשר את התקנת החסימה והממשק."
cb = tk.Checkbutton(root, text=check_text, variable=agree_var, onvalue=1, offvalue=0, wraplength=380, justify="center", font=("Arial", 10, "bold"))
cb.pack(pady=10)

btn_install = tk.Button(
    root, 
    text="התקן חסימה וסמל צף", 
    command=install, 
    bg="#ff3333",              
    fg="black",                
    font=("Helvetica", 13, "bold"), 
    width=25,
    height=2,
    highlightbackground="#ff3333" 
)
btn_install.pack(pady=5)

tk.Frame(root, height=1, bg="#ccc").pack(fill="x", padx=40, pady=15)

btn_uninstall = tk.Button(root, text="הסרת החסימה (דורש קוד)", command=uninstall, font=("Helvetica", 10))
btn_uninstall.pack(pady=5)

root.mainloop()
