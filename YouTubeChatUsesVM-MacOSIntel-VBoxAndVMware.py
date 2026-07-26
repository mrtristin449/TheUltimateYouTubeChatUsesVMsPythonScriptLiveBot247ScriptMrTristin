# ========================= VERSION =========================
VERSION = "1.0"

# Pytchat signal fix for running inside threads
import signal as _signal_module
import threading as _threading_module
_orig_signal = _signal_module.signal
def _safe_signal(sig, handler):
    if _threading_module.current_thread() is _threading_module.main_thread():
        return _orig_signal(sig, handler)
_signal_module.signal = _safe_signal

import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox, ttk, simpledialog as _simpledialog
import threading, time, sys, traceback, random, subprocess, os, re, json, platform, ctypes, collections, queue, shutil, gc, math
import urllib.request, urllib.error, urllib.parse
from ctypes import wintypes
sys.coinit_flags = 0

# Hide the annoying VirtualBox COM warning from the black terminal
class _StderrFilter:
    def __init__(self, orig): self.orig = orig
    def write(self, msg):
        if "CoInitializeSecurity was already called" not in str(msg):
            self.orig.write(msg)
    def flush(self): self.orig.flush()
sys.stderr = _StderrFilter(sys.stderr)

try: import pythoncom
except ImportError: pass

# ── Detect "--autostart-everything" (set by the auto-update/hot-reload relaunch
#    pipeline's generated batch/shell file on the freshly downloaded
#    *_autostarteverything.py copy) -- tells this instance to read video_id.json and
#    self-start the bot without anyone at the keyboard. ──
_AUTOSTART_EVERYTHING = "--autostart-everything" in sys.argv[1:]

def _native_dialog_yesno(msg, title):
    """Shows a native Yes/No dialog WITHOUT needing tkinter initialized yet (used during
    the UAC-elevation and update-check flows, both of which run before the GUI exists).
    Returns True for Yes, False for No -- or True if the dialog couldn't be shown at all,
    since defaulting to "proceed" is safer than silently blocking startup forever."""
    if platform.system() == "Windows":
        import ctypes
        MB_YESNO, MB_ICONQUESTION, IDYES = 0x04, 0x20, 6
        try:
            return ctypes.windll.user32.MessageBoxW(0, msg, title, MB_YESNO | MB_ICONQUESTION) == IDYES
        except Exception:
            return True
    elif platform.system() == "Darwin":
        try:
            esc_msg = msg.replace('\\', '\\\\').replace('"', '\\"')
            esc_title = title.replace('\\', '\\\\').replace('"', '\\"')
            script = f'display dialog "{esc_msg}" with title "{esc_title}" buttons {{"No", "Yes"}} default button "Yes"'
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=120)
            return "button returned:Yes" in (result.stdout or "")
        except Exception:
            return True
    else:
        print(f"[{title}] {msg}")
        return True

def _native_dialog_error(msg, title):
    """Shows a native error/info dialog WITHOUT needing tkinter initialized yet."""
    if platform.system() == "Windows":
        import ctypes
        MB_ICONERROR = 0x10
        try:
            ctypes.windll.user32.MessageBoxW(0, msg, title, MB_ICONERROR)
        except Exception:
            pass
    elif platform.system() == "Darwin":
        try:
            esc_msg = msg.replace('\\', '\\\\').replace('"', '\\"')
            esc_title = title.replace('\\', '\\\\').replace('"', '\\"')
            script = f'display alert "{esc_title}" message "{esc_msg}"'
            subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=60)
        except Exception:
            pass
    else:
        print(f"[{title}] {msg}")

# ========================= VERSION & AUTO-UPDATE =========================
# This script's own filename -- used to make sure a shared/misconfigured version.json
# is actually meant for THIS file before ever applying an update. A single version.json
# with one sha256/signature pair can only ever be valid for ONE file's actual content --
# if the repo hosts multiple platform/backend variants (like this one does), each variant
# needs its OWN version.json with a "filename" field matching this constant, or this
# script has no way to tell "a new version exists" apart from "a DIFFERENT file's new
# version exists, and applying it here would silently corrupt this install."
# If version.json has no "filename" field at all, this check is skipped (so this still
# works with a simple single-file repo) -- but IS enforced the moment that field appears.
CURRENT_FILENAME = "YouTubeChatUsesVM-MacOSIntel-VBoxAndVMware.py"

# Replace these two URLs with your own GitHub repo paths.
# GITHUB_VERSION_URL  → raw URL of version.json in your repo
# GITHUB_SCRIPT_URL   → raw URL of THIS file (YouTubeChatUsesVM-MacOSIntel-VBoxAndVMware.py) in your repo
#   Browsable page: https://github.com/mrtristin449/TheUltimateYouTubeChatUsesVMsPythonScriptLiveBot247ScriptMrTristin/blob/main/YouTubeChatUsesVMs/YouTubeChatUsesVM-MacOSIntel-VBoxAndVMware.py
#   (urllib needs the RAW content URL below, not the browsable page above --
#   raw.githubusercontent.com serves the actual file bytes, github.com/.../blob/
#   serves an HTML viewer page that urlopen() can't parse as source code.)
#
# Other macOS Intel variants in this repo (for reference only -- deliberately NOT fetched
# or checked by this script, only its OWN file above is ever downloaded/verified/replaced):
#   https://github.com/mrtristin449/TheUltimateYouTubeChatUsesVMsPythonScriptLiveBot247ScriptMrTristin/blob/main/YouTubeChatUsesVMs/YouTubeChatUsesVM-MacOSIntel-VBox.py
#   https://github.com/mrtristin449/TheUltimateYouTubeChatUsesVMsPythonScriptLiveBot247ScriptMrTristin/blob/main/YouTubeChatUsesVMs/YouTubeChatUsesVM-MacOSIntel-VMware.py
GITHUB_VERSION_URL = "https://raw.githubusercontent.com/mrtristin449/TheUltimateYouTubeChatUsesVMsPythonScriptLiveBot247ScriptMrTristin/main/version.json"
GITHUB_SCRIPT_URL  = "https://raw.githubusercontent.com/mrtristin449/TheUltimateYouTubeChatUsesVMsPythonScriptLiveBot247ScriptMrTristin/main/YouTubeChatUsesVMs/YouTubeChatUsesVM-MacOSIntel-VBoxAndVMware.py"

# Public key used to verify the signature of downloaded updates.
# This is SAFE to keep here — it can only verify signatures, not create them.
# Generate this pair locally with generate_keys.py and paste the public key below.
UPDATE_PUBLIC_KEY_HEX = "13eebf036b59fe64547d23cd2e3e23fae1d5ee086e912939a91d5535ed4df08b"


def _verify_update_signature(file_bytes, expected_sha256_hex, signature_hex):
    """
    Verifies that file_bytes matches the expected SHA-256 hash, and that the
    hash was signed by the holder of the private key matching
    UPDATE_PUBLIC_KEY_HEX. Returns True only if both checks pass.
    """
    import hashlib
    import binascii

    try:
        from nacl.signing import VerifyKey
        from nacl.exceptions import BadSignatureError
    except ImportError:
        print("[Updater] PyNaCl is not installed; cannot verify update signature. Aborting update.")
        return False

    actual_hash = hashlib.sha256(file_bytes).hexdigest()
    if actual_hash != expected_sha256_hex:
        print("[Updater] Hash mismatch -- downloaded file does not match version.json. Rejecting update.")
        return False

    try:
        verify_key = VerifyKey(binascii.unhexlify(UPDATE_PUBLIC_KEY_HEX))
        verify_key.verify(expected_sha256_hex.encode("ascii"), binascii.unhexlify(signature_hex))
        return True
    except BadSignatureError:
        print("[Updater] Signature is invalid. Rejecting update.")
        return False
    except Exception as e:
        print(f"[Updater] Signature verification error: {e}. Rejecting update.")
        return False


def _check_for_update():
    """
    Downloads version.json from GitHub and compares it to the running version.
    If a newer version is available, asks the user whether to update.
    Called once during splash, before the main GUI is built.
    Returns True if the script restarted (caller should exit), False otherwise.
    """
    import urllib.request
    import urllib.error
    import json as _json

    try:
        _update_splash(8, "Checking for updates...")
        with urllib.request.urlopen(GITHUB_VERSION_URL, timeout=5) as resp:
            data            = _json.loads(resp.read().decode("utf-8"))
            latest_ver      = data.get("version", "0.0.0").strip()
            expected_sha256 = data.get("sha256", "").strip()
            signature_hex   = data.get("signature", "").strip()
            version_filename = str(data.get("filename", "")).strip()
    except Exception as e:
        # Network unavailable or repo not configured — silently skip.
        print(f"[Updater] Could not check for updates: {e}")
        return False

    if version_filename and version_filename != CURRENT_FILENAME:
        # version.json is declaring itself as meant for a DIFFERENT file in this repo
        # (a different platform/backend variant) -- this is exactly the "shared
        # version.json breaks multi-variant repos" scenario. Refuse rather than risk
        # applying a mismatched update: staying on the current version is always safer
        # than silently overwriting this file with a different variant's content.
        print(f"[Updater] version.json is for '{version_filename}', not this file "
              f"('{CURRENT_FILENAME}') -- skipping update. This is expected if you just "
              f"updated a DIFFERENT variant's version.json and haven't gotten to this "
              f"one yet.")
        return False

    def _ver_tuple(v):
        try:
            return tuple(int(x) for x in v.strip().split("."))
        except Exception:
            return (0, 0, 0)

    if _ver_tuple(latest_ver) <= _ver_tuple(VERSION):
        print(f"[Updater] Up to date ({VERSION}).")
        return False

    if not expected_sha256 or not signature_hex:
        print("[Updater] version.json is missing sha256/signature fields. Refusing to update.")
        return False

    # New version found — ask the user.
    msg = (
        f"A new version is available!\n\n"
        f"  Current version : {VERSION}\n"
        f"  New version     : {latest_ver}\n\n"
        f"Update now? The bot will restart automatically after downloading."
    )
    if not _native_dialog_yesno(msg, "Update Available"):
        print(f"[Updater] User declined update to {latest_ver}.")
        return False

    # Download new script to a temporary file first (atomic update).
    _update_splash(9, f"Downloading version {latest_ver}...")
    script_path = os.path.abspath(sys.argv[0])
    tmp_path    = script_path + ".update_tmp"
    try:
        with urllib.request.urlopen(GITHUB_SCRIPT_URL, timeout=30) as resp:
            new_code = resp.read()

        _update_splash(9, "Verifying update signature...")
        if not _verify_update_signature(new_code, expected_sha256, signature_hex):
            _native_dialog_error(
                "Update rejected: the downloaded file failed signature verification.\n\n"
                "This could mean the update source has been compromised.\n"
                "The bot will start with the current version.",
                "Update Security Warning"
            )
            print("[Updater] Update rejected due to failed signature verification.")
            return False

        with open(tmp_path, "wb") as f:
            f.write(new_code)
        # Atomic replace: rename tmp over the live file.
        if os.path.exists(script_path):
            os.replace(tmp_path, script_path)
        print(f"[Updater] Updated to {latest_ver}. Restarting...")
        # Restart the process with the same arguments.
        subprocess.Popen([sys.executable, script_path] + sys.argv[1:])
        sys.exit(0)
    except Exception as e:
        # Clean up temp file if something went wrong.
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except Exception: pass
        _native_dialog_error(
            f"Update failed:\n{e}\n\nThe bot will start with the current version.",
            "Update Error"
        )
        print(f"[Updater] Update failed: {e}")
        return False


# ========================= CONTINUOUS AUTO-UPDATE + AUTO-RELAUNCH =========================
# Separate from the signature-verified startup updater above. This runs continuously
# in the background the whole time the bot is open, checking a NEW GitHub source once
# per second (quietly -- only logs when something actually changes or on real errors,
# not on every check). When it finds a new version, instead of overwriting the running
# file in place, it hands off to a generated batch file that: kills the running python
# process, re-downloads every file from GitHub, and launches a NEW copy of the script
# named "{filename}_autostarteverything.py" that self-starts the bot, extra streams,
# and (if one was running) the web dashboard -- all without needing anyone at the
# keyboard. Real PC Control is deliberately NOT auto-resumed this way -- see below.

# Browsable page: https://github.com/mrtristin449/TheUltimateYouTubeChatUsesVMsPythonScriptLiveBot247ScriptMrTristin/blob/main/YouTubeChatUsesVMs/YouTubeChatUsesVM-MacOSIntel-VBoxAndVMware.py
AUTOUPDATE_VERSION_URL = "https://raw.githubusercontent.com/mrtristin449/TheUltimateYouTubeChatUsesVMsPythonScriptLiveBot247ScriptMrTristin/main/version.json"
AUTOUPDATE_SCRIPT_URL  = "https://raw.githubusercontent.com/mrtristin449/TheUltimateYouTubeChatUsesVMsPythonScriptLiveBot247ScriptMrTristin/main/YouTubeChatUsesVMs/YouTubeChatUsesVM-MacOSIntel-VBoxAndVMware.py"
AUTOUPDATE_POLL_INTERVAL = 1  # seconds -- checked with a conditional GET (ETag), so most
                              # checks are cheap "304 Not Modified" responses, not full downloads.

_autoupdate_relaunch_triggered = False   # guards against triggering the pipeline twice
_autoupdate_lock = _threading_module.Lock()

def _script_paths():
    """(full script path, folder, base filename without .py)."""
    script_path = os.path.abspath(sys.argv[0])
    folder = os.path.dirname(script_path)
    base_name = os.path.splitext(os.path.basename(script_path))[0]
    # If we're already running as a previously-generated "_autostarteverything" copy,
    # strip that suffix so we don't end up with "..._autostarteverything_autostarteverything".
    if base_name.endswith("_autostarteverything"):
        base_name = base_name[:-len("_autostarteverything")]
    return script_path, folder, base_name

def _write_video_id_json(folder):
    try:
        active_url = app_instance.active_url if app_instance is not None else ""
        with open(os.path.join(folder, "video_id.json"), "w", encoding="utf-8") as f:
            json.dump({"video_id": active_url}, f, indent=2)
    except Exception as e:
        print(f"[AutoUpdate] Could not write video_id.json: {e}")

def _write_autostart_flags_json(folder):
    """Captures anything that isn't already in its own persisted config file, so the
    relaunched instance knows to resume it -- currently just the web dashboard port,
    if one was running (extra video IDs / VM config already persist in their own
    json files in this same folder and carry over automatically)."""
    flask_running = (app_instance is not None and hasattr(app_instance, "flask_thread")
                     and app_instance.flask_thread is not None and app_instance.flask_thread.is_alive())
    flags = {"flask_port": flask_port if flask_running else None}
    try:
        with open(os.path.join(folder, "autostart_flags.json"), "w", encoding="utf-8") as f:
            json.dump(flags, f, indent=2)
    except Exception as e:
        print(f"[AutoUpdate] Could not write autostart_flags.json: {e}")
    return flags

def _download_and_verify_update(version_data):
    """Downloads the new script and verifies it against version.json's sha256+signature
    using the exact same Ed25519 verification the safe startup updater uses (same
    UPDATE_PUBLIC_KEY_HEX). Returns the verified bytes on success. Returns None (with
    a clear log explaining why) if verification fails -- the caller must NOT proceed
    with the update in that case. If version.json has no sha256/signature at all, this
    downloads unverified with a clear warning, so the pipeline stays usable while
    you're still setting up signing, but that gap is loud, not silent."""
    import urllib.request
    version_filename = str(version_data.get("filename", "")).strip()
    if version_filename and version_filename != CURRENT_FILENAME:
        print(f"[AutoUpdate] SECURITY: version_data is for '{version_filename}', not this "
              f"file ('{CURRENT_FILENAME}') -- refusing to download/apply. This should "
              f"have been caught before this function was ever called; if you're seeing "
              f"this, something upstream isn't checking version.json's filename first.")
        return None
    expected_sha256 = str(version_data.get("sha256", "")).strip()
    signature_hex   = str(version_data.get("signature", "")).strip()
    try:
        with urllib.request.urlopen(AUTOUPDATE_SCRIPT_URL, timeout=30) as resp:
            new_code = resp.read()
    except Exception as e:
        print(f"[AutoUpdate] Download failed: {e}")
        return None

    if not expected_sha256 or not signature_hex:
        print("[AutoUpdate] WARNING: version.json has no sha256/signature -- installing "
              "UNVERIFIED. Add both fields (signed with the key matching "
              "UPDATE_PUBLIC_KEY_HEX) to get real update verification.")
        return new_code

    if not _verify_update_signature(new_code, expected_sha256, signature_hex):
        print("[AutoUpdate] SECURITY: the downloaded update failed signature verification "
              "-- staying on the current version. This means either version.json's "
              "sha256/signature don't match the file at AUTOUPDATE_SCRIPT_URL, or they "
              "weren't signed with the private key matching this script's "
              "UPDATE_PUBLIC_KEY_HEX. Re-sign the release, or update UPDATE_PUBLIC_KEY_HEX "
              "to your own key pair's public key if this repo uses a different one.")
        return None

    print("[AutoUpdate] Update signature verified OK.")
    return new_code

def _generate_relaunch_script_macos(folder, base_name, flags):
    """macOS equivalent of _generate_relaunch_batch() below -- same steps (stop the
    running bot, refresh version.json for the record, launch the new instance with
    everything auto-starting), just in shell instead of batch. Uses curl (built into
    macOS, no PowerShell equivalent needed) instead of Invoke-WebRequest, and pkill
    instead of taskkill."""
    autostart_script = f"{base_name}_autostarteverything.py"
    autostart_path   = os.path.join(folder, autostart_script)
    script_path      = os.path.join(folder, "run_update.sh")
    python_exe       = sys.executable

    launch_args = "--autostart-everything"
    if flags.get("flask_port"):
        launch_args += f" --flaskport={flags['flask_port']}"

    sh = f"""#!/bin/bash
# ============================================================
# Auto-generated by the bot's auto-update system. Do not run
# this by hand unless you mean to force an update/relaunch --
# step 1 below kills EVERY python/python3 process owned by you
# on this machine, not just this bot. The updated script itself
# was already downloaded and signature-verified by Python
# before this script was written -- this just re-fetches
# version.json for the record and launches the new instance.
# ============================================================
echo "Stopping the running bot..."
pkill -9 -u "$(whoami)" -f "python3?( |$)" 2>/dev/null
sleep 2

echo "Refreshing version.json..."
curl -fsSL "{AUTOUPDATE_VERSION_URL}" -o "{os.path.join(folder, 'version.json')}" || \\
    echo "WARNING: could not refresh version.json (non-fatal, continuing)"

if [ ! -f "{autostart_path}" ]; then
    echo "============================================================"
    echo "ERROR: \\"{autostart_script}\\" is missing -- nothing to launch."
    echo "This should have been written by the bot before this script"
    echo "ran. Nothing was started."
    echo "============================================================"
    read -p "Press Enter to close..."
    exit 1
fi

echo "Launching the updated bot with everything auto-starting..."
echo "Using interpreter: {python_exe}"
cd "{folder}"
"{python_exe}" "{autostart_script}" {launch_args}
if [ $? -ne 0 ]; then
    echo "============================================================"
    echo "ERROR: the relaunch exited with an error."
    echo "Common causes: a missing pip package, or \\"{python_exe}\\""
    echo "no longer being a valid Python install on this machine."
    echo "============================================================"
    read -p "Press Enter to close..."
    exit 1
fi

echo "Update complete."
"""
    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(sh)
        os.chmod(script_path, 0o755)
        return script_path
    except Exception as e:
        print(f"[AutoUpdate] Could not write relaunch script: {e}")
        return None

def _generate_relaunch_batch(folder, base_name, flags):
    """Writes the batch file: kill python, fetch a fresh version.json (for the record --
    the actual script content was already downloaded and signature-verified by Python
    before this was even called, and is written straight to disk, not re-fetched here
    unverified), then launch the new {base_name}_autostarteverything.py with everything
    auto-starting.

    Uses sys.executable (the exact interpreter this process is actually running under)
    rather than a bare "python" -- a bare "python" on PATH can silently resolve to a
    different install than the one with all this bot's pip packages, or not exist on
    PATH at all, which looks exactly like "the bot never comes back" with no visible
    error, since the console window closes before anyone can read it."""
    autostart_script = f"{base_name}_autostarteverything.py"
    autostart_path   = os.path.join(folder, autostart_script)
    batch_path       = os.path.join(folder, "run_update.bat")
    python_exe       = sys.executable

    launch_args = "--autostart-everything"
    if flags.get("flask_port"):
        launch_args += f" --flaskport={flags['flask_port']}"

    bat = f"""@echo off
REM ============================================================
REM  Auto-generated by the bot's auto-update system. Do not run
REM  this by hand unless you mean to force an update/relaunch --
REM  step 1 below kills EVERY python.exe/pythonw.exe process on
REM  this machine, not just this bot. The updated script itself
REM  was already downloaded and signature-verified by Python
REM  before this batch file was written -- this just re-fetches
REM  version.json for the record and launches the new instance.
REM ============================================================
echo Stopping the running bot...
taskkill /IM python.exe /F >nul 2>&1
taskkill /IM pythonw.exe /F >nul 2>&1
timeout /t 2 /nobreak >nul

echo Refreshing version.json...
powershell -NoProfile -Command "Invoke-WebRequest -Uri '{AUTOUPDATE_VERSION_URL}' -OutFile '{os.path.join(folder, 'version.json')}'"

if not exist "{autostart_path}" (
    echo ============================================================
    echo ERROR: "{autostart_script}" is missing -- nothing to launch.
    echo This should have been written by the bot before this batch
    echo file ran. Nothing was started.
    echo ============================================================
    pause
    exit /b 1
)

echo Launching the updated bot with everything auto-starting...
echo Using interpreter: "{python_exe}"
cd /d "{folder}"
"{python_exe}" "{autostart_script}" {launch_args}
if errorlevel 1 (
    echo ============================================================
    echo ERROR: the relaunch exited with an error ^(code %errorlevel%^).
    echo Common causes: a missing pip package, or "{python_exe}"
    echo no longer being a valid Python install on this machine.
    echo ============================================================
    pause
    exit /b 1
)

echo Update complete.
"""
    try:
        with open(batch_path, "w", encoding="utf-8") as f:
            f.write(bat)
        return batch_path
    except Exception as e:
        print(f"[AutoUpdate] Could not write batch file: {e}")
        return None

def trigger_relaunch_pipeline(reason, version_data=None):
    """Shared by both the version-update watcher and the file-edit watchdog below.
    If version_data is given (came from a real version.json check), the new script
    is downloaded and signature-verified FIRST -- the pipeline aborts cleanly if
    that fails, instead of installing something that didn't check out. If
    version_data is None (a local file-edit trigger, nothing remote to verify
    against), it skips straight to relaunching."""
    global _autoupdate_relaunch_triggered
    with _autoupdate_lock:
        if _autoupdate_relaunch_triggered:
            return
        _autoupdate_relaunch_triggered = True

    print(f"[AutoUpdate] {reason} -- preparing to relaunch.")
    script_path, folder, base_name = _script_paths()

    if version_data is not None:
        verified_code = _download_and_verify_update(version_data)
        if verified_code is None:
            _autoupdate_relaunch_triggered = False
            return
        try:
            with open(os.path.join(folder, f"{base_name}.py"), "wb") as f:
                f.write(verified_code)
            with open(os.path.join(folder, f"{base_name}_autostarteverything.py"), "wb") as f:
                f.write(verified_code)
        except Exception as e:
            print(f"[AutoUpdate] Could not write verified update to disk: {e}")
            _autoupdate_relaunch_triggered = False
            return
    else:
        # Local file-edit trigger, not a version update -- nothing remote to verify,
        # just carry the just-edited file's content over to the autostart copy.
        try:
            shutil.copyfile(script_path, os.path.join(folder, f"{base_name}_autostarteverything.py"))
        except Exception as e:
            print(f"[AutoUpdate] Could not copy edited file: {e}")
            _autoupdate_relaunch_triggered = False
            return

    _write_video_id_json(folder)
    flags = _write_autostart_flags_json(folder)

    if realpc_config.get("enabled"):
        print("[AutoUpdate] NOTE: Real PC Control was enabled before this relaunch. "
              "It will NOT auto-resume for safety -- go to the Real PC Control tab "
              "and click Start again once the new instance is up.")

    if platform.system() == "Darwin":
        script_path = _generate_relaunch_script_macos(folder, base_name, flags)
        if not script_path:
            _autoupdate_relaunch_triggered = False
            return
        try:
            # osascript + Terminal.app is the macOS equivalent of Windows'
            # CREATE_NEW_CONSOLE -- subprocess.Popen alone would run the script hidden
            # in the background, with no visible window to see progress or errors in.
            osa = f'tell application "Terminal" to do script "\\"{script_path}\\""'
            subprocess.Popen(["osascript", "-e", osa], close_fds=True)
            print(f"[AutoUpdate] Launched {os.path.basename(script_path)} in a new Terminal window. Exiting so it can take over...")
        except Exception as e:
            print(f"[AutoUpdate] Failed to launch relaunch script: {e}")
            _autoupdate_relaunch_triggered = False
            return
        time.sleep(1.0)
        os._exit(0)
        return

    batch_path = _generate_relaunch_batch(folder, base_name, flags)
    if not batch_path:
        _autoupdate_relaunch_triggered = False
        return

    try:
        subprocess.Popen(["cmd", "/c", batch_path], creationflags=0x00000010,  # CREATE_NEW_CONSOLE
                          cwd=folder, close_fds=True)
        print(f"[AutoUpdate] Launched {os.path.basename(batch_path)}. Exiting so it can take over...")
    except Exception as e:
        print(f"[AutoUpdate] Failed to launch batch file: {e}")
        _autoupdate_relaunch_triggered = False
        return

    time.sleep(1.0)
    os._exit(0)   # hard exit -- the batch file's taskkill would get us anyway

def _ver_tuple_v2(v):
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except Exception:
        return (0, 0, 0)

def _autoupdate_watcher():
    """Runs the whole time the bot is open. Checks AUTOUPDATE_VERSION_URL once a
    second using a conditional GET (If-None-Match/ETag) so repeated checks are cheap
    304 responses -- logs nothing on a normal check, only when a new version is
    actually found or on a real (non-network-hiccup) error."""
    import urllib.request
    import urllib.error
    last_etag = None
    consecutive_errors = 0
    while app_instance is None or app_instance.running:
        time.sleep(AUTOUPDATE_POLL_INTERVAL)
        if app_instance is not None and not app_instance.running:
            break
        try:
            req = urllib.request.Request(AUTOUPDATE_VERSION_URL)
            if last_etag:
                req.add_header("If-None-Match", last_etag)
            with urllib.request.urlopen(req, timeout=5) as resp:
                last_etag = resp.headers.get("ETag", last_etag)
                data = json.loads(resp.read().decode("utf-8"))
            consecutive_errors = 0
            version_filename = str(data.get("filename", "")).strip()
            if version_filename and version_filename != CURRENT_FILENAME:
                # Same "shared version.json across multiple variants" safety check as
                # _check_for_update() -- if it's declared for a different file, this
                # isn't a real update for THIS script, so don't act on it.
                continue
            latest_ver = str(data.get("version", "0.0.0")).strip()
            if _ver_tuple_v2(latest_ver) > _ver_tuple_v2(VERSION):
                print(f"[AutoUpdate] New version detected: {latest_ver} (current: {VERSION}).")
                trigger_relaunch_pipeline(f"New version {latest_ver} available", version_data=data)
                break
        except urllib.error.HTTPError as e:
            if e.code == 304:
                consecutive_errors = 0   # not modified -- totally normal, stay silent
            else:
                consecutive_errors += 1
                if consecutive_errors in (1, 300) or consecutive_errors % 1800 == 0:
                    print(f"[AutoUpdate] Version check failed (HTTP {e.code}). Will keep retrying quietly.")
        except Exception:
            consecutive_errors += 1
            if consecutive_errors in (1, 300) or consecutive_errors % 1800 == 0:
                print("[AutoUpdate] Version check failed (network). Will keep retrying quietly.")

def _file_edit_watchdog():
    """Watches THIS running .py file's own modified-time once a second (whether this
    is the main GUI instance or one spawned just for the web dashboard -- both are
    just running some .py file) and relaunches via the same pipeline if it changes
    on disk, e.g. because you edited it or something else replaced it."""
    script_path, _, _ = _script_paths()
    try:
        last_mtime = os.path.getmtime(script_path)
    except Exception:
        return
    while app_instance is None or app_instance.running:
        time.sleep(1)
        if app_instance is not None and not app_instance.running:
            break
        try:
            mtime = os.path.getmtime(script_path)
            if mtime != last_mtime:
                last_mtime = mtime
                trigger_relaunch_pipeline(f"{os.path.basename(script_path)} was modified on disk")
                break
        except Exception:
            pass   # file briefly missing mid-write, etc. -- just try again next second


# Show the splash immediately — before any heavy imports — so the user
# sees something within milliseconds of launching the script.

_splash_root   = None
_splash_bar    = None
_splash_label  = None
_splash_pct    = None
_host_root     = None   # the one-and-only tk.Tk() instance (kept hidden during splash)

def _create_splash():
    global _splash_root, _splash_bar, _splash_label, _splash_pct, _host_root

    # Create the single tk.Tk() host window and keep it hidden.
    # All ttk styles will be registered on this interpreter.
    _host_root = tk.Tk()
    _host_root.withdraw()

    W, H = 480, 220
    # Splash is a Toplevel so it shares the same Tk interpreter
    splash = tk.Toplevel(_host_root)
    splash.title("")
    splash.resizable(False, False)
    splash.overrideredirect(True)          # borderless window
    sw = splash.winfo_screenwidth()
    sh = splash.winfo_screenheight()
    x  = (sw - W) // 2
    y  = (sh - H) // 2
    splash.geometry(f"{W}x{H}+{x}+{y}")
    splash.configure(bg="#0f0f1a")

    # Border frame
    border = tk.Frame(splash, bg="#7c5cbf", padx=2, pady=2)
    border.place(relx=0, rely=0, relwidth=1, relheight=1)
    inner = tk.Frame(border, bg="#0f0f1a")
    inner.pack(fill="both", expand=True)

    # "Script by Nexovative"
    tk.Label(inner, text="Script by Nexovative",
             bg="#0f0f1a", fg="#f0c060",
             font=("Segoe UI", 11, "bold")).pack(pady=(22, 0))

    # App title
    tk.Label(inner, text="VirtualBox Chat Bot",
             bg="#0f0f1a", fg="#ffffff",
             font=("Segoe UI", 18, "bold")).pack(pady=(4, 0))

    # Status label
    _splash_label = tk.Label(inner, text="Loading GUI...",
                              bg="#0f0f1a", fg="#aaaaaa",
                              font=("Segoe UI", 9))
    _splash_label.pack(pady=(14, 4))

    # Progress bar container
    bar_bg = tk.Frame(inner, bg="#1e1e2e", height=18, width=380)
    bar_bg.pack(pady=(0, 8))
    bar_bg.pack_propagate(False)

    _splash_bar = tk.Frame(bar_bg, bg="#3ddc97", width=0, height=18)
    _splash_bar.place(x=0, y=0, relheight=1)

    _splash_pct = tk.Label(inner, text="0%",
                            bg="#0f0f1a", fg="#3ddc97",
                            font=("Segoe UI", 8))
    _splash_pct.pack()

    _splash_root = splash
    splash.lift()
    # splash.attributes("-topmost", True)  # removed: caused splash to stay always on top
    splash.update()

def _update_splash(pct, label=None):
    """Update progress bar (0-100) and optional status text (call from main thread)."""
    if _splash_root is None:
        return
    try:
        bar_width = int(380 * pct / 100)
        _splash_bar.place(x=0, y=0, relheight=1, width=bar_width)
        _splash_pct.configure(text=f"{pct}%")
        if label:
            _splash_label.configure(text=label)
        _splash_root.update()
    except Exception:
        pass

def _close_splash():
    global _splash_root
    if _splash_root:
        try:
            _splash_root.destroy()   # destroy only the Toplevel splash
        except Exception:
            pass
        _splash_root = None
    # _host_root stays alive — it becomes the main window

# ── Show splash immediately ──
_create_splash()
_update_splash(5, "Loading GUI...")
_check_for_update()   # checks GitHub, asks user if update available, restarts if accepted


try:
    import virtualbox
    vbox_pkg = "virtualbox"
except ImportError:
    try:
        from vboxapi import VirtualBoxManager
        vbox_pkg = "vboxapi"
    except ImportError: vbox_pkg = None

try:
    import obsws_python as obs
    obs_available = True
except ImportError: obs_available = False

try:
    from flask import Flask, jsonify, render_template_string
    import logging as flask_logging
    flask_available = True
except ImportError: flask_available = False

try:
    import pytchat
    pytchat_available = True
except ImportError: pytchat_available = False

# --- Additional optional deps (ported from VBOX-Script-Linux.py) ---
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    pyautogui_available = True
except ImportError:
    pyautogui = None
    pyautogui_available = False

try:
    from vncdotool import api as _vnc_api
    vncdotool_available = True
except ImportError:
    _vnc_api = None
    vncdotool_available = False

try:
    import pyttsx3 as _pyttsx3
    pyttsx3_available = True
except ImportError:
    _pyttsx3 = None
    pyttsx3_available = False

try:
    from gtts import gTTS as _gTTS
    gtts_available = True
except ImportError:
    _gTTS = None
    gtts_available = False

try:
    import pystray
    from PIL import Image as _TrayImage, ImageDraw as _TrayDraw
    pystray_available = True
except ImportError:
    pystray_available = False

try:
    import pytesseract
    from PIL import Image
    ocr_available = True
except ImportError:
    ocr_available = False

try:
    from plyer import notification as _plyer_notification
    plyer_available = True
except ImportError:
    plyer_available = False

try:
    import yt_dlp
    ytdlp_available = True
except ImportError:
    yt_dlp = None
    ytdlp_available = False

try:
    import vlc as _vlc
    vlc_available = True
except ImportError:
    _vlc = None
    vlc_available = False

instance_id = 1
for arg in sys.argv:
    if arg == "--multistream": instance_id = 2
    elif arg.startswith("--multistream") and arg != "--multistream":
        try: instance_id = int(arg.replace("--multistream", "")) + 1
        except Exception: pass

is_multistream = instance_id > 1
flask_port = 5000 + instance_id - 1
version = "v44.0.chaos_engine"

suffix = f"_multi{instance_id-1}" if instance_id > 2 else ("_multi" if instance_id == 2 else "")
settings_file = f"settings{suffix}.json"
stats_file = f"stats{suffix}.json"
log_file = f"server_log{suffix}.txt"
snap_file = f"snapshot{suffix}.txt"
session_file = f"session{suffix}.txt"
logs_file = f"logs{suffix}.json"
modlogs_file = f"modlogsandownerlogs{suffix}.json"
allmsglogs_file = f"allmsglogs{suffix}.json"
voteslogs_file = f"voteslogs{suffix}.json"
scancodes_file = "keycodes.json"
realpc_config_file = f"realpc_config{suffix}.json"
vbox_config_file = f"vbox_config{suffix}.json"
event_log_file = f"event_log{suffix}.json"
permissions_config_file = f"permissions_config{suffix}.json"
sound_config_file = f"sound_config{suffix}.json"
scheduler_config_file = f"scheduler_config{suffix}.json"
os_voting_config_file = f"os_voting_config{suffix}.json"
user_mgmt_file = f"user_mgmt{suffix}.json"
multi_stream_config_file = f"multi_stream_config{suffix}.json"
appearance_config_file = f"appearance_config{suffix}.json"
obs_config_file = f"obs_config{suffix}.json"
music_config_file = f"music_config{suffix}.json"
soundboard_config_file = f"soundboard_config{suffix}.json"
video_config_file = f"video_config{suffix}.json"

refresh_rate = 100  
keyboard_layout = "US" 
available_layouts = ["US", "UK", "DANISH", "TURKISH", "GERMAN", "FRENCH"]
vote_timeout = 60

obs_host = "localhost"
obs_port = 4454 + instance_id  
obs_password = ""  
obs_scene_main = "main2" if is_multistream else "main"
obs_scene_revert = "revert2" if is_multistream else "revert"
obs_scene_error = "serverdown2" if is_multistream else "serverdown"
obs_scene_changevm = "changevm2" if is_multistream else "changevm"
obs_scene_starting = "starting2" if is_multistream else "starting"

admins = [] 
owners = ["reallyiron"]
gui_log_queue = queue.Queue(maxsize=300)
log_lock = threading.Lock()

def script_dir():
    """Folder the script itself lives in -- used to look for exported *.json files the user
    dropped alongside it (settings/music_config/video_config/etc.) so they can be auto-imported
    on startup instead of needing to click 'Import as JSON' in every tab."""
    try: return os.path.dirname(os.path.abspath(__file__))
    except Exception: return os.getcwd()

_auto_imported_json_hints = set()  # filename_hints already checked this run, so a manual Import
                                    # (which rebuilds the tab, re-running add_json_io_bar) doesn't
                                    # trigger a second auto-import on top of it.

def safe_json_dump(filename, data):
    tmp_file = filename + ".tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)
        os.replace(tmp_file, filename)
    except Exception:
        try:
            with open(filename, "w", encoding="utf-8") as f: json.dump(data, f, indent=4)
        except Exception: pass

def append_to_json_log(filename, user, command):
    try:
        with log_lock:
            entry = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "username": user, "command": command}
            logs = []
            if os.path.exists(filename):
                try:
                    with open(filename, "r", encoding="utf-8") as f: logs = json.load(f)
                except Exception: pass
            logs.append(entry)
            if len(logs) > 1000: logs = logs[-1000:]
            safe_json_dump(filename, logs)
    except Exception: pass

def append_to_all_msgs_log(user, msg):
    try:
        with log_lock:
            entry = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "username": user, "message": msg}
            with open(allmsglogs_file, "a", encoding="utf-8") as f: f.write(json.dumps(entry) + "\n")
    except Exception: pass

def log_vote_action(action, user, vote_type, target, current_votes=0):
    try:
        with log_lock:
            entry = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": action.lower(), "user": user, "vote": vote_type, "progress": f"{current_votes}/{target}" if current_votes else str(target)}
            logs = []
            if os.path.exists(voteslogs_file):
                try:
                    with open(voteslogs_file, "r", encoding="utf-8") as f: logs = json.load(f)
                except Exception: pass
            logs.append(entry)
            if len(logs) > 1000: logs = logs[-1000:]
            safe_json_dump(voteslogs_file, logs)
    except Exception: pass

def _capitalize_each_word(text):
    """Capitalizes the first letter of every whitespace-separated word, leaving the rest
    of each word's casing untouched -- unlike str.title(), which mangles acronyms (VM, OBS,
    TTS, URL) and adds spurious capitals after apostrophes (don't -> Don'T). Used to format
    every log line consistently."""
    if not isinstance(text, str) or not text:
        return text
    def _cap_word(w):
        for i, c in enumerate(w):
            if c.isalpha():
                return w[:i] + c.upper() + w[i+1:]
        return w
    return ' '.join(_cap_word(w) for w in text.split(' '))

def console_log(level, msg):
    timestamp = time.strftime("%H:%M:%S")
    date_stamp = time.strftime("%Y-%m-%d")
    msg = _capitalize_each_word(msg)
    log_line = f"[{timestamp}] [{level.lower()}] {msg}"
    print(log_line, flush=True)
    try: gui_log_queue.put_nowait((level, log_line))
    except queue.Full: pass
    try:
        with log_lock:
            with open(log_file, "a", encoding="utf-8") as f: f.write(f"[{date_stamp} {timestamp}] [{level.lower()}] {msg}\n")
    except Exception: pass
    # EVERY log -- not just self.log() calls from the App class -- also flows into the same
    # chat/overlay history feed (web_chat_history), so it shows up on the OBS overlay and the
    # multi-stream sync too, not just the internal debug console.
    try:
        hist_msg = msg if level.upper() != "ERROR" else f"[err] {msg}"
        add_to_history("[system]", hist_msg, "sysmsg", is_mod=True, is_owner=True)
    except Exception: pass

possible_paths = [
    r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe",
    r"C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe",
    "/Applications/VirtualBox.app/Contents/MacOS/VBoxManage",
    "/usr/bin/VBoxManage", "/usr/local/bin/VBoxManage", "VBoxManage",
]
vbox_manage_cmd = "VBoxManage"
for path in possible_paths:
    if os.path.exists(path):
        vbox_manage_cmd = path
        break

vmrun_possible_paths = [
    r"C:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe",
    r"C:\Program Files\VMware\VMware Workstation\vmrun.exe",
    r"D:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe",
    r"E:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe",
    "/Applications/VMware Fusion.app/Contents/Library/vmrun",
    "/usr/bin/vmrun", "/usr/local/bin/vmrun", "vmrun",
]
vmrun_cmd = "vmrun"
for path in vmrun_possible_paths:
    if os.path.exists(path):
        vmrun_cmd = path
        break

_FLOOD_APP_POOL = ["notepad", "calc", "mspaint", "charmap", "osk", "magnify"]

# Commands gated by the "VM Control" toggle on the Dashboard (SYSTEM CONTROLS card) -- flipping
# it off blocks all of these for EVERYONE, including admins/console, while leaving every other
# command (soundboard, tts, keyboard/mouse, etc.) working normally.
VM_CONTROL_COMMANDS = {
    "!startvm", "!shutdown", "!killvm", "!restartvm", "!revert", "!makesnapshot",
    "!forcefixvm", "!efail", "!poweroff", "!pausevm", "!resumevm", "!vmsavestate",
    "!vmstatus", "!acpishutdown", "!acpirestart", "!deletesnapshot",
    "!enableinternet", "!disableinternet", "!discardvmwarestate",
}

def get_all_vbox_vms(vbox_path="VBoxManage"):
    """Returns every VM registered with VirtualBox (VBoxManage lists these natively --
    unlike vmrun, there's no need for a local alias->path registry file)."""
    vms = []
    try:
        res = subprocess.run([vbox_path, "list", "vms"], capture_output=True, text=True, timeout=5)
        for line in res.stdout.splitlines():
            if '"' in line: vms.append(line.split('"')[1])
    except Exception: pass
    return vms if vms else [""]

def get_vbox_snapshots(vbox_path, vm_name):
    """Lists snapshot names for a VM via 'VBoxManage snapshot <vm> list'."""
    snaps = []
    try:
        res = subprocess.run([vbox_path, "snapshot", vm_name, "list"], capture_output=True, text=True, timeout=15)
        for line in res.stdout.splitlines():
            if "Name:" in line and "(UUID:" in line:
                part = line.split("Name:")[1].split("(UUID:")[0].strip()
                if part: snaps.append(part)
    except Exception: pass
    return snaps

# vmrun has no "list all registered VMs" command (only currently-running ones), so VMware
# VMs are tracked locally by alias -> .vmx path in a small registry file.
vmware_vm_registry_file = "vmware_vms.json"

def _load_vmware_vm_registry():
    try:
        if os.path.exists(vmware_vm_registry_file):
            with open(vmware_vm_registry_file, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception: pass
    return {}

def _save_vmware_vm_registry(registry):
    safe_json_dump(vmware_vm_registry_file, registry)

def register_vmware_vm(vmx_path, alias=None):
    """Adds a .vmx to the local registry so it shows up in get_all_vmware_vms()."""
    registry = _load_vmware_vm_registry()
    alias = alias or os.path.splitext(os.path.basename(vmx_path))[0]
    registry[alias] = vmx_path
    _save_vmware_vm_registry(registry)
    return alias

def get_all_vmware_vms(vmrun_path="vmrun"):
    """Returns known .vmx paths: everything in the local registry, plus anything vmrun
    currently reports as running (auto-registered if not already known)."""
    registry = _load_vmware_vm_registry()
    vms = list(registry.values())
    try:
        res = subprocess.run([vmrun_path, "-T", VMRUN_TARGET_TYPE, "list"], capture_output=True, text=True, timeout=5)
        for line in res.stdout.splitlines():
            line = line.strip()
            if line.lower().endswith(".vmx") and line not in vms:
                vms.append(line)
                register_vmware_vm(line)
    except Exception: pass
    return vms if vms else [""]

def get_vmware_snapshots(vmrun_path, vmx_path):
    """Lists snapshot names for a .vmx via 'vmrun listSnapshots'."""
    snaps = []
    try:
        res = subprocess.run([vmrun_path, "-T", VMRUN_TARGET_TYPE, "listSnapshots", vmx_path], capture_output=True, text=True, timeout=15)
        for line in res.stdout.splitlines():
            line = line.strip()
            if line and not line.lower().startswith("total snapshot"):
                snaps.append(line)
    except Exception: pass
    return snaps

available_vms = get_all_vbox_vms(vbox_manage_cmd)

vm_name = ""  # holds the CURRENTLY ACTIVE vm's identifier -- a VirtualBox VM name if
              # current_vm_backend == "vbox", or a .vmx file path if == "vmware"
current_vm_backend = "vbox"  # "vbox" or "vmware" -- which backend controls vm_name right now.
                              # Every VM-lifecycle and keyboard/mouse function branches on this.
                              # Set from the VM Config panel's backend choice in single-VM mode,
                              # or updated automatically by switch_os() to match whichever OS
                              # Voting row is currently active. Real PC is unaffected either way --
                              # it always uses its own separate VNC target, never this.

default_blocked_terms = [] 
banned_words = []
custom_commands = {}

default_keydata = {"RAW":{"esc":[1],"1":[2],"2":[3],"3":[4],"4":[5],"5":[6],"6":[7],"7":[8],"8":[9],"9":[10],"0":[11],"-":[12],"=":[13],"backspace":[14],"tab":[15],"q":[16],"w":[17],"e":[18],"r":[19],"t":[20],"y":[21],"u":[22],"i":[23],"o":[24],"p":[25],"[":[26],"]":[27],"enter":[28],"ctrl":[29],"lctrl":[29],"rctrl":[224,29],"a":[30],"s":[31],"d":[32],"f":[33],"g":[34],"h":[35],"j":[36],"k":[37],"l":[38],";":[39],"'":[40],"`":[41],"shift":[42],"lshift":[42],"\\":[43],"z":[44],"x":[45],"c":[46],"v":[47],"b":[48],"n":[49],"m":[50],",":[51],".":[52],"/":[53],"rshift":[54],"alt":[56],"lalt":[56],"ralt":[224,56],"space":[57],"capslock":[58],"f1":[59],"f2":[60],"f3":[61],"f4":[62],"f5":[63],"f6":[64],"f7":[65],"f8":[66],"f9":[67],"f10":[68],"f11":[87],"f12":[88],"numlock":[69],"scrolllock":[70],"home":[224,71],"up":[224,72],"pageup":[224,73],"left":[224,75],"right":[224,77],"end":[224,79],"down":[224,80],"pagedown":[224,81],"insert":[224,82],"delete":[224,83],"del":[224,83],"win":[224,91],"lwin":[224,91],"rwin":[224,92],"menu":[224,93],"plus":[13],"minus":[12],"return":[28],"numpad0":[82],"numpad1":[79],"numpad2":[80],"numpad3":[81],"numpad4":[75],"numpad5":[76],"numpad6":[77],"numpad7":[71],"numpad8":[72],"numpad9":[73],"numpad_dot":[83],"numpad_enter":[224,28],"numpad_plus":[78],"numpad_minus":[74],"numpad_mul":[55],"numpad_div":[224,53],"printscreen":[224,55,224,183],"pause":[225,29,69,225,157,197],"vol_mute":[224,32],"vol_down":[224,46],"vol_up":[224,48],"media_next":[224,25],"media_prev":[224,16],"media_stop":[224,36],"media_play_pause":[224,34]},"LAYOUTS":{"US":{"noshift":{'1':[0x02],'2':[0x03],'3':[0x04],'4':[0x05],'5':[0x06],'6':[0x07],'7':[0x08],'8':[0x09],'9':[0x0A],'0':[0x0B],'q':[0x10],'w':[0x11],'e':[0x12],'r':[0x13],'t':[0x14],'y':[0x15],'u':[0x16],'i':[0x17],'o':[0x18],'p':[0x19],'a':[0x1E],'s':[0x1F],'d':[0x20],'f':[0x21],'g':[0x22],'h':[0x23],'j':[0x24],'k':[0x25],'l':[0x26],'z':[0x2C],'x':[0x2D],'c':[0x2E],'v':[0x2F],'b':[0x30],'n':[0x31],'m':[0x32],' ':[0x39],'-':[0x0C],'=':[0x0D],'[':[0x1A],']':[0x1B],'\\':[0x2B],';':[0x27],'\'':[0x28],'`':[0x29],',':[0x33],'.':[0x34],'/':[0x35]},"shift":{'!':[0x02],'@':[0x03],'#':[0x04],'$':[0x05],'%':[0x06],'^':[0x07],'&':[0x08],'*':[0x09],'(':[0x0A],')':[0x0B],'_':[0x0C],'+':[0x0D],'{':[0x1A],'}':[0x1B],'|':[0x2B],':':[0x27],'"':[0x28],'~':[0x29],'<':[0x33],'>':[0x34],'?':[0x35]},"altgr":{}}}}

_needs_update = False
if os.path.exists(scancodes_file):
    try:
        with open(scancodes_file, "r", encoding="utf-8") as f: _loaded_data = json.load(f)
        if "LAYOUTS" not in _loaded_data or "RAW" not in _loaded_data: _needs_update = True
    except Exception: _needs_update = True
else: _needs_update = True

if _needs_update:
    try:
        with open(scancodes_file, "w", encoding="utf-8") as f: json.dump(default_keydata, f, indent=4, ensure_ascii=False)
        _loaded_data = default_keydata.copy()
    except Exception: _loaded_data = default_keydata.copy()

scancodes = _loaded_data["RAW"]
_layouts = _loaded_data["LAYOUTS"]

def parse_combo_keys(args):
    """Splits a combo argument string into individual key names, accepting THREE
    interchangeable input styles: space-separated ('win r'), plus-separated
    ('win+r'), or no separator at all ('winr'). Mirrors the same tokenizer used
    for the VMware/VBox nexovative scripts' !combo, just against this file's own
    scancodes dict.

    If a space or '+' is present anywhere, that's unambiguous -- just split on it.
    Only when there's NO separator at all does this fall back to a greedy
    longest-match scan against known key names in scancodes (checked longest name
    first)."""
    text = (args or "").strip().lower()
    if not text:
        return []
    if ' ' in text or '+' in text:
        return [k for k in text.replace('+', ' ').split() if k]
    known_keys = sorted(scancodes.keys(), key=len, reverse=True)
    result = []
    i = 0
    while i < len(text):
        for k in known_keys:
            if text.startswith(k, i):
                result.append(k)
                i += len(k)
                break
        else:
            result.append(text[i:])
            break
    return result

def get_typed_codes(char, layout="US"):
    SHIFT = [[0x2A]]
    ALTGR = [[0x1D], [0xE0, 0x38]]
    target = _layouts.get(layout, _layouts["US"])
    active_no = target.get("noshift", {})
    active_sh = target.get("shift", {})
    active_al = target.get("altgr", {})
    if char in active_sh: return (SHIFT, active_sh[char])
    if char in active_al: return (ALTGR, active_al[char])
    if char in active_no: return ([], active_no[char])
    char_lower = char.lower()
    if char.isupper() and char_lower in active_no: return (SHIFT, active_no[char_lower])
    if char_lower != char and char_lower in active_no: return (SHIFT, active_no[char_lower])
    if char_lower in active_no: return ([], active_no[char_lower])
    us = _layouts["US"]
    if char in us["shift"]: return (SHIFT, us["shift"][char])
    if char in us["noshift"]: return ([], us["noshift"][char])
    if char.isupper() and char_lower in us["noshift"]: return (SHIFT, us["noshift"][char_lower])
    if char_lower in us["noshift"]: return ([], us["noshift"][char_lower])
    return ([], [0])

# === Chat command lookup tables ===
# Maps a bare "!app" chat command to the string typed into the Win+R "Run" box.
# Best-effort exe/UWP names -- some legacy games vary by Windows version.
APP_RUN_MAP = {
    "notepad": "notepad", "calc": "calc", "paint": "mspaint", "wordpad": "write",
    "cmdnew": "cmd", "powershell": "powershell", "regedit": "regedit", "explorer": "explorer",
    "ie": "iexplore", "wmp": "wmplayer", "control": "control", "devmgr": "devmgmt.msc",
    "taskmgrapp": "taskmgr", "sticky": "StikyNot", "snip": "SnippingTool", "magnify": "magnify",
    "narrator": "narrator", "osk": "osk", "charmap": "charmap", "eventvwr": "eventvwr.msc",
    "perfmon": "perfmon", "resmon": "resmon", "defrag": "dfrgui", "cleanmgr": "cleanmgr",
    "msconfig": "msconfig", "dxdiag": "dxdiag", "sndvol": "sndvol", "dvdmaker": "dvdmaker",
    "solitaire": "sol", "minesweeper": "winmine", "hearts": "mshearts", "spider": "spider",
    "freecell": "freecell", "mahjong": "mahjong", "chess": "chess", "inkball": "inkball",
    "purble": "purblebrain",
}

# Maps a bare "!shortcut" chat command to a "mod+key" string fed straight into the
# existing !combo handler (which already supports single keys with no modifier).
COMBO_SHORTCUTS = {
    "altf4": "alt+f4", "alttab": "alt+tab", "copy": "ctrl+c", "paste": "ctrl+v", "cut": "ctrl+x",
    "undo": "ctrl+z", "redo": "ctrl+y", "selectall": "ctrl+a", "save": "ctrl+s", "saveas": "ctrl+shift+s",
    "find": "ctrl+f", "replace": "ctrl+h", "new": "ctrl+n", "closetab": "ctrl+w",
    "zoomin": "ctrl+=", "zoomout": "ctrl+-", "zoomreset": "ctrl+0", "fullscreen": "f11",
    "refresh": "f5", "hardrefresh": "ctrl+f5", "back": "alt+left", "forward": "alt+right",
    "bold": "ctrl+b", "italic": "ctrl+i", "underline": "ctrl+u", "capslock": "capslock",
    "numlock": "numlock", "scrolllock": "scrolllock", "prtsc": "printscreen",
    "altprintscreen": "alt+printscreen", "desktop": "win+d", "lock": "win+l",
    "taskman": "ctrl+shift+esc", "startmenu": "win",
}

# Maps a bare "!cmdutility" chat command to text typed (then Enter) into an already-focused
# cmd.exe window -- pair these with !cmdnew first, exactly like the in-game help text says.
CMD_TYPED_MAP = {
    "tasklist": "tasklist", "cls": "cls", "tree": "tree", "ver": "ver", "date": "date /t",
    "time": "time /t", "diskpart": "diskpart", "chkdsk": "chkdsk", "sfc": "sfc /scannow",
    "gpupdate": "gpupdate /force", "abortshutdown": "shutdown /a", "logoff": "shutdown /l",
    "hibernate": "shutdown /h",
}

# Small pool of harmless built-in apps used by the chaos "flood" commands.
_FLOOD_APP_POOL = ["notepad", "calc", "mspaint", "charmap", "osk", "magnify"]

global_msg_id = 0
web_chat_history = collections.deque(maxlen=50)
history_lock = threading.Lock()
messages_buffer = collections.deque(maxlen=200)
buffer_lock = threading.Lock()
script_start_time = time.time()
total_commands_executed = 0
total_commands_failed = 0
stats_lock = threading.Lock()

try:
    if os.path.exists(stats_file):
        with open(stats_file, "r") as f:
            _saved = json.load(f)
            total_commands_executed = _saved.get("commands", 0)
            total_commands_failed = _saved.get("failed", 0)
            script_start_time = time.time() - _saved.get("uptime", 0)
except Exception: pass

def save_stats():
    try:
        uptime = int(time.time() - script_start_time)
        with stats_lock:
            tmp_file = stats_file + ".tmp"
            with open(tmp_file, "w") as f: json.dump({"uptime": uptime, "commands": total_commands_executed, "failed": total_commands_failed, "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")}, f)
            os.replace(tmp_file, stats_file)
    except Exception: pass

current_status = "initializing..."
current_vote_info = {"active": False, "text": ""}
current_viewers = "0"
current_likes = "0"
overlay_chat_visible = True
split_overlay_mode = False

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    print("\n==================================================")
    print("critical script error encountered:")
    print("==================================================")
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    print("==================================================\n")
    try:
        with open("crash_log.txt", "w") as f: traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
        if 'main_gui_application' in globals():
            main_gui_application.log("[system]", f"[err] FATAL RAW CRASH: {exc_type.__name__}: {exc_value}", "err")
    except Exception: pass
    set_obs_scene(obs_scene_error)
sys.excepthook = handle_exception

def clean_text(text):
    if not isinstance(text, str): return str(text)
    return ''.join(c for c in text if c <= '\uFFFF')

def escape_html(text):
    if not isinstance(text, str): return str(text)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")

def add_to_history(user, msg, tag, is_mod=False, is_owner=False, pfp_url=""):
    global global_msg_id
    global_msg_id += 1
    safe_user = escape_html(user)
    safe_msg = escape_html(msg)
    msg_obj = {"id": global_msg_id, "u": safe_user, "m": safe_msg, "t": tag, "is_admin": is_mod, "is_owner": is_owner, "img": pfp_url or ""}
    with buffer_lock: messages_buffer.append(msg_obj)
    with history_lock: web_chat_history.append(msg_obj)

_obs_scene_retry_lock = threading.Lock()
_obs_scene_retry_running = False
_obs_scene_target = None

def set_obs_scene(scene_name):
    """Requests an OBS scene switch. If OBS/websocket isn't reachable on the first try,
    this keeps retrying with backoff until it succeeds -- it never just gives up. Calling
    this again while a retry is already in progress simply updates the target scene
    (coalesced into the single retry worker) instead of piling up parallel retry threads."""
    global _obs_scene_target, _obs_scene_retry_running
    try:
        if not obs_available: return
        _obs_scene_target = scene_name
        with _obs_scene_retry_lock:
            if _obs_scene_retry_running: return
            _obs_scene_retry_running = True
        threading.Thread(target=_obs_scene_retry_worker, daemon=True).start()
    except Exception: pass

def _obs_scene_retry_worker():
    global _obs_scene_retry_running
    delay = 1.0
    try:
        while True:
            target = _obs_scene_target
            if target is None: break
            try:
                if verbose_conn_logging_enabled():
                    console_log("INFO", f"[websocket] connecting to {obs_host}:{obs_port} to switch OBS scene to '{target}'...")
                cl = obs.ReqClient(host=obs_host, port=obs_port, password=obs_password, timeout=3) if obs_password else obs.ReqClient(host=obs_host, port=obs_port, timeout=3)
                cl.set_current_program_scene(target)
                if verbose_conn_logging_enabled():
                    console_log("INFO", f"[websocket] disconnected after switching scene to '{target}'.")
                if _obs_scene_target == target:
                    break  # nothing newer requested while we were working -- done
                delay = 1.0
                continue  # a newer scene was requested mid-retry; go apply that one now
            except Exception as e:
                hint = ""
                if "authentication" in str(e).lower() or "password" in str(e).lower():
                    hint = " -- OBS's WebSocket Server has a password set (Tools > WebSocket Server Settings in OBS); copy it into the Password field on this bot's OBS tab."
                console_log("WARN", f"[websocket] OBS scene switch to '{target}' failed ({e}){hint}, retrying in {delay:.0f}s...")
                time.sleep(delay)
                delay = min(delay * 1.5, 30.0)
    finally:
        with _obs_scene_retry_lock:
            _obs_scene_retry_running = False

if flask_available:
    obs_web_overlay_app = Flask(__name__)
    flask_log = flask_logging.getLogger('werkzeug')
    flask_log.setLevel(flask_logging.ERROR)
    @obs_web_overlay_app.after_request
    def add_cors_headers(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    html_index = """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Chat Controls</title><style>body{background:#09090b;color:#00E5FF;font-family:'Segoe UI',Consolas,monospace;text-align:center;padding:40px}h1{color:#10B981;font-size:36px;text-shadow:0 0 10px rgba(16,185,129,0.3);margin-bottom:5px}.grid{display:flex;flex-wrap:wrap;gap:20px;justify-content:center;max-width:800px;margin:40px auto}a{background:#18181b;border:1px solid #27272a;color:#fff;text-decoration:none;padding:20px;border-radius:12px;width:300px;transition:all 0.2s;box-shadow:0 4px 6px rgba(0,0,0,0.3);text-align:left}a:hover{transform:translateY(-5px);border-color:#00E5FF;box-shadow:0 8px 15px rgba(0,229,255,0.2)}.title{font-size:20px;font-weight:bold;margin-bottom:10px;color:#00E5FF}.desc{font-size:14px;color:#a1a1aa}</style></head><body><h1>[active] chat server active</h1><p style="color:#71717a;font-size:18px">Add one of these links to your OBS Browser Source:</p><div class="grid"><a href="/obsnew"><div class="title">Liquid Glass Chat (/obsnew)</div><div class="desc">Sleek gray bubbles with a glass background.</div></a><a href="/oldobsnew"><div class="title">Classic Dark Chat (/oldobsnew)</div><div class="desc">The OG dark background modern chat.</div></a><a href="/ultradebug"><div class="title">Ultra Debug (/ultradebug)</div><div class="desc">Shows core system status and queues.</div></a><a href="/stats"><div class="title">Live Stats (/stats)</div><div class="desc">Viewers, Likes, and Uptime widget.</div></a><a href="/obs"><div class="title">Legacy Chat (/obs)</div><div class="desc">The original transparent overlay.</div></a><a href="/status"><div class="title">Bot Status (/status)</div><div class="desc">Simple current-status text box.</div></a><a href="/osvotestatus"><div class="title">OS Vote Status (/osvotestatus)</div><div class="desc">Per-OS voting tally, highlights the currently running OS.</div></a><a href="/votes-overlay"><div class="title">Restart/Revert Votes (/votes-overlay)</div><div class="desc">Live progress bars for pending restart/revert votes.</div></a><a href="/banvote"><div class="title">Ban Vote (/banvote)</div><div class="desc">Progress toward the current ban vote, if any.</div></a></div></body></html>"""
    html_template = """<!DOCTYPE html><html><head><meta charset="UTF-8"><style>@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@500;700&display=swap');@keyframes slideIn{from{transform:translateX(20px);opacity:0}to{transform:translateX(0);opacity:1}}html,body{background-color:rgba(0,0,0,0)!important;margin:0;padding:0;width:100vw;height:100vh;overflow:hidden}body{font-family:'Fira Code','Consolas',monospace;display:flex;flex-direction:column;padding:10px;text-shadow:2px 2px 0 #000;color:#ccc;font-size:16px;justify-content:flex-end}.header{position:absolute;top:10px;right:10px;text-align:right;display:flex;flex-direction:column;align-items:flex-end;z-index:10}div[id="vote-text"]{font-family:'Impact',sans-serif;font-size:24px;color:red;text-transform:uppercase;margin-bottom:5px;text-shadow:2px 2px 0 #000;background:rgba(0,0,0,0.85);padding:5px 12px;border:1px solid #444;border-radius:4px;display:none}.stats-container{display:flex;gap:15px;font-family:'Fira Code',monospace;font-weight:bold;font-size:20px;align-items:center;background:rgba(0,0,0,0.85);padding:5px 12px;border:1px solid #444;border-radius:4px}.stat-item{display:flex;align-items:center;gap:6px}.icon-eye{fill:#0af;width:22px;height:22px;filter:drop-shadow(0 0 2px #0af)}.icon-thumb{fill:#0f0;width:22px;height:22px;filter:drop-shadow(0 0 2px #0f0)}.stat-text{color:#fff;text-shadow:0 0 2px #fff}.chat-box{flex-grow:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:flex-end;padding-bottom:10px;z-index:5}.line{font-size:18px;font-weight:500;margin-bottom:3px;color:#fff;line-height:1.3;word-wrap:break-word;overflow-wrap:break-word;display:flex;align-items:flex-start;justify-content:flex-end;width:100%;animation:slideIn 0.2s ease-out forwards}.admin-name{color:#5e84f1;font-weight:700;text-shadow:0 0 3px #5e84f1}.owner-name{color:#ffd700;font-weight:700;text-shadow:0 0 3px #ffd700}.user-name{color:#e0e0e0;font-weight:700}.sys-text{color:#f0f;font-weight:700;text-shadow:0 0 3px #f0f}.sys-msg-text{color:#0f0;font-weight:bold}.err-text{color:#f33;font-weight:bold}.msg-text{color:#fff}.separator{margin-right:8px;color:#888;font-weight:bold}</style></head><body><div class="header"><div id="vote-text">no active votes</div><div class="stats-container"><div class="stat-item"><svg class="icon-eye" viewBox="0 0 24 24"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.61 11 7.61s9.27-3.22 11-7.61C21.27 7.61 17 4.5 12 4.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg><span id="viewers" class="stat-text">0</span></div><div class="stat-item"><svg class="icon-thumb" viewBox="0 0 24 24"><path d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-1.91l-.01-.01L23 10z"/></svg><span id="likes" class="stat-text">0</span></div></div></div><div class="chat-box" id="chat"></div><script>let lastId=-1;let fetchingUpdates=!1;setInterval(function(){if(fetchingUpdates)return;fetchingUpdates=!0;fetch('/history?t='+Date.now()).then(r=>r.json()).then(data=>{if(data&&Array.isArray(data)){const c=document.getElementById('chat');if(!c)return;const fragment=document.createDocumentFragment();let added=!1;data.forEach(i=>{if(i.id>lastId){lastId=i.id;try{let nameClass="user-name";let msgClass="msg-text";if(i.is_owner){nameClass="owner-name";}else if(i.is_admin){nameClass="admin-name";}let u=i.u||"Unknown";let m=i.m||"";if(u==='[system]'||u==='system'){u="[system]";nameClass="sys-text";msgClass=m.includes("[err]")?"err-text":"sys-msg-text";}else if(u==='[console]'||u==='[announcement]'){nameClass="admin-name";}else{if(typeof u==='string'&&!u.startsWith('@'))u="@"+u;}const div=document.createElement('div');div.className='line';div.innerHTML=`<span class='${nameClass}'>${u}</span><span class="separator">:</span><span class='${msgClass}'>${m}</span>`;fragment.appendChild(div);added=!0;}catch(err){}}});if(added){c.appendChild(fragment);window.scrollTo(0,document.body.scrollHeight);while(c.children.length>50)c.removeChild(c.firstChild);}}fetchingUpdates=!1;}).catch(e=>{fetchingUpdates=!1;});},1000);let fetchingStatus=!1;setInterval(function(){if(fetchingStatus)return;fetchingStatus=!0;fetch('/status_update?t='+Date.now()).then(r=>r.json()).then(data=>{try{const v=document.getElementById('vote-text');const chatBox=document.getElementById('chat');const headerBox=document.querySelector('.header');if(chatBox){chatBox.style.display=data.chat_visible?'flex':'none';}if(headerBox){if(data.split_mode){headerBox.style.display='none';}else{headerBox.style.display='flex';if(v&&data.vote&&data.vote.active){v.innerHTML=(data.vote.text||"").replace('[vote] ','');v.style.display="block";}else if(v){v.style.display="none";}const viewEl=document.getElementById('viewers');const likeEl=document.getElementById('likes');if(viewEl)viewEl.innerText=data.viewers||"0";if(likeEl)likeEl.innerText=data.likes||"0";}}}catch(err){}fetchingStatus=!1;}).catch(e=>{fetchingStatus=!1;});},2000);</script></body></html>"""
    html_template_2 = """<!DOCTYPE html><html><head><meta charset="UTF-8"><style>@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@500;700&display=swap');html,body{background-color:rgba(0,0,0,0)!important;margin:0;padding:0;width:100vw;height:100vh;overflow:hidden}body{font-family:'Fira Code','Consolas',monospace;display:flex;flex-direction:column;align-items:flex-end;padding:3vw;box-sizing:border-box}.header{text-align:right;display:flex;flex-direction:column;align-items:flex-end}div[id="vote-text"]{font-family:'Impact',sans-serif;font-size:10vw;color:red;text-transform:uppercase;margin-bottom:2vw;text-shadow:0.5vw 0.5vw 0 #000;display:none;line-height:1}.stats-container{display:flex;gap:5vw;font-family:'Fira Code',monospace;font-weight:bold;font-size:8vw;align-items:center}.stat-item{display:flex;align-items:center;gap:2vw}.icon-eye{fill:#0af;width:9vw;height:9vw;filter:drop-shadow(0.4vw 0.4vw 0 #000)}.icon-thumb{fill:#0f0;width:9vw;height:9vw;filter:drop-shadow(0.4vw 0.4vw 0 #000)}.stat-text{color:#fff;text-shadow:0.4vw 0.4vw 0 #000}</style></head><body><div class="header"><div id="vote-text"></div><div class="stats-container"><div class="stat-item"><svg class="icon-eye" viewBox="0 0 24 24"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.61 11 7.61s9.27-3.22 11-7.61C21.27 7.61 17 4.5 12 4.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg><span id="viewers" class="stat-text">0</span></div><div class="stat-item"><svg class="icon-thumb" viewBox="0 0 24 24"><path d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-1.91l-.01-.01L23 10z"/></svg><span id="likes" class="stat-text">0</span></div></div></div><script>let fetchingStatus2=!1;setInterval(function(){if(fetchingStatus2)return;fetchingStatus2=!0;fetch('/status_update?t='+Date.now()).then(r=>r.json()).then(data=>{try{const v=document.getElementById('vote-text');if(data.vote&&data.vote.active){v.innerHTML=(data.vote.text||"").replace('[vote] ','');v.style.display="block";}else if(v){v.style.display="none";}const viewEl=document.getElementById('viewers');const likeEl=document.getElementById('likes');if(viewEl)viewEl.innerText=data.viewers||"0";if(likeEl)likeEl.innerText=data.likes||"0";}catch(err){}fetchingStatus2=!1;}).catch(e=>{fetchingStatus2=!1;});},2000);</script></body></html>"""
    html_template_new = """<!DOCTYPE html><html><head><meta charset="UTF-8"><style>@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');html,body{background-color:rgba(0,0,0,0)!important;margin:0;padding:0;width:100%;height:100%;overflow:hidden}body{font-family:'-apple-system','BlinkMacSystemFont','Inter',sans-serif;display:flex;flex-direction:column;padding:25px;justify-content:flex-end;box-sizing:border-box}.chat-box{display:flex;flex-direction:column;align-items:flex-end;gap:16px;width:100%}.msg-block{background:rgba(80,80,85,0.25);backdrop-filter:blur(25px) saturate(200%);-webkit-backdrop-filter:blur(25px) saturate(200%);padding:12px 18px;display:flex;align-items:flex-start;font-size:16px;border-radius:22px;box-shadow:0 8px 32px rgba(0,0,0,0.15),inset 0 1px 1px rgba(255,255,255,0.4);animation:popIn 0.35s cubic-bezier(0.175,0.885,0.32,1.2) forwards;max-width:90%;word-wrap:break-word;border:1px solid rgba(255,255,255,0.15);border-bottom:1px solid rgba(255,255,255,0.05)}.msg-block.cmd-border{box-shadow:0 8px 32px rgba(0,0,0,0.15),inset 0 1px 1px rgba(255,255,255,0.4),inset 4px 0 0 #00E5FF}.msg-block.chat-border{box-shadow:0 8px 32px rgba(0,0,0,0.15),inset 0 1px 1px rgba(255,255,255,0.4),inset 4px 0 0 #10B981}.msg-block.vote-border{box-shadow:0 8px 32px rgba(0,0,0,0.15),inset 0 1px 1px rgba(255,255,255,0.4),inset 4px 0 0 #F59E0B}.msg-block.err-border{box-shadow:0 8px 32px rgba(0,0,0,0.15),inset 0 1px 1px rgba(255,255,255,0.4),inset 4px 0 0 #EF4444}.msg-block.info-border{box-shadow:0 8px 32px rgba(0,0,0,0.15),inset 0 1px 1px rgba(255,255,255,0.4),inset 4px 0 0 #3B82F6}.badge{padding:4px 10px;font-weight:800;font-size:11px;border-radius:20px;margin-right:14px;flex-shrink:0;align-self:center;color:#fff;letter-spacing:0.8px;text-transform:uppercase;box-shadow:0 4px 10px rgba(0,0,0,0.2)}.badge.cmd{background:linear-gradient(135deg,#00E5FF,#0083B0)}.badge.chat{background:linear-gradient(135deg,#10B981,#047857)}.badge.vote{background:linear-gradient(135deg,#F59E0B,#B45309)}.badge.err{background:linear-gradient(135deg,#EF4444,#991B1B)}.badge.info{background:linear-gradient(135deg,#3B82F6,#1D4ED8)}.msg-content{display:flex;flex-direction:column;gap:2px}.username{font-weight:700;font-size:14px;letter-spacing:0.3px;text-shadow:0 1px 4px rgba(0,0,0,0.3)}.username.cmd{color:#40C4FF}.username.chat{color:#34D399}.username.vote{color:#FBBF24}.username.err{color:#FF8A8A}.username.info{color:#60A5FA}.message{color:#fff;font-weight:500;line-height:1.4;font-size:16px;text-shadow:0 1px 3px rgba(0,0,0,0.4)}.msg-block.warn-border{box-shadow:0 8px 32px rgba(0,0,0,0.15),inset 0 1px 1px rgba(255,255,255,0.4),inset 4px 0 0 #EAB308}.badge.warn{background:linear-gradient(135deg,#EAB308,#A16207)}.username.warn{color:#FDE047}.avatar{width:34px;height:34px;border-radius:50%;margin-right:12px;flex-shrink:0;object-fit:cover;align-self:center;box-shadow:0 0 0 2px rgba(255,255,255,0.35)}.avatar-sys{width:34px;height:34px;border-radius:50%;margin-right:12px;flex-shrink:0;align-self:center;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:15px;color:#fff}.avatar-sys.success{background:#10B981;box-shadow:0 0 10px rgba(16,185,129,0.6)}.avatar-sys.fail{background:#EF4444;box-shadow:0 0 10px rgba(239,68,68,0.6)}.avatar-sys.warn{background:#EAB308;box-shadow:0 0 10px rgba(234,179,8,0.6)}.avatar-sys.neutral{background:#71717A;box-shadow:0 0 10px rgba(113,113,122,0.4)}@keyframes popIn{from{transform:translateY(20px) scale(0.95);opacity:0;filter:blur(4px)}to{transform:translateY(0) scale(1);opacity:1;filter:blur(0)}}</style></head><body><div class="chat-box" id="chat"></div><script>let lastId=-1;let fetchingUpdates=!1;let hasConnected=!1;setInterval(function(){if(fetchingUpdates)return;fetchingUpdates=!0;fetch('/history?t='+Date.now()).then(r=>r.json()).then(data=>{try{if(data&&Array.isArray(data)){const c=document.getElementById('chat');if(c){if(!hasConnected){hasConnected=!0;const div=document.createElement('div');div.className='msg-block chat-border';div.innerHTML=`<div class="badge chat">SYS</div><div class="msg-content"><span class="username chat">system</span> <span class="message">ui connected successfully</span></div>`;c.appendChild(div);}const fragment=document.createDocumentFragment();let added=!1;data.forEach(i=>{if(i.id>lastId){lastId=i.id;try{let u=i.u||"Unknown";let m=i.m||"";if(u==='[system]'&&!m.includes('vote')&&!m.includes('[err]')&&!m.includes('[info]')&&!m.includes('waiting')&&!m.includes('ready')&&!m.includes('chat listener')&&!m.includes('running')&&!m.includes('[ban]')&&!m.includes('[warn]'))return;let isCmd=m.trim().startsWith('!');let badgeClass=isCmd?'cmd':'chat';let badgeText=isCmd?'CMD':'CHAT';let borderClass=isCmd?'cmd-border':'chat-border';let unameClass=isCmd?'username cmd':'username chat';let cleanU=u.replace(/^@+/,'');let displayU='@'+cleanU;if(u==='[console]'){displayU='CONSOLE';badgeText='SYS';}else if(u==='[announcement]'){displayU='ANNOUNCEMENT';badgeText='INFO';badgeClass='info';borderClass='info-border';unameClass='username info';}else if(u==='[system]'){displayU='SYSTEM';badgeText='SYS';badgeClass='cmd';borderClass='cmd-border';unameClass='username cmd';if(m.includes('[vote]')){badgeText='VOTE';badgeClass='vote';borderClass='vote-border';unameClass='username vote';}else if(m.includes('[err]')||m.includes('[ban]')){badgeText='ERR';badgeClass='err';borderClass='err-border';unameClass='username err';}else if(m.includes('[warn]')){badgeText='WARN';badgeClass='warn';borderClass='warn-border';unameClass='username warn';}else if(m.includes('[info]')){badgeText='INFO';badgeClass='info';borderClass='info-border';unameClass='username info';}else if(m.includes('running:')){badgeText='EXEC';badgeClass='cmd';borderClass='cmd-border';unameClass='username cmd';}else if(m.includes('[debug]')){badgeText='DBG';badgeClass='cmd';borderClass='cmd-border';unameClass='username cmd';}}let avatarClass=badgeClass==='err'?'fail':(badgeClass==='warn'?'warn':((u==='[system]'&&badgeText==='SYS')?'neutral':'success'));let avatarHtml=i.img?`<img class="avatar" src="${i.img}" onerror="this.style.display='none'">`:`<div class="avatar-sys ${avatarClass}">${avatarClass==='fail'?'&#10005;':(avatarClass==='warn'?'!':(avatarClass==='neutral'?'&#8226;':'&#10003;'))}</div>`;const div=document.createElement('div');div.className=`msg-block ${borderClass}`;div.innerHTML=avatarHtml+`<div class="badge ${badgeClass}">${badgeText}</div><div class="msg-content"><span class="${unameClass}">${displayU}</span> <span class="message">${m}</span></div>`;fragment.appendChild(div);added=!0;}catch(err){}}});if(added){c.appendChild(fragment);window.scrollTo(0,document.body.scrollHeight);while(c.children.length>15)c.removeChild(c.firstChild);}}}}finally{fetchingUpdates=!1;}}).catch(e=>{fetchingUpdates=!1;});},1000);</script></body></html>"""
    html_template_oldnew = """<!DOCTYPE html><html><head><meta charset="UTF-8"><style>@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@500;700&display=swap');html,body{background-color:rgba(0,0,0,0)!important;margin:0;padding:0;width:100%;height:100%;overflow:hidden}body{font-family:'Fira Code','Consolas',monospace;display:flex;flex-direction:column;padding:15px;justify-content:flex-end;box-sizing:border-box}.chat-box{display:flex;flex-direction:column;align-items:flex-end;gap:6px;width:100%}.msg-block{background-color:rgba(0,0,0,0.85);padding:6px 10px;display:flex;align-items:baseline;font-size:16px;border-radius:6px;box-shadow:2px 2px 4px rgba(0,0,0,0.5);animation:slideIn 0.2s ease-out forwards;margin-bottom:2px;max-width:95%;word-wrap:break-word}.msg-block.cmd-border{border-left:5px solid #00e5ff}.msg-block.chat-border{border-left:5px solid #00e676}.msg-block.vote-border{border-left:5px solid orange}.msg-block.err-border{border-left:5px solid #f33}.msg-block.info-border{border-left:5px solid #3B82F6}.badge{padding:2px 6px;font-weight:800;color:#111;font-size:11px;border-radius:3px;margin-right:8px;flex-shrink:0;align-self:flex-start;margin-top:3px}.badge.cmd{background-color:#00e5ff}.badge.chat{background-color:#00e676}.badge.vote{background-color:orange}.badge.err{background-color:#f33;color:#fff}.badge.info{background-color:#3B82F6;color:#fff}.msg-content{display:block;word-break:break-word}.username{font-weight:900;text-shadow:1px 1px 0 rgba(0,0,0,0.8);margin-right:5px}.username.cmd{color:#00e5ff}.username.chat{color:#00e676}.username.vote{color:orange}.username.err{color:#f33}.username.info{color:#60A5FA}.message{color:#fff;font-weight:600;text-shadow:1px 1px 0 rgba(0,0,0,0.8);line-height:1.4}@keyframes slideIn{from{transform:translateX(30px);opacity:0}to{transform:translateX(0);opacity:1}}</style></head><body><div class="chat-box" id="chat"></div><script>let lastId=-1;let fetchingUpdates=!1;let hasConnected=!1;setInterval(function(){if(fetchingUpdates)return;fetchingUpdates=!0;fetch('/history?t='+Date.now()).then(r=>r.json()).then(data=>{try{if(data&&Array.isArray(data)){const c=document.getElementById('chat');if(c){if(!hasConnected){hasConnected=!0;const div=document.createElement('div');div.className='msg-block cmd-border';div.innerHTML=`<div class="badge cmd">SYS</div><div class="msg-content"><span class="username cmd">system</span> <span class="message">connected</span></div>`;c.appendChild(div);}const fragment=document.createDocumentFragment();let added=!1;data.forEach(i=>{if(i.id>lastId){lastId=i.id;try{let u=i.u||"Unknown";let m=i.m||"";if(u==='[system]'&&!m.includes('vote')&&!m.includes('[debug]')&&!m.includes('[err]')&&!m.includes('[info]')&&!m.includes('waiting')&&!m.includes('ready')&&!m.includes('chat listener')&&!m.includes('running')&&!m.includes('[ban]')&&!m.includes('[warn]'))return;let isCmd=m.trim().startsWith('!');let badgeClass=isCmd?'cmd':'chat';let badgeText=isCmd?'CMD':'CHAT';let borderClass=isCmd?'cmd-border':'chat-border';let unameClass=isCmd?'username cmd':'username chat';let cleanU=u.replace(/^@+/,'');let displayU='@'+cleanU;if(u==='[console]'){displayU='CONSOLE';badgeText='SYS';}else if(u==='[announcement]'){displayU='ANNOUNCEMENT';badgeText='INFO';badgeClass='info';borderClass='info-border';unameClass='username info';}else if(u==='[system]'){displayU='SYSTEM';badgeText='SYS';badgeClass='cmd';borderClass='cmd-border';unameClass='username cmd';if(m.includes('[vote]')){badgeText='VOTE';badgeClass='vote';borderClass='vote-border';unameClass='username vote';}else if(m.includes('[err]')||m.includes('[ban]')||m.includes('[warn]')){badgeText='ERR';badgeClass='err';borderClass='err-border';unameClass='username err';}else if(m.includes('[info]')){badgeText='INFO';badgeClass='info';borderClass='info-border';unameClass='username info';}else if(m.includes('running:')){badgeText='EXEC';badgeClass='cmd';borderClass='cmd-border';unameClass='username cmd';}else if(m.includes('[debug]')){badgeText='DBG';badgeClass='cmd';borderClass='cmd-border';unameClass='username cmd';}}const div=document.createElement('div');div.className=`msg-block ${borderClass}`;div.innerHTML=`<div class="badge ${badgeClass}">${badgeText}</div><div class="msg-content"><span class="${unameClass}">${displayU}</span> <span class="message">${m}</span></div>`;fragment.appendChild(div);added=!0;}catch(err){}}});if(added){c.appendChild(fragment);window.scrollTo(0,document.body.scrollHeight);while(c.children.length>20)c.removeChild(c.firstChild);}}}}finally{fetchingUpdates=!1;}}).catch(e=>{fetchingUpdates=!1;});},1000);</script></body></html>"""
    html_debugchat = """<!DOCTYPE html><html><head><meta charset="UTF-8"><style>@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@500;700&display=swap');html,body{background-color:rgba(0,0,0,0)!important;margin:0;padding:0;width:100%;height:100%;overflow:hidden}body{font-family:'Fira Code','Consolas',monospace;display:flex;flex-direction:column;padding:15px;justify-content:flex-end;box-sizing:border-box}.chat-box{display:flex;flex-direction:column;align-items:flex-end;gap:6px;width:100%}.msg-block{background-color:rgba(0,0,0,0.85);padding:6px 10px;display:flex;align-items:baseline;font-size:16px;border-radius:6px;box-shadow:2px 2px 4px rgba(0,0,0,0.5);animation:slideIn 0.2s ease-out forwards;margin-bottom:2px;max-width:95%;word-wrap:break-word}.msg-block.cmd-border{border-left:5px solid #00e5ff}.msg-block.chat-border{border-left:5px solid #00e676}.msg-block.vote-border{border-left:5px solid orange}.msg-block.err-border{border-left:5px solid #f33}.badge{padding:2px 6px;font-weight:800;color:#111;font-size:11px;border-radius:3px;margin-right:8px;flex-shrink:0;align-self:flex-start;margin-top:3px}.badge.cmd{background-color:#00e5ff}.badge.chat{background-color:#00e676}.badge.vote{background-color:orange}.badge.err{background-color:#f33;color:#fff}.msg-content{display:block;word-break:break-word}.username{font-weight:900;text-shadow:1px 1px 0 rgba(0,0,0,0.8);margin-right:5px}.username.cmd{color:#00e5ff}.username.chat{color:#00e676}.username.vote{color:orange}.username.err{color:#f33}.message{color:#fff;font-weight:600;text-shadow:1px 1px 0 rgba(0,0,0,0.8);line-height:1.4}@keyframes slideIn{from{transform:translateX(30px);opacity:0}to{transform:translateX(0);opacity:1}}</style></head><body><div class="chat-box" id="chat"></div><script>let lastId=-1;let fetchingUpdates=!1;setInterval(function(){if(fetchingUpdates)return;fetchingUpdates=!0;fetch('/history?t='+Date.now()).then(r=>r.json()).then(data=>{try{if(data&&Array.isArray(data)){const c=document.getElementById('chat');if(c){const fragment=document.createDocumentFragment();let added=!1;data.forEach(i=>{if(i.id>lastId){lastId=i.id;try{let u=i.u||"Unknown";let m=i.m||"";let isCmd=m.trim().startsWith('!');let badgeClass=isCmd?'cmd':'chat';let badgeText=isCmd?'CMD':'CHAT';let borderClass=isCmd?'cmd-border':'chat-border';let unameClass=isCmd?'username cmd':'username chat';let cleanU=u.replace(/^@+/,'');let displayU='@'+cleanU;if(u==='[console]'){displayU='CONSOLE';badgeText='SYS';}else if(u==='[announcement]'){displayU='ANNOUNCEMENT';badgeText='INFO';badgeClass='cmd';borderClass='cmd-border';unameClass='username cmd';}else if(u==='[system]'){displayU='SYSTEM';badgeText='SYS';badgeClass='cmd';borderClass='cmd-border';unameClass='username cmd';if(m.includes('[vote]')){badgeText='VOTE';badgeClass='vote';borderClass='vote-border';unameClass='username vote';}else if(m.includes('[err]')||m.includes('[ban]')||m.includes('[warn]')){badgeText='ERR';badgeClass='err';borderClass='err-border';unameClass='username err';}else if(m.includes('[info]')){badgeText='INFO';badgeClass='cmd';borderClass='cmd-border';unameClass='username cmd';}else if(m.includes('running:')){badgeText='EXEC';badgeClass='cmd';borderClass='cmd-border';unameClass='username cmd';}else if(m.includes('[debug]')){badgeText='DBG';badgeClass='cmd';borderClass='cmd-border';unameClass='username cmd';}}const div=document.createElement('div');div.className=`msg-block ${borderClass}`;div.innerHTML=`<div class="badge ${badgeClass}">${badgeText}</div><div class="msg-content"><span class="${unameClass}">${displayU}</span> <span class="message">${m}</span></div>`;fragment.appendChild(div);added=!0;}catch(err){}}});if(added){c.appendChild(fragment);window.scrollTo(0,document.body.scrollHeight);while(c.children.length>20)c.removeChild(c.firstChild);}}}}finally{fetchingUpdates=!1;}}).catch(e=>{fetchingUpdates=!1;});},1000);</script></body></html>"""
    html_stats = """<!DOCTYPE html><html><head><meta charset="UTF-8"><style>@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@500;700&display=swap');html,body{background-color:rgba(0,0,0,0)!important;margin:0;padding:20px;overflow:hidden;font-family:'Fira Code',Consolas,monospace}.stats-widget{background:rgba(20,20,25,0.85);backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:20px 30px;display:inline-block;box-shadow:0 10px 25px rgba(0,0,0,0.5)}.stat-row{display:flex;align-items:center;justify-content:space-between;margin:12px 0;gap:40px}.stat-label{color:#a1a1aa;font-weight:bold;font-size:16px;text-transform:uppercase;letter-spacing:1px}.stat-value{color:#fff;font-weight:bold;font-size:24px;text-shadow:0 0 10px rgba(255,255,255,0.2)}.stat-row.cmds .stat-value{color:#00E5FF;text-shadow:0 0 10px rgba(0,229,255,0.3)}.stat-row.views .stat-value{color:#3B82F6;text-shadow:0 0 10px rgba(59,130,246,0.3)}.stat-row.likes .stat-value{color:#10B981;text-shadow:0 0 10px rgba(16,185,129,0.3)}.stat-row.errs .stat-value{color:#EF4444;text-shadow:0 0 10px rgba(239,68,68,0.3)}.version-tag{font-size:12px;color:#52525b;text-align:right;margin-top:15px;font-weight:bold;border-top:1px solid #3f3f46;padding-top:10px}</style></head><body><div class="stats-widget"><div class="stat-row"><span class="stat-label">UPTIME</span><span class="stat-value" id="uptime">0d 0h 0m 0s</span></div><div class="stat-row views"><span class="stat-label">VIEWERS</span><span class="stat-value" id="viewers">0</span></div><div class="stat-row likes"><span class="stat-label">LIKES</span><span class="stat-label" id="likes">0</span></div><div class="stat-row cmds"><span class="stat-label">CMDS EXECUTED</span><span class="stat-value" id="cmds">0</span></div><div class="stat-row errs"><span class="stat-label">FAILED CMDS</span><span class="stat-value" id="failed">0</span></div><div class="version-tag">{{ version }}</div></div><script>setInterval(function(){fetch('/stats_data?t='+Date.now()).then(r=>r.json()).then(data=>{document.getElementById('uptime').innerText=data.uptime;document.getElementById('cmds').innerText=data.commands;document.getElementById('failed').innerText=data.failed;if(document.getElementById('viewers'))document.getElementById('viewers').innerText=data.viewers||"0";if(document.getElementById('likes'))document.getElementById('likes').innerText=data.likes||"0";}).catch(e=>{});},1000);</script></body></html>"""
    html_ultradebug = """<!DOCTYPE html><html><head><meta charset="UTF-8"><style>@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@500;700&display=swap');html,body{background-color:#09090b!important;margin:0;padding:20px;overflow:hidden;font-family:'Fira Code',Consolas,monospace;color:#00FF41}.stats-widget{background:rgba(20,20,25,0.95);border:1px solid #00FF41;border-radius:12px;padding:20px 30px;box-shadow:0 0 15px rgba(0,255,65,0.2)}.stat-row{display:flex;align-items:center;justify-content:space-between;margin:12px 0;gap:40px;border-bottom:1px solid #18181b;padding-bottom:8px}.stat-label{color:#a1a1aa;font-weight:bold;font-size:16px;text-transform:uppercase}.stat-value{color:#00FF41;font-weight:bold;font-size:24px;text-shadow:0 0 8px rgba(0,255,65,0.5)}</style></head><body><div class="stats-widget"><div class="stat-row"><span class="stat-label">QUEUE SIZE</span><span class="stat-value" id="qsize">0</span></div><div class="stat-row"><span class="stat-label">COM LOCKED</span><span class="stat-value" id="comstate">FALSE</span></div><div class="stat-row"><span class="stat-label">ACTIVE THREADS</span><span class="stat-value" id="threads">0</span></div><div class="stat-row"><span class="stat-label">LAST REBUILD</span><span class="stat-value" id="rebuild">0s ago</span></div><div class="stat-row"><span class="stat-label">FAILED ACTIONS</span><span class="stat-value" style="color:#FF3333" id="failed">0</span></div></div><script>setInterval(function(){fetch('/debug_data?t='+Date.now()).then(r=>r.json()).then(data=>{document.getElementById('qsize').innerText=data.qsize;document.getElementById('comstate').innerText=data.comstate;document.getElementById('threads').innerText=data.threads;document.getElementById('rebuild').innerText=data.rebuild;document.getElementById('failed').innerText=data.failed;}).catch(e=>{});},500);</script></body></html>"""

    @obs_web_overlay_app.route('/')
    def index_page(): return render_template_string(html_index)
    @obs_web_overlay_app.route('/obs')
    def obs_overlay(): return render_template_string(html_template, padding=10)
    @obs_web_overlay_app.route('/obs2')
    def obs_overlay2(): return render_template_string(html_template_2)
    @obs_web_overlay_app.route('/obsnew')
    def obs_overlay_new(): return render_template_string(html_template_new)
    @obs_web_overlay_app.route('/oldobsnew')
    def obs_overlay_oldnew(): return render_template_string(html_template_oldnew)
    @obs_web_overlay_app.route('/debugchat')
    def obs_overlay_debugchat(): return render_template_string(html_debugchat)
    @obs_web_overlay_app.route('/ultradebug')
    def ultradebug_overlay(): return render_template_string(html_ultradebug)
    @obs_web_overlay_app.route('/stats')
    def stats_overlay(): return render_template_string(html_stats, version=version)
    @obs_web_overlay_app.route('/stats_data')
    def get_stats_data(): 
        uptime_sec = int(time.time() - script_start_time)
        d, r = divmod(uptime_sec, 86400)
        h, r = divmod(r, 3600)
        m, s = divmod(r, 60)
        uptime_str = f"{d}d {h}h {m}m {s}s" if d > 0 else f"{h}h {m}m {s}s"
        return jsonify({"uptime": uptime_str, "commands": total_commands_executed, "failed": total_commands_failed, "viewers": current_viewers, "likes": current_likes})
    @obs_web_overlay_app.route('/updates')
    def get_updates(): 
        with buffer_lock:
            data = list(messages_buffer)
            messages_buffer.clear()
        return jsonify(data)
    @obs_web_overlay_app.route('/debug_data')
    def get_debug_data():
        comstate = "FALSE"
        threads = threading.active_count()
        rebuild_sec = 0
        if 'main_gui_application' in globals():
            comstate = "TRUE" if getattr(main_gui_application, 'shared_kb', None) else "FALSE"
            rebuild_sec = int(time.time() - getattr(main_gui_application, 'last_com_rebuild_time', time.time()))
        return jsonify({"qsize": "UNLIMITED", "comstate": comstate, "threads": threads, "rebuild": f"{rebuild_sec}s ago", "failed": total_commands_failed})
    @obs_web_overlay_app.route('/history')
    def get_history(): 
        with history_lock: return jsonify(list(web_chat_history))
    @obs_web_overlay_app.route('/status_update')
    def get_status_update(): return jsonify({"status": current_status, "vote": current_vote_info, "viewers": current_viewers, "likes": current_likes, "chat_visible": overlay_chat_visible, "split_mode": split_overlay_mode})


    # ── The 4 extra overlay boxes -- embedded templates (not file reads), so they
    #    ALWAYS render live content immediately, never a placeholder/can't-display
    #    message, regardless of whether any vote/switch has happened yet. ──
    html_newstatus = """<html><head><style>
    body{background:rgba(0,0,0,0);color:white;font-family:Arial;font-size:32px;text-align:center;text-shadow:2px 2px 4px #000;}
    #s{margin-top:20px;padding:10px;background:rgba(0,0,0,0.4);border-radius:8px;display:inline-block;}
    </style></head><body><div id="s">Status: Loading...</div>
    <script>
    function refresh(){
        fetch('/status_update?t='+Date.now()).then(r=>r.json()).then(data=>{
            document.getElementById('s').innerText = 'Status: ' + (data.status || 'unknown');
        }).catch(()=>{});
    }
    setInterval(refresh, 3000);
    refresh();
    </script></body></html>"""

    html_os_vote_status = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    *{box-sizing:border-box;margin:0;padding:0;}
    body{background:transparent;font-family:'Segoe UI',Arial,sans-serif;color:white;text-shadow:1px 1px 3px rgba(0,0,0,0.9);padding:12px;}
    #panel{background:rgba(10,10,20,0.82);border:1px solid rgba(124,92,191,0.5);border-radius:16px;padding:18px 22px 14px;min-width:340px;max-width:420px;backdrop-filter:blur(6px);}
    #title{font-size:22px;font-weight:700;color:#b39ddb;letter-spacing:1px;text-align:center;margin-bottom:4px;}
    #current{font-size:13px;color:#3ddc97;text-align:center;margin-bottom:14px;opacity:0.9;}
    .row{display:flex;align-items:center;gap:10px;margin-bottom:9px;}
    .label{font-size:15px;font-weight:600;min-width:120px;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
    .trigger{font-size:11px;color:#aaa;font-weight:400;margin-left:5px;}
    .bar-wrap{flex:1;background:rgba(255,255,255,0.1);border-radius:8px;height:16px;overflow:hidden;}
    .bar{height:100%;border-radius:8px;transition:width 0.4s ease;min-width:4px;}
    .count{font-size:16px;font-weight:700;min-width:36px;text-align:right;}
    .sep{color:rgba(255,255,255,0.3);font-weight:300;margin:0 1px;}
    #empty{color:#888;font-size:13px;text-align:center;padding:8px 0;}
    </style></head><body>
    <div id="panel">
      <div id="title">&#128229; OS Vote</div>
      <div id="current">Now running: <strong id="curname">-</strong></div>
      <div id="rows"></div>
      <div id="empty" style="display:none;">No OS Voting entries configured yet.</div>
    </div>
    <script>
    function refresh(){
        fetch('/osvote_data?t='+Date.now()).then(r=>r.json()).then(data=>{
            document.getElementById('curname').innerText = data.current_name || '-';
            const rows = document.getElementById('rows');
            const empty = document.getElementById('empty');
            if (!data.entries || data.entries.length === 0) {
                rows.innerHTML = ''; empty.style.display = 'block'; return;
            }
            empty.style.display = 'none';
            rows.innerHTML = data.entries.map(e => {
                const pct = e.required > 0 ? Math.min(100, (e.count / e.required) * 100) : 0;
                const color = e.is_current ? '#3ddc97' : '#7c5cbf';
                const labelStyle = e.is_current ? 'color:#3ddc97;font-weight:bold;' : '';
                return `<div class="row">
                    <div class="label" style="${labelStyle}">${e.name}<span class="trigger">!${e.trigger}</span></div>
                    <div class="bar-wrap"><div class="bar" style="width:${pct}%;background:${color};"></div></div>
                    <div class="count" style="color:${color};">${e.count}<span class="sep">/</span>${e.required}</div>
                </div>`;
            }).join('');
        }).catch(()=>{});
    }
    setInterval(refresh, 2000);
    refresh();
    </script>
    </body></html>"""

    html_votes_overlay = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>OBS Vote Overlay</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { background-color: transparent; width: 320px; overflow: hidden; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: white; padding: 10px; }
        .vote-box { border-radius: 10px; padding: 15px; margin-bottom: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.9); }
        #restart-box { background-color: #0a2a12; border: 2px solid #00ff87; }
        #restart-box .vote-title { color: #00ff87; text-shadow: 0 0 10px rgba(0,255,135,0.8); }
        #restart-box .vote-info { color: #ccffdd; }
        #restart-box .vote-info.timer { color: #aaffcc; }
        #restart-box .progress-container { background-color: #0a2010; border: 1px solid #00aa55; }
        #restart-box .progress-bar { background: linear-gradient(90deg, #00aa55, #00ff87); box-shadow: 0 0 8px #00ff87; }
        #revert-box { background-color: #0a1a3a; border: 2px solid #00aaff; }
        #revert-box .vote-title { color: #00aaff; text-shadow: 0 0 10px rgba(0,170,255,0.8); }
        #revert-box .vote-info { color: #cceeff; }
        #revert-box .vote-info.timer { color: #aaddff; }
        #revert-box .progress-container { background-color: #071525; border: 1px solid #0066aa; }
        #revert-box .progress-bar { background: linear-gradient(90deg, #0066cc, #00aaff); box-shadow: 0 0 8px #00aaff; }
        .vote-title { font-size: 18px; font-weight: bold; text-align: center; margin-bottom: 10px; }
        .vote-info { font-size: 15px; font-weight: 700; text-align: center; margin-bottom: 5px; }
        .vote-info.timer { font-size: 13px; font-weight: 600; }
        .progress-container { border-radius: 10px; width: 100%; height: 12px; margin-top: 10px; overflow: hidden; }
        .progress-bar { height: 100%; width: 0%; transition: width 0.3s ease; }
    </style>
</head>
<body>
    <div class="vote-box" id="restart-box">
        <div class="vote-title">&#10227; Restart Vote</div>
        <div class="vote-info" id="restart-collected">0 / 2 votes</div>
        <div class="vote-info timer" id="restart-time">Waiting...</div>
        <div class="progress-container"><div class="progress-bar" id="restart-bar"></div></div>
    </div>
    <div class="vote-box" id="revert-box">
        <div class="vote-title">&#8617; Revert Vote</div>
        <div class="vote-info" id="revert-collected">0 / 2 votes</div>
        <div class="vote-info timer" id="revert-time">Waiting...</div>
        <div class="progress-container"><div class="progress-bar" id="revert-bar"></div></div>
    </div>
    <script>
        const state = {
            restartvm: { remaining: 0, interval: null, required: 2, current: 0 },
            revert:    { remaining: 0, interval: null, required: 2, current: 0 }
        };
        const elements = {
            restartvm: { collected: document.getElementById('restart-collected'), time: document.getElementById('restart-time'), bar: document.getElementById('restart-bar') },
            revert:    { collected: document.getElementById('revert-collected'), time: document.getElementById('revert-time'), bar: document.getElementById('revert-bar') }
        };
        function updateDisplay(type) {
            const s = state[type]; const el = elements[type];
            const active = s.remaining > 0;
            el.collected.textContent = `${s.current} / ${s.required} votes`;
            el.time.textContent = active ? `\u23f1 ${s.remaining}s remaining` : 'Waiting...';
            const pct = s.required > 0 ? (s.current / s.required) * 100 : 0;
            el.bar.style.width = Math.min(pct, 100) + '%';
        }
        function startClientCountdown(type, fromSeconds) {
            const s = state[type];
            if (s.interval) { clearInterval(s.interval); s.interval = null; }
            s.remaining = fromSeconds;
            updateDisplay(type);
            if (fromSeconds <= 0) return;
            s.interval = setInterval(() => {
                if (s.remaining > 0) { s.remaining--; updateDisplay(type); }
                else { clearInterval(s.interval); s.interval = null; updateDisplay(type); }
            }, 1000);
        }
        function syncFromServer(type, serverRemaining, serverCurrent, serverRequired) {
            const s = state[type];
            s.current = serverCurrent; s.required = serverRequired;
            const diff = Math.abs(serverRemaining - s.remaining);
            if (serverRemaining <= 0) {
                if (s.interval) { clearInterval(s.interval); s.interval = null; }
                s.remaining = 0; updateDisplay(type);
            } else if (!s.interval || diff > 2) { startClientCountdown(type, serverRemaining); }
            else { updateDisplay(type); }
        }
        function fetchVotes() {
            fetch('/votes_json?t=' + Date.now()).then(r => r.json()).then(data => {
                syncFromServer('restartvm', data.restartvm.remaining_time, data.restartvm.current, data.restartvm.required);
                syncFromServer('revert', data.revert.remaining_time, data.revert.current, data.revert.required);
            }).catch(() => {});
        }
        setInterval(fetchVotes, 2000);
        fetchVotes();
    </script>
</body>
</html>"""

    html_ban_vote = """<html><head><style>
    body{background:rgba(0,0,0,0);color:white;font-family:Arial;text-align:center;font-size:28px;text-shadow:2px 2px 4px #000;}
    #c{margin-top:40px;padding:20px;background:rgba(0,0,0,0.5);border-radius:12px;display:inline-block;}
    h1{color:#ff4444;} .progress{width:80%;height:25px;background:rgba(255,255,255,0.2);border-radius:12px;margin:15px auto;overflow:hidden;}
    .bar{height:100%;width:0%;background:#ff4444;transition:width 0.5s;}
    </style></head><body><div id="c"><h1>Ban Vote</h1>
    <p id="target">Empty</p><p id="count">0/3</p><p id="timer"></p>
    <div class="progress"><div class="bar" id="bar"></div></div></div>
    <script>
    function refresh(){
        fetch('/banvote_data?t='+Date.now()).then(r=>r.json()).then(data=>{
            document.getElementById('target').innerText = data.target ? ('Ban @' + data.target) : 'Empty';
            document.getElementById('count').innerText = data.current + '/' + data.required;
            document.getElementById('timer').innerText = data.remaining_time > 0 ? (Math.round(data.remaining_time) + 's remaining') : '';
            const pct = data.required > 0 ? Math.min(100, (data.current / data.required) * 100) : 0;
            document.getElementById('bar').style.width = pct + '%';
        }).catch(()=>{});
    }
    setInterval(refresh, 2000);
    refresh();
    </script></body></html>"""

    @obs_web_overlay_app.route('/status')
    def status_overlay_box(): return render_template_string(html_newstatus)
    @obs_web_overlay_app.route('/osvotestatus')
    def os_vote_status_box(): return render_template_string(html_os_vote_status)
    @obs_web_overlay_app.route('/osvote_data')
    def os_vote_data():
        current_name = "-"
        for e in os_list:
            if e.get("vm") == current_os_vm:
                current_name = e.get("name", "-")
                break
        entries = []
        for e in os_list:
            trig = (e.get("trigger") or "").strip().lower()
            if not trig: continue
            entries.append({
                "name": e.get("name", trig), "trigger": trig,
                "count": len(os_votes.get(trig, set())), "required": OS_VOTE_REQUIRED,
                "is_current": e.get("vm") == current_os_vm,
            })
        return jsonify({"current_name": current_name, "entries": entries})
    @obs_web_overlay_app.route('/votes-overlay')
    def votes_overlay_box(): return render_template_string(html_votes_overlay)
    @obs_web_overlay_app.route('/votes_json')
    def votes_json_data():
        def _one(vote_type, default_required=2):
            app_ref = globals().get('main_gui_application')
            if app_ref is None: return {"remaining_time": 0, "current": 0, "required": default_required}
            with app_ref.vote_lock:
                v = app_ref.active_votes.get(vote_type)
            if not v: return {"remaining_time": 0, "current": 0, "required": default_required}
            remaining = max(0, vote_timeout - (time.time() - v["start_time"]))
            return {"remaining_time": remaining, "current": len(v["voters"]), "required": v["target"]}
        prefix = main_gui_application.command_prefix if 'main_gui_application' in globals() and main_gui_application else "!"
        return jsonify({"restartvm": _one(f"{prefix}restartvm"), "revert": _one(f"{prefix}revert")})
    @obs_web_overlay_app.route('/banvote')
    def ban_vote_box(): return render_template_string(html_ban_vote)
    @obs_web_overlay_app.route('/banvote_data')
    def ban_vote_data():
        app_ref = globals().get('main_gui_application')
        if app_ref is None:
            return jsonify({"target": None, "current": 0, "required": 3, "remaining_time": 0})
        prefix = app_ref.command_prefix
        with app_ref.vote_lock:
            for vtype, v in app_ref.active_votes.items():
                if vtype.startswith(f"{prefix}ban:"):
                    remaining = max(0, vote_timeout - (time.time() - v["start_time"]))
                    return jsonify({"target": vtype.split(":", 1)[1], "current": len(v["voters"]), "required": v["target"], "remaining_time": remaining})
        return jsonify({"target": None, "current": 0, "required": 3, "remaining_time": 0})


def start_flask():
    global flask_port
    console_log("INFO", f"[flask] web/overlay server thread started (flask_available={flask_available}).")
    if not flask_available:
        console_log("ERROR", "[flask] flask is not installed in this Python environment -- the web/overlay server (and multi-stream port) cannot start. Run: pip install flask")
        return
    try:
        if 'flask.cli' in sys.modules: sys.modules['flask.cli'].show_server_banner = lambda *x: None
        if platform.system() == "Windows":
            try:
                out = subprocess.check_output("netstat -ano", shell=True, timeout=8).decode()
                for line in out.splitlines():
                    if "LISTENING" in line and f":{flask_port} " in line + " ":
                        pid = line.strip().split()[-1]
                        if pid.isdigit() and int(pid) > 0 and int(pid) != os.getpid():
                            subprocess.call(["taskkill", "/F", "/PID", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8)
                            time.sleep(0.5)
            except subprocess.TimeoutExpired:
                console_log("WARN", f"[flask] 'netstat -ano' timed out after 8s while checking port {flask_port} -- skipping port-clear step.")
            except Exception as e:
                console_log("WARN", f"[flask] couldn't check/clear port {flask_port} on windows: {e}")
        elif platform.system() == "Darwin":
            # macOS doesn't ship 'ss' (that's Linux/iproute2-only) -- lsof is the
            # built-in equivalent here and needs no extra install.
            try:
                out = subprocess.check_output(["lsof", "-nP", f"-i:{flask_port}", "-sTCP:LISTEN", "-t"],
                                               text=True, stderr=subprocess.DEVNULL, timeout=8)
                for pid_str in out.splitlines():
                    pid_str = pid_str.strip()
                    if pid_str.isdigit():
                        pid = int(pid_str)
                        if pid > 0 and pid != os.getpid():
                            try:
                                os.kill(pid, _signal_module.SIGKILL)
                                time.sleep(0.5)
                            except Exception as e:
                                console_log("WARN", f"[flask] found something on port {flask_port} (pid {pid}) but couldn't kill it -- you may need sudo, or another user's process owns it: {e}")
            except subprocess.TimeoutExpired:
                console_log("WARN", f"[flask] 'lsof' timed out after 8s while checking port {flask_port} -- skipping port-clear step.")
            except FileNotFoundError:
                console_log("WARN", f"[flask] 'lsof' not found -- skipping port-clear step for port {flask_port}.")
            except Exception as e:
                console_log("WARN", f"[flask] couldn't run 'lsof' to check port {flask_port}: {e}")
        else:
            try:
                out = subprocess.check_output(["ss", "-ltnp"], text=True, stderr=subprocess.DEVNULL, timeout=8)
                for line in out.splitlines():
                    if f":{flask_port} " in line or line.rstrip().endswith(f":{flask_port}"):
                        m = re.search(r"pid=(\d+)", line)
                        if m:
                            pid = int(m.group(1))
                            if pid > 0 and pid != os.getpid():
                                try:
                                    os.kill(pid, _signal_module.SIGKILL)
                                    time.sleep(0.5)
                                except Exception as e:
                                    console_log("WARN", f"[flask] found something on port {flask_port} (pid {pid}) but couldn't kill it -- you may need sudo, or another user's process owns it: {e}")
            except subprocess.TimeoutExpired:
                console_log("WARN", f"[flask] 'ss -ltnp' timed out after 8s while checking port {flask_port} -- skipping port-clear step.")
            except Exception as e:
                console_log("WARN", f"[flask] couldn't run 'ss -ltnp' to check port {flask_port}: {e}")
        from werkzeug.serving import make_server
        bound = False
        start_port = flask_port
        for port in range(start_port, start_port + 10):
            try:
                flask_port = port
                console_log("INFO", f"[flask] attempting to bind web/overlay server to 0.0.0.0:{port}...")
                httpd = make_server('0.0.0.0', port, obs_web_overlay_app, threaded=True)
                bound = True
                console_log("INFO", f"[flask] bound successfully -- web/overlay server is live on 0.0.0.0:{port}.")
                httpd.serve_forever()
                break
            except OSError as e:
                bound = False
                console_log("WARN", f"[flask] port {port} unavailable ({e}), trying next port...")
                continue
        if not bound:
            console_log("ERROR", f"[flask] failed to bind ANY port in range {start_port}-{start_port + 9}. all of them are in use.")
        if start_port != flask_port:
            console_log("WARN", f"[flask] requested port {start_port} was busy -- actually listening on {flask_port} instead.")
    except Exception as e:
        console_log("ERROR", f"[flask] server crashed: {e}\n{traceback.format_exc()}")

# ============================================================
# ============ ADDITIONAL FEATURES ============
# ============================================================
# Ported/adapted from VBOX-Script-Linux.py (Real PC control, OS-switch
# voting, scheduler, permissions, sound/TTS, event log, user management,
# system tray, notifications). Nothing above this section was touched;
# everything below is purely additive and hooks into the existing app
# via `app_instance` (set at the end of ChatPlaysApp.__init__).

app_instance = None

def verbose_conn_logging_enabled():
    return app_instance is not None and getattr(app_instance, "config", {}).get("verbose_connection_logs", False)

def normalize_username(name):
    try:
        import unicodedata
        name = "".join(ch for ch in str(name) if unicodedata.category(ch) not in ("Cf", "Cc", "Cs"))
    except Exception: pass
    return str(name).strip().lstrip("@").strip().lower()

# ---------------- notifications & system tray ----------------
_tray_icon = None
_tray_thread = None

def notify(title, message, timeout=4):
    def _send():
        if plyer_available:
            try: _plyer_notification.notify(title=title, message=message, app_name="ChatUses", timeout=timeout)
            except Exception as e: console_log("WARN", f"notify failed: {e}")
        else:
            console_log("INFO", f"[notify] {title}: {message}")
    threading.Thread(target=_send, daemon=True).start()

def _make_tray_image():
    size = 64
    img = _TrayImage.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = _TrayDraw.Draw(img)
    draw.ellipse([4, 4, size - 4, size - 4], fill=(0, 229, 255, 255))
    draw.rectangle([28, 18, 36, 42], fill="white")
    draw.rectangle([28, 46, 36, 54], fill="white")
    return img

def _tray_show_gui(icon, item):
    if app_instance is not None:
        if verbose_conn_logging_enabled():
            console_log("INFO", "[tray] restored from system tray.")
        app_instance.root.after(0, app_instance.root.deiconify)
        app_instance.root.after(0, app_instance.root.lift)

def _tray_exit(icon, item):
    try: icon.stop()
    except Exception: pass
    if app_instance is not None: app_instance.running = False
    os._exit(0)

def start_tray_icon():
    global _tray_icon, _tray_thread
    if not pystray_available or _tray_icon is not None: return
    try:
        menu = pystray.Menu(
            pystray.MenuItem("Show", _tray_show_gui, default=True),
            pystray.MenuItem("Exit", _tray_exit),
        )
        _tray_icon = pystray.Icon(name="ChatUses", icon=_make_tray_image(), title=version, menu=menu)
        if platform.system() == "Darwin":
            # macOS: pystray.Icon.run() needs to own the Cocoa/AppKit run loop -- the SAME
            # run loop Tkinter's Cocoa-backed Tk relies on for its own event notifier.
            # Running .run() on a background thread (the pattern below, fine on
            # Windows/Linux) creates a run-loop ownership conflict that can corrupt
            # Tcl's notifier and crash with "Tcl_WaitForEvent: Notifier not initialized" --
            # possibly not immediately, and not necessarily from code that looks related.
            # run_detached() is pystray's own documented answer for apps that already have
            # a different main loop (Tkinter's mainloop() here): it integrates without
            # needing to own the thread, instead of fighting Tkinter for it.
            _tray_icon.run_detached()
            _tray_thread = None
            console_log("INFO", "system tray icon started (macOS run_detached).")
        else:
            _tray_thread = threading.Thread(target=_tray_icon.run, daemon=True)
            _tray_thread.start()
            console_log("INFO", "system tray icon started.")
    except Exception as e:
        console_log("WARN", f"tray icon failed to start: {e}")

def stop_tray_icon():
    global _tray_icon
    if _tray_icon:
        try: _tray_icon.stop()
        except Exception: pass
        _tray_icon = None

# ---------------- event log ----------------
event_log_lock = threading.Lock()
event_log_entries = []

def load_event_log():
    global event_log_entries
    try:
        if os.path.exists(event_log_file):
            with open(event_log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            event_log_entries = data if isinstance(data, list) else []
    except Exception: event_log_entries = []

def append_event(event_type, username, detail=""):
    entry = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "type": event_type, "user": username, "detail": detail}
    with event_log_lock:
        event_log_entries.append(entry)
        if len(event_log_entries) > 5000: del event_log_entries[:-5000]
        snapshot = list(event_log_entries)
    threading.Thread(target=lambda: safe_json_dump(event_log_file, snapshot), daemon=True).start()

# ---------------- permissions config ----------------
permissions_config = {"restart_votes": 2, "revert_votes": 2, "ban_votes": 3, "action_cooldown": 60,
                       "command_spam_threshold": 5, "command_spam_window": 10,
                       "vote_threshold_percent_enabled": False, "vote_threshold_percent": 30,
                       "youtube_api_key": ""}

def get_vote_threshold(key, default):
    """Returns the votes required for a given vote type. If percent-based voting is
    enabled, computes ceil(live_viewers * percent/100) instead -- falls back to the
    fixed count if no live viewer number is available yet."""
    if permissions_config.get("vote_threshold_percent_enabled"):
        try:
            viewers = int(current_viewers)
        except Exception:
            viewers = 0
        if viewers > 0:
            pct = permissions_config.get("vote_threshold_percent", 30)
            return max(1, math.ceil(viewers * pct / 100))
    return permissions_config.get(key, default)
command_usage_log = {}         # cmd string ("!combo" etc) -> list of recent-use timestamps
command_cooldown_until = {}    # cmd string -> timestamp the command is locked out until
command_spam_lock = threading.Lock()

def load_permissions_config():
    global permissions_config
    try:
        if os.path.exists(permissions_config_file):
            with open(permissions_config_file, "r", encoding="utf-8") as f:
                permissions_config.update(json.load(f))
    except Exception: pass

def save_permissions_config():
    safe_json_dump(permissions_config_file, permissions_config)

# ---------------- sound / TTS config ----------------
sound_config = {
    "tts_enabled": True, "tts_rate": 150, "tts_volume": 100,
    "success_sound": "", "revert_sound": "", "restart_sound": "", "ban_sound": "", "os_switch_sound": "",
}

def load_sound_config():
    global sound_config
    try:
        if os.path.exists(sound_config_file):
            with open(sound_config_file, "r", encoding="utf-8") as f:
                sound_config.update(json.load(f))
    except Exception: pass

def save_sound_config():
    safe_json_dump(sound_config_file, sound_config)

# ── Log broadcast: every log line (from self.log() and console_log() both -- they
#    converge on the same gui_log_queue) gets spoken via PowerShell SAPI on the HOST, and
#    typed directly into a dedicated logging VM's own keyboard input (the same steps as
#    !type {log} then !key enter). Off by default -- this spawns PowerShell processes and
#    a VM keyboard session per log line, which is a lot of overhead to turn on silently for
#    everyone the moment this feature ships. ──
LOG_BROADCAST_CONFIG_FILE = "log_broadcast_config.json"
LOG_BROADCAST_CONFIG = {
    "enabled": False,
    "tts_enabled": True,
    "vm_typing_enabled": True,
    "target_vm": "",
}

def load_log_broadcast_config():
    global LOG_BROADCAST_CONFIG
    try:
        if os.path.exists(LOG_BROADCAST_CONFIG_FILE):
            with open(LOG_BROADCAST_CONFIG_FILE, "r", encoding="utf-8") as f:
                LOG_BROADCAST_CONFIG.update(json.load(f))
    except Exception: pass

def save_log_broadcast_config():
    safe_json_dump(LOG_BROADCAST_CONFIG_FILE, LOG_BROADCAST_CONFIG)

_log_broadcast_queue = queue.Queue(maxsize=500)
_log_broadcast_worker_started = False
_log_broadcast_lock = threading.Lock()

def _ensure_log_broadcast_worker():
    global _log_broadcast_worker_started
    with _log_broadcast_lock:
        if _log_broadcast_worker_started:
            return
        _log_broadcast_worker_started = True
        threading.Thread(target=_log_broadcast_worker, daemon=True, name="log_broadcast_worker").start()

def _log_broadcast_worker():
    """Runs sequentially, one log line at a time, in strict FIFO order (queue.Queue()
    guarantees this, and only one worker thread ever runs -- see _ensure_log_broadcast_worker).
    Each log line's TTS + VM-typing fully completes -- including every 100-char chunk and
    its 5s waits, if the line is long -- before the NEXT log line starts processing. That's
    deliberate: it's what keeps log order intact even when a single long line takes a while
    to fully type out, rather than firing overlapping operations that finish in whatever
    order they happen to."""
    while True:
        msg_type, data = _log_broadcast_queue.get()
        try:
            if LOG_BROADCAST_CONFIG.get("tts_enabled", True):
                _powershell_speak_host(data)
            if LOG_BROADCAST_CONFIG.get("vm_typing_enabled", True):
                _send_log_to_vm(data)
        except Exception as e:
            console_log("ERROR", f"[logbroadcast] failed: {e}")
        finally:
            _log_broadcast_queue.task_done()

def _powershell_speak_host(text):
    """Speaks text on the HOST (unlike !tts, which types a PowerShell one-liner INTO the
    guest VM via Win+R). Windows: PowerShell's System.Speech SAPI wrapper. macOS: the
    built-in 'say' command -- no PowerShell equivalent needed, it's a native CLI tool
    that's been on every Mac since OS X, no install required."""
    safe_text = str(text).replace("'", "").replace('"', "").replace("`", "")[:500]
    if not safe_text.strip(): return
    if platform.system() == "Darwin":
        try:
            subprocess.run(["say", safe_text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        except FileNotFoundError:
            console_log("ERROR", "[logbroadcast] 'say' not found -- this should be built into every Mac; check your PATH.")
        except Exception as e:
            console_log("ERROR", f"[logbroadcast] macOS 'say' failed: {e}")
        return
    ps_script = f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe_text}')"
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
    except FileNotFoundError:
        console_log("ERROR", "[logbroadcast] powershell.exe not found -- this feature is Windows-only.")
    except Exception as e:
        console_log("ERROR", f"[logbroadcast] powershell tts failed: {e}")

def _find_window_and_send(process_name_pattern, text_or_key, is_special_key=False):
    """Generic implementation for posting input to VMware Workstation's own dialogs
    (currently the only user of this is !closevmwarewindow -- log broadcast types into a
    VM's own keyboard input instead, see _type_log_into_vm, not a host window).

    Windows: PostMessage/WM_CHAR (or WM_KEYDOWN/WM_KEYUP for special keys) posts directly
    to the window's message queue WITHOUT calling SetForegroundWindow, so it doesn't steal
    focus. Reliable against classic Win32 windows/dialogs, which is exactly what VMware
    Workstation's own prompts are.

    macOS: HONEST TRADEOFF -- there's no simple equivalent to background PostMessage
    without adding pyobjc/Quartz as a new dependency just for this one feature. This uses
    AppleScript (System Events) instead, which DOES briefly activate VMware Fusion first --
    it's a real, working way to dismiss a blocking Fusion dialog, just not a silent
    background one the way the Windows path is."""
    if platform.system() == "Darwin":
        app_name = "VMware Fusion" if "vmware" in process_name_pattern.lower() else process_name_pattern
        try:
            if is_special_key:
                # Only Enter (0x0D) is actually used via this path today.
                key_script = 'key code 36'  # 36 = Return on macOS
            else:
                safe_text = str(text_or_key).replace('"', '\\"').replace("'", "").replace("\\", "")[:500]
                key_script = f'keystroke "{safe_text}"\n            key code 36'
            osa = f'''tell application "{app_name}" to activate
delay 0.3
tell application "System Events"
    {key_script}
end tell'''
            subprocess.run(["osascript", "-e", osa], capture_output=True, text=True, timeout=15)
            return True
        except FileNotFoundError:
            console_log("ERROR", "[sendkeys] osascript not found -- this should be built into every Mac.")
            return False
        except Exception as e:
            console_log("ERROR", f"[sendkeys] failed targeting '{app_name}': {e}")
            return False
    if is_special_key:
        ps_body = f"""
foreach ($p in $procs) {{
    $hwnd = $p.MainWindowHandle
    [Win32SendKeys]::PostMessage($hwnd, 0x0100, [IntPtr]{text_or_key}, [IntPtr]::Zero)
    Start-Sleep -Milliseconds 30
    [Win32SendKeys]::PostMessage($hwnd, 0x0101, [IntPtr]{text_or_key}, [IntPtr]::Zero)
}}"""
    else:
        safe_text = str(text_or_key).replace("'", "''")[:500]
        ps_body = f"""
foreach ($p in $procs) {{
    $hwnd = $p.MainWindowHandle
    foreach ($ch in [char[]]'{safe_text}') {{
        [Win32SendKeys]::PostMessage($hwnd, 0x0102, [IntPtr][int]$ch, [IntPtr]::Zero)
    }}
    Start-Sleep -Milliseconds 30
    [Win32SendKeys]::PostMessage($hwnd, 0x0100, [IntPtr]0x0D, [IntPtr]::Zero)
    Start-Sleep -Milliseconds 30
    [Win32SendKeys]::PostMessage($hwnd, 0x0101, [IntPtr]0x0D, [IntPtr]::Zero)
}}"""
    ps_script = f"""
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32SendKeys {{
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);
}}
"@
$procs = Get-Process | Where-Object {{ $_.ProcessName -match "{process_name_pattern}" -and $_.MainWindowHandle -ne 0 }}
{ps_body}
"""
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        return True
    except FileNotFoundError:
        console_log("ERROR", "[sendkeys] powershell.exe not found -- this feature is Windows-only.")
        return False
    except Exception as e:
        console_log("ERROR", f"[sendkeys] failed targeting '{process_name_pattern}': {e}")
        return False

def _type_log_into_vm(target_vm_name, text):
    """Types text into a VBox VM's own keyboard input, then presses Enter -- the exact same
    steps as !type {text} followed by !key enter, just running against a SEPARATE, dedicated
    logging VM rather than whichever VM is currently the main stream target. Establishes its
    own short-lived COM session (connect, lock, type, unlock) rather than sharing/hijacking
    the main VM's persistent session in executor_loop, since they could easily be two
    different VMs running at the same time. Returns (ok: bool, message: str)."""
    if not target_vm_name:
        return False, "no logging VM selected"
    if not vbox_pkg:
        return False, "no VirtualBox COM package available (install 'virtualbox' or vboxapi)"

    vbox = None
    session = None
    try:
        if 'pythoncom' in sys.modules:
            try: pythoncom.CoInitialize()
            except Exception: pass

        if vbox_pkg == "virtualbox":
            vbox = virtualbox.VirtualBox()
            machine = vbox.find_machine(target_vm_name)
            state_str = str(getattr(machine, "state", "unknown")).lower()
        else:
            mgr = VirtualBoxManager(None, None)
            vbox = mgr.getVirtualBox()
            machine = vbox.findMachine(target_vm_name)
            state_str = str(getattr(machine, "state", "unknown")).lower()

        is_running = ("running" in state_str) or ("5" in state_str)
        if not is_running:
            return False, f"'{target_vm_name}' isn't running right now"

        if vbox_pkg == "virtualbox":
            session = virtualbox.Session()
            machine.lock_machine(session, virtualbox.library.LockType.shared)
        else:
            session = mgr.getSessionObject(vbox)
            machine.lockMachine(session, mgr.constants.LockType_Shared)

        keyboard = session.console.keyboard

        def _send_codes(codes):
            int_codes = [int(c) for c in codes]
            if hasattr(keyboard, 'put_scancodes'): keyboard.put_scancodes(int_codes)
            else: keyboard.putScancodes(int_codes)

        def _release_codes(codes):
            return [c if c in (224, 225) else c | 0x80 for c in codes]

        for char in text:
            modifiers, base_code = get_typed_codes(char, keyboard_layout)
            if base_code == [0]:
                continue
            for mod in modifiers:
                _send_codes(mod)
                time.sleep(0.002)
            _send_codes(base_code)
            time.sleep(0.01)
            _send_codes(_release_codes(base_code))
            for mod in reversed(modifiers):
                time.sleep(0.002)
                if mod == [0x2A]: _send_codes([0xAA])
                elif mod == [0xE0, 0x38]: _send_codes([0xE0, 0xB8])
                else: _send_codes(_release_codes(mod))
                time.sleep(0.002)

        time.sleep(0.05)
        if "enter" in scancodes:
            _send_codes(scancodes["enter"])
            time.sleep(0.1)
            _send_codes(_release_codes(scancodes["enter"]))

        return True, f"typed into '{target_vm_name}'"
    except Exception as e:
        return False, str(e)
    finally:
        try:
            if session is not None:
                if vbox_pkg == "virtualbox": session.unlock_machine()
                else: session.unlockMachine()
        except Exception: pass
        try:
            if 'pythoncom' in sys.modules: pythoncom.CoUninitialize()
        except Exception: pass


def _send_log_to_vm(text):
    """Splits text into 100-character chunks. Each chunk is typed into the configured
    logging VM and Enter-pressed (the same steps as !type {chunk} !key enter) in full
    before the next one starts, with a 5-second wait between chunks -- all still inside
    the single sequential _log_broadcast_worker, so log lines never interleave with each
    other even when one of them needs several chunks."""
    target_vm = LOG_BROADCAST_CONFIG.get("target_vm", "").strip()
    if not target_vm:
        console_log("WARN", "[logbroadcast] no logging VM selected -- pick one on the Automation tab.")
        return
    text = str(text)
    chunks = [text[i:i+100] for i in range(0, len(text), 100)] or [""]
    for i, chunk in enumerate(chunks):
        ok, msg = _type_log_into_vm(target_vm, chunk)
        if not ok:
            console_log("ERROR", f"[logbroadcast] failed typing into '{target_vm}': {msg}")
            break
        if i < len(chunks) - 1:
            time.sleep(5)


def _send_enter_to_vmware_window():
    """!closevmwarewindow -- posts Enter to the VMware window to dismiss a blocking
    prompt/dialog ("this VM may have been moved or copied", etc.) that would otherwise
    stall automated VM control. On Windows this doesn't need the window focused; on macOS
    it briefly activates VMware Fusion first (see _find_window_and_send for why)."""
    return _find_window_and_send("vmware", "0x0D", is_special_key=True)

def play_event_sound(event_key):
    sound_file = sound_config.get(event_key, "")
    if not sound_file or not os.path.exists(sound_file): return
    def _play():
        try:
            if platform.system() == "Windows": subprocess.Popen(['start', sound_file], shell=True)
            elif platform.system() == "Darwin": subprocess.Popen(['afplay', sound_file])
            else: subprocess.Popen(['aplay', sound_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e: console_log("WARN", f"sound playback failed: {e}")
    threading.Thread(target=_play, daemon=True).start()

def log_startup_diagnostics():
    """One-time diagnostic line so odd low-level errors (e.g. unusual Python versions not
    yet fully validated against Twisted/vncdotool) are easy to rule in or out."""
    console_log("INFO", f"[diag] python {sys.version.split()[0]} on {platform.system()} {platform.release()} | "
                         f"vncdotool: {'available' if vncdotool_available else 'not installed'} | "
                         f"obsws-python: {'available' if obs_available else 'not installed'} | "
                         f"flask: {'available' if flask_available else 'NOT INSTALLED'} (web/overlay server will try port {flask_port})")

def check_tts_backend_available():
    """One-time startup check so 'tts not speaking' shows a clear reason immediately in the log,
    instead of the user discovering it silently later."""
    has_pyttsx3 = pyttsx3_available
    has_espeak_cli = shutil.which("espeak-ng") is not None or shutil.which("espeak") is not None
    if not sound_config.get("tts_enabled", True):
        console_log("INFO", "[tts] text-to-speech is currently DISABLED in settings (Automation tab).")
    elif not has_pyttsx3 and not has_espeak_cli:
        console_log("ERROR", "[tts] NO TTS backend detected at startup. Host-side announcements (like OS-switch "
                              "narration) will be silent until you install one: 'pip install pyttsx3' and/or "
                              "'sudo dnf install espeak-ng' (Fedora/Bazzite) / 'sudo apt install espeak-ng' "
                              "(Debian/Ubuntu). On Bazzite specifically: 'rpm-ostree install espeak-ng' then "
                              "reboot, or install it inside a Distrobox container.")
    elif not has_pyttsx3 and has_espeak_cli:
        console_log("INFO", "[tts] pyttsx3 not installed -- will use the espeak/espeak-ng CLI directly as the TTS backend.")
    else:
        console_log("INFO", "[tts] TTS backend ready (pyttsx3).")

def speak_text(text):
    if not sound_config.get("tts_enabled", True): return
    if not text or not str(text).strip(): return
    _tts_queue.put(str(text))
    _tts_ensure_worker()

_tts_queue = queue.Queue()
_tts_worker_thread = None
_tts_worker_lock = threading.Lock()
_tts_engine = None  # persistent pyttsx3 engine, created once (re-creating per call is what breaks pyttsx3 on Linux)
_tts_backend_warned = False

def _tts_get_engine():
    """pyttsx3 on Linux wraps espeak and is NOT safe to re-init per call or drive from multiple
    threads -- doing that is the classic cause of 'tts silently does nothing'. We create exactly
    one engine, lazily, and only ever touch it from the single _tts_worker thread below."""
    global _tts_engine
    if _tts_engine is not None: return _tts_engine
    if not pyttsx3_available: return None
    try:
        _tts_engine = _pyttsx3.init()
        return _tts_engine
    except Exception as e:
        console_log("ERROR", f"[tts] pyttsx3.init() failed ({e}). On Linux this almost always means the "
                              f"'espeak' or 'espeak-ng' package isn't installed. Falling back to raw espeak CLI.")
        _tts_engine = False  # sentinel: "tried and failed, don't retry init every call"
        return None

def _tts_speak_espeak_cli(text, rate, volume):
    for binary in ("espeak-ng", "espeak"):
        if shutil.which(binary) is None: continue
        try:
            subprocess.run([binary, "-s", str(rate), "-a", str(int(max(0, min(100, volume)) * 2)), text],
                            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            return True
        except Exception as e:
            console_log("ERROR", f"[tts] '{binary}' CLI failed: {e}")
    return False

def _tts_worker():
    global _tts_backend_warned
    while True:
        try:
            text = _tts_queue.get(timeout=2)
        except queue.Empty:
            if app_instance is None or not app_instance.running:
                return  # app is closing, let this daemon thread end
            continue
        rate = int(sound_config.get("tts_rate", 150))
        volume = int(sound_config.get("tts_volume", 100))
        spoke = False
        engine = _tts_get_engine()
        if engine:
            try:
                engine.setProperty("rate", rate)
                engine.setProperty("volume", max(0.0, min(1.0, volume / 100.0)))
                engine.say(text)
                engine.runAndWait()
                spoke = True
            except Exception as e:
                console_log("ERROR", f"[tts] pyttsx3 engine.say()/runAndWait() failed: {e}. Trying espeak CLI fallback.")
        if not spoke:
            spoke = _tts_speak_espeak_cli(text, rate, volume)
        if not spoke and not _tts_backend_warned:
            _tts_backend_warned = True
            console_log("ERROR", "[tts] NO working TTS backend found. Install one of: "
                                  "'sudo dnf install espeak-ng' (or 'sudo apt install espeak-ng' / your distro's "
                                  "package manager), and/or 'pip install pyttsx3'. On Bazzite/immutable distros, "
                                  "layer it with 'rpm-ostree install espeak-ng' + reboot, or run the bot inside a "
                                  "Distrobox container where you can dnf/apt install normally.")
            notify("TTS Unavailable", "No text-to-speech backend found -- see console log for install steps.", timeout=8)

def _tts_ensure_worker():
    global _tts_worker_thread
    with _tts_worker_lock:
        if _tts_worker_thread is None or not _tts_worker_thread.is_alive():
            _tts_worker_thread = threading.Thread(target=_tts_worker, daemon=True)
            _tts_worker_thread.start()

# ---------------- !gtts: Google Text-to-Speech ----------------
# Unlike !tts/!ttsxp/etc (which type a PowerShell/VBScript one-liner INTO the VM so it speaks
# through the VM's own Windows SAPI voice), !gtts synthesizes real speech via Google Translate's
# TTS API and plays it on the HOST's speakers through python-vlc -- the same playback engine the
# Music and Soundboard panels use. No VNC/VM interaction at all, so it works even with no VNC
# target configured.
gtts_vlc_instance = None
gtts_active_players = []   # live vlc.MediaPlayer refs, kept so overlapping clips don't get GC'd mid-playback
gtts_status_text = "idle"
gtts_lock = threading.RLock()

def _gtts_cache_dir():
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gtts_cache")
    try: os.makedirs(d, exist_ok=True)
    except Exception: pass
    return d

def _gtts_cache_key(text):
    key = re.sub(r"[^a-zA-Z0-9_-]+", "_", (text or "").strip().lower()).strip("_")
    return (key or "speech")[:60]

def _gtts_get_vlc_instance():
    global gtts_vlc_instance
    if not vlc_available: return None
    if gtts_vlc_instance is None:
        try: gtts_vlc_instance = _vlc.Instance("--no-video", "--quiet", "--aout=any")
        except Exception as e:
            console_log("ERROR", f"[gtts] vlc init failed: {e}")
            return None
    return gtts_vlc_instance

def gtts_speak(text, lang="en"):
    """Synthesizes `text` with Google TTS (cached to disk by text) and plays it on the host's
    speakers. Returns (ok, info_or_error)."""
    global gtts_status_text
    text = (text or "").strip()
    if not text:
        return False, "no text given"
    if not gtts_available:
        return False, "gTTS is not installed -- run: pip install gTTS"
    inst = _gtts_get_vlc_instance()
    if inst is None:
        return False, "python-vlc is not installed (pip install python-vlc, and install VLC itself)"

    cache_path = os.path.join(_gtts_cache_dir(), _gtts_cache_key(text) + ".mp3")
    if not os.path.exists(cache_path):
        gtts_status_text = f"synthesizing '{text[:40]}'..."
        console_log("INFO", f"[gtts] {gtts_status_text}")
        try:
            _gTTS(text=text, lang=lang).save(cache_path)
        except Exception as e:
            gtts_status_text = f"synthesis failed: {e}"
            console_log("ERROR", f"[gtts] {gtts_status_text}")
            return False, str(e)

    try:
        media = inst.media_new(cache_path)
        mp = inst.media_player_new()
        mp.set_media(media)
        try: mp.audio_set_volume(int(sound_config.get("tts_volume", 100)))
        except Exception: pass
        mp.play()
        with gtts_lock:
            gtts_active_players.append(mp)
            gtts_active_players[:] = [p for p in gtts_active_players if p is mp or p.is_playing()][-30:]
        gtts_status_text = f"speaking: {text[:60]}"
        console_log("INFO", f"[gtts] {gtts_status_text}")
        return True, text
    except Exception as e:
        gtts_status_text = f"playback error: {e}"
        console_log("ERROR", f"[gtts] {gtts_status_text}")
        return False, str(e)

# ---------------- user management (whitelist / vip / persistent blocked) ----------------
whitelist_users = set()
vip_users = {}
blocked_users_persistent = set()
banned_users_chat = {}   # {username: unix_timestamp_when_ban_expires} -- from !ban chat votes
ban_votes_active = {}    # {target_username: set(voter_usernames)} -- in-progress !ban votes

def load_user_mgmt():
    global whitelist_users, vip_users, blocked_users_persistent, banned_users_chat
    try:
        if os.path.exists(user_mgmt_file):
            with open(user_mgmt_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            whitelist_users = set(normalize_username(u) for u in data.get("whitelist", []))
            vip_users = {normalize_username(k): v for k, v in data.get("vip", {}).items()}
            blocked_users_persistent = set(normalize_username(u) for u in data.get("blocked", []))
            banned_users_chat = {normalize_username(k): v for k, v in data.get("banned_chat", {}).items()}
    except Exception: pass

def save_user_mgmt():
    safe_json_dump(user_mgmt_file, {
        "whitelist": sorted(whitelist_users), "vip": vip_users, "blocked": sorted(blocked_users_persistent),
        "banned_chat": banned_users_chat
    })

# ---------------- multi-stream toggle config (separate from --multistream instances) ----------------
multi_stream_config = {"video_ids": []}

def load_multi_stream_config():
    global multi_stream_config
    try:
        if os.path.exists(multi_stream_config_file):
            with open(multi_stream_config_file, "r", encoding="utf-8") as f:
                multi_stream_config.update(json.load(f))
    except Exception: pass

def save_multi_stream_config():
    safe_json_dump(multi_stream_config_file, multi_stream_config)

# ---------------- Real PC remote-control bot ----------------
realpc_config = {
    "video_id": "", "cooldown": 1.0, "whitelist_only": False, "whitelist": [], "blocked": [],
    "failsafe": True, "action_delay": 0.05, "mouse_step": 50, "scroll_step": 3, "max_type_length": 100,
    "text_only": False,
    "allowed_actions": {"keyboard": True, "mouse": True, "combo": True, "screenshot": True},
    # VNC target -- can point at a VMware VM's own VNC server, or a completely
    # separate real machine running any VNC server. This is now the ONE input mechanism used
    # for both the "Real PC" panel and the main chat-controls-the-target input path; direct COM
    # keyboard/mouse injection is no longer used for input (VM lifecycle -- start/stop/revert/
    # snapshot -- goes through vmrun and is unaffected by this).
    "vnc_host": "", "vnc_port": 5900, "vnc_password": "",
}
realpc_stop_event = threading.Event()
realpc_bot_thread = None
realpc_user_cooldowns = {}
realpc_cooldown_lock = threading.Lock()
realpc_status_text = "stopped"

def load_realpc_config():
    global realpc_config
    try:
        if os.path.exists(realpc_config_file):
            with open(realpc_config_file, "r", encoding="utf-8") as f:
                realpc_config.update(json.load(f))
    except Exception: pass

def save_realpc_config():
    safe_json_dump(realpc_config_file, realpc_config)

# ---------------- VMware vmrun + VNC backend (ported from the VMware-styled bot) ----------------
# vmrun is VMware Workstation's command-line VM control tool (the vmrun.exe equivalent of
# VBoxManage). vmrun has no keystroke/mouse-injection command of its own, so keyboard/mouse
# control for a VMware-backed VM goes over VNC (vncdotool) directly to the VM's console --
# VMware Workstation exposes a VNC server per-VM, the same way VirtualBox's VRDE does.
vbox_config = {
    "vmrun_path": "", "vmx_path": "", "snapshot_name": "",
    "vnc_host": "", "vnc_port": 5900, "vnc_password": "",
    "host_vmnet_interface": "",
    "internet_adapter": "ethernet0",
}

def load_vbox_config():
    global vbox_config
    try:
        if os.path.exists(vbox_config_file):
            with open(vbox_config_file, "r", encoding="utf-8") as f:
                vbox_config.update(json.load(f))
        if isinstance(vbox_config.get("vmware_vnc"), dict):
            vmware_panel_vnc_config.update(vbox_config["vmware_vnc"])
    except Exception: pass

def save_vbox_config():
    safe_json_dump(vbox_config_file, vbox_config)

def _looks_like_exe_named(path, name_fragment):
    """Defensive sanity check: does this path's filename actually look like the tool we
    think it is? Catches a stale/misconfigured path silently pointing at the WRONG
    executable (e.g. vmrun_path resolving to VBoxManage.exe) instead of invoking it blindly
    and getting a confusing error back from the wrong tool."""
    if not path:
        return False
    base = os.path.basename(str(path)).lower()
    return name_fragment in base

VMRUN_TARGET_TYPE = "fusion" if platform.system() == "Darwin" else "ws"
# vmrun's -T flag identifies which VMware product is being driven -- 'ws' (Workstation)
# on Windows/Linux, 'fusion' (VMware Fusion) on macOS.

def get_vmrun_path():
    """Locates vmrun.exe, VMware Workstation's command-line control tool. The single
    source of truth is the vmrun_cmd global (kept in sync by save_vbox_settings() whenever
    the VM Config panel's backend is set to vmware) -- deliberately NOT cross-checking
    vbox_config here, since that dict is only ever written vboxmanage_path/vmware_vnc keys
    by the VM Backends tab, and a stale/leftover "vmrun_path" key there from an older
    version of this config file has caused this to silently resolve to VBoxManage.exe
    before."""
    if vmrun_cmd and (os.path.exists(vmrun_cmd) or vmrun_cmd == "vmrun"):
        if vmrun_cmd == "vmrun" or _looks_like_exe_named(vmrun_cmd, "vmrun"):
            return vmrun_cmd
        console_log("ERROR", f"[vmrun] configured path '{vmrun_cmd}' doesn't look like vmrun.exe -- refusing to use it. Re-set it on the VM Config tab.")
        return None
    return None

def get_vboxmanage_path():
    """Locates VBoxManage.exe, VirtualBox's command-line control tool. Same reasoning as
    get_vmrun_path() above -- vbox_manage_cmd is the single source of truth."""
    if vbox_manage_cmd and (os.path.exists(vbox_manage_cmd) or vbox_manage_cmd == "VBoxManage"):
        if vbox_manage_cmd == "VBoxManage" or _looks_like_exe_named(vbox_manage_cmd, "vboxmanage"):
            return vbox_manage_cmd
        console_log("ERROR", f"[vboxmanage] configured path '{vbox_manage_cmd}' doesn't look like VBoxManage.exe -- refusing to use it. Re-set it on the VM Backends tab.")
        return None
    return None

# ── VBox (VBoxManage-backed) primitives ──
def vbox_is_running(target_vm_name, vbox_exe=None):
    vbox_exe = vbox_exe or vbox_manage_cmd
    if not target_vm_name or not vbox_exe:
        return False
    try:
        result = subprocess.run([vbox_exe, "list", "runningvms"], capture_output=True, text=True, timeout=15)
        return f'"{target_vm_name}"' in (result.stdout or "")
    except Exception as e:
        console_log("ERROR", f"[vboxmanage] list error: {e}")
        return False

def vbox_start(target_vm_name, gui=True, vbox_exe=None):
    vbox_exe = vbox_exe or vbox_manage_cmd
    mode = "gui" if gui else "headless"
    return subprocess.run([vbox_exe, "startvm", target_vm_name, "--type", mode], capture_output=True, text=True)

def vbox_stop(target_vm_name, hard=True, vbox_exe=None):
    vbox_exe = vbox_exe or vbox_manage_cmd
    verb = "poweroff" if hard else "acpipowerbutton"
    return subprocess.run([vbox_exe, "controlvm", target_vm_name, verb], capture_output=True, text=True)

def vbox_reset(target_vm_name, hard=True, vbox_exe=None):
    vbox_exe = vbox_exe or vbox_manage_cmd
    verb = "reset" if hard else "acpipowerbutton"
    return subprocess.run([vbox_exe, "controlvm", target_vm_name, verb], capture_output=True, text=True)

def vbox_revert_to_snapshot(target_vm_name, snapshot_name, vbox_exe=None):
    vbox_exe = vbox_exe or vbox_manage_cmd
    return subprocess.run([vbox_exe, "snapshot", target_vm_name, "restore", snapshot_name], capture_output=True, text=True)

def vbox_snapshot(target_vm_name, snapshot_name, vbox_exe=None):
    vbox_exe = vbox_exe or vbox_manage_cmd
    return subprocess.run([vbox_exe, "snapshot", target_vm_name, "take", snapshot_name, "--live"], capture_output=True, text=True)

def vbox_delete_snapshot(target_vm_name, snapshot_name, vbox_exe=None):
    vbox_exe = vbox_exe or vbox_manage_cmd
    return subprocess.run([vbox_exe, "snapshot", target_vm_name, "delete", snapshot_name], capture_output=True, text=True)

def vbox_suspend(target_vm_name, vbox_exe=None):
    vbox_exe = vbox_exe or vbox_manage_cmd
    return subprocess.run([vbox_exe, "controlvm", target_vm_name, "savestate"], capture_output=True, text=True)

def vbox_pause(target_vm_name, vbox_exe=None):
    vbox_exe = vbox_exe or vbox_manage_cmd
    return subprocess.run([vbox_exe, "controlvm", target_vm_name, "pause"], capture_output=True, text=True)

def vbox_unpause(target_vm_name, vbox_exe=None):
    vbox_exe = vbox_exe or vbox_manage_cmd
    return subprocess.run([vbox_exe, "controlvm", target_vm_name, "resume"], capture_output=True, text=True)

def vbox_toggle_internet(target_vm_name, enable, vbox_exe=None):
    """Cuts/restores internet access LIVE via VBoxManage controlvm setlinkstate1 on/off --
    works on a running VM directly, no file editing or restart needed."""
    vbox_exe = vbox_exe or vbox_manage_cmd
    if not vbox_exe:
        return subprocess.CompletedProcess([], 1, "", "VBoxManage not found")
    state = "on" if enable else "off"
    try:
        res = subprocess.run([vbox_exe, "controlvm", target_vm_name, "setlinkstate1", state],
                              capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess([], 1, "", "timed out waiting for VBoxManage to respond")
    if res.returncode == 0:
        note = f"adapter 1 link state set to '{state}' LIVE via VBoxManage (works on a running VM, no restart needed)."
        res.stdout = ((res.stdout or "") + " " + note).strip()
    return res

# ── VMware (vmrun-backed) primitives ──
def vmware_is_running(vmx_path, vmrun_exe=None):
    vmrun_exe = vmrun_exe or vmrun_cmd
    if not vmx_path or not vmrun_exe:
        return False
    try:
        result = subprocess.run([vmrun_exe, "-T", VMRUN_TARGET_TYPE, "list"], capture_output=True, text=True, timeout=15)
        return vmx_path.lower() in (result.stdout or "").lower()
    except Exception as e:
        console_log("ERROR", f"[vmrun] list error: {e}")
        return False

def vmware_start(vmx_path, gui=True, vmrun_exe=None):
    vmrun_exe = vmrun_exe or vmrun_cmd
    mode = "gui" if gui else "nogui"
    return subprocess.run([vmrun_exe, "-T", VMRUN_TARGET_TYPE, "start", vmx_path, mode], capture_output=True, text=True)

def vmware_stop(vmx_path, hard=True, vmrun_exe=None):
    vmrun_exe = vmrun_exe or vmrun_cmd
    mode = "hard" if hard else "soft"
    return subprocess.run([vmrun_exe, "-T", VMRUN_TARGET_TYPE, "stop", vmx_path, mode], capture_output=True, text=True)

def vmware_reset(vmx_path, hard=True, vmrun_exe=None):
    vmrun_exe = vmrun_exe or vmrun_cmd
    mode = "hard" if hard else "soft"
    return subprocess.run([vmrun_exe, "-T", VMRUN_TARGET_TYPE, "reset", vmx_path, mode], capture_output=True, text=True)

def vmware_revert_to_snapshot(vmx_path, snapshot_name, vmrun_exe=None):
    vmrun_exe = vmrun_exe or vmrun_cmd
    return subprocess.run([vmrun_exe, "-T", VMRUN_TARGET_TYPE, "revertToSnapshot", vmx_path, snapshot_name], capture_output=True, text=True)

def vmware_snapshot(vmx_path, snapshot_name, vmrun_exe=None):
    vmrun_exe = vmrun_exe or vmrun_cmd
    return subprocess.run([vmrun_exe, "-T", VMRUN_TARGET_TYPE, "snapshot", vmx_path, snapshot_name], capture_output=True, text=True)

def vmware_delete_snapshot(vmx_path, snapshot_name, vmrun_exe=None):
    vmrun_exe = vmrun_exe or vmrun_cmd
    return subprocess.run([vmrun_exe, "-T", VMRUN_TARGET_TYPE, "deleteSnapshot", vmx_path, snapshot_name], capture_output=True, text=True)

def vmware_suspend(vmx_path, vmrun_exe=None):
    vmrun_exe = vmrun_exe or vmrun_cmd
    return subprocess.run([vmrun_exe, "-T", VMRUN_TARGET_TYPE, "suspend", vmx_path], capture_output=True, text=True)

def vmware_pause(vmx_path, vmrun_exe=None):
    vmrun_exe = vmrun_exe or vmrun_cmd
    return subprocess.run([vmrun_exe, "-T", VMRUN_TARGET_TYPE, "pause", vmx_path], capture_output=True, text=True)

def vmware_unpause(vmx_path, vmrun_exe=None):
    vmrun_exe = vmrun_exe or vmrun_cmd
    return subprocess.run([vmrun_exe, "-T", VMRUN_TARGET_TYPE, "unpause", vmx_path], capture_output=True, text=True)

def vmware_toggle_internet(vmx_path, enable, adapter="ethernet0", vmrun_exe=None):
    """Cuts/restores internet access LIVE via vmrun writeVariable's runtimeConfig override --
    host-side only, does not persist across a full VM restart (use the Host VMnet Adapter
    toggle instead if you need something that survives a restart)."""
    vmrun_exe = vmrun_exe or vmrun_cmd
    if not vmrun_exe:
        return subprocess.CompletedProcess([], 1, "", "vmrun not found")
    target_type = "nat" if enable else "hostonly"
    cmd = [vmrun_exe, "-T", VMRUN_TARGET_TYPE, "writeVariable", vmx_path, "runtimeConfig", f"{adapter}.connectionType", target_type]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 1, "", "timed out waiting for vmrun to respond")
    if res.returncode == 0:
        note = f'{adapter}.connectionType set to "{target_type}" LIVE via vmrun (host-side only -- same as switching Bridged/NAT/Host-only in VM Settings while running).'
        res.stdout = ((res.stdout or "") + " " + note).strip()
    return res

def toggle_vmware_nat_service(enable):
    """!enableinternetvmware / !disableinternetvmware -- starts/stops VMware's host-wide
    NAT networking. This is DELIBERATELY different from vmware_toggle_internet() above
    (vmrun's per-VM runtimeConfig override): this affects every VMware VM using NAT on
    this machine, not just whichever VM is currently active -- and doesn't need a specific
    VM target at all.

    Windows: starts/stops the "VMware NAT Service" via net start/stop.
    macOS: VMware Fusion has no equivalent Windows-style service -- NAT networking is
    provided by a LaunchDaemon (com.vmware.launchd.vmnet) that vmnet-natd/vmnet-dhcpd run
    under. Stopping/starting it via launchctl is the closest equivalent, but this requires
    admin privileges, and raw subprocess sudo doesn't work from a GUI app (no way to enter
    the password) -- osascript's "with administrator privileges" pops the native macOS
    auth dialog instead, which is the correct way to do this from Tkinter.
    HONEST NOTE: the exact LaunchDaemon label can vary by Fusion version -- if this fails,
    check `sudo launchctl list | grep vmware` on your machine and adjust NAT_LAUNCHD_LABEL
    below to match."""
    if platform.system() == "Darwin":
        verb = "start" if enable else "stop"
        NAT_LAUNCHD_LABEL = "com.vmware.launchd.vmnet"
        script = f'do shell script "launchctl {verb} {NAT_LAUNCHD_LABEL}" with administrator privileges'
        try:
            return subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess([], 1, "", "timed out waiting for the admin-privileges prompt")
        except Exception as e:
            return subprocess.CompletedProcess([], 1, "", str(e))
    verb = "start" if enable else "stop"
    try:
        return subprocess.run(["net", verb, "VMware NAT Service"], capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess([], 1, "", "timed out waiting for 'net' to respond")
    except Exception as e:
        return subprocess.CompletedProcess([], 1, "", str(e))

# ── Backend-aware generic wrappers -- these are what callers (run_cmd_worker,
#    _do_vm_maintenance, executor_loop, switch_os) should actually use. Each just
#    dispatches to the vbox_*/vmware_* implementation above matching `backend`. ──
def vm_is_running(target, backend=None, exe=None):
    backend = backend or current_vm_backend
    if backend == "vmware":
        return vmware_is_running(target, exe or get_vmrun_path())
    return vbox_is_running(target, exe or get_vboxmanage_path())

def vm_start(target, backend=None, gui=True):
    backend = backend or current_vm_backend
    if backend == "vmware":
        return vmware_start(target, gui, get_vmrun_path())
    return vbox_start(target, gui, get_vboxmanage_path())

def vm_stop(target, backend=None, hard=True):
    backend = backend or current_vm_backend
    if backend == "vmware":
        return vmware_stop(target, hard, get_vmrun_path())
    return vbox_stop(target, hard, get_vboxmanage_path())

def vm_reset(target, backend=None, hard=True):
    backend = backend or current_vm_backend
    if backend == "vmware":
        return vmware_reset(target, hard, get_vmrun_path())
    return vbox_reset(target, hard, get_vboxmanage_path())

def vm_revert_to_snapshot(target, snapshot_name, backend=None):
    backend = backend or current_vm_backend
    if backend == "vmware":
        return vmware_revert_to_snapshot(target, snapshot_name, get_vmrun_path())
    return vbox_revert_to_snapshot(target, snapshot_name, get_vboxmanage_path())

def vm_snapshot(target, snapshot_name, backend=None):
    backend = backend or current_vm_backend
    if backend == "vmware":
        return vmware_snapshot(target, snapshot_name, get_vmrun_path())
    return vbox_snapshot(target, snapshot_name, get_vboxmanage_path())

def vm_delete_snapshot(target, snapshot_name, backend=None):
    backend = backend or current_vm_backend
    if backend == "vmware":
        return vmware_delete_snapshot(target, snapshot_name, get_vmrun_path())
    return vbox_delete_snapshot(target, snapshot_name, get_vboxmanage_path())

def vm_suspend(target, backend=None):
    backend = backend or current_vm_backend
    if backend == "vmware":
        return vmware_suspend(target, get_vmrun_path())
    return vbox_suspend(target, get_vboxmanage_path())

def vm_pause(target, backend=None):
    backend = backend or current_vm_backend
    if backend == "vmware":
        return vmware_pause(target, get_vmrun_path())
    return vbox_pause(target, get_vboxmanage_path())

def vm_unpause(target, backend=None):
    backend = backend or current_vm_backend
    if backend == "vmware":
        return vmware_unpause(target, get_vmrun_path())
    return vbox_unpause(target, get_vboxmanage_path())

def vm_toggle_internet(target, enable, backend=None):
    backend = backend or current_vm_backend
    if backend == "vmware":
        return vmware_toggle_internet(target, enable, vbox_config.get("internet_adapter", "ethernet0"), get_vmrun_path())
    return vbox_toggle_internet(target, enable, get_vboxmanage_path())

def vm_get_snapshots(target, backend=None):
    backend = backend or current_vm_backend
    if backend == "vmware":
        return get_vmware_snapshots(get_vmrun_path(), target)
    return get_vbox_snapshots(get_vboxmanage_path(), target)

# Back-compat aliases for any remaining call sites still using the old names directly --
# these always mean "the VBox implementation" now that vmrun_* is reserved for real vmrun.
vmrun_is_running = vbox_is_running
get_vmrun_snapshots = get_vbox_snapshots
vmrun_toggle_internet = vbox_toggle_internet

def toggle_host_vmnet_adapter(interface_name, enable):
    """Disables/enables a REAL host-side VMware virtual network adapter (e.g. 'VMware Network
    Adapter VMnet8' for NAT, or 'VMware Network Adapter VMnet1' for Host-only) on the HOST
    itself -- no vmrun, no guest login, no GUI/mouse control, nothing VM-internal at all.
    Windows: PowerShell's Disable-NetAdapter/Enable-NetAdapter, which actually disables and
    re-enables the adapter at the driver level (a thorough reset, not just an admin-state
    flag flip) -- genuine Windows network interface, so it's instant and dependable, but
    cuts that network off for EVERY VM using it, not just one target VM.
    NOTE: VMnet0 (Bridged, the default) usually has NO dedicated host adapter to toggle this
    way -- bridged mode hooks the physical NIC directly instead of creating a separate
    virtual adapter. This only works for NAT/Host-only-style vnets.

    macOS: HONEST NOTE -- this is a genuinely different concept here. There's no Windows-style
    named, toggleable network adapter for vmnet1/vmnet8 the way Device Manager exposes one --
    they're kernel-level virtual interfaces, normally always up as long as Fusion's vmnet
    daemon is running (see toggle_vmware_nat_service/vmware_toggle_internet for the actual
    macOS equivalent of "cut this network off for everyone"). This falls back to `ifconfig
    <iface> down/up` as the closest analog, but expects a PLAIN interface name like "vmnet8",
    not the Windows-style "VMware Network Adapter VMnet8" -- strips any such prefix if given
    one anyway, as a best-effort convenience."""
    if platform.system() == "Darwin":
        iface = interface_name
        for prefix in ("VMware Network Adapter ", "vmnet adapter "):
            if iface.lower().startswith(prefix.lower()):
                iface = iface[len(prefix):]
        iface = iface.strip().lower()
        if not iface.startswith("vmnet"):
            iface = f"vmnet{iface}" if iface.isdigit() else iface
        verb = "up" if enable else "down"
        script = f'do shell script "ifconfig {iface} {verb}" with administrator privileges'
        try:
            return subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=20)
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess([], 1, "", "timed out waiting for the admin-privileges prompt")
        except Exception as e:
            return subprocess.CompletedProcess([], 1, "", str(e))
    action = "Enable-NetAdapter" if enable else "Disable-NetAdapter"
    ps_script = f'{action} -Name "{interface_name}" -Confirm:$false'
    cmd = ["powershell.exe", "-NoProfile", "-Command", ps_script]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 1, "", "timed out waiting for powershell")
    except FileNotFoundError:
        return subprocess.CompletedProcess(cmd, 1, "", "powershell.exe not found on this host")
    except Exception as e:
        return subprocess.CompletedProcess(cmd, 1, "", str(e))

# --- VMware console input over VNC ("the gui stuff") -- X11 keysym codes used directly to
# sidestep vncdotool keyname bugs, same approach as the VMware-styled bot's keyboard handling. ---
VMWARE_SCANCODES = {
    "esc": chr(0xff1b), "escape": chr(0xff1b),
    "tab": chr(0xff09),
    "enter": chr(0xff0d), "return": chr(0xff0d),
    "space": " ",
    "backspace": chr(0xff08),
    "delete": chr(0xffff), "del": chr(0xffff),
    "insert": chr(0xff63), "ins": chr(0xff63),
    "home": chr(0xff50),
    "end": chr(0xff57),
    "pageup": chr(0xff55), "pgup": chr(0xff55),
    "pagedown": chr(0xff56), "pgdn": chr(0xff56),
    "ctrl": chr(0xffe3), "control": chr(0xffe3),
    "alt": chr(0xffe9),
    "shift": chr(0xffe1),
    "capslock": chr(0xffe5),
    "win": chr(0xffeb), "super": chr(0xffeb), "windows": chr(0xffeb),
    "up": chr(0xff52),
    "down": chr(0xff54),
    "left": chr(0xff51),
    "right": chr(0xff53),
    "f1": chr(0xffbe), "f2": chr(0xffbf), "f3": chr(0xffc0), "f4": chr(0xffc1),
    "f5": chr(0xffc2), "f6": chr(0xffc3), "f7": chr(0xffc4), "f8": chr(0xffc5),
    "f9": chr(0xffc6), "f10": chr(0xffc7), "f11": chr(0xffc8), "f12": chr(0xffc9),
}
for _vmwc in "abcdefghijklmnopqrstuvwxyz0123456789":
    VMWARE_SCANCODES[_vmwc] = _vmwc
del _vmwc

_vmware_vnc_client = None
_vmware_vnc_lock = threading.Lock()
_vmware_vnc_cursor = {"x": 512, "y": 384}

def _vmware_vnc_clear_stuck_modifiers(client):
    """Releases every modifier key, in case a previous keyDown never got its keyUp."""
    for name in ("shift", "ctrl", "alt", "win", "capslock"):
        mapped = VMWARE_SCANCODES.get(name)
        if mapped:
            try: client.keyUp(mapped)
            except Exception: pass

def vmware_vnc_connect_fresh():
    """Disconnects any existing session and opens a brand-new VNC connection to the
    VMware VM's console (Host/Password come from the VMware panel)."""
    global _vmware_vnc_client
    if not vncdotool_available:
        console_log("ERROR", "[vmware-vnc] vncdotool is not installed -- run: pip install vncdotool")
        return None
    if _vmware_vnc_client is not None:
        try: _vmware_vnc_client.disconnect()
        except Exception: pass
        _vmware_vnc_client = None
    host = vbox_config.get("vnc_host", "").strip()
    if not host:
        console_log("WARN", "[vmware-vnc] no VNC host configured yet (set it in the VMware panel).")
        return None
    port = int(vbox_config.get("vnc_port", 5900) or 5900)
    password = vbox_config.get("vnc_password", "")
    try:
        _vmware_vnc_client = _vnc_api.connect(f"{host}::{port}", password=str(password) if password else None)
        _vmware_vnc_clear_stuck_modifiers(_vmware_vnc_client)
        return _vmware_vnc_client
    except Exception as e:
        console_log("ERROR", f"[vmware-vnc] connect failed: {e}")
        _vmware_vnc_client = None
        return None

def vmware_vnc_key_down(key_name):
    """Presses (and holds) a named key over VNC on the VMware VM's console."""
    mapped = VMWARE_SCANCODES.get(key_name, key_name)
    with _vmware_vnc_lock:
        client = vmware_vnc_connect_fresh()
        if not client: return
        try: client.keyDown(mapped)
        except Exception as e: console_log("ERROR", f"[vmware-vnc] keyDown error: {e}")

def vmware_vnc_key_up(key_name):
    """Releases a named key over VNC on the VMware VM's console."""
    mapped = VMWARE_SCANCODES.get(key_name, key_name)
    with _vmware_vnc_lock:
        client = vmware_vnc_connect_fresh()
        if not client: return
        try: client.keyUp(mapped)
        except Exception as e: console_log("ERROR", f"[vmware-vnc] keyUp error: {e}")

def vmware_vnc_send_combo(keys):
    """Holds down a chord of keys (e.g. ['win', 'r']) then releases them in reverse order."""
    with _vmware_vnc_lock:
        client = vmware_vnc_connect_fresh()
        if not client: return
        mapped_keys = [VMWARE_SCANCODES.get(k.strip(), k.strip()) for k in keys]
        try:
            for k in mapped_keys:
                try: client.keyDown(k)
                except Exception: pass
                time.sleep(0.01)
        finally:
            for k in reversed(mapped_keys):
                try: client.keyUp(k)
                except Exception: pass
                time.sleep(0.01)

# Many VNC servers only apply Shift correctly if the client explicitly holds Shift down
# around the keypress -- sending the "capital" keysym alone (no Shift) often gets silently
# treated as lowercase. This is why typed text over VNC can come out all-lowercase otherwise.
_VNC_SHIFT_SYMBOLS = set('~!@#$%^&*()_+{}|:"<>?')

def _vnc_needs_shift(ch):
    return ch.isupper() or ch in _VNC_SHIFT_SYMBOLS

def vmware_vnc_type_text(text):
    """Types a string of text into the VMware VM's console over VNC."""
    with _vmware_vnc_lock:
        client = vmware_vnc_connect_fresh()
        if not client: return
        try:
            for ch in text:
                if _vnc_needs_shift(ch):
                    client.keyDown('shift')
                    client.keyPress(ch)
                    client.keyUp('shift')
                else:
                    client.keyPress(ch)
        except Exception as e:
            console_log("ERROR", f"[vmware-vnc] type failed: {e}")
        finally:
            _vmware_vnc_clear_stuck_modifiers(client)

def vmware_vnc_move_mouse(x=None, y=None, dx=None, dy=None):
    """Moves the mouse on the VMware VM's console over VNC -- absolute (x, y) or relative (dx, dy)."""
    global _vmware_vnc_cursor
    with _vmware_vnc_lock:
        client = vmware_vnc_connect_fresh()
        if not client: return
        try:
            if x is not None and y is not None:
                _vmware_vnc_cursor["x"], _vmware_vnc_cursor["y"] = int(x), int(y)
            elif dx is not None or dy is not None:
                _vmware_vnc_cursor["x"] += int(dx or 0)
                _vmware_vnc_cursor["y"] += int(dy or 0)
            client.mouseMove(_vmware_vnc_cursor["x"], _vmware_vnc_cursor["y"])
        except Exception as e:
            console_log("ERROR", f"[vmware-vnc] mouse move failed: {e}")

def vmware_vnc_click(button=1):
    """Clicks a mouse button (1=left, 2=middle, 3=right) at the current cursor position over VNC."""
    with _vmware_vnc_lock:
        client = vmware_vnc_connect_fresh()
        if not client: return
        try: client.mousePress(button)
        except Exception as e: console_log("ERROR", f"[vmware-vnc] click failed: {e}")

def vmware_vnc_capture_screen(path):
    """Saves a screenshot of the VMware VM's console to `path` over VNC.
    vmrun/VMware Workstation has no CLI screenshot command, unlike VBoxManage's screenshotpng."""
    with _vmware_vnc_lock:
        client = vmware_vnc_connect_fresh()
        if not client: return False
        try:
            client.captureScreen(path)
            return os.path.exists(path)
        except Exception as e:
            console_log("ERROR", f"[vmware-vnc] screenshot failed: {e}")
            return False

# ==================== VNC input backend ====================
# Replaces VirtualBox COM scancode/mouse-event injection as the input mechanism. Works against
# any VNC target (a VM's own VRDE/VNC server, or an entirely separate real machine) -- same code
# path either way, since VNC just sees "a screen with a keyboard and mouse" on the other end.
vnc_client = None
vnc_connected = False
vnc_cursor_x, vnc_cursor_y = 0, 0  # tracked locally since RFB has no "give me the current pointer pos" query
_vnc_lock = threading.RLock()
_vnc_connect_retry_lock = threading.Lock()
_vnc_connect_retry_running = False
_vnc_connect_retry_cancel = threading.Event()

# vncdotool's threaded API (vncdotool.api) is explicitly documented as EXPERIMENTAL, and its
# ThreadedVNCClientProxy uses a single un-correlated queue.Queue() per connection shared across
# EVERY method call -- there is no per-call ID, so if two calls to the proxy ever overlap from
# different threads, one thread's queue.get() can silently receive a completely different call's
# result or exception. Since every chat command runs on its own thread, that overlap is a real
# risk even with careful locking on our side. To eliminate it entirely (not just reduce it), every
# vnc_client call is routed through exactly one dedicated worker thread below -- so only ONE
# thread on our side EVER touches the proxy, period, no matter how many chat commands fire at once.
_vnc_job_queue = queue.Queue()
_vnc_worker_thread = None
_vnc_worker_lock = threading.Lock()

def _vnc_ensure_worker():
    global _vnc_worker_thread
    with _vnc_worker_lock:
        if _vnc_worker_thread is None or not _vnc_worker_thread.is_alive():
            _vnc_worker_thread = threading.Thread(target=_vnc_worker_loop, daemon=True)
            _vnc_worker_thread.start()

def _vnc_worker_loop():
    while True:
        try:
            fn, result_box, done_event = _vnc_job_queue.get(timeout=2)
        except queue.Empty:
            if app_instance is None or not app_instance.running: return
            continue
        try:
            result_box["value"] = fn()
        except Exception as e:
            result_box["error"] = e
        done_event.set()

def _vnc_run_job(fn, timeout=20, _retried=False):
    """Runs fn() on the single VNC worker thread and blocks (this calling thread only) until
    it completes, re-raising any exception it hit. Guarantees fn() never overlaps with any
    other vnc_client call, closing the vncdotool shared-queue race described above.

    If the job fails (dropped socket, dead session, etc.), this forces a real reconnect via
    reconnect_vnc() and retries fn() exactly once before giving up -- so every VNC call is
    self-healing without paying the cost/risk of tearing down a perfectly good connection
    before every single keystroke or click (that raced the RFB handshake and silently ate
    input -- see the fixed regression this replaced)."""
    _vnc_ensure_worker()
    result_box = {}
    done_event = threading.Event()
    _vnc_job_queue.put((fn, result_box, done_event))
    if not done_event.wait(timeout):
        raise TimeoutError(f"VNC job timed out after {timeout}s (worker may be stuck on a previous call)")
    if "error" in result_box:
        if not _retried:
            console_log("WARN", f"[vnc] job failed ({result_box['error']}), reconnecting and retrying once...")
            try: reconnect_vnc()
            except Exception: pass
            return _vnc_run_job(fn, timeout=timeout, _retried=True)
        raise result_box["error"]
    return result_box.get("value")

vmware_panel_vnc_config = {"vnc_host": "", "vnc_port": 5900, "vnc_password": ""}
_vnc_purpose = "realpc"  # "realpc" or "mainvm" -- set by whichever caller is about to use the
                          # shared vnc_* functions below, since there's only ever one live VNC
                          # connection at a time. _realpc_execute() sets this to "realpc" before
                          # it does anything; _run_vnc_input_action() (the main VM's VMware-
                          # backed input path) sets it to "mainvm". If both happen to need VNC
                          # in the same moment they'll contend for the same connection -- a
                          # pre-existing limitation of having one shared VNC pipeline, not
                          # something new here.

def _vnc_target_config():
    """Resolves (host, port, password) for the shared VNC input pipeline. Which config it
    reads from depends on _vnc_purpose -- Real PC (an arbitrary separate machine) and the
    main VM (only when it's VMware-backed; VBox uses its own COM API instead, see
    shared_kb/shared_mouse in run_cmd_worker) are two distinct, independently-configured
    targets that must never bleed into each other."""
    if _vnc_purpose == "mainvm":
        host = vmware_panel_vnc_config.get("vnc_host", "").strip()
        if host:
            return host, int(vmware_panel_vnc_config.get("vnc_port", 5900) or 5900), vmware_panel_vnc_config.get("vnc_password", "")
        return "", 5900, ""
    host = realpc_config.get("vnc_host", "").strip()
    if host:
        return host, int(realpc_config.get("vnc_port", 5900) or 5900), realpc_config.get("vnc_password", "")
    return "", 5900, ""

def vnc_connect():
    global vnc_client, vnc_connected
    if not vncdotool_available:
        console_log("ERROR", "[vnc] vncdotool is not installed -- run: pip install vncdotool")
        return False
    host, port, password = _vnc_target_config()
    if not host:
        console_log("WARN", "[vnc] no VNC host configured yet (set it in the Real PC or VMware panel).")
        return False
    if verbose_conn_logging_enabled():
        console_log("INFO", f"[vnc] attempting connection to {host}::{port}...")

    def _do_connect():
        global vnc_client
        if vnc_client is not None:
            try: vnc_client.disconnect()
            except Exception: pass
        vnc_client = _vnc_api.connect(f"{host}::{port}", password=password or None)

    try:
        _vnc_run_job(_do_connect, timeout=15)
        vnc_connected = True
        console_log("INFO", f"[vnc] connected to {host}::{port}.")
        return True
    except Exception as e:
        vnc_connected = False
        console_log("ERROR", f"[vnc] connect to {host}::{port} failed: {e}\n" + traceback.format_exc())
        return False

def vnc_connect_with_retry():
    """Same as vnc_connect(), but keeps retrying with backoff in the background until it
    succeeds (or vnc_disconnect() cancels it) instead of giving up after one failed attempt."""
    global _vnc_connect_retry_running
    if vnc_connect(): return
    with _vnc_connect_retry_lock:
        if _vnc_connect_retry_running: return
        _vnc_connect_retry_running = True
    _vnc_connect_retry_cancel.clear()
    threading.Thread(target=_vnc_connect_retry_worker, daemon=True).start()

def _vnc_connect_retry_worker():
    global _vnc_connect_retry_running
    delay = 2.0
    try:
        while not _vnc_connect_retry_cancel.is_set():
            console_log("WARN", f"[vnc] retrying connection in {delay:.0f}s...")
            if _vnc_connect_retry_cancel.wait(delay): return
            if vnc_connect(): return
            delay = min(delay * 1.5, 30.0)
    finally:
        with _vnc_connect_retry_lock:
            _vnc_connect_retry_running = False

def vnc_disconnect():
    global vnc_client, vnc_connected
    _vnc_connect_retry_cancel.set()

    def _do_disconnect():
        global vnc_client
        if vnc_client is not None:
            try: vnc_client.disconnect()
            except Exception: pass
        vnc_client = None

    try: _vnc_run_job(_do_disconnect, timeout=10)
    except Exception: pass
    vnc_connected = False
    if verbose_conn_logging_enabled():
        console_log("INFO", "[vnc] disconnected.")

def vnc_ensure_connected():
    if vnc_connected and vnc_client is not None: return True
    vnc_connect_with_retry()
    return vnc_connected

def reconnect_vnc():
    """Forces a fresh VNC reconnect (tears down any existing client and reconnects from
    scratch), rather than just checking whether we're *already* connected like
    vnc_ensure_connected() does. Called at the top of every vnc_* action below so a
    connection that silently died/hung on the server side never causes commands to keep
    silently failing -- every single VNC action always starts from a known-good connection."""
    return vnc_connect()

# --- keysym translation: our command keywords -> vncdotool key names ---
_VNC_KEY_ALIASES = {
    "win": "super", "lwin": "super", "rwin": "super", "cmd": "super", "menu": "menu",
    "esc": "esc", "escape": "esc", "enter": "return", "return": "return", "space": "space",
    "backspace": "bsp", "bksp": "bsp", "tab": "tab", "capslock": "caplk", "numlock": "numlk",
    "scrolllock": "scrlk", "printscreen": "prtsc", "prtsc": "prtsc", "delete": "delete", "del": "delete",
    "insert": "insert", "home": "home", "end": "end", "pageup": "pgup", "pgup": "pgup",
    "pagedown": "pgdn", "pgdn": "pgdn", "up": "up", "down": "down", "left": "left", "right": "right",
    "ctrl": "ctrl", "control": "ctrl", "alt": "alt", "shift": "shift",
    # vncdotool has dedicated key names for the right-hand modifiers (rctrl -> KEY_ControlRight,
    # etc.) -- only alias the ones that don't (lctrl/lalt/lshift collapse fine onto the plain
    # left-hand name), so "rctrl" actually sends right ctrl instead of being flattened to ctrl.
    "lctrl": "ctrl", "rctrl": "rctrl", "lalt": "alt", "ralt": "ralt", "lshift": "shift", "rshift": "rshift",
}
for _i in range(1, 13): _VNC_KEY_ALIASES[f"f{_i}"] = f"f{_i}"

def _vnc_keyname(key):
    k = key.strip().lower()
    return _VNC_KEY_ALIASES.get(k, k)

def _vnc_split_combo(key_or_keys):
    """Accepts a list of key names, or a single string that might still be '+'/'-'/space
    joined (e.g. someone passed 'ctrl+alt+t' straight through) -- always returns a clean
    list of individual key tokens so we never hand vncdotool an unsplit combo string.
    Also handles NO separator at all ('ctrlaltt') via a greedy longest-match scan against
    the known VNC key vocabulary, the same fallback used elsewhere for combo parsing."""
    if isinstance(key_or_keys, str):
        raw = [key_or_keys]
    else:
        raw = list(key_or_keys)
    out = []
    for item in raw:
        item = str(item).strip()
        pieces = [p for p in re.split(r"[+\-\s]+", item) if p]
        if len(pieces) <= 1 and item and not re.search(r"[+\-\s]", item):
            # No delimiter anywhere in this piece -- try the greedy tokenizer instead
            # of assuming it's a single (possibly multi-key) unrecognized token.
            out.extend(_vnc_tokenize_undelimited(item))
        else:
            out.extend(pieces)
    return out

def _vnc_tokenize_undelimited(text):
    """Greedy longest-match scan against the known VNC key vocabulary (named keys from
    _VNC_KEY_ALIASES, plus every single letter/digit, which don't need aliasing but are
    still valid key names on their own). Mirrors parse_combo_keys()'s fallback for the
    other two backends, just against this file's own VNC key names."""
    text = text.lower()
    known_keys = set(_VNC_KEY_ALIASES.keys()) | set("abcdefghijklmnopqrstuvwxyz0123456789")
    known_keys = sorted(known_keys, key=len, reverse=True)
    result = []
    i = 0
    while i < len(text):
        for k in known_keys:
            if text.startswith(k, i):
                result.append(k)
                i += len(k)
                break
        else:
            result.append(text[i:])
            break
    return result

def vnc_type_text(text):
    if not vnc_ensure_connected(): return False
    def _do_type():
        for ch in text:
            if _vnc_needs_shift(ch):
                vnc_client.keyDown('shift')
                vnc_client.keyPress(ch)
                vnc_client.keyUp('shift')
            else:
                vnc_client.keyPress(ch)
    try:
        _vnc_run_job(_do_type)
        return True
    except Exception as e:
        console_log("ERROR", f"[vnc] type failed: {e}\n" + traceback.format_exc())
        return False

def vnc_key_press(key):
    if not vnc_ensure_connected(): return False
    names = [_vnc_keyname(k) for k in _vnc_split_combo(key)]
    if not names: return False
    combo_str = "-".join(names)
    if verbose_conn_logging_enabled(): console_log("INFO", f"[vnc] key '{key}' -> sending '{combo_str}'")
    try:
        _vnc_run_job(lambda: vnc_client.keyPress(combo_str))
        return True
    except Exception as e:
        console_log("ERROR", f"[vnc] key '{key}' (sent as '{combo_str}') failed: {e}\n" + traceback.format_exc())
        return False

def vnc_key_down(key):
    if not vnc_ensure_connected(): return False
    names = [_vnc_keyname(k) for k in _vnc_split_combo(key)]
    if not names: return False
    try:
        _vnc_run_job(lambda: [vnc_client.keyDown(n) for n in names])
        return True
    except Exception as e:
        console_log("ERROR", f"[vnc] keydown '{key}' failed: {e}\n" + traceback.format_exc())
        return False

def vnc_key_up(key):
    if not vnc_ensure_connected(): return False
    names = [_vnc_keyname(k) for k in _vnc_split_combo(key)]
    if not names: return False
    try:
        _vnc_run_job(lambda: [vnc_client.keyUp(n) for n in reversed(names)])
        return True
    except Exception as e:
        console_log("ERROR", f"[vnc] keyup '{key}' failed: {e}\n" + traceback.format_exc())
        return False

def vnc_combo(keys):
    """keys: list like ['ctrl','alt','del'] (or even a raw '+'/'-' joined string -- it's
    defensively re-split either way). Uses vncdotool's native hyphen-combo syntax, which
    presses all keys down together and releases them in reverse order atomically."""
    if not vnc_ensure_connected(): return False
    names = [_vnc_keyname(k) for k in _vnc_split_combo(keys)]
    if not names: return False
    combo_str = "-".join(names)
    if verbose_conn_logging_enabled(): console_log("INFO", f"[vnc] combo -> sending '{combo_str}'")
    try:
        _vnc_run_job(lambda: vnc_client.keyPress(combo_str))
        return True
    except Exception as e:
        console_log("ERROR", f"[vnc] combo '{'+'.join(names)}' (sent as '{combo_str}') failed: {e}\n" + traceback.format_exc())
        return False

def vnc_move_abs(x, y):
    global vnc_cursor_x, vnc_cursor_y
    if not vnc_ensure_connected(): return False
    try:
        _vnc_run_job(lambda: vnc_client.mouseMove(int(x), int(y)))
        vnc_cursor_x, vnc_cursor_y = int(x), int(y)
        return True
    except Exception as e:
        console_log("ERROR", f"[vnc] move to ({x},{y}) failed: {e}\n" + traceback.format_exc())
        return False

def vnc_move_rel(dx, dy):
    return vnc_move_abs(vnc_cursor_x + int(dx), vnc_cursor_y + int(dy))

def vnc_click(button=1, count=1, x=None, y=None):
    if not vnc_ensure_connected(): return False
    if x is not None and y is not None: vnc_move_abs(x, y)
    def _do():
        for _ in range(max(1, min(count, 50))):
            vnc_client.mousePress(button)
            time.sleep(0.03)
    try:
        _vnc_run_job(_do)
        return True
    except Exception as e:
        console_log("ERROR", f"[vnc] click failed: {e}\n" + traceback.format_exc())
        return False

def vnc_scroll(amount):
    """VNC represents the scroll wheel as mouse buttons 4 (up) and 5 (down)."""
    if not vnc_ensure_connected(): return False
    button = 4 if amount > 0 else 5
    def _do():
        for _ in range(min(abs(amount), 50)):
            vnc_client.mousePress(button)
            time.sleep(0.02)
    try:
        _vnc_run_job(_do)
        return True
    except Exception as e:
        console_log("ERROR", f"[vnc] scroll failed: {e}\n" + traceback.format_exc())
        return False

def vnc_drag(x1, y1, x2, y2, steps=8):
    global vnc_cursor_x, vnc_cursor_y
    if not vnc_ensure_connected(): return False
    def _do():
        vnc_client.mouseMove(int(x1), int(y1))
        vnc_client.mouseDown(1)
        for i in range(1, steps + 1):
            ix = x1 + (x2 - x1) * i // steps
            iy = y1 + (y2 - y1) * i // steps
            vnc_client.mouseMove(int(ix), int(iy))
            time.sleep(0.02)
        vnc_client.mouseUp(1)
    try:
        _vnc_run_job(_do)
        vnc_cursor_x, vnc_cursor_y = int(x2), int(y2)
        return True
    except Exception as e:
        console_log("ERROR", f"[vnc] drag failed: {e}\n" + traceback.format_exc())
        return False

def vnc_screenshot(fname):
    if not vnc_ensure_connected(): return False
    try:
        _vnc_run_job(lambda: vnc_client.captureScreen(fname))
        return True
    except Exception as e:
        console_log("ERROR", f"[vnc] screenshot failed: {e}\n" + traceback.format_exc())
        return False

def _realpc_set_status(msg):
    global realpc_status_text
    realpc_status_text = msg
    console_log("INFO", f"[realpc] {msg}")

def _realpc_check_cooldown(username):
    cd = realpc_config.get("cooldown", 1.0)
    now = time.time()
    with realpc_cooldown_lock:
        last = realpc_user_cooldowns.get(username, 0)
        if now - last < cd: return False
        realpc_user_cooldowns[username] = now
    return True

def _realpc_parse_two_ints(s):
    try:
        nums = [int(n) for n in re.split(r"[\s,]+", s.strip()) if n]
        if len(nums) >= 2: return nums[0], nums[1]
    except Exception: pass
    return None

def _realpc_execute(username, action, args):
    global _vnc_purpose
    _vnc_purpose = "realpc"
    if not vncdotool_available:
        console_log("ERROR", "[realpc] vncdotool not installed -- run: pip install vncdotool")
        return
    if not realpc_config.get("vnc_host", "").strip():
        console_log("WARN", "[realpc] no VNC target configured (set Host/Port/Password in the Real PC panel).")
        return
    text_only_actions = {"type", "write", "text", "say", "send", "sendline", "typeenter"}
    if realpc_config.get("text_only", False) and action not in text_only_actions: return
    allowed = realpc_config.get("allowed_actions", {})
    try:
        if action in ("wait", "sleep", "delay"):
            try: seconds = max(0.0, min(10.0, float(args.strip())))
            except Exception: seconds = 0.5
            time.sleep(seconds)
        elif action in ("type", "write", "text", "say"):
            if not allowed.get("keyboard", True): return
            text = args[:realpc_config.get("max_type_length", 100)]
            vnc_type_text(text)
        elif action in ("key", "press"):
            if not allowed.get("keyboard", True): return
            key = args.strip().lower()
            if key: vnc_key_press(key)
        elif action in ("combo", "hotkey"):
            if not allowed.get("combo", True): return
            keys = [k.strip() for k in args.replace("+", " ").split() if k.strip()]
            if keys: vnc_combo(keys)
        elif action == "enter":
            if allowed.get("keyboard", True): vnc_key_press("enter")
        elif action == "space":
            if allowed.get("keyboard", True): vnc_key_press("space")
        elif action == "backspace":
            if allowed.get("keyboard", True): vnc_key_press("backspace")
        elif action in ("send", "sendline", "typeenter"):
            if not allowed.get("keyboard", True): return
            text = args[:realpc_config.get("max_type_length", 100)]
            vnc_type_text(text)
            vnc_key_press("enter")
        elif action in ("click", "lclick"):
            if not allowed.get("mouse", True): return
            nums = _realpc_parse_two_ints(args)
            vnc_click(1, 1, nums[0], nums[1]) if nums else vnc_click(1, 1)
        elif action in ("rclick", "rightclick"):
            if not allowed.get("mouse", True): return
            nums = _realpc_parse_two_ints(args)
            vnc_click(3, 1, nums[0], nums[1]) if nums else vnc_click(3, 1)
        elif action in ("dclick", "doubleclick"):
            if not allowed.get("mouse", True): return
            nums = _realpc_parse_two_ints(args)
            vnc_click(1, 2, nums[0], nums[1]) if nums else vnc_click(1, 2)
        elif action == "tripleclick":
            if not allowed.get("mouse", True): return
            nums = _realpc_parse_two_ints(args)
            vnc_click(1, 3, nums[0], nums[1]) if nums else vnc_click(1, 3)
        elif action == "mclick":
            if not allowed.get("mouse", True): return
            nums = _realpc_parse_two_ints(args)
            vnc_click(2, 1, nums[0], nums[1]) if nums else vnc_click(2, 1)
        elif action == "keydown":
            if not allowed.get("keyboard", True): return
            if args.strip(): vnc_key_down(args.strip())
        elif action == "keyup":
            if not allowed.get("keyboard", True): return
            if args.strip(): vnc_key_up(args.strip())
        elif action in ("move", "moveto", "abs", "moveabs"):
            if not allowed.get("mouse", True): return
            nums = _realpc_parse_two_ints(args)
            if nums: vnc_move_abs(nums[0], nums[1])
        elif action in ("moverel", "mv", "rel"):
            if not allowed.get("mouse", True): return
            step = realpc_config.get("mouse_step", 50)
            direction = args.strip().lower()
            dx, dy = 0, 0
            if direction in ("up", "u"): dy = -step
            elif direction in ("down", "d"): dy = step
            elif direction in ("left", "l"): dx = -step
            elif direction in ("right", "r"): dx = step
            else:
                nums = _realpc_parse_two_ints(args)
                if nums: dx, dy = nums
            if dx or dy: vnc_move_rel(dx, dy)
        elif action in ("scroll", "wheel"):
            if not allowed.get("mouse", True): return
            try: amount = int(args.strip()) if args.strip() else realpc_config.get("scroll_step", 3)
            except Exception: amount = realpc_config.get("scroll_step", 3)
            vnc_scroll(amount)
        elif action == "scrollup":
            if not allowed.get("mouse", True): return
            try: amount = int(args.strip()) if args.strip() else realpc_config.get("scroll_step", 3)
            except Exception: amount = realpc_config.get("scroll_step", 3)
            vnc_scroll(abs(amount))
        elif action == "scrolldown":
            if not allowed.get("mouse", True): return
            try: amount = int(args.strip()) if args.strip() else realpc_config.get("scroll_step", 3)
            except Exception: amount = realpc_config.get("scroll_step", 3)
            vnc_scroll(-abs(amount))
        elif action in ("drag", "dragrel"):
            if not allowed.get("mouse", True): return
            nums = _realpc_parse_two_ints(args)
            if nums: vnc_drag(vnc_cursor_x, vnc_cursor_y, vnc_cursor_x + nums[0], vnc_cursor_y + nums[1])
        elif action in ("screenshot", "ss", "snap"):
            if not allowed.get("screenshot", True): return
            fname = f"realpc_screenshot_{int(time.time())}.png"
            if vnc_screenshot(fname): _realpc_set_status(f"screenshot saved: {fname}")
        elif action in ("pos", "position"):
            _realpc_set_status(f"cursor: x={vnc_cursor_x} y={vnc_cursor_y}")
        elif action in ("size", "screen", "resolution"):
            try:
                w, h = _vnc_run_job(lambda: (vnc_client.screen.width, vnc_client.screen.height))
                _realpc_set_status(f"screen: {w}x{h}")
            except Exception:
                _realpc_set_status("screen size unavailable (not connected yet)")

        elif action in ("run", "cmd", "open_app"):
            if not allowed.get("keyboard", True) or not allowed.get("combo", True): return
            is_admin = (action == "cmd")
            full_cmd = f"cmd /c {args}" if is_admin else args
            vnc_combo(["super", "r"])
            time.sleep(0.5)
            if action == "run" and not args.strip():
                pass  # bare run: just pop the dialog open
            else:
                vnc_type_text(full_cmd)
                time.sleep(0.1)
                if is_admin:
                    vnc_combo(["ctrl", "shift", "return"])
                    time.sleep(0.6)
                    vnc_key_press("left")
                    time.sleep(0.1)
                    vnc_key_press("return")
                else:
                    vnc_key_press("return")

        elif action == "winkey":
            if not allowed.get("combo", True): return
            k = args.strip()
            if k: vnc_combo(["super", k])

        elif action == "dir":
            if not allowed.get("keyboard", True): return
            _realpc_execute(username, "send", f"dir {args}".strip())

        elif action == "taskkill":
            if not allowed.get("keyboard", True): return
            proc = args if args.lower().endswith(".exe") else f"{args}.exe"
            _realpc_execute(username, "send", f"taskkill /F /IM {proc}")

        elif action == "openfile":
            if not allowed.get("keyboard", True): return
            _realpc_execute(username, "send", f"start {args}")

        elif action == "msgbox":
            if not allowed.get("keyboard", True): return
            safe_text = args.replace("'", "").replace('"', "")
            _realpc_execute(username, "run", f"powershell -c \"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('{safe_text}')\"")

        elif action == "spam":
            if not allowed.get("keyboard", True): return
            parts = args.rsplit(" ", 1)
            spam_text, spam_n = args, 5
            if len(parts) == 2 and parts[1].isdigit(): spam_text, spam_n = parts[0], int(parts[1])
            spam_n = max(1, min(spam_n, 20))
            for _ in range(spam_n):
                if realpc_stop_event.is_set(): break
                _realpc_execute(username, "send", spam_text)
                time.sleep(0.15)

        elif action == "countdown":
            try: cd_n = int(args)
            except Exception: cd_n = 10
            cd_n = max(1, min(cd_n, 60))
            for i in range(cd_n, 0, -1):
                if realpc_stop_event.is_set(): break
                console_log("INFO", f"[realpc][countdown] {i}")
                time.sleep(1)
            console_log("INFO", "[realpc][countdown] go!")

        elif action == "matrix":
            mx_chars = "01ｱｲｳｴｵｶｷｸｹｺABCDEFGHIJKLMNOPQRSTUVWXYZ"
            for _ in range(6):
                line = "".join(random.choice(mx_chars) for _ in range(random.randint(10, 24)))
                console_log("INFO", f"[realpc][matrix] {line}")
                time.sleep(0.15)

        elif action == "colorscheme":
            if not allowed.get("keyboard", True): return
            code = re.sub(r'[^0-9A-Fa-f]', '', args)[:2] or "0A"
            if len(code) < 2: code = (code + "0A")[:2]
            _realpc_execute(username, "send", f"color {code}")

        elif action == "rainbow":
            if not allowed.get("keyboard", True): return
            for code in ["4E", "1F", "2A", "5C", "6D", "0A"]:
                if realpc_stop_event.is_set(): break
                _realpc_execute(username, "send", f"color {code}")
                time.sleep(0.4)

        elif action == "notepadflood":
            if not allowed.get("keyboard", True): return
            try: nf_n = int(args)
            except Exception: nf_n = 5
            nf_n = max(1, min(nf_n, 15))
            for _ in range(nf_n):
                if realpc_stop_event.is_set(): break
                _realpc_execute(username, "run", "notepad")
                time.sleep(0.3)

        elif action == "exeflood":
            if not allowed.get("keyboard", True): return
            for _ in range(8):
                if realpc_stop_event.is_set(): break
                _realpc_execute(username, "run", random.choice(_FLOOD_APP_POOL))
                time.sleep(0.3)

        elif action == "txtflood":
            if not allowed.get("keyboard", True): return
            tf_words = ["chaos", "lol", "bruh", "pog", "haha", "yo", "wow", "nice", "gg", "wat"]
            for _ in range(5):
                if realpc_stop_event.is_set(): break
                line = " ".join(random.choice(tf_words) for _ in range(random.randint(3, 8)))
                _realpc_execute(username, "send", line)
                time.sleep(0.2)

        elif action == "deskflood":
            if not allowed.get("keyboard", True): return
            try: df_n = int(args)
            except Exception: df_n = 6
            df_n = max(1, min(df_n, 15))
            for _ in range(df_n):
                if realpc_stop_event.is_set(): break
                _realpc_execute(username, "run", random.choice(_FLOOD_APP_POOL))
                time.sleep(0.25)

        elif action == "beep":
            if not allowed.get("keyboard", True): return
            bits = args.split()
            try: freq = int(bits[0]) if bits else 800
            except Exception: freq = 800
            try: ms = int(bits[1]) if len(bits) > 1 else 300
            except Exception: ms = 300
            freq, ms = max(37, min(freq, 32767)), max(50, min(ms, 5000))
            _realpc_execute(username, "run", f"powershell -c [console]::beep({freq},{ms})")

        elif action in ("tts", "ttsloop", "ttsxp", "ttsxploop"):
            if not allowed.get("keyboard", True): return
            safe_text = args.replace("'", "").replace('"', "")
            if action == "tts":
                payload = f"powershell -c \"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe_text}')\""
            elif action == "ttsloop":
                payload = f"powershell -c \"Add-Type -AssemblyName System.Speech; $s=(New-Object System.Speech.Synthesis.SpeechSynthesizer); while($true){{$s.Speak('{safe_text}')}}\""
            elif action == "ttsxp":
                payload = f'mshta vbscript:Execute("CreateObject(""SAPI.SpVoice"").Speak(""{safe_text}"")(window.close)")'
            else:
                payload = f'mshta vbscript:Execute("Set s=CreateObject(""SAPI.SpVoice""):Do:s.Speak(""{safe_text}""):Loop")'
            _realpc_execute(username, "run", payload)

        elif action == "roll":
            res = str(random.randint(1, 100))
            _realpc_execute(username, "send", f"rolling... {res}")
        elif action == "coinflip":
            _realpc_execute(username, "send", random.choice(["heads", "tails"]))

        elif action == "shake":
            if not allowed.get("mouse", True): return
            try: amp = max(5, min(int(args), 150)) if args else 30
            except Exception: amp = 30
            for _ in range(10):
                if realpc_stop_event.is_set(): break
                vnc_move_rel(random.choice([-1, 1]) * amp, random.choice([-1, 1]) * amp)
                time.sleep(0.02)

        elif action == "jiggle":
            if not allowed.get("mouse", True): return
            try: amp = max(2, min(int(args), 40)) if args else 8
            except Exception: amp = 8
            for _ in range(14):
                if realpc_stop_event.is_set(): break
                vnc_move_rel(random.randint(-amp, amp), random.randint(-amp, amp))
                time.sleep(0.03)

        elif action == "circle":
            if not allowed.get("mouse", True): return
            try: radius = max(10, min(int(args), 200)) if args else 60
            except Exception: radius = 60
            steps = 16
            prev_x, prev_y = float(radius), 0.0
            for i in range(1, steps + 1):
                if realpc_stop_event.is_set(): break
                angle = 2 * math.pi * i / steps
                x, y = radius * math.cos(angle), radius * math.sin(angle)
                vnc_move_rel(int(x - prev_x), int(y - prev_y))
                prev_x, prev_y = x, y
                time.sleep(0.02)

        elif action == "spiral":
            if not allowed.get("mouse", True): return
            steps = 20
            prev_x, prev_y = 0.0, 0.0
            for i in range(1, steps + 1):
                if realpc_stop_event.is_set(): break
                angle = 2 * math.pi * i / 5
                radius = i * 4
                x, y = radius * math.cos(angle), radius * math.sin(angle)
                vnc_move_rel(int(x - prev_x), int(y - prev_y))
                prev_x, prev_y = x, y
                time.sleep(0.02)

        elif action in APP_RUN_MAP:
            if not allowed.get("keyboard", True): return
            _realpc_execute(username, "run", APP_RUN_MAP[action])
        elif action in COMBO_SHORTCUTS:
            if not allowed.get("combo", True): return
            _realpc_execute(username, "combo", COMBO_SHORTCUTS[action])
        elif action in CMD_TYPED_MAP:
            if not allowed.get("keyboard", True): return
            _realpc_execute(username, "send", CMD_TYPED_MAP[action] + (f" {args}" if args else ""))

        else:
            return
        append_event("REALPC_CMD", username, f"!{action} {args}".strip())
    except Exception as e:
        append_event("REALPC_ERROR", username, f"!{action}: {e}")

def _realpc_bot_loop():
    vid = realpc_config.get("video_id", "").strip()
    if not vid:
        _realpc_set_status("no video id configured.")
        return
    if not pytchat_available:
        _realpc_set_status("pytchat not installed.")
        return
    if not vncdotool_available:
        _realpc_set_status("vncdotool not installed. run: pip install vncdotool")
        return
    if not realpc_config.get("vnc_host", "").strip():
        _realpc_set_status("no VNC target configured (set Host/Port/Password in the Real PC panel).")
        return
    wl_only = realpc_config.get("whitelist_only", False)
    whitelist = {normalize_username(u) for u in realpc_config.get("whitelist", [])}
    blocked = {normalize_username(u) for u in realpc_config.get("blocked", [])}
    _realpc_set_status(f"connecting to stream: {vid}")
    chat = None
    try: chat = pytchat.create(video_id=vid)
    except Exception as e:
        _realpc_set_status(f"connection failed: {e}")
        return
    _realpc_set_status("listening for real pc commands...")
    while not realpc_stop_event.is_set():
        if not chat.is_alive():
            _realpc_set_status("chat ended or disconnected.")
            break
        try:
            for msg_obj in chat.get().sync_items():
                if realpc_stop_event.is_set(): break
                user = normalize_username(msg_obj.author.name)
                msg = msg_obj.message.strip()
                if not msg or not msg.startswith("!"): continue
                if user in blocked: continue
                if wl_only and user not in whitelist: continue
                if not _realpc_check_cooldown(user): continue
                segments = [s.strip() for s in re.split(r'\s+(?=!)', msg.strip())]
                commands = []
                for seg in segments:
                    if seg.startswith("!"): seg = seg[1:].strip()
                    if not seg: continue
                    parts = seg.split(maxsplit=1)
                    commands.append((parts[0].lower(), parts[1] if len(parts) > 1 else ""))
                if not commands: continue
                def _run_chain(cmds=commands, u=user):
                    for action, args in cmds:
                        if realpc_stop_event.is_set(): break
                        _realpc_execute(u, action, args)
                threading.Thread(target=_run_chain, daemon=True).start()
        except Exception as e:
            if not realpc_stop_event.is_set(): console_log("WARN", f"realpc loop error: {e}")
        if realpc_stop_event.wait(0.05): break
    if chat:
        try: chat.terminate()
        except Exception: pass
    _realpc_set_status("stopped.")

def start_realpc_bot():
    global realpc_bot_thread
    if realpc_bot_thread and realpc_bot_thread.is_alive(): return False
    realpc_stop_event.clear()
    realpc_bot_thread = threading.Thread(target=_realpc_bot_loop, daemon=True, name="realpc_bot")
    realpc_bot_thread.start()
    return True

def stop_realpc_bot():
    realpc_stop_event.set()

# ---------------- scheduler ----------------
scheduler_config = {"enabled": False, "tasks": []}
_scheduler_last_tick = ""

def load_scheduler_config():
    global scheduler_config
    try:
        if os.path.exists(scheduler_config_file):
            with open(scheduler_config_file, "r", encoding="utf-8") as f:
                scheduler_config.update(json.load(f))
    except Exception: pass

def save_scheduler_config():
    safe_json_dump(scheduler_config_file, scheduler_config)

def _run_scheduled_action(action, label):
    console_log("INFO", f"[scheduler] running '{label}' -> {action}")
    notify("Scheduled Task", f"{action} triggered by scheduler: {label}")
    append_event("SCHEDULER", "scheduler", f"{action} / {label}")
    if app_instance is not None and action in ("revert", "restartvm", "shutdown"):
        app_instance.trigger_command((action, "", "[scheduler]"))

def scheduler_loop():
    global _scheduler_last_tick
    while app_instance is None:
        time.sleep(1)
    while app_instance.running:
        if not app_instance.running: break
        time.sleep(15)
        if not app_instance.running: break
        if not scheduler_config.get("enabled"): continue
        now = time.localtime()
        tick = f"{now.tm_hour:02d}:{now.tm_min:02d}"
        today_str = time.strftime("%Y-%m-%d")
        if tick == _scheduler_last_tick: continue
        _scheduler_last_tick = tick
        for task in scheduler_config.get("tasks", []):
            try:
                days_ok = (not task.get("days")) or (now.tm_wday in task["days"])
                time_ok = (task.get("hour") == now.tm_hour and task.get("minute") == now.tm_min)
                if not (days_ok and time_ok): continue
                if task.get("last_run") == today_str: continue
                task["last_run"] = today_str
                save_scheduler_config()
                _run_scheduled_action(task.get("action", "revert"), task.get("label", "unnamed"))
            except Exception as e:
                console_log("ERROR", f"scheduler task error: {e}")
    console_log("INFO", "scheduler loop stopped.")

# ---------------- OS-switch voting (separate from the existing revert/restart vote system) ----------------
OS_VOTE_SLOTS = 25
OS_VOTE_REQUIRED = 3
OS_VOTE_TIMEOUT = 45
os_voting_enabled = False
os_list = []              # [{"trigger": "win7", "vm": "Win7Vm", "name": "Windows 7"}, ...]
current_os_vm = None
os_votes = {}              # trigger -> set(users)
os_vote_start_time = None
os_vote_lock = threading.Lock()
os_switch_lock = threading.Lock()
os_switch_in_progress = False

def load_os_voting_config():
    global os_voting_enabled, os_list, current_os_vm
    try:
        if os.path.exists(os_voting_config_file):
            with open(os_voting_config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            os_voting_enabled = bool(data.get("enabled", False))
            os_list = data.get("os_list", [])[:OS_VOTE_SLOTS]
            saved_vm = data.get("last_active_vm", "")
            if saved_vm and saved_vm in [e.get("vm", "") for e in os_list]:
                current_os_vm = saved_vm
    except Exception: pass

def save_os_voting_config():
    safe_json_dump(os_voting_config_file, {
        "enabled": os_voting_enabled,
        "os_list": os_list,
        "last_active_vm": current_os_vm or ""
    })

def get_os_trigger_map():
    result = {}
    for entry in os_list:
        trig = (entry.get("trigger") or "").strip().lower().lstrip("!")
        vm = (entry.get("vm") or "").strip()
        name = (entry.get("name") or "").strip()
        if trig and vm and name: result[trig] = entry
    return result

def _get_current_os_live_scene():
    """Returns the currently active VM's own obs_live_scene if OS Voting has a matching
    row for it, otherwise falls back to the single generic Main scene (single-VM mode,
    or a VM that isn't one of the configured OS Voting entries)."""
    for e in os_list:
        if e.get("vm") == vm_name:
            row_live_scene = (e.get("obs_live_scene") or "").strip()
            if row_live_scene:
                return row_live_scene
            break
    return obs_scene_main

def switch_os(target_entry, user="vote"):
    global current_os_vm, os_switch_in_progress, os_votes, os_vote_start_time, vm_name, current_vm_backend
    if not os_switch_lock.acquire(blocking=False):
        console_log("WARN", "os switch already in progress, ignoring duplicate request.")
        return
    os_switch_in_progress = True
    previous_vm = current_os_vm
    try:
        target_name = target_entry.get("name", "Unknown OS")
        target_vm = target_entry.get("vm", "")
        target_backend = target_entry.get("backend", "vbox")
        if not target_vm: return
        
        # --- FIX FOR MANUAL VMWARE ENTRIES ---
        # If the backend is explicitly configured as vmware, or the input contains '.vmx'
        if "vmware" in str(target_backend).lower() or ".vmx" in str(target_vm).lower():
            target_backend = "vmware"
            # If it's a bare name (doesn't point to a file pathway already), auto-expand it
            if not str(target_vm).lower().endswith('.vmx') and "/" not in str(target_vm) and "\\" not in str(target_vm):
                user_docs = os.path.join(os.environ.get('USERPROFILE', 'C:\\Users\\default'), 'Documents')
                target_vm = os.path.join(user_docs, 'Virtual Machines', target_vm, f"{target_vm}.vmx")
        # -------------------------------------

        switch_scene = (target_entry.get("obs_switch_scene") or "").strip()
        live_scene = (target_entry.get("obs_live_scene") or "").strip()
        if switch_scene: set_obs_scene(switch_scene)
        speak_text(f"Switching to {target_name}...")
        if app_instance is not None: app_instance.set_status(f"Switching to {target_name}...")
        if current_os_vm and current_os_vm != target_vm:
            # The PREVIOUS vm might be on a different backend than the one we're switching
            # to -- look its own backend up from os_list rather than assuming, so it gets
            # powered off with the right tool (vmrun vs VBoxManage).
            previous_backend = "vbox"
            for e in os_list:
                if e.get("vm") == current_os_vm:
                    previous_backend = e.get("backend", "vbox")
                    break
            console_log("INFO", f"[osvoting] powering off previous VM ({previous_backend}): {current_os_vm}")
            try:
                res = vm_stop(current_os_vm, previous_backend, hard=True)
                if res.returncode != 0:
                    console_log("WARN", f"os switch poweroff failed: {(res.stderr or res.stdout or '').strip()[:150]}")
            except Exception as e:
                console_log("WARN", f"os switch poweroff failed: {e}")
            time.sleep(3)

        console_log("INFO", f"[osvoting] starting target VM ({target_backend}): {target_vm}")
        try:
            res = vm_start(target_vm, target_backend, gui=True)
            ok = res.returncode == 0
            if not ok:
                console_log("ERROR", f"os switch start failed: {(res.stderr or res.stdout or '').strip()[:150]}")
        except Exception as e:
            ok = False
            console_log("ERROR", f"os switch startvm failed: {e}")
        if ok:
            current_os_vm = target_vm
            vm_name = target_vm
            current_vm_backend = target_backend  # every subsequent command (input, lifecycle,
                                                 # executor_loop) now follows this OS's backend
            if app_instance is not None:
                app_instance.force_session_refresh = True  # release any stale VBox COM session
                                                             # / reconnect VNC to match the new target
            if live_scene: set_obs_scene(live_scene)
            if app_instance is not None:
                app_instance.set_status(f"Running {target_name}")
                app_instance.config["vm_name"] = target_vm
                app_instance.config["vm_backend"] = target_backend
                app_instance.save_settings()
                app_instance.log("[system]", f"[info] os switched to {target_name} ({target_vm}, backend: {target_backend})", "sysmsg")
            play_event_sound("os_switch_sound")
            append_event("OS_SWITCH", user, f"switched to {target_name} ({target_backend})")
            notify("OS Switched", f"Now running: {target_name}")
            save_os_voting_config()
        else:
            notify("OS Switch Failed", f"Could not start {target_name}.", timeout=7)
            if app_instance is not None:
                app_instance.log("[system]", f"[err] os switch to {target_name} failed, restoring previous...", "err")
            if previous_vm and previous_vm != target_vm:
                recover_backend = "vbox"
                for e in os_list:
                    if e.get("vm") == previous_vm:
                        recover_backend = e.get("backend", "vbox")
                        break
                try:
                    res = vm_start(previous_vm, recover_backend, gui=True)
                    if res.returncode == 0:
                        current_vm_backend = recover_backend
                        vm_name = previous_vm
                except Exception: pass
    finally:
        os_votes.clear()
        os_vote_start_time = None
        os_switch_in_progress = False
        os_switch_lock.release()

def process_os_vote(user, trigger, target_entry):
    global os_votes, os_vote_start_time
    with os_vote_lock:
        if trigger not in os_votes: os_votes[trigger] = set()
        if user in os_votes[trigger]: return
        os_votes[trigger].add(user)
        if os_vote_start_time is None: os_vote_start_time = time.time()
        count = len(os_votes[trigger])
        if app_instance is not None:
            app_instance.log("[system]", f"[vote] [alert] os-switch to '{target_entry.get('name')}' progress: {count}/{OS_VOTE_REQUIRED}!", "sysmsg")
        if count >= OS_VOTE_REQUIRED:
            if app_instance is not None:
                app_instance.log("[system]", f"[vote] [success] os-switch to {target_entry.get('name')} passed! switching now...", "sysmsg")
            threading.Thread(target=switch_os, args=(target_entry, user), daemon=True).start()

def os_vote_timeout_checker():
    global os_votes, os_vote_start_time
    while app_instance is None:
        time.sleep(1)
    while app_instance.running:
        if app_instance.running is False: break
        time.sleep(1)
        if os_vote_start_time is not None and time.time() - os_vote_start_time > OS_VOTE_TIMEOUT:
            with os_vote_lock:
                os_votes.clear()
                os_vote_start_time = None
    console_log("INFO", "os vote timeout checker stopped.")

# ---------------- Appearance / theming ----------------
appearance_config = {
    "accent_color": "#00E5FF", "accent_hover": "#00B3CC", "bg_color": "#09090B", "card_color": "#18181B",
    "card_border_color": "#27272A", "text_color": "#F4F4F5", "text_dim_color": "#A1A1AA",
    "success_color": "#10B981", "error_color": "#EF4444", "warning_color": "#F59E0B", "info_color": "#3B82F6",
    "tab_bg_color": "#18181B", "tab_selected_color": "#00E5FF", "console_bg_color": "#09090B",
    "console_text_color": "#D4D4D8", "scrollbar_color": "#27272A", "input_bg_color": "#09090B",
    "font_family": "Segoe UI", "font_size": 10, "density": "comfortable", "corner_style": "sharp",
    "reduce_motion": False,
}

def load_appearance_config():
    global appearance_config
    try:
        if os.path.exists(appearance_config_file):
            with open(appearance_config_file, "r", encoding="utf-8") as f:
                appearance_config.update(json.load(f))
    except Exception: pass

def save_appearance_config():
    safe_json_dump(appearance_config_file, appearance_config)

# ---------------- OBS integration config ----------------
obs_config = {
    "host": obs_host, "port": obs_port, "password": obs_password,
    "scene_main": obs_scene_main, "scene_starting": "Starting", "scene_brb": "BRB",
    "scene_reverting": "", "scene_restarting": "", "scene_error": "", "scene_shutdown": "",
    "auto_connect": False, "event_scenes": {},
}
obs_client = None
obs_connected = False

def load_obs_config():
    global obs_config, obs_host, obs_port, obs_password, obs_scene_main
    try:
        if os.path.exists(obs_config_file):
            with open(obs_config_file, "r", encoding="utf-8") as f:
                obs_config.update(json.load(f))
    except Exception: pass
    obs_host = obs_config.get("host", obs_host)
    obs_port = int(obs_config.get("port", obs_port) or obs_port)
    obs_password = obs_config.get("password", obs_password)
    obs_scene_main = obs_config.get("scene_main", obs_scene_main)

def save_obs_config():
    obs_config["host"], obs_config["port"], obs_config["password"] = obs_host, obs_port, obs_password
    obs_config["scene_main"] = obs_scene_main
    safe_json_dump(obs_config_file, obs_config)

def obs_connect():
    global obs_client, obs_connected
    if not obs_available:
        console_log("WARN", "obsws_python not installed; cannot connect to OBS.")
        return False
    if verbose_conn_logging_enabled():
        console_log("INFO", f"[obs websocket] attempting connection to {obs_host}:{obs_port}...")
    try:
        obs_client = obs.ReqClient(host=obs_host, port=obs_port, password=obs_password, timeout=4) if obs_password else obs.ReqClient(host=obs_host, port=obs_port, timeout=4)
        obs_connected = True
        console_log("INFO", "connected to OBS websocket.")
        return True
    except Exception as e:
        obs_connected = False
        hint = ""
        if "authentication" in str(e).lower() or "password" in str(e).lower():
            hint = " -- OBS's WebSocket Server has a password set (Tools > WebSocket Server Settings in OBS); copy it into the Password field on this bot's OBS tab."
        console_log("ERROR", f"obs connect failed: {e}{hint}")
        return False

_obs_connect_retry_lock = threading.Lock()
_obs_connect_retry_running = False
_obs_connect_retry_cancel = threading.Event()

def obs_connect_with_retry():
    """Same as obs_connect(), but if the first attempt fails it keeps retrying with backoff
    in the background until it succeeds (or obs_disconnect() cancels it) instead of giving up."""
    global _obs_connect_retry_running
    if obs_connect(): return
    with _obs_connect_retry_lock:
        if _obs_connect_retry_running: return
        _obs_connect_retry_running = True
    _obs_connect_retry_cancel.clear()
    threading.Thread(target=_obs_connect_retry_worker, daemon=True).start()

def _obs_connect_retry_worker():
    global _obs_connect_retry_running
    delay = 2.0
    try:
        while not _obs_connect_retry_cancel.is_set():
            console_log("WARN", f"[obs websocket] retrying connection in {delay:.0f}s...")
            if _obs_connect_retry_cancel.wait(delay): return
            if obs_connect(): return
            delay = min(delay * 1.5, 30.0)
    finally:
        with _obs_connect_retry_lock:
            _obs_connect_retry_running = False

def obs_disconnect():
    global obs_client, obs_connected
    was_connected = obs_connected
    _obs_connect_retry_cancel.set()  # stop any in-progress connect retries
    obs_client, obs_connected = None, False
    if was_connected and verbose_conn_logging_enabled():
        console_log("INFO", "[obs websocket] disconnected.")

def obs_trigger(event):
    scene = obs_config.get("event_scenes", {}).get(event, "")
    if scene: set_obs_scene(scene)

# ---------------- Music panel (yt-dlp + python-vlc) ----------------
MUSIC_SCHEDULE_MAX = 20
music_config = {
    "tracks": [],       # list of single yt urls
    "playlists": [],    # list of yt playlist urls (played shuffle+loop)
    "schedule": [],     # ordered list: {"type": "track"/"playlist", "url": "..."}
    "change_hours": 1,  # advance to next schedule slot every N hours
    "enabled": False,
}
music_lock = threading.RLock()
music_player = None            # vlc.Instance
music_media_player = None      # vlc.MediaPlayer
music_media_list_player = None # vlc.MediaListPlayer (for shuffled/looped playlists)
music_stop_event = threading.Event()
music_thread = None
music_status_text = "stopped"
music_current_desc = ""
music_track_naturally_ended = threading.Event()  # set when a single track finishes -- change_hours
                                                   # is a PLAYLIST-only wait; a lone track should
                                                   # advance the schedule immediately when it ends.

def load_music_config():
    global music_config
    try:
        if os.path.exists(music_config_file):
            with open(music_config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            music_config.update(data)
    except Exception: pass
    music_config["schedule"] = music_config.get("schedule", [])[:MUSIC_SCHEDULE_MAX]

def save_music_config():
    safe_json_dump(music_config_file, music_config)

_DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

def _music_resolve_playlist_entries(url):
    """Lightweight (no stream resolution) listing of a playlist's video urls, via yt-dlp's flat extraction."""
    if not ytdlp_available: return []
    ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist", "skip_download": True}
    urls = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        entries = info.get("entries") if isinstance(info, dict) else None
        if entries:
            for entry in entries:
                if not entry: continue
                vid = entry.get("id") or entry.get("url")
                if not vid: continue
                urls.append(vid if str(vid).startswith("http") else f"https://www.youtube.com/watch?v={vid}")
        elif isinstance(info, dict) and info.get("id"):
            urls.append(url)
    except Exception as e:
        console_log("ERROR", f"[music] failed to list playlist {url}: {e}")
    return urls

def _music_resolve_stream(url):
    """Use yt-dlp to resolve a single video/track to a direct playable stream url + http headers."""
    if not ytdlp_available: return None, None, None
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best", "quiet": True, "no_warnings": True,
        "noplaylist": True, "skip_download": True,
        # The "android" client is far less likely to get throttled/require extra signature
        # work than the default web client, which is the #1 cause of resolved-but-unplayable
        # streams. Falls back to "web" if android extraction fails for a given video.
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        stream_url = info.get("url")
        if not stream_url and info.get("entries"):
            info = info["entries"][0]
            stream_url = info.get("url")
        if not stream_url: return None, None, None
        headers = info.get("http_headers") or {}
        title = info.get("title") or url
        return stream_url, headers, title
    except Exception as e:
        console_log("ERROR", f"[music] yt-dlp resolve failed for {url}: {e}")
        return None, None, None

def _music_get_vlc_instance():
    global music_player
    if not vlc_available: return None
    if music_player is None:
        try: music_player = _vlc.Instance("--no-video", "--quiet", "--aout=any")
        except Exception as e:
            console_log("ERROR", f"[music] vlc init failed: {e}")
            return None
    return music_player

# ---- queue-based engine: resolves + plays one track at a time, auto-advances on end ----
music_queue = []          # list of source urls (watch page urls) for the current schedule item
music_queue_index = -1
music_queue_is_playlist = False
music_queue_source_url = ""

# ---- !sr song requests: queued and played at the NEXT scheduled music change, not immediately ----
music_song_requests = []  # list of {"url": watch/playlist url, "is_playlist": bool, "raw": original text, "user": requester}

def _music_parse_request(raw):
    """Turns a video id/url or playlist id/url into (watch_or_playlist_url, is_playlist)."""
    raw = (raw or "").strip().strip("<>").strip()
    if not raw: return None, False
    if raw.startswith("http://") or raw.startswith("https://"):
        m = re.search(r"[?&]list=([A-Za-z0-9_-]+)", raw)
        if m: return f"https://www.youtube.com/playlist?list={m.group(1)}", True
        return raw, False
    if raw.upper().startswith(("PL", "UU", "OL", "RD", "LL", "FL", "WL")) and len(raw) >= 10:
        return f"https://www.youtube.com/playlist?list={raw}", True
    return f"https://www.youtube.com/watch?v={raw}", False

def queue_song_request(raw, user=""):
    """Queues a !sr request; it plays automatically the next time the music schedule advances."""
    url, is_playlist = _music_parse_request(raw)
    if not url: return None
    with music_lock:
        music_song_requests.append({"url": url, "is_playlist": is_playlist, "raw": raw, "user": user})
    return url, is_playlist

def find_youtube_video_id(query):
    """The engine behind !findsr: searches YouTube for `query` and returns the first result's
    video id, or None if nothing was found / the search failed."""
    query = (query or "").strip()
    if not query: return None
    try:
        search_url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
        req = urllib.request.Request(search_url, headers={"User-Agent": _DEFAULT_UA})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        m = re.search(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
        return m.group(1) if m else None
    except Exception as e:
        console_log("ERROR", f"[findsr] youtube search failed: {e}")
        return None

def _music_on_end_reached(event):
    # Runs on a libvlc-internal thread; hop to a normal Python thread before doing real work.
    console_log("INFO", "[music] track finished, advancing to next in queue.")
    threading.Thread(target=_music_advance_queue, daemon=True).start()

def _music_on_playback_error(event):
    global music_status_text
    music_status_text = "playback error encountered mid-track, skipping after short delay..."
    console_log("ERROR", f"[music] {music_status_text}")
    notify("Music Playback Error", "A track failed to stream and will be skipped.", timeout=5)
    def _delayed_advance():
        time.sleep(2.5)  # avoid hammering the CDN/VLC in a tight failure loop
        _music_advance_queue()
    threading.Thread(target=_delayed_advance, daemon=True).start()

def _music_advance_queue():
    global music_queue_index
    if music_stop_event.is_set(): return
    with music_lock:
        if not music_queue: return
        if not music_queue_is_playlist:
            # A single track just finished. change_hours is meant to govern how long a
            # PLAYLIST stays on rotation -- a lone track shouldn't loop itself or sit waiting
            # out the rest of that hour. Signal music_player_loop to move on right away.
            music_track_naturally_ended.set()
            return
        music_queue_index += 1
        if music_queue_index >= len(music_queue):
            music_queue_index = 0
            if music_queue_is_playlist:
                random.shuffle(music_queue)  # loop = restart shuffled playlist from the top
        target = music_queue[music_queue_index]
    _music_play_queue_current(target)

def _music_play_queue_current(watch_url, _attempt=1):
    global music_media_player, music_status_text, music_current_desc
    inst = _music_get_vlc_instance()
    if inst is None:
        music_status_text = "vlc/yt-dlp not available"
        return False
    stream, headers, title = _music_resolve_stream(watch_url)
    if not stream:
        if _attempt < 3:
            music_status_text = f"resolve failed (attempt {_attempt}/3), retrying: {watch_url}"
            console_log("WARN", f"[music] {music_status_text}")
            def _retry():
                time.sleep(2.5)
                _music_play_queue_current(watch_url, _attempt + 1)
            threading.Thread(target=_retry, daemon=True).start()
            return False
        music_status_text = f"failed to resolve after 3 attempts, skipping: {watch_url}"
        console_log("WARN", f"[music] {music_status_text}")
        notify("Music Error", f"Couldn't resolve after 3 tries: {watch_url}", timeout=5)
        threading.Thread(target=_music_advance_queue, daemon=True).start()
        return False
    try:
        media = inst.media_new(stream)
        ua = (headers or {}).get("User-Agent", _DEFAULT_UA)
        media.add_option(f":http-user-agent={ua}")
        media.add_option(":http-referrer=https://www.youtube.com/")
        media.add_option(":http-reconnect")
        media.add_option(":network-caching=4000")
        mp = inst.media_player_new()
        mp.set_media(media)
        try: mp.audio_set_volume(int(music_config.get("volume", 90)))
        except Exception: pass
        ev = mp.event_manager()
        ev.event_attach(_vlc.EventType.MediaPlayerEndReached, _music_on_end_reached)
        ev.event_attach(_vlc.EventType.MediaPlayerEncounteredError, _music_on_playback_error)
        mp.play()
        old = music_media_player
        music_media_player = mp
        try:
            if old is not None: old.stop()
        except Exception: pass
        music_current_desc = title or watch_url
        music_status_text = f"playing: {music_current_desc}"
        console_log("INFO", f"[music] {music_status_text}")
        notify("Now Playing", music_current_desc, timeout=4)
        return True
    except Exception as e:
        music_status_text = f"playback error: {e}"
        console_log("ERROR", f"[music] {music_status_text}")
        notify("Music Error", str(e), timeout=5)
        return False

def music_play_url(url, shuffle_loop=False):
    """Start playing a single track, or (if shuffle_loop) a playlist url shuffled+looping."""
    global music_queue, music_queue_index, music_queue_is_playlist, music_queue_source_url, music_status_text
    if not vlc_available or not ytdlp_available:
        music_status_text = "vlc/yt-dlp not available"
        return False
    music_stop_current()
    music_track_naturally_ended.clear()
    with music_lock:
        if shuffle_loop:
            entries = _music_resolve_playlist_entries(url)
            if not entries: entries = [url]
            random.shuffle(entries)
            music_queue = entries
        else:
            music_queue = [url]
        music_queue_index = 0
        music_queue_is_playlist = shuffle_loop
        music_queue_source_url = url
        first = music_queue[0]
    return _music_play_queue_current(first)

def music_skip_track():
    """Manually skip to the next track in the current queue."""
    threading.Thread(target=_music_advance_queue, daemon=True).start()

def music_stop_current():
    global music_media_player
    try:
        if music_media_player is not None:
            ev = music_media_player.event_manager()
            try:
                ev.event_detach(_vlc.EventType.MediaPlayerEndReached)
                ev.event_detach(_vlc.EventType.MediaPlayerEncounteredError)
            except Exception: pass
            music_media_player.stop()
    except Exception: pass
    music_media_player = None

def music_pause_toggle():
    try:
        if music_media_player is not None:
            music_media_player.pause()
    except Exception: pass

def music_set_volume(vol):
    music_config["volume"] = max(0, min(100, int(vol)))
    save_music_config()
    try:
        if music_media_player is not None: music_media_player.audio_set_volume(music_config["volume"])
    except Exception: pass

def music_player_loop():
    """Advances through the schedule every `change_hours` hours, in order, looping.
    Any pending !sr song requests are played first, ahead of the schedule, at each change."""
    global music_status_text
    idx = 0
    while app_instance is None:
        time.sleep(1)
    while app_instance.running and not music_stop_event.is_set():
        with music_lock:
            pending = music_song_requests.pop(0) if music_song_requests else None
            schedule = list(music_config.get("schedule", []))
            hours = float(music_config.get("change_hours", 1) or 1)

        if pending:
            music_play_url(pending["url"], shuffle_loop=pending["is_playlist"])
            kind = "playlist" if pending["is_playlist"] else "track"
            who = f" (requested by {pending['user']})" if pending.get("user") else ""
            notify("Song Request", f"Now playing requested {kind}{who}.", timeout=5)
            wait_seconds = max(30, hours * 3600)
            waited = 0
            while waited < wait_seconds and not music_stop_event.is_set() and app_instance.running:
                if not pending["is_playlist"] and music_track_naturally_ended.is_set():
                    music_track_naturally_ended.clear()
                    break  # single track -- move on the moment it ends, don't wait out the hour
                if music_stop_event.wait(2): break
                waited += 2
            continue  # request didn't consume a schedule slot -- idx stays put

        if not schedule or not music_config.get("enabled", False):
            music_status_text = "stopped (no schedule / disabled)"
            music_stop_current()
            if music_stop_event.wait(5): break
            continue
        idx = idx % len(schedule)
        item = schedule[idx]
        url, itype = item.get("url", ""), item.get("type", "track")
        if url:
            music_play_url(url, shuffle_loop=(itype == "playlist"))
            notify("Music Schedule", f"Now on schedule slot {idx + 1}/{len(schedule)} ({itype}).", timeout=4)
        else:
            music_track_naturally_ended.clear()
        wait_seconds = max(30, hours * 3600)
        waited = 0
        while waited < wait_seconds and not music_stop_event.is_set() and app_instance.running:
            if itype != "playlist" and music_track_naturally_ended.is_set():
                music_track_naturally_ended.clear()
                break  # single track -- move on the moment it ends, don't wait out the hour
            if music_stop_event.wait(2): break
            waited += 2
        idx += 1
    music_stop_current()
    console_log("INFO", "[music] player loop stopped.")

def start_music_player():
    global music_thread
    music_stop_event.clear()
    if music_thread is None or not music_thread.is_alive():
        music_thread = threading.Thread(target=music_player_loop, daemon=True)
        music_thread.start()

def stop_music_player():
    music_stop_event.set()
    music_stop_current()

# ---------------- Video panel (yt-dlp + python-vlc, rendered into a movable window) ----------------
# Same engine/schedule design as the Music panel above, except tracks are resolved as a playable
# VIDEO stream (not audio-only) and rendered into a floating, draggable Toplevel window (the OS
# window titlebar itself is what makes it "movable" -- position/size persist across restarts).
VIDEO_SCHEDULE_MAX = 20
video_config = {
    "tracks": [],       # list of single yt urls
    "playlists": [],    # list of yt playlist urls (played shuffle+loop)
    "schedule": [],     # ordered list: {"type": "track"/"playlist", "url": "..."}
    "change_hours": 1,  # advance to next schedule slot every N hours
    "enabled": False,
    "volume": 90,
    "window_x": None, "window_y": None, "window_w": 640, "window_h": 360,
    "always_on_top": False,
}
video_lock = threading.RLock()
video_player = None            # vlc.Instance (video-enabled, separate from the Music panel's)
video_media_player = None      # vlc.MediaPlayer
video_stop_event = threading.Event()
video_thread = None
video_status_text = "stopped"
video_current_desc = ""
video_track_naturally_ended = threading.Event()  # same purpose as the Music panel's flag

def load_video_config():
    global video_config
    try:
        if os.path.exists(video_config_file):
            with open(video_config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            video_config.update(data)
    except Exception: pass
    video_config["schedule"] = video_config.get("schedule", [])[:VIDEO_SCHEDULE_MAX]

def save_video_config():
    safe_json_dump(video_config_file, video_config)

# playlist listing and id/url parsing are format-agnostic (audio vs video), so the Music panel's
# helpers are reused as-is instead of duplicating them.
_video_resolve_playlist_entries = _music_resolve_playlist_entries
_video_parse_request = _music_parse_request

def _video_resolve_stream(url):
    """Use yt-dlp to resolve a single video/track to a direct playable VIDEO stream url + headers."""
    if not ytdlp_available: return None, None, None
    ydl_opts = {
        "format": "best[ext=mp4]/best", "quiet": True, "no_warnings": True,
        "noplaylist": True, "skip_download": True,
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        stream_url = info.get("url")
        if not stream_url and info.get("entries"):
            info = info["entries"][0]
            stream_url = info.get("url")
        if not stream_url: return None, None, None
        headers = info.get("http_headers") or {}
        title = info.get("title") or url
        return stream_url, headers, title
    except Exception as e:
        console_log("ERROR", f"[video] yt-dlp resolve failed for {url}: {e}")
        return None, None, None

def _video_get_vlc_instance():
    global video_player
    if not vlc_available: return None
    if video_player is None:
        try: video_player = _vlc.Instance("--quiet")
        except Exception as e:
            console_log("ERROR", f"[video] vlc init failed: {e}")
            return None
    return video_player

def _video_ensure_window_sync(timeout=5):
    """Runs from a background thread: hops to the Tk main thread to (re)create/show the movable
    video window, waits for it, then returns the native window id VLC should render into."""
    if app_instance is None: return None
    ready = threading.Event()
    result = {}
    def _create():
        try:
            app_instance.ensure_video_window()
            result["winid"] = app_instance.video_canvas.winfo_id()
        except Exception as e:
            result["error"] = e
        ready.set()
    try:
        app_instance.root.after(0, _create)
    except Exception:
        return None
    ready.wait(timeout)
    return result.get("winid")

# ---- queue-based engine: resolves + plays one clip at a time, auto-advances on end ----
video_queue = []          # list of source urls (watch page urls) for the current schedule item
video_queue_index = -1
video_queue_is_playlist = False
video_queue_source_url = ""

# ---- !vr video requests: queued and played at the NEXT scheduled video change, not immediately ----
video_requests = []  # list of {"url": watch/playlist url, "is_playlist": bool, "raw": original text, "user": requester}

def queue_video_request(raw, user=""):
    """Queues a !vr request; it plays automatically the next time the video schedule advances."""
    url, is_playlist = _video_parse_request(raw)
    if not url: return None
    with video_lock:
        video_requests.append({"url": url, "is_playlist": is_playlist, "raw": raw, "user": user})
    return url, is_playlist

def _video_on_end_reached(event):
    # Runs on a libvlc-internal thread; hop to a normal Python thread before doing real work.
    console_log("INFO", "[video] clip finished, advancing to next in queue.")
    threading.Thread(target=_video_advance_queue, daemon=True).start()

def _video_on_playback_error(event):
    global video_status_text
    video_status_text = "playback error encountered mid-clip, skipping after short delay..."
    console_log("ERROR", f"[video] {video_status_text}")
    notify("Video Playback Error", "A clip failed to stream and will be skipped.", timeout=5)
    def _delayed_advance():
        time.sleep(2.5)  # avoid hammering the CDN/VLC in a tight failure loop
        _video_advance_queue()
    threading.Thread(target=_delayed_advance, daemon=True).start()

def _video_advance_queue():
    global video_queue_index
    if video_stop_event.is_set(): return
    with video_lock:
        if not video_queue: return
        if not video_queue_is_playlist:
            # A single clip just finished. change_hours is meant to govern how long a
            # PLAYLIST stays on rotation -- a lone clip shouldn't loop itself or sit waiting
            # out the rest of that hour. Signal video_player_loop to move on right away.
            video_track_naturally_ended.set()
            return
        video_queue_index += 1
        if video_queue_index >= len(video_queue):
            video_queue_index = 0
            if video_queue_is_playlist:
                random.shuffle(video_queue)  # loop = restart shuffled playlist from the top
        target = video_queue[video_queue_index]
    _video_play_queue_current(target)

def _video_play_queue_current(watch_url, _attempt=1):
    global video_media_player, video_status_text, video_current_desc
    inst = _video_get_vlc_instance()
    if inst is None:
        video_status_text = "vlc/yt-dlp not available"
        return False
    stream, headers, title = _video_resolve_stream(watch_url)
    if not stream:
        if _attempt < 3:
            video_status_text = f"resolve failed (attempt {_attempt}/3), retrying: {watch_url}"
            console_log("WARN", f"[video] {video_status_text}")
            def _retry():
                time.sleep(2.5)
                _video_play_queue_current(watch_url, _attempt + 1)
            threading.Thread(target=_retry, daemon=True).start()
            return False
        video_status_text = f"failed to resolve after 3 attempts, skipping: {watch_url}"
        console_log("WARN", f"[video] {video_status_text}")
        notify("Video Error", f"Couldn't resolve after 3 tries: {watch_url}", timeout=5)
        threading.Thread(target=_video_advance_queue, daemon=True).start()
        return False
    winid = _video_ensure_window_sync()
    if not winid:
        video_status_text = "couldn't open the video window"
        console_log("ERROR", f"[video] {video_status_text}")
        return False
    try:
        media = inst.media_new(stream)
        ua = (headers or {}).get("User-Agent", _DEFAULT_UA)
        media.add_option(f":http-user-agent={ua}")
        media.add_option(":http-referrer=https://www.youtube.com/")
        media.add_option(":http-reconnect")
        media.add_option(":network-caching=4000")
        mp = inst.media_player_new()
        mp.set_media(media)
        try:
            plat = platform.system()
            if plat == "Windows": mp.set_hwnd(winid)
            elif plat == "Darwin": mp.set_nsobject(winid)
            else: mp.set_xwindow(winid)
        except Exception as e:
            console_log("ERROR", f"[video] failed to bind video output to window: {e}")
        try: mp.audio_set_volume(int(video_config.get("volume", 90)))
        except Exception: pass
        ev = mp.event_manager()
        ev.event_attach(_vlc.EventType.MediaPlayerEndReached, _video_on_end_reached)
        ev.event_attach(_vlc.EventType.MediaPlayerEncounteredError, _video_on_playback_error)
        mp.play()
        old = video_media_player
        video_media_player = mp
        try:
            if old is not None: old.stop()
        except Exception: pass
        video_current_desc = title or watch_url
        video_status_text = f"playing: {video_current_desc}"
        console_log("INFO", f"[video] {video_status_text}")
        notify("Now Playing (Video)", video_current_desc, timeout=4)
        if app_instance is not None:
            desc = video_current_desc
            app_instance.root.after(0, lambda: app_instance.set_video_window_title(desc))
        return True
    except Exception as e:
        video_status_text = f"playback error: {e}"
        console_log("ERROR", f"[video] {video_status_text}")
        notify("Video Error", str(e), timeout=5)
        return False

def video_play_url(url, shuffle_loop=False):
    """Start playing a single clip, or (if shuffle_loop) a playlist url shuffled+looping."""
    global video_queue, video_queue_index, video_queue_is_playlist, video_queue_source_url, video_status_text
    if not vlc_available or not ytdlp_available:
        video_status_text = "vlc/yt-dlp not available"
        return False
    video_stop_current()
    video_track_naturally_ended.clear()
    with video_lock:
        if shuffle_loop:
            entries = _video_resolve_playlist_entries(url)
            if not entries: entries = [url]
            random.shuffle(entries)
            video_queue = entries
        else:
            video_queue = [url]
        video_queue_index = 0
        video_queue_is_playlist = shuffle_loop
        video_queue_source_url = url
        first = video_queue[0]
    return _video_play_queue_current(first)

def video_skip_track():
    """Manually skip to the next clip in the current queue."""
    threading.Thread(target=_video_advance_queue, daemon=True).start()

def video_stop_current():
    global video_media_player
    try:
        if video_media_player is not None:
            ev = video_media_player.event_manager()
            try:
                ev.event_detach(_vlc.EventType.MediaPlayerEndReached)
                ev.event_detach(_vlc.EventType.MediaPlayerEncounteredError)
            except Exception: pass
            video_media_player.stop()
    except Exception: pass
    video_media_player = None

def video_pause_toggle():
    try:
        if video_media_player is not None:
            video_media_player.pause()
    except Exception: pass

def video_set_volume(vol):
    video_config["volume"] = max(0, min(100, int(vol)))
    save_video_config()
    try:
        if video_media_player is not None: video_media_player.audio_set_volume(video_config["volume"])
    except Exception: pass

def video_player_loop():
    """Advances through the schedule every `change_hours` hours, in order, looping.
    Any pending !vr video requests are played first, ahead of the schedule, at each change."""
    global video_status_text
    idx = 0
    while app_instance is None:
        time.sleep(1)
    while app_instance.running and not video_stop_event.is_set():
        with video_lock:
            pending = video_requests.pop(0) if video_requests else None
            schedule = list(video_config.get("schedule", []))
            hours = float(video_config.get("change_hours", 1) or 1)

        if pending:
            video_play_url(pending["url"], shuffle_loop=pending["is_playlist"])
            kind = "playlist" if pending["is_playlist"] else "video"
            who = f" (requested by {pending['user']})" if pending.get("user") else ""
            notify("Video Request", f"Now playing requested {kind}{who}.", timeout=5)
            wait_seconds = max(30, hours * 3600)
            waited = 0
            while waited < wait_seconds and not video_stop_event.is_set() and app_instance.running:
                if not pending["is_playlist"] and video_track_naturally_ended.is_set():
                    video_track_naturally_ended.clear()
                    break  # single clip -- move on the moment it ends, don't wait out the hour
                if video_stop_event.wait(2): break
                waited += 2
            continue  # request didn't consume a schedule slot -- idx stays put

        if not schedule or not video_config.get("enabled", False):
            video_status_text = "stopped (no schedule / disabled)"
            video_stop_current()
            if video_stop_event.wait(5): break
            continue
        idx = idx % len(schedule)
        item = schedule[idx]
        url, itype = item.get("url", ""), item.get("type", "track")
        if url:
            video_play_url(url, shuffle_loop=(itype == "playlist"))
            notify("Video Schedule", f"Now on schedule slot {idx + 1}/{len(schedule)} ({itype}).", timeout=4)
        else:
            video_track_naturally_ended.clear()
        wait_seconds = max(30, hours * 3600)
        waited = 0
        while waited < wait_seconds and not video_stop_event.is_set() and app_instance.running:
            if itype != "playlist" and video_track_naturally_ended.is_set():
                video_track_naturally_ended.clear()
                break  # single clip -- move on the moment it ends, don't wait out the hour
            if video_stop_event.wait(2): break
            waited += 2
        idx += 1
    video_stop_current()
    console_log("INFO", "[video] player loop stopped.")

def start_video_player():
    global video_thread
    video_stop_event.clear()
    if video_thread is None or not video_thread.is_alive():
        video_thread = threading.Thread(target=video_player_loop, daemon=True)
        video_thread.start()

def stop_video_player():
    video_stop_event.set()
    video_stop_current()

# ---------------- Soundboard panel (web search only, python-vlc for playback) ----------------
# !sb <search term> searches myinstants.com, takes the FIRST result, and plays it. No local
# sound files/folders involved -- pygame kept failing to build on newer Python versions (no
# prebuilt wheel + distutils removed), and this reuses python-vlc, which the Music panel already
# needs, so there's no extra dependency to install.
soundboard_config = {"volume": 90}
soundboard_lock = threading.RLock()
soundboard_status_text = "idle"
soundboard_vlc_instance = None     # vlc.Instance, separate from the Music panel's
soundboard_active_players = []     # live vlc.MediaPlayer refs, kept so overlapping sounds don't get GC'd mid-playback

def load_soundboard_config():
    global soundboard_config
    try:
        if os.path.exists(soundboard_config_file):
            with open(soundboard_config_file, "r", encoding="utf-8") as f:
                soundboard_config.update(json.load(f))
    except Exception: pass

def save_soundboard_config():
    safe_json_dump(soundboard_config_file, soundboard_config)

def _soundboard_get_vlc_instance():
    global soundboard_vlc_instance
    if not vlc_available: return None
    if soundboard_vlc_instance is None:
        try: soundboard_vlc_instance = _vlc.Instance("--no-video", "--quiet", "--aout=any")
        except Exception as e:
            console_log("ERROR", f"[soundboard] vlc init failed: {e}")
            return None
    return soundboard_vlc_instance

# ---- !sb web search: searches myinstants.com, grabs the FIRST result, downloads and plays it
# (the "red button" on an instant's page is just the JS play() call -- we pull the mp3 straight
# from that button's onclick instead of literally clicking it in a browser) ----
def _soundboard_cache_dir():
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soundboard_web_cache")
    try: os.makedirs(d, exist_ok=True)
    except Exception: pass
    return d

def _soundboard_cache_key(query):
    key = re.sub(r"[^a-zA-Z0-9_-]+", "_", (query or "").strip().lower()).strip("_")
    return (key or "sound")[:60]

def _soundboard_web_search_first(query):
    """Searches myinstants.com for `query` and returns (mp3_url, display_name) for the FIRST
    result on the page, or (None, None) if nothing was found."""
    search_url = "https://www.myinstants.com/en/search/?name=" + urllib.parse.quote(query)
    try:
        req = urllib.request.Request(search_url, headers={"User-Agent": _DEFAULT_UA})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        console_log("ERROR", f"[soundboard] myinstants search failed: {e}")
        return None, None
    # Each result button is onclick="play('/media/sounds/<file>.mp3','<id>')" -- the FIRST match
    # on the results page is the first search result (myinstants lists them in relevance order).
    m = re.search(r"onclick=\"play\('([^']+)'", html)
    if not m:
        return None, None
    mp3_path = m.group(1)
    mp3_url = mp3_path if mp3_path.startswith("http") else "https://www.myinstants.com" + mp3_path
    name_m = re.search(r'<a[^>]+href="/en/instant/[^"]+"[^>]*>([^<]+)</a>', html)
    display_name = name_m.group(1).strip() if name_m else query
    return mp3_url, display_name

def _soundboard_web_fetch_by_id(instant_id):
    """Fetches a myinstants.com instant page directly by its slug/id (the part of the URL after
    /en/instant/, e.g. 'mlg-air-horn' from myinstants.com/en/instant/mlg-air-horn/) and returns
    (mp3_url, display_name), or (None, None) if that id doesn't exist. No search/guessing --
    this is the exact sound, unlike !sb which takes the first search RESULT."""
    instant_id = instant_id.strip().strip("/")
    page_url = f"https://www.myinstants.com/en/instant/{urllib.parse.quote(instant_id)}/"
    try:
        req = urllib.request.Request(page_url, headers={"User-Agent": _DEFAULT_UA})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, None
        console_log("ERROR", f"[soundboard] myinstants id lookup failed ({e.code}): {instant_id}")
        return None, None
    except Exception as e:
        console_log("ERROR", f"[soundboard] myinstants id lookup failed: {e}")
        return None, None
    m = re.search(r"onclick=\"play\('([^']+)'", html)
    if not m:
        return None, None
    mp3_path = m.group(1)
    mp3_url = mp3_path if mp3_path.startswith("http") else "https://www.myinstants.com" + mp3_path
    title_m = re.search(r"<h1[^>]*>([^<]+)</h1>", html)
    display_name = title_m.group(1).strip() if title_m else instant_id
    return mp3_url, display_name

def _soundboard_play_file(path, label):
    """Plays a local mp3 file via python-vlc. Each call spawns its own MediaPlayer, so multiple
    soundboard clips (and music) can overlap without stepping on each other."""
    global soundboard_status_text
    inst = _soundboard_get_vlc_instance()
    if inst is None:
        soundboard_status_text = "python-vlc not available"
        return False, "python-vlc is not installed (pip install python-vlc, and install VLC itself)"
    try:
        media = inst.media_new(path)
        mp = inst.media_player_new()
        mp.set_media(media)
        try: mp.audio_set_volume(int(soundboard_config.get("volume", 90)))
        except Exception: pass
        mp.play()
        with soundboard_lock:
            soundboard_active_players.append(mp)
            # periodically drop refs to players that have finished, so the list doesn't grow forever
            soundboard_active_players[:] = [p for p in soundboard_active_players if p is mp or p.is_playing()][-30:]
        soundboard_status_text = f"playing: {label}"
        console_log("INFO", f"[soundboard] {soundboard_status_text}")
        return True, label
    except Exception as e:
        soundboard_status_text = f"playback error: {e}"
        console_log("ERROR", f"[soundboard] {soundboard_status_text}")
        return False, str(e)

def _soundboard_download_and_play(mp3_url, label, save_path):
    global soundboard_status_text
    try:
        req = urllib.request.Request(mp3_url, headers={"User-Agent": _DEFAULT_UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        with open(save_path, "wb") as f:
            f.write(data)
    except Exception as e:
        soundboard_status_text = f"download failed: {e}"
        console_log("ERROR", f"[soundboard] {soundboard_status_text}")
        return False, str(e)
    return _soundboard_play_file(save_path, label)

def soundboard_stop_all():
    global soundboard_status_text
    with soundboard_lock:
        for p in soundboard_active_players:
            try: p.stop()
            except Exception: pass
        soundboard_active_players.clear()
    soundboard_status_text = "stopped all sounds"

def soundboard_set_volume(vol):
    soundboard_config["volume"] = max(0, min(100, int(float(vol))))
    save_soundboard_config()
    with soundboard_lock:
        for p in soundboard_active_players:
            try: p.audio_set_volume(soundboard_config["volume"])
            except Exception: pass

def soundboard_web_search_and_play(query, user=""):
    """The engine behind !sb <name>: searches myinstants.com for `query`, takes the first
    result, and plays it -- pulling the mp3 straight off the result's play button instead of
    literally driving a browser. Repeat searches are served from a local disk cache."""
    global soundboard_status_text
    query = (query or "").strip()
    if not query:
        return False, "no search term given"
    if not vlc_available:
        return False, "python-vlc is not installed (pip install python-vlc, and install VLC itself)"

    cache_path = os.path.join(_soundboard_cache_dir(), _soundboard_cache_key(query) + ".mp3")
    if os.path.exists(cache_path):
        return _soundboard_play_file(cache_path, query)

    soundboard_status_text = f"searching myinstants for '{query}'..."
    console_log("INFO", f"[soundboard] {soundboard_status_text}")
    mp3_url, display_name = _soundboard_web_search_first(query)
    if not mp3_url:
        soundboard_status_text = f"no results for '{query}'"
        return False, f"no soundboard results found for '{query}'"

    soundboard_status_text = f"downloading '{display_name}'..."
    console_log("INFO", f"[soundboard] {soundboard_status_text}")
    return _soundboard_download_and_play(mp3_url, display_name, cache_path)

def soundboard_web_id_and_play(instant_id, user=""):
    """The engine behind !sbid <id>: fetches a myinstants.com instant page directly by its
    exact slug/id (the part of the URL after /en/instant/) and plays it -- no search, no
    'first result' guessing, just that one sound. Cached separately from !sb's cache."""
    global soundboard_status_text
    instant_id = (instant_id or "").strip()
    if not instant_id:
        return False, "no soundboard id given"
    if not vlc_available:
        return False, "python-vlc is not installed (pip install python-vlc, and install VLC itself)"

    cache_path = os.path.join(_soundboard_cache_dir(), "id_" + _soundboard_cache_key(instant_id) + ".mp3")
    if os.path.exists(cache_path):
        return _soundboard_play_file(cache_path, instant_id)

    soundboard_status_text = f"looking up myinstants id '{instant_id}'..."
    console_log("INFO", f"[soundboard] {soundboard_status_text}")
    mp3_url, display_name = _soundboard_web_fetch_by_id(instant_id)
    if not mp3_url:
        soundboard_status_text = f"no soundboard found for id '{instant_id}'"
        return False, f"no soundboard found for id '{instant_id}' (check the id in the myinstants.com URL)"

    soundboard_status_text = f"downloading '{display_name}'..."
    console_log("INFO", f"[soundboard] {soundboard_status_text}")
    return _soundboard_download_and_play(mp3_url, display_name, cache_path)

class ChatPlaysApp:
    def __init__(self, root):
        try:
            self.root = root
            self.vm_crashed = False
            self.is_multistream = is_multistream
            self.changevm_enabled = not self.is_multistream
            self.last_gc_time = time.time()
            self.last_vbox_refresh = time.time()
            self.vm_frozen_since = None
            self.watchdog_action_level = 0
            self.last_watchdog_action_time = 0
            self.consecutive_failures = 0
            self.last_success_time = time.time()
            self.api_watchdog_level = 0
            self.last_api_watchdog_action_time = 0
            self.maintenance_lock = threading.Lock()
            self.maintenance_gen = 0
            self.recent_bot_messages = collections.deque(maxlen=50)
            self.cancel_macros = False
            
            # LOAD ISOLATED SETTINGS FIRST
            self.config = self.load_settings()
            
            self.last_queue_warn_time = 0
            self.last_unstick_time = time.time()
            self.last_offline_warn = 0
            self.last_err_spam = 0
            self._last_status = ""
            
            self.ultra_speed = self.config.get("ultra_speed", False)
            self.enable_ocr = self.config.get("enable_ocr", False)
            self.log_queue = queue.Queue(maxsize=300)
            
            global vm_name, keyboard_layout, vbox_manage_cmd, vmrun_cmd, current_vm_backend
            
            # ENFORCE EXACT JSON VM NAME (No array guessing!)
            vm_name = self.config.get("vm_name", vm_name)
            keyboard_layout = self.config.get("keyboard_layout", keyboard_layout)
            vbox_manage_cmd = self.config.get("vbox_path", vbox_manage_cmd).strip().strip('"').strip("'")
            vmrun_cmd = self.config.get("vmrun_path", vmrun_cmd).strip().strip('"').strip("'")
            current_vm_backend = self.config.get("vm_backend", current_vm_backend)
            self.command_prefix = self.config.get("command_prefix", "!")
            self.custom_commands = self.config.get("custom_commands", {})
            self.app_name = self.config.get("app_name", "YT2VM")

            self.root.title(f"{self.app_name} {version}: {vm_name}")
            x_cood = int((self.root.winfo_screenwidth()/2) - (1150/2))
            y_cood = int((self.root.winfo_screenheight()/2) - (800/2))
            self.root.geometry(f"1150x800+{x_cood}+{y_cood}")
            self.root.configure(bg="#09090B")
            self.accent_main = "#8B5CF6" if self.is_multistream else "#00E5FF"
            self.accent_hover = "#7C3AED" if self.is_multistream else "#00B3CC"

            self._setup_right_click_menus()

            self.root.option_add('*TCombobox*Listbox.background', '#18181B')
            self.root.option_add('*TCombobox*Listbox.foreground', 'white')
            self.root.option_add('*TCombobox*Listbox.selectBackground', self.accent_main)
            self.root.option_add('*TCombobox*Listbox.selectForeground', 'black')

            style = ttk.Style()
            if platform.system() == "Darwin" and "aqua" in style.theme_names(): style.theme_use("aqua")
            elif "clam" in style.theme_names():
                style.theme_use("clam")
                style.configure("TCombobox", fieldbackground="#09090B", background="#27272A", foreground="white", bordercolor="#27272A", arrowcolor="white")
                style.map("TCombobox", fieldbackground=[("readonly", "#09090B")], foreground=[("readonly", "white")])

            style.configure(".", background="#09090B", foreground="#F4F4F5")
            style.configure("TFrame", background="#09090B")
            style.configure("Card.TFrame", background="#18181B")
            style.configure("TLabel", background="#09090B", foreground="#D4D4D8", font=("Segoe UI", 10))
            style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#FFFFFF", background="#09090B")
            style.configure("TNotebook", background="#09090B", tabmargins=[20, 10, 20, 0], borderwidth=0)
            style.configure("TNotebook.Tab", background="#18181B", foreground="#A1A1AA", padding=[25, 8], font=("Segoe UI", 11, "bold"), borderwidth=0)
            style.map("TNotebook.Tab", background=[("selected", self.accent_main)], foreground=[("selected", "#000000")])
            style.configure("Toggle.TCheckbutton", background="#18181B", foreground="#D4D4D8", font=("Segoe UI", 10), indicatorcolor="#27272A", padding=5)
            style.map("Toggle.TCheckbutton", indicatorcolor=[("selected", "#10B981")])
            
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            self.running = True
            self.active_url = self.config.get("youtube_url", "")
            self.listening_to_chat = self.config.get("enable_chat", True)
            self.disabled_commands = set()
            self.vm_control_enabled = True
            self.say_admin_only = True
            self.blocked_terms = list(default_blocked_terms)
            self.twenty_four_seven_mode = self.config.get("auto_start", False)
            self.blacklisted_users = set()
            self.active_votes = {}
            self.vote_lock = threading.Lock()
            self.processed_msg_ids = set()
            self.last_command_time = time.time()
            self.listener_id = 0
            self.executor_id = 0
            self.lag_multiplier = 1.0
            self.chat_paused = False
            self.shared_kb = None
            self.shared_mouse = None
            self.shared_session = None
            self.vbox_mouse_btns = 0
            self.input_lock = threading.RLock()
            self.vm_maintenance = False
            self.user_last_cmd_time = {}
            self.cmd_cooldown = float(self.config.get("cmd_cooldown", 1.5))
            self.user_cmd_counts = collections.Counter()
            self.active_chains = 0
            self.chains_lock = threading.Lock()
            self.last_com_rebuild_time = time.time()

            self.current_snapshot = ""
            if os.path.exists(snap_file):
                try:
                    with open(snap_file, "r") as f:
                        saved_snap = f.read().strip()
                        if saved_snap: self.current_snapshot = saved_snap
                except Exception: pass

            if not self.current_snapshot:
                snaps_found = get_vbox_snapshots(vbox_manage_cmd, vm_name)
                if snaps_found: self.current_snapshot = snaps_found[-1]

            self.vbox = None
            self.mgr = None

            try: set_obs_scene(_get_current_os_live_scene()) 
            except Exception: pass
                
            global app_instance
            app_instance = self
            load_realpc_config(); load_vbox_config(); load_event_log(); load_permissions_config(); load_sound_config()
            load_scheduler_config(); load_os_voting_config(); load_user_mgmt(); load_multi_stream_config()
            load_appearance_config(); load_obs_config(); load_music_config(); load_soundboard_config()
            load_log_broadcast_config()
            load_video_config()
            log_startup_diagnostics()
            check_tts_backend_available()

            self.build_unified_dashboard()
            if music_config.get("enabled"): start_music_player()
            if video_config.get("enabled"): start_video_player()
            self.start_terminal_thread()
            self.start_app_threads()
            if self.twenty_four_seven_mode and self.active_url: self.go_live()
            self.root.after(refresh_rate, self.process_ui_queue)
        except Exception as e:
            err_msg = f"[err] RAW FAULT: {type(e).__name__}: {e}"
            print(err_msg + f"\n{traceback.format_exc()}")
            try: messagebox.showerror("error", err_msg)
            except: pass

    def load_settings(self):
        all_vms = get_all_vbox_vms(vbox_manage_cmd)
        # Smart First-Time Boot Fallback (Only used if JSON doesn't exist yet)
        fallback_vm = all_vms[instance_id - 1] if (all_vms and len(all_vms) >= instance_id) else (all_vms[0] if all_vms else "Windows10ChatVm")
        
        default_config = {
            "youtube_url": "", "vm_name": fallback_vm, "vbox_path": vbox_manage_cmd, "auto_start": False,
            "enable_chat": True, "strict_live_check": True, "keyboard_layout": "US", "command_prefix": "!",
            "stats_interval": 15, "typing_speed": 0.015, "key_delay": 0.015, "mouse_delay": 0.005,
            "max_wait_time": 20.0, "enable_starting_scene": True, "app_name": "YT2VM", "ultra_speed": False, 
            "enable_ocr": False, "custom_commands": {}
        }
        
        # Hard load isolated settings for this specific multi-stream
        if os.path.exists(settings_file):
            try:
                with open(settings_file, "r") as f: 
                    saved_data = json.load(f)
                    default_config.update(saved_data)
            except Exception: pass
            
        return default_config

    def save_settings(self):
        try:
            tmp_file = settings_file + ".tmp"
            with open(tmp_file, "w") as f: json.dump(self.config, f, indent=4)
            os.replace(tmp_file, settings_file)
        except Exception: pass

    def _async_cmd_runner(self, action_chain):
        try:
            if 'pythoncom' in sys.modules: pythoncom.CoInitialize()
        except: pass
        
        for action in action_chain:
            if getattr(self, 'cancel_macros', False): break
            cmd_type, arg, user = action
            if cmd_type == "wait":
                try:
                    w_time = min(float(arg), 3600.0)
                    if w_time > 0: time.sleep(w_time)
                except Exception: pass
            else:
                self.run_cmd_worker(action)
                
        try:
            if 'pythoncom' in sys.modules: pythoncom.CoUninitialize()
        except: pass

    def trigger_command(self, action_tuple):
        threading.Thread(target=self._async_cmd_runner, args=([action_tuple],), daemon=True).start()

    def trigger_command_chain(self, action_chain):
        threading.Thread(target=self._async_cmd_runner, args=(action_chain,), daemon=True).start()

    def clear_commands(self):
        self.cancel_macros = True
        self.root.after(2000, lambda: setattr(self, 'cancel_macros', False))

    def on_closing(self):
        self.running = False
        save_stats()
        try: stop_music_player()
        except Exception: pass
        try: stop_realpc_bot()
        except Exception: pass
        try: vnc_disconnect()
        except Exception: pass
        try: stop_tray_icon()
        except Exception: pass
        self.root.update()
        time.sleep(0.2)
        os._exit(0)

    def start_terminal_thread(self):
        def listen_terminal():
            while self.running:
                try:
                    cmd = sys.stdin.readline().strip()
                    if cmd:
                        if not cmd.startswith(self.command_prefix) and not cmd.startswith("!"):
                            cmd = self.command_prefix + cmd
                        elif cmd.startswith("!") and not cmd.startswith(self.command_prefix):
                            cmd = self.command_prefix + cmd[1:]
                        self.root.after(0, self._handle_terminal_cmd, cmd)
                except Exception:
                    time.sleep(1)
        t = threading.Thread(target=listen_terminal, daemon=True)
        t.start()

    def _handle_terminal_cmd(self, cmd):
        self.log("[console]", cmd, "user", is_mod=True, is_owner=True)
        self.parse_command(cmd, "[console]", is_mod=True, is_owner=True)

    def extract_all_msgs(self):
        try:
            if not os.path.exists(allmsglogs_file):
                messagebox.showinfo("extract", "no messages logged yet.")
                return
            save_path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile="extracted_messages.txt", title="save extracted messages", filetypes=[("text files", "*.txt")])
            if not save_path: return
            count = 0
            with open(save_path, "w", encoding="utf-8") as out_f:
                with open(allmsglogs_file, "r", encoding="utf-8") as in_f:
                    for line in in_f:
                        line = line.strip()
                        if not line or line in ["[", "]"]: continue
                        try:
                            entry = json.loads(line.rstrip(","))
                            out_f.write(f"[{entry.get('time', '')}] {entry.get('username', '')}: {entry.get('message', '')}\n")
                            count += 1
                        except: pass
            self.log("[system]", f"extracted {count} messages to {save_path}", "sysmsg")
            messagebox.showinfo("success", f"extracted {count} messages!")
        except Exception as e: self.log("[system]", f"[err] extract failed: {e}", "err")

    def spawn_multistream(self, suffix_id=""):
        try:
            self.log("[system]", f"[info] spawning multi-stream instance {suffix_id}...", "sysmsg")
            script_path = os.path.abspath(sys.argv[0])
            base_dir, base_name = os.path.dirname(script_path), os.path.basename(script_path)
            name, ext = os.path.splitext(base_name)
            multi_script_path = os.path.join(base_dir, f"{name}_multi{suffix_id}{ext}")
            try:
                shutil.copyfile(script_path, multi_script_path)
            except Exception as e:
                self.log("[system]", f"[err] failed to copy script: {e}. using original.", "err")
                multi_script_path = script_path
            args = [sys.executable, multi_script_path, f"--multistream{suffix_id}"]
            if platform.system() == "Windows": subprocess.Popen(args, creationflags=0x00000010, close_fds=True)
            else: subprocess.Popen(args, start_new_session=True, close_fds=True)
            self.log("[system]", f"[info] successfully spawned instance {suffix_id}!", "sysmsg")
        except Exception as e:
            err_msg = f"[err] spawn_multistream crashed: {e}"
            console_log("ERROR", err_msg + f"\n{traceback.format_exc()}")
            self.log("[system]", err_msg, "err")
            messagebox.showerror("error", err_msg)

    def _setup_right_click_menus(self):
        """Adds a Cut/Copy/Paste/Select All right-click context menu to EVERY Entry, Text,
        and Combobox widget in the app -- tkinter/ttk give you none of this out of the box.
        Bound once at the CLASS level (not per-widget), so it automatically covers every
        such widget across all ~18 tabs, including ones built after this runs."""
        self._rclick_menu = tk.Menu(self.root, tearoff=0, bg="#18181B", fg="white",
                                    activebackground=self.accent_main, activeforeground="white", bd=0)
        self._rclick_menu.add_command(label="Cut", command=lambda: self._rclick_action("cut"))
        self._rclick_menu.add_command(label="Copy", command=lambda: self._rclick_action("copy"))
        self._rclick_menu.add_command(label="Paste", command=lambda: self._rclick_action("paste"))
        self._rclick_menu.add_separator()
        self._rclick_menu.add_command(label="Select All", command=lambda: self._rclick_action("selectall"))
        self._rclick_target = None

        def _show_menu(event):
            self._rclick_target = event.widget
            try:
                if not str(event.widget).startswith('.'):  # sanity check it's a real widget
                    return
                event.widget.focus_set()
            except Exception:
                pass
            try:
                self._rclick_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self._rclick_menu.grab_release()

        for cls in ("Entry", "TEntry", "TCombobox", "Text"):
            self.root.bind_class(cls, "<Button-3>", _show_menu)

    def _rclick_action(self, action):
        w = self._rclick_target
        if w is None: return
        try:
            is_text_widget = isinstance(w, tk.Text)
            if action == "cut":
                if is_text_widget: w.event_generate("<<Cut>>")
                else: w.event_generate("<<Cut>>")
            elif action == "copy":
                w.event_generate("<<Copy>>")
            elif action == "paste":
                w.event_generate("<<Paste>>")
            elif action == "selectall":
                if is_text_widget:
                    w.tag_add("sel", "1.0", "end")
                else:
                    w.selection_range(0, "end")
        except Exception:
            pass

    def _setup_tab_paging(self):
        """ALL tabs are always visible in the tab strip -- nothing gets hidden. Mousewheel
        over the tab bar (or title bar) still lets you quickly cycle through tabs one at a
        time as a convenience, same as Ctrl-Tab/Ctrl-Shift-Tab, but it only SELECTS a tab,
        it never hides any of the others from the strip."""
        self._all_tab_ids = list(self.tabview.tabs())
        for tid in self._all_tab_ids:
            self.tabview.add(tid)  # make sure every tab is shown

        def _cycle(delta):
            try:
                total = self.tabview.index("end")
                if total <= 0: return
                cur = self.tabview.index("current")
                self.tabview.select((cur + delta) % total)
            except Exception:
                pass

        def _wheel_cycle(event):
            _cycle(-1 if event.delta > 0 else 1)

        self.tabview.bind("<MouseWheel>", _wheel_cycle)
        self._title_bar_ref.bind("<MouseWheel>", _wheel_cycle)
        self.root.bind("<Control-Tab>", lambda e: _cycle(1))
        self.root.bind("<Control-Shift-Tab>", lambda e: _cycle(-1))

    def _make_tab_scrollable(self, tab_frame):
        """Wraps a tab's content area in a vertical-scrolling Canvas with the scrollbar on
        the far right. Returns the frame to build the tab's actual content into -- pack
        widgets into the RETURNED frame exactly like you would into the tab directly."""
        canvas = tk.Canvas(tab_frame, bg="#09090B", highlightthickness=0)
        vbar = ttk.Scrollbar(tab_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        vbar.pack(side="right", fill="y")
        inner = tk.Frame(canvas, bg="#09090B")
        inner_window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.bind("<Configure>", lambda e: (canvas.itemconfigure(inner_window, width=e.width),
                                              canvas.configure(scrollregion=canvas.bbox("all"))))
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        def _wheel(e): canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _wheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        return inner

    def build_unified_dashboard(self):
        try:
            title_bar = tk.Frame(self.root, bg="#18181B", height=44)
            title_bar.pack(fill="x", side="top")
            title_bar.pack_propagate(False)
            tk.Label(title_bar, text="🤖  ChatPlays Control Panel (VBox)",
                     bg="#18181B", fg="#F4F4F5",
                     font=("Segoe UI", 12, "bold")).pack(side="left", padx=14, pady=8)
            tk.Button(title_bar, text="❓ Help", font=("Segoe UI", 9, "bold"),
                      bg="#27272A", fg="white", activebackground="#3F3F46",
                      activeforeground="white", bd=0, cursor="hand2",
                      command=lambda: self.show_welcome_guide(force=True)
                      ).pack(side="right", padx=12, pady=7, ipady=3, ipadx=10)

            # ── Tab bar wrapper -- paging + hover-scrollbar set up after all tabs below
            #    are registered, since it needs the full tab list (see _setup_tab_paging). ──
            nb_outer = tk.Frame(self.root, bg="#09090B")
            nb_outer.pack(fill="both", expand=True, padx=10, pady=(10, 10))

            self.tabview = ttk.Notebook(nb_outer, style="TNotebook")
            self.tabview.pack(fill="both", expand=True)
            self._nb_outer = nb_outer
            self._title_bar_ref = title_bar

            self.tab_dash = ttk.Frame(self.tabview, style="TFrame")
            self.tab_vbox = ttk.Frame(self.tabview, style="TFrame")
            self.tab_cmds = ttk.Frame(self.tabview, style="TFrame")
            self.tab_sett = ttk.Frame(self.tabview, style="TFrame")
            self.tab_extra = ttk.Frame(self.tabview, style="TFrame")
            self.tab_osvote = ttk.Frame(self.tabview, style="TFrame")
            self.tab_realpc = ttk.Frame(self.tabview, style="TFrame")
            self.tab_vmware = ttk.Frame(self.tabview, style="TFrame")
            self.tab_automation = ttk.Frame(self.tabview, style="TFrame")
            self.tab_eventlog = ttk.Frame(self.tabview, style="TFrame")
            self.tab_appearance = ttk.Frame(self.tabview, style="TFrame")
            self.tab_obs = ttk.Frame(self.tabview, style="TFrame")
            self.tab_music = ttk.Frame(self.tabview, style="TFrame")
            self.tab_video = ttk.Frame(self.tabview, style="TFrame")
            self.tab_soundboard = ttk.Frame(self.tabview, style="TFrame")
            self.tab_stats = ttk.Frame(self.tabview, style="TFrame")
            self.tab_permissions = ttk.Frame(self.tabview, style="TFrame")
            self.tab_users = ttk.Frame(self.tabview, style="TFrame")
            self.tabview.add(self.tab_dash, text="  Dashboard  ")
            self.tabview.add(self.tab_vbox, text="  VM Config  ")
            self.tabview.add(self.tab_cmds, text="  Commands  ")
            self.tabview.add(self.tab_sett, text="  Settings  ")
            self.tabview.add(self.tab_extra, text="  Extra Things  ")
            self.tabview.add(self.tab_osvote, text="  OS Voting  ")
            self.tabview.add(self.tab_realpc, text="  Real PC  ")
            self.tabview.add(self.tab_vmware, text="  VM Backends  ")
            self.tabview.add(self.tab_automation, text="  Automation  ")
            self.tabview.add(self.tab_eventlog, text="  Event Log  ")
            self.tabview.add(self.tab_appearance, text="  Appearance  ")
            self.tabview.add(self.tab_obs, text="  OBS  ")
            self.tabview.add(self.tab_music, text="  Music  ")
            self.tabview.add(self.tab_video, text="  Video  ")
            self.tabview.add(self.tab_soundboard, text="  Soundboard  ")
            self.tabview.add(self.tab_stats, text="  Stats  ")
            self.tabview.add(self.tab_permissions, text="  Permissions  ")
            self.tabview.add(self.tab_users, text="  Users  ")

            self._setup_tab_paging()
            dash_left = ttk.Frame(self.tab_dash, style="TFrame", width=380)
            dash_left.pack(side="left", fill="both", expand=False, padx=20, pady=20)
            dash_right = ttk.Frame(self.tab_dash, style="TFrame")
            dash_right.pack(side="right", fill="both", expand=True, padx=(0, 20), pady=20)
            def create_card(parent, title):
                border = tk.Frame(parent, bg="#27272A", bd=0)
                border.pack(fill="x", pady=(0, 20))
                card = tk.Frame(border, bg="#18181B", bd=0)
                card.pack(fill="both", expand=True, padx=1, pady=1)
                tk.Label(card, text=title, bg="#18181B", fg="#A1A1AA", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15, pady=(15, 5))
                return card
            conn_card = create_card(dash_left, "YOUTUBE STREAM LINK")
            self.entry_url = tk.Entry(conn_card, font=("Consolas", 12), bg="#09090B", fg="#F4F4F5", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A", highlightcolor=self.accent_main, justify="center")
            self.entry_url.pack(fill="x", padx=15, pady=(5, 15), ipady=8)
            self.entry_url.insert(0, self.config.get("youtube_url", "@yourchannel"))
            conn_btn_row = tk.Frame(conn_card, bg="#18181B")
            conn_btn_row.pack(fill="x", padx=15, pady=(0, 15))
            self.btn_connect = tk.Button(conn_btn_row, text="Connect Chat", font=("Segoe UI", 10, "bold"), bg=self.accent_main, fg="black", activebackground=self.accent_hover, activeforeground="black", bd=0, cursor="hand2", command=self.go_live)
            self.btn_connect.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 6))
            self.btn_disconnect = tk.Button(conn_btn_row, text="Disconnect Chat", font=("Segoe UI", 10, "bold"), bg="#EF4444", fg="white", activebackground="#DC2626", activeforeground="white", bd=0, cursor="hand2", command=self.disconnect_chat)
            self.btn_disconnect.pack(side="left", fill="x", expand=True, ipady=6)
            status_card = create_card(dash_left, "SYSTEM STATUS")
            self.lbl_status = tk.Label(status_card, text="BOOTING...", font=("Segoe UI", 16, "bold"), bg="#18181B", fg="#10B981")
            self.lbl_status.pack(anchor="w", padx=15, pady=(0, 5))
            
            target_str = vm_name
            vm_target_frame = tk.Frame(status_card, bg="#18181B")
            vm_target_frame.pack(fill="x", padx=15, pady=(5, 15))
            self.btn_vm = tk.Button(vm_target_frame, text=f"target: {target_str}", font=("Segoe UI", 9, "bold"), bg="#27272A", fg="white", activebackground="#3F3F46", activeforeground="white", bd=0, cursor="hand2", command=self.cycle_vm)
            self.btn_vm.pack(fill="x", ipady=5)
            self.lbl_vm_voting_warning = tk.Label(vm_target_frame, text="OS Voting is enabled, this is ignored", font=("Segoe UI", 8, "bold"), bg="#F59E0B", fg="#000000")
            self.refresh_vm_target_display()
            stats_card = create_card(dash_left, "LIVE STATS")
            stat_grid = tk.Frame(stats_card, bg="#18181B")
            stat_grid.pack(fill="x", padx=15, pady=(0, 15))
            stat_grid.columnconfigure(1, weight=1)
            tk.Label(stat_grid, text="Uptime", bg="#18181B", fg="#D4D4D8", font=("Segoe UI", 11)).grid(row=0, column=0, sticky="w", pady=4)
            self.lbl_uptime_val = tk.Label(stat_grid, text="0h 0m 0s", bg="#18181B", fg="#FFFFFF", font=("Consolas", 12, "bold"))
            self.lbl_uptime_val.grid(row=0, column=1, sticky="e", pady=4)
            tk.Label(stat_grid, text="Commands Run", bg="#18181B", fg="#D4D4D8", font=("Segoe UI", 11)).grid(row=1, column=0, sticky="w", pady=4)
            self.lbl_cmds_val = tk.Label(stat_grid, text="0 (0 Failed)", bg="#18181B", fg="#FFFFFF", font=("Consolas", 12, "bold"))
            self.lbl_cmds_val.grid(row=1, column=1, sticky="e", pady=4)
            tk.Label(stat_grid, text="Viewers", bg="#18181B", fg="#D4D4D8", font=("Segoe UI", 11)).grid(row=2, column=0, sticky="w", pady=4)
            self.lbl_viewers_val = tk.Label(stat_grid, text="0", bg="#18181B", fg=self.accent_main, font=("Consolas", 12, "bold"))
            self.lbl_viewers_val.grid(row=2, column=1, sticky="e", pady=4)
            tk.Label(stat_grid, text="Likes", bg="#18181B", fg="#D4D4D8", font=("Segoe UI", 11)).grid(row=3, column=0, sticky="w", pady=4)
            self.lbl_likes_val = tk.Label(stat_grid, text="0", bg="#18181B", fg="#10B981", font=("Consolas", 12, "bold"))
            self.lbl_likes_val.grid(row=3, column=1, sticky="e", pady=4)
            actions_card = create_card(dash_left, "SYSTEM CONTROLS")
            def quick_cmd(c, a=""): self.trigger_command((c, a, "[console]"))
            actions_scroll_wrap = tk.Frame(actions_card, bg="#18181B")
            actions_scroll_wrap.pack(fill="both", expand=True, padx=10, pady=(0, 15))
            actions_canvas = tk.Canvas(actions_scroll_wrap, bg="#18181B", highlightthickness=0, height=260)
            actions_scrollbar = ttk.Scrollbar(actions_scroll_wrap, orient="vertical", command=actions_canvas.yview)
            btn_grid = tk.Frame(actions_canvas, bg="#18181B")
            btn_grid_window = actions_canvas.create_window((0, 0), window=btn_grid, anchor="nw")
            btn_grid.bind("<Configure>", lambda e: actions_canvas.configure(scrollregion=actions_canvas.bbox("all")))
            actions_canvas.bind("<Configure>", lambda e: actions_canvas.itemconfigure(btn_grid_window, width=e.width))
            actions_canvas.configure(yscrollcommand=actions_scrollbar.set)
            actions_canvas.pack(side="left", fill="both", expand=True)
            actions_scrollbar.pack(side="right", fill="y")
            def _actions_mousewheel(e): actions_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            actions_canvas.bind("<Enter>", lambda e: actions_canvas.bind_all("<MouseWheel>", _actions_mousewheel))
            actions_canvas.bind("<Leave>", lambda e: actions_canvas.unbind_all("<MouseWheel>"))
            btn_grid.columnconfigure(0, weight=1)
            btn_grid.columnconfigure(1, weight=1)
            tk.Button(btn_grid, text="Start VM", font=("Segoe UI", 10, "bold"), bg="#27272A", fg="white", activebackground="#3F3F46", activeforeground="white", bd=0, cursor="hand2", command=lambda: quick_cmd("startvm")).grid(row=0, column=0, padx=5, pady=5, sticky="we", ipady=5)
            tk.Button(btn_grid, text="Restart", font=("Segoe UI", 10, "bold"), bg="#27272A", fg="white", activebackground="#3F3F46", activeforeground="white", bd=0, cursor="hand2", command=lambda: quick_cmd("restartvm")).grid(row=0, column=1, padx=5, pady=5, sticky="we", ipady=5)
            tk.Button(btn_grid, text="Shutdown", font=("Segoe UI", 10, "bold"), bg="#27272A", fg="white", activebackground="#3F3F46", activeforeground="white", bd=0, cursor="hand2", command=lambda: quick_cmd("shutdown")).grid(row=1, column=0, padx=5, pady=5, sticky="we", ipady=5)
            tk.Button(btn_grid, text="Revert VM", font=("Segoe UI", 10, "bold"), bg="#EF4444", fg="white", activebackground="#DC2626", activeforeground="white", bd=0, cursor="hand2", command=lambda: quick_cmd("revert")).grid(row=1, column=1, padx=5, pady=5, sticky="we", ipady=5)
            tk.Button(btn_grid, text="Rebuild COM", font=("Segoe UI", 10, "bold"), bg="#3B82F6", fg="white", activebackground="#2563EB", activeforeground="white", bd=0, cursor="hand2", command=lambda: setattr(self, 'force_session_refresh', True)).grid(row=2, column=0, padx=5, pady=5, sticky="we", ipady=5)
            tk.Button(btn_grid, text="Extract All Msgs", font=("Segoe UI", 10, "bold"), bg="#8B5CF6", fg="white", activebackground="#7C3AED", activeforeground="white", bd=0, cursor="hand2", command=self.extract_all_msgs).grid(row=2, column=1, padx=5, pady=5, sticky="we", ipady=5)
            tk.Button(btn_grid, text="Pause VM", font=("Segoe UI", 10, "bold"), bg="#27272A", fg="white", activebackground="#3F3F46", activeforeground="white", bd=0, cursor="hand2", command=lambda: quick_cmd("pausevm")).grid(row=3, column=0, padx=5, pady=5, sticky="we", ipady=5)
            tk.Button(btn_grid, text="Resume VM", font=("Segoe UI", 10, "bold"), bg="#27272A", fg="white", activebackground="#3F3F46", activeforeground="white", bd=0, cursor="hand2", command=lambda: quick_cmd("resumevm")).grid(row=3, column=1, padx=5, pady=5, sticky="we", ipady=5)
            tk.Button(btn_grid, text="Quick Snapshot", font=("Segoe UI", 10, "bold"), bg="#F59E0B", fg="black", activebackground="#D97706", activeforeground="black", bd=0, cursor="hand2", command=lambda: quick_cmd("makesnapshot", time.strftime("Quick_%Y%m%d_%H%M%S"))).grid(row=4, column=0, padx=5, pady=5, sticky="we", ipady=5)
            tk.Button(btn_grid, text="Toggle Pause Chat", font=("Segoe UI", 10, "bold"), bg="#F59E0B", fg="black", activebackground="#D97706", activeforeground="black", bd=0, cursor="hand2", command=lambda: setattr(self, 'chat_paused', not self.chat_paused)).grid(row=4, column=1, padx=5, pady=5, sticky="we", ipady=5)
            tk.Button(btn_grid, text="🔄 Restart Bot", font=("Segoe UI", 10, "bold"), bg="#3B82F6", fg="white", activebackground="#2563EB", activeforeground="white", bd=0, cursor="hand2", command=self._on_restart_bot_clicked).grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky="we", ipady=5)
            tk.Button(btn_grid, text="Discard VM State", font=("Segoe UI", 10, "bold"), bg="#DC2626", fg="white", activebackground="#B91C1C", activeforeground="white", bd=0, cursor="hand2", command=lambda: self.discard_vmware_state("[console]")).grid(row=6, column=0, columnspan=2, padx=5, pady=5, sticky="we", ipady=5)
            tk.Button(btn_grid, text="Cancel Command Queue", font=("Segoe UI", 10, "bold"), bg="#EF4444", fg="white", activebackground="#DC2626", activeforeground="white", bd=0, cursor="hand2", command=self.cancel_command_queue).grid(row=7, column=0, columnspan=2, padx=5, pady=5, sticky="we", ipady=5)
            self.btn_vm_control_toggle = tk.Button(btn_grid, font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2", command=lambda: self.toggle_vm_control())
            self.btn_vm_control_toggle.grid(row=7, column=0, columnspan=2, padx=5, pady=5, sticky="we", ipady=5)
            self._refresh_vm_control_btn()
            ttk.Label(dash_right, text="Live Output Console", style="Header.TLabel").pack(anchor="w", pady=(0, 10))
            console_border = tk.Frame(dash_right, bg="#27272A", bd=0)
            console_border.pack(fill="both", expand=True)
            console_inner = tk.Frame(console_border, bg="#09090B", bd=0)
            console_inner.pack(fill="both", expand=True, padx=1, pady=1)
            self.console_text = scrolledtext.ScrolledText(console_inner, font=("Consolas", 11), bg="#09090B", fg="#D4D4D8", bd=0, highlightthickness=0, insertbackground="white", padx=15, pady=15)
            self.console_text.pack(fill="both", expand=True)
            self.console_text.configure(state='disabled')
            self.console_text.tag_config("SYSTEM", foreground="#10B981", font=("Consolas", 11, "bold"))
            self.console_text.tag_config("ERROR", foreground="#EF4444", font=("Consolas", 11, "bold"))
            self.console_text.tag_config("EXEC", foreground="#A78BFA")
            self.console_text.tag_config("CHAT", foreground="#A1A1AA")
            cmd_frame = tk.Frame(dash_right, bg="#09090B")
            cmd_frame.pack(fill="x", pady=(20, 0))
            tk.Label(cmd_frame, text=">_", font=("Consolas", 18, "bold"), fg=self.accent_main, bg="#09090B").pack(side="left", padx=(0, 15))
            self.entry_cmd = tk.Entry(cmd_frame, font=("Consolas", 14), bg="#18181B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A", highlightcolor=self.accent_main)
            self.entry_cmd.pack(side="left", fill="x", expand=True, ipady=8)
            self.entry_cmd.bind("<Return>", self.on_manual_cmd)
            tk.Button(cmd_frame, text="Execute", font=("Segoe UI", 11, "bold"), bg=self.accent_main, fg="black", activebackground=self.accent_hover, activeforeground="black", bd=0, cursor="hand2", command=self.on_manual_cmd).pack(side="right", padx=(15, 0), ipady=6, ipadx=20)
            
            self.entry_cmd.focus_set()
            
            vbox_wrapper = tk.Frame(self.tab_vbox, bg="#09090B")
            vbox_wrapper.pack(fill="both", expand=True)
            vbox_canvas = tk.Canvas(vbox_wrapper, bg="#09090B", highlightthickness=0)
            vbox_scrollbar = ttk.Scrollbar(vbox_wrapper, orient="vertical", command=vbox_canvas.yview)
            vbox_card_border = tk.Frame(vbox_canvas, bg="#27272A")
            vbox_border_window = vbox_canvas.create_window((0, 0), window=vbox_card_border, anchor="nw")
            vbox_card_border.bind("<Configure>", lambda e: vbox_canvas.configure(scrollregion=vbox_canvas.bbox("all")))
            vbox_canvas.bind("<Configure>", lambda e: vbox_canvas.itemconfigure(vbox_border_window, width=e.width))
            vbox_canvas.configure(yscrollcommand=vbox_scrollbar.set)
            vbox_canvas.pack(side="left", fill="both", expand=True, padx=(40, 0), pady=40)
            vbox_scrollbar.pack(side="right", fill="y")
            def _vbox_mousewheel(e): vbox_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            vbox_canvas.bind("<Enter>", lambda e: vbox_canvas.bind_all("<MouseWheel>", _vbox_mousewheel))
            vbox_canvas.bind("<Leave>", lambda e: vbox_canvas.unbind_all("<MouseWheel>"))
            vbox_content = tk.Frame(vbox_card_border, bg="#18181B", padx=30, pady=30)

            def _vbox_apply_json(data):
                if not isinstance(data, dict): return
                if "backend" in data:
                    self.var_vm_backend.set(data.get("backend", "vbox"))
                    self._on_backend_changed()
                if "path" in data:
                    self.entry_vbox_new.delete(0, "end"); self.entry_vbox_new.insert(0, data.get("path", ""))
                if "vm_target" in data:
                    self.cb_vm_new.set(data.get("vm_target", ""))
                if "snapshot" in data:
                    self.cb_snap_vbox.set(data.get("snapshot", ""))
                self.save_vbox_settings()

            vbox_content.pack(fill="both", expand=True, padx=1, pady=1)

            tk.Label(vbox_content, text="Backend", font=("Segoe UI", 11, "bold"), bg="#18181B", fg="#D4D4D8").grid(row=0, column=0, sticky="e", pady=15, padx=(0, 20))
            backend_frame = tk.Frame(vbox_content, bg="#18181B")
            backend_frame.grid(row=0, column=1, sticky="w", pady=15)
            self.var_vm_backend = tk.StringVar(value=self.config.get("vm_backend", "vbox"))
            tk.Radiobutton(backend_frame, text="VirtualBox", variable=self.var_vm_backend, value="vbox",
                           bg="#18181B", fg="white", selectcolor="#09090B", activebackground="#18181B",
                           activeforeground="white", font=("Segoe UI", 10, "bold"),
                           command=lambda: self._on_backend_changed()).pack(side="left", padx=(0, 20))
            tk.Radiobutton(backend_frame, text="VMware", variable=self.var_vm_backend, value="vmware",
                           bg="#18181B", fg="white", selectcolor="#09090B", activebackground="#18181B",
                           activeforeground="white", font=("Segoe UI", 10, "bold"),
                           command=lambda: self._on_backend_changed()).pack(side="left")

            self.lbl_vbox_path = tk.Label(vbox_content, text="VBoxManage Path", font=("Segoe UI", 11, "bold"), bg="#18181B", fg="#D4D4D8")
            self.lbl_vbox_path.grid(row=1, column=0, sticky="e", pady=15, padx=(0, 20))
            path_frame = tk.Frame(vbox_content, bg="#18181B")
            path_frame.grid(row=1, column=1, sticky="w", pady=15)
            self.entry_vbox_new = tk.Entry(path_frame, width=50, font=("Consolas", 11), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A", highlightcolor=self.accent_main)
            self.entry_vbox_new.pack(side="left", ipady=7, padx=(0, 10))
            self.entry_vbox_new.insert(0, self.config.get("vbox_path", vbox_manage_cmd) if self.var_vm_backend.get() == "vbox" else self.config.get("vmrun_path", vmrun_cmd))
            tk.Button(path_frame, text="Browse", font=("Segoe UI", 10, "bold"), bg="#27272A", fg="white", activebackground="#3F3F46", activeforeground="white", bd=0, cursor="hand2", command=lambda: self.browse_file(self.entry_vbox_new)).pack(side="left", ipady=5, ipadx=15)
            
            self.lbl_vbox_target = tk.Label(vbox_content, text="Target VM Name", font=("Segoe UI", 11, "bold"), bg="#18181B", fg="#D4D4D8")
            self.lbl_vbox_target.grid(row=2, column=0, sticky="e", pady=15, padx=(0, 20))
            vm_frame = tk.Frame(vbox_content, bg="#18181B")
            vm_frame.grid(row=2, column=1, sticky="w", pady=15)
            self.cb_vm_new = ttk.Combobox(vm_frame, width=45, state="readonly", font=("Segoe UI", 11))
            self.cb_vm_new.pack(side="left", padx=(0, 10))
            self.btn_vbox_refresh_or_browse = tk.Button(vm_frame, text="Refresh", font=("Segoe UI", 10, "bold"), bg="#27272A", fg="white", activebackground="#3F3F46", activeforeground="white", bd=0, cursor="hand2", command=self.refresh_vbox_vms)
            self.btn_vbox_refresh_or_browse.pack(side="left", ipady=5, ipadx=15)

            tk.Label(vbox_content, text="Target Snapshot", font=("Segoe UI", 11, "bold"), bg="#18181B", fg="#D4D4D8").grid(row=3, column=0, sticky="e", pady=15, padx=(0, 20))
            snap_frame_vb = tk.Frame(vbox_content, bg="#18181B")
            snap_frame_vb.grid(row=3, column=1, sticky="w", pady=15)
            self.cb_snap_vbox = ttk.Combobox(snap_frame_vb, width=45, font=("Segoe UI", 11))
            self.cb_snap_vbox.pack(side="left", padx=(0, 10))
            tk.Button(snap_frame_vb, text="Refresh", font=("Segoe UI", 10, "bold"), bg="#27272A", fg="white", activebackground="#3F3F46", activeforeground="white", bd=0, cursor="hand2", command=self.refresh_vbox_snaps).pack(side="left", ipady=5, ipadx=15)

            self.cb_vm_new.bind("<<ComboboxSelected>>", lambda e: self.refresh_vbox_snaps())
            tk.Button(vbox_content, text="Save VM Configuration", font=("Segoe UI", 11, "bold"), bg="#10B981", fg="#000000", bd=0, cursor="hand2", command=self.save_vbox_settings).grid(row=4, column=1, sticky="w", pady=30, ipady=8, ipadx=20)
            self._on_backend_changed()
            self.add_json_io_bar(vbox_card_border, None, None,
                                  lambda: {"backend": self.var_vm_backend.get(), "path": self.entry_vbox_new.get(),
                                           "vm_target": self.cb_vm_new.get(), "snapshot": self.cb_snap_vbox.get()},
                                  _vbox_apply_json, "vm_config")

            actions_box = tk.Frame(vbox_content, bg="#0F0F12", highlightthickness=1, highlightbackground="#27272A")
            actions_box.grid(row=5, column=0, columnspan=2, sticky="we", pady=(10, 0))
            tk.Label(actions_box, text="DIRECT VM ACTIONS (no vote required)", font=("Segoe UI", 10, "bold"), bg="#0F0F12", fg=self.accent_main).pack(anchor="w", padx=15, pady=(12, 8))
            def vm_action(c, a=""): self.trigger_command((c, a, "[console]"))
            def do_snapshot():
                name = _simpledialog.askstring("New Snapshot", "Snapshot name:", parent=self.root, initialvalue=time.strftime("Backup_%Y%m%d_%H%M%S"))
                if name: vm_action("makesnapshot", name)
            def do_delete_recent_snap():
                if messagebox.askyesno("Delete Recent Snapshot", "Delete the MOST RECENT snapshot for the current VM? This cannot be undone."):
                    vm_action("deletesnapshot")
            def do_taskkill():
                proc = _simpledialog.askstring("Taskkill (Guest)", "Process name to force-kill inside the VM (e.g. notepad.exe):", parent=self.root)
                if proc and proc.strip():
                    self.parse_command(f"{self.command_prefix}taskkill {proc.strip()}", "[console]", is_mod=True, is_owner=True)
            def do_acpi_shutdown():
                if messagebox.askyesno("ACPI Shutdown", "Send a graceful ACPI shutdown signal to the guest OS?"):
                    vm_action("acpishutdown")
            def do_acpi_restart():
                if messagebox.askyesno("ACPI Restart", "Send an ACPI shutdown signal, wait for the guest to power off, then boot it back up?"):
                    vm_action("acpirestart")
            actgrid = tk.Frame(actions_box, bg="#0F0F12")
            actgrid.pack(fill="x", padx=15, pady=(0, 15))
            btns = [
                ("Pause VM", "#27272A", lambda: vm_action("pausevm")),
                ("Resume VM", "#27272A", lambda: vm_action("resumevm")),
                ("Save State", "#27272A", lambda: vm_action("vmsavestate")),
                ("VM Status", "#3B82F6", lambda: vm_action("vmstatus")),
                ("New Snapshot...", "#8B5CF6", do_snapshot),
                ("Force-Fix VBox", "#EF4444", lambda: vm_action("forcefixvm")),
                ("ACPI Restart", "#F59E0B", do_acpi_restart),
                ("ACPI Shutdown", "#F59E0B", do_acpi_shutdown),
                ("Taskkill...", "#EF4444", do_taskkill),
                ("Delete Recent SNP", "#EF4444", do_delete_recent_snap),
            ]
            for i, (lbl, color, cmd) in enumerate(btns):
                tk.Button(actgrid, text=lbl, font=("Segoe UI", 10, "bold"), bg=color, fg="white", bd=0, cursor="hand2", command=cmd).grid(row=i // 3, column=i % 3, padx=6, pady=6, sticky="we", ipady=6)
            actgrid.columnconfigure(0, weight=1); actgrid.columnconfigure(1, weight=1); actgrid.columnconfigure(2, weight=1)


            self.refresh_vbox_vms()

            self.build_commands_tab()
            _sp = self._make_tab_scrollable(self.tab_sett)
            sett_wrapper = tk.Frame(_sp, bg="#09090B")
            sett_wrapper.pack(fill="both", expand=True)
            sett_card_border = tk.Frame(sett_wrapper, bg="#27272A")
            sett_card_border.pack(pady=30, padx=40, fill="both", expand=True)
            sett_content = tk.Frame(sett_card_border, bg="#18181B", padx=20, pady=20)
            sett_content.pack(fill="both", expand=True, padx=1, pady=1)

            def _sett_get_json():
                return {
                    "command_prefix": self.entry_prefix_new.get(), "keyboard_layout": self.cb_layout_new.get(),
                    "auto_start": self.var_auto_new.get(), "enable_chat": self.var_chat_new.get(),
                    "say_admin_only": self.say_admin_var.get(), "enable_starting_scene": self.var_starting_scene.get(),
                    "strict_live_check": self.var_strict_live.get(), "enable_ocr": self.var_ocr.get(),
                    "verbose_connection_logs": self.var_verbose_conn_logs.get(), "app_name": self.cb_app_name.get(),
                    "ultra_speed": self.var_ultra_speed.get(), "stats_interval": self.entry_stats_int.get(),
                    "typing_speed": self.entry_type_spd.get(), "key_delay": self.entry_key_del.get(),
                    "mouse_delay": self.entry_mouse_del.get(),
                }
            def _sett_apply_json(data):
                if not isinstance(data, dict): return
                def set_entry(entry, key):
                    if key in data:
                        entry.delete(0, "end"); entry.insert(0, str(data.get(key, "")))
                set_entry(self.entry_prefix_new, "command_prefix")
                if "keyboard_layout" in data: self.cb_layout_new.set(data["keyboard_layout"])
                if "auto_start" in data: self.var_auto_new.set(bool(data["auto_start"]))
                if "enable_chat" in data: self.var_chat_new.set(bool(data["enable_chat"]))
                if "say_admin_only" in data: self.say_admin_var.set(bool(data["say_admin_only"])); self.update_say_admin()
                if "enable_starting_scene" in data: self.var_starting_scene.set(bool(data["enable_starting_scene"]))
                if "strict_live_check" in data: self.var_strict_live.set(bool(data["strict_live_check"]))
                if "enable_ocr" in data: self.var_ocr.set(bool(data["enable_ocr"]))
                if "verbose_connection_logs" in data: self.var_verbose_conn_logs.set(bool(data["verbose_connection_logs"]))
                if "app_name" in data: self.cb_app_name.set(data["app_name"])
                if "ultra_speed" in data: self.var_ultra_speed.set(bool(data["ultra_speed"]))
                set_entry(self.entry_stats_int, "stats_interval")
                set_entry(self.entry_type_spd, "typing_speed")
                set_entry(self.entry_key_del, "key_delay")
                set_entry(self.entry_mouse_del, "mouse_delay")
                self.save_general_settings()
            sett_cols = tk.Frame(sett_content, bg="#18181B")
            sett_cols.pack(fill="both", expand=True)
            sett_left = tk.Frame(sett_cols, bg="#18181B")
            sett_left.pack(side="left", fill="both", expand=True, padx=(0, 10))
            sett_right = tk.Frame(sett_cols, bg="#18181B")
            sett_right.pack(side="right", fill="both", expand=True, padx=(10, 0))
            
            tk.Label(sett_left, text="GENERAL SETTINGS", font=("Segoe UI", 12, "bold"), bg="#18181B", fg=self.accent_main).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))
            tk.Label(sett_left, text="Command Prefix", font=("Segoe UI", 11, "bold"), bg="#18181B", fg="#D4D4D8").grid(row=1, column=0, sticky="e", pady=10, padx=(0, 20))
            self.entry_prefix_new = tk.Entry(sett_left, width=15, font=("Consolas", 13), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A", highlightcolor=self.accent_main, justify="center")
            self.entry_prefix_new.grid(row=1, column=1, sticky="w", pady=10, ipady=5)
            self.entry_prefix_new.insert(0, str(self.config.get("command_prefix", "!")))
            
            tk.Label(sett_left, text="Keyboard Layout", font=("Segoe UI", 11, "bold"), bg="#18181B", fg="#D4D4D8").grid(row=2, column=0, sticky="e", pady=10, padx=(0, 20))
            self.cb_layout_new = ttk.Combobox(sett_left, values=available_layouts, width=30, state="readonly", font=("Segoe UI", 11))
            self.cb_layout_new.grid(row=2, column=1, sticky="w", pady=10)
            if self.config.get("keyboard_layout") in available_layouts: self.cb_layout_new.set(self.config["keyboard_layout"])
            else: self.cb_layout_new.set("US")
            
            self.var_auto_new = tk.BooleanVar(value=self.config.get("auto_start", False))
            ttk.Checkbutton(sett_left, text="Auto-start VM on launch", variable=self.var_auto_new, style="Toggle.TCheckbutton").grid(row=3, column=0, columnspan=2, sticky="w", pady=6)
            
            self.var_chat_new = tk.BooleanVar(value=self.config.get("enable_chat", True))
            ttk.Checkbutton(sett_left, text="Enable chat listener", variable=self.var_chat_new, style="Toggle.TCheckbutton").grid(row=4, column=0, columnspan=2, sticky="w", pady=6)
            
            self.say_admin_var = tk.BooleanVar(value=self.say_admin_only)
            ttk.Checkbutton(sett_left, text="Require Admin for !say", variable=self.say_admin_var, command=self.update_say_admin, style="Toggle.TCheckbutton").grid(row=5, column=0, columnspan=2, sticky="w", pady=6)
            
            self.var_starting_scene = tk.BooleanVar(value=self.config.get("enable_starting_scene", True))
            ttk.Checkbutton(sett_left, text="Enable 'Starting' OBS Scene", variable=self.var_starting_scene, style="Toggle.TCheckbutton").grid(row=6, column=0, columnspan=2, sticky="w", pady=6)
            
            self.var_strict_live = tk.BooleanVar(value=self.config.get("strict_live_check", True))
            ttk.Checkbutton(sett_left, text="Strict Live Check (Only connect if currently LIVE)", variable=self.var_strict_live, style="Toggle.TCheckbutton").grid(row=7, column=0, columnspan=2, sticky="w", pady=6)
            
            self.var_ocr = tk.BooleanVar(value=self.config.get("enable_ocr", False))
            ttk.Checkbutton(sett_left, text="Auto-Restart on iPXE Screen (OCR - Needs pytesseract)", variable=self.var_ocr, style="Toggle.TCheckbutton").grid(row=8, column=0, columnspan=2, sticky="w", pady=6)

            self.var_verbose_conn_logs = tk.BooleanVar(value=self.config.get("verbose_connection_logs", False))
            ttk.Checkbutton(sett_left, text="Log OBS websocket, websocket, GUI connect/disconnect, tray minimize, and pytchat connection events", variable=self.var_verbose_conn_logs, style="Toggle.TCheckbutton").grid(row=9, column=0, columnspan=2, sticky="w", pady=6)

            tk.Label(sett_left, text="App Name", font=("Segoe UI", 11, "bold"), bg="#18181B", fg="#D4D4D8").grid(row=10, column=0, sticky="e", pady=10, padx=(0, 20))
            self.cb_app_name = ttk.Combobox(sett_left, values=["YT2VM", "c2vm", "ycpv", "ytpvm"], width=30, state="readonly", font=("Segoe UI", 11))
            self.cb_app_name.grid(row=10, column=1, sticky="w", pady=10)
            self.cb_app_name.set(self.config.get("app_name", "YT2VM"))

            tk.Label(sett_right, text="PERFORMANCE & TIMINGS", font=("Segoe UI", 12, "bold"), bg="#18181B", fg="#10B981").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))
            self.var_ultra_speed = tk.BooleanVar(value=self.config.get("ultra_speed", False))
            ttk.Checkbutton(sett_right, text="ULTRA SPEED MODE (Zero Delay)", variable=self.var_ultra_speed, style="Toggle.TCheckbutton").grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 10))
            tk.Label(sett_right, text="Stats Update Interval (s)", font=("Segoe UI", 11, "bold"), bg="#18181B", fg="#D4D4D8").grid(row=2, column=0, sticky="e", pady=10, padx=(0, 20))
            self.entry_stats_int = tk.Entry(sett_right, width=15, font=("Consolas", 12), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A", highlightcolor="#10B981", justify="center")
            self.entry_stats_int.grid(row=2, column=1, sticky="w", pady=10, ipady=5)
            self.entry_stats_int.insert(0, str(self.config.get("stats_interval", 15)))
            tk.Label(sett_right, text="Typing Speed (s)", font=("Segoe UI", 11, "bold"), bg="#18181B", fg="#D4D4D8").grid(row=3, column=0, sticky="e", pady=10, padx=(0, 20))
            self.entry_type_spd = tk.Entry(sett_right, width=15, font=("Consolas", 12), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A", highlightcolor="#10B981", justify="center")
            self.entry_type_spd.grid(row=3, column=1, sticky="w", pady=10, ipady=5)
            self.entry_type_spd.insert(0, str(self.config.get("typing_speed", 0.015)))
            tk.Label(sett_right, text="Key Press Delay (s)", font=("Segoe UI", 11, "bold"), bg="#18181B", fg="#D4D4D8").grid(row=4, column=0, sticky="e", pady=10, padx=(0, 20))
            self.entry_key_del = tk.Entry(sett_right, width=15, font=("Consolas", 12), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A", highlightcolor="#10B981", justify="center")
            self.entry_key_del.grid(row=4, column=1, sticky="w", pady=10, ipady=5)
            self.entry_key_del.insert(0, str(self.config.get("key_delay", 0.015)))
            tk.Label(sett_right, text="Mouse Click Delay (s)", font=("Segoe UI", 11, "bold"), bg="#18181B", fg="#D4D4D8").grid(row=5, column=0, sticky="e", pady=10, padx=(0, 20))
            self.entry_mouse_del = tk.Entry(sett_right, width=15, font=("Consolas", 12), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A", highlightcolor="#10B981", justify="center")
            self.entry_mouse_del.grid(row=5, column=1, sticky="w", pady=10, ipady=5)
            self.entry_mouse_del.insert(0, str(self.config.get("mouse_delay", 0.005)))
            btn_save_frame = tk.Frame(sett_content, bg="#18181B")
            btn_save_frame.pack(fill="x", pady=(20, 0))
            tk.Button(btn_save_frame, text="SAVE ALL SETTINGS", font=("Segoe UI", 11, "bold"), bg=self.accent_main, fg="black", bd=0, cursor="hand2", command=self.save_general_settings).pack(ipady=8, ipadx=40)
            self.add_json_io_bar(sett_content, None, None, _sett_get_json, _sett_apply_json, "general_settings")
            self.build_extra_tab()
            self.build_osvoting_tab()
            self.build_realpc_tab()
            self.build_vmware_tab()
            self.build_automation_tab()
            self.build_eventlog_tab()
            self.build_appearance_tab()
            self.build_obs_tab()
            self.build_music_tab()
            self.build_video_tab()
            self.build_soundboard_tab()
            self.build_stats_tab()
            self.build_permissions_tab()
            self.build_users_tab()
        except Exception as e:
            self.log("[system]", f"[err] ui build error: {e}", "err")

    def browse_file(self, entry_widget, types=None):
        if types is None:
            types = [("Executable", "*.exe")] if platform.system() == "Windows" else [("All files", "*")]
        fp = filedialog.askopenfilename(filetypes=types)
        if fp:
            entry_widget.delete(0, 'end')
            entry_widget.insert(0, fp)

    def add_json_io_bar(self, parent, tab_widget, rebuild_fn, get_data_fn, apply_data_fn, filename_hint):
        """Adds a 'Save as JSON' / 'Import as JSON' button row to a panel.
        - get_data_fn() -> dict/list to export.
        - apply_data_fn(loaded_data) -> writes the imported data into the relevant config
          object(s) and persists them to disk.
        Import then tears the tab down and calls rebuild_fn() to rebuild it from scratch, so
        every field on the panel refreshes to the newly-imported values automatically.

        Also auto-imports: if "{filename_hint}.json" (the same default name 'Save as JSON'
        exports to) exists in the same folder as the script, it's loaded automatically the
        first time this panel is built -- no manual Import click needed. This only fires once
        per file per run.
        """
        if filename_hint not in _auto_imported_json_hints:
            _auto_imported_json_hints.add(filename_hint)
            auto_path = os.path.join(script_dir(), f"{filename_hint}.json")
            if os.path.exists(auto_path):
                try:
                    with open(auto_path, "r", encoding="utf-8") as f:
                        auto_data = json.load(f)
                    apply_data_fn(auto_data)
                    self.log("[system]", f"[info] auto-imported {filename_hint}.json from the bot's folder.", "sysmsg")
                except Exception as e:
                    self.log("[system]", f"[err] auto-import of {filename_hint}.json failed: {e}", "err")
        try:
            bar_bg = parent.cget("bg")
        except Exception:
            bar_bg = "#09090B"
        bar = tk.Frame(parent, bg=bar_bg)
        bar.pack(fill="x", pady=(0, 12))

        def do_save():
            try:
                data = get_data_fn()
                path = filedialog.asksaveasfilename(defaultextension=".json", initialfile=f"{filename_hint}.json",
                                                     filetypes=[("JSON files", "*.json")], title=f"Save {filename_hint} as JSON")
                if not path: return
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                self.log("[system]", f"[info] saved {filename_hint} -> {path}", "sysmsg")
            except Exception as e:
                self.log("[system]", f"[err] save as json failed: {e}", "err")

        def do_import():
            try:
                path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")], title=f"Import {filename_hint} from JSON")
                if not path: return
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                apply_data_fn(data)
                if tab_widget is not None and rebuild_fn is not None:
                    for w in tab_widget.winfo_children(): w.destroy()
                    rebuild_fn()
                self.log("[system]", f"[info] imported {filename_hint} <- {path}", "sysmsg")
            except Exception as e:
                self.log("[system]", f"[err] import json failed: {e}", "err")

        tk.Button(bar, text="💾 Save as JSON", font=("Segoe UI", 9, "bold"), bg="#27272A", fg="white", bd=0, cursor="hand2",
                  command=do_save).pack(side="left", ipady=5, ipadx=12, padx=(0, 6))
        tk.Button(bar, text="📥 Import as JSON", font=("Segoe UI", 9, "bold"), bg="#27272A", fg="white", bd=0, cursor="hand2",
                  command=do_import).pack(side="left", ipady=5, ipadx=12)
        return bar

    def _on_logbroadcast_enabled_changed(self):
        """When log broadcast is OFF, the VM dropdown gets grayed out and a yellow warning
        takes over its description, since picking a VM there does nothing while disabled.
        When ON, the warning disappears and the dropdown is usable again."""
        enabled = self.var_logbroadcast_enabled.get()
        if enabled:
            self.lbl_logbroadcast_disabled_warn.pack_forget()
            self.lbl_logbroadcast_vm_desc.pack(anchor="w")
            self.cb_logbroadcast_vm.configure(state="readonly")
        else:
            self.lbl_logbroadcast_vm_desc.pack_forget()
            self.lbl_logbroadcast_disabled_warn.pack(anchor="w", fill="x")
            self.cb_logbroadcast_vm.configure(state="disabled")

    def _on_backend_changed(self):
        """Reconfigures the VM Config panel's path/target labels and behavior for whichever
        backend (VBox/VMware) is currently selected -- called on radio button change and
        once at tab-build time."""
        backend = self.var_vm_backend.get()
        if backend == "vmware":
            self.lbl_vbox_path.configure(text="vmrun Path")
            self.lbl_vbox_target.configure(text="Target .vmx File")
            self.cb_vm_new.configure(state="readonly")
            self.btn_vbox_refresh_or_browse.configure(text="Browse", command=self._browse_vmx_and_register)
        else:
            self.lbl_vbox_path.configure(text="VBoxManage Path")
            self.lbl_vbox_target.configure(text="Target VM Name")
            self.cb_vm_new.configure(state="readonly")
            self.btn_vbox_refresh_or_browse.configure(text="Refresh", command=self.refresh_vbox_vms)
        self.refresh_vbox_vms()

    def _browse_vmx_and_register(self):
        """VMware VMs aren't auto-listable the way VBoxManage lists VBox VMs -- browse for
        a .vmx directly and register it so it shows up in the dropdown from now on."""
        path = filedialog.askopenfilename(title="Select a .vmx file", filetypes=[("VMware VM files", "*.vmx"), ("All files", "*.*")])
        if not path:
            return
        register_vmware_vm(path)
        self.refresh_vbox_vms()
        self.cb_vm_new.set(path)
        self.refresh_vbox_snaps()
        self.log("[system]", f"[info] registered VMware VM: {path}", "sysmsg")

    def refresh_vbox_vms(self):
        backend = self.var_vm_backend.get()
        path = self.entry_vbox_new.get().strip()
        if backend == "vmware":
            vms = get_all_vmware_vms(path or vmrun_cmd)
        else:
            vms = get_all_vbox_vms(path or vbox_manage_cmd)
        if vms:
            self.cb_vm_new['values'] = vms
            if self.config.get("vm_name") in vms: self.cb_vm_new.set(self.config.get("vm_name"))
            else: self.cb_vm_new.set(vms[0])
        self.refresh_vbox_snaps()

    def refresh_vbox_snaps(self):
        current_vm = self.cb_vm_new.get()
        if not current_vm: return
        backend = self.var_vm_backend.get()
        path = self.entry_vbox_new.get().strip()
        if backend == "vmware":
            snaps = get_vmware_snapshots(path or vmrun_cmd, current_vm)
        else:
            snaps = get_vbox_snapshots(path or vbox_manage_cmd, current_vm)
        self.cb_snap_vbox['values'] = snaps if snaps else [""]
        if self.current_snapshot in snaps: self.cb_snap_vbox.set(self.current_snapshot)
        elif snaps: self.cb_snap_vbox.set(snaps[-1])

    def build_extra_tab(self):
        try:
            _sp = self._make_tab_scrollable(self.tab_extra)
            extra_wrapper = tk.Frame(_sp, bg="#09090B")
            extra_wrapper.pack(fill="both", expand=True)
            extra_card_border = tk.Frame(extra_wrapper, bg="#27272A")
            extra_card_border.pack(pady=40, padx=40, fill="x")
            extra_content = tk.Frame(extra_card_border, bg="#18181B", padx=30, pady=30)
            extra_content.pack(fill="both", expand=True, padx=1, pady=1)
            tk.Label(extra_content, text="MULTI-STREAMING SETUP", font=("Segoe UI", 12, "bold"), bg="#18181B", fg=self.accent_main).pack(anchor="w", pady=(0, 5))
            def _extra_apply_json(data):
                if isinstance(data, dict):
                    multi_stream_config.clear()
                    multi_stream_config.update(data)
                    save_multi_stream_config()
            self.add_json_io_bar(extra_content, self.tab_extra, self.build_extra_tab,
                                  lambda: dict(multi_stream_config), _extra_apply_json, "multistream_config")
            tk.Label(extra_content, text="Launch secondary instances. They will automatically increment the web server ports (5001, 5002, 5003...).", font=("Segoe UI", 10), bg="#18181B", fg="#A1A1AA").pack(anchor="w", pady=(0, 20))
            if instance_id == 1:
                tk.Button(extra_content, text="Spawn Multi-Stream 1 (Port 5001)", font=("Segoe UI", 11, "bold"), bg="#8B5CF6", fg="white", activebackground="#7C3AED", activeforeground="white", bd=0, cursor="hand2", command=lambda: self.spawn_multistream("")).pack(anchor="w", ipady=8, ipadx=20, pady=5)
                tk.Button(extra_content, text="Spawn Multi-Stream 2 (Port 5002)", font=("Segoe UI", 11, "bold"), bg="#8B5CF6", fg="white", activebackground="#7C3AED", activeforeground="white", bd=0, cursor="hand2", command=lambda: self.spawn_multistream("2")).pack(anchor="w", ipady=8, ipadx=20, pady=5)
                tk.Button(extra_content, text="Spawn Multi-Stream 3 (Port 5003)", font=("Segoe UI", 11, "bold"), bg="#8B5CF6", fg="white", activebackground="#7C3AED", activeforeground="white", bd=0, cursor="hand2", command=lambda: self.spawn_multistream("3")).pack(anchor="w", ipady=8, ipadx=20, pady=5)
                tk.Button(extra_content, text="Spawn Multi-Stream 4 (Port 5004)", font=("Segoe UI", 11, "bold"), bg="#8B5CF6", fg="white", activebackground="#7C3AED", activeforeground="white", bd=0, cursor="hand2", command=lambda: self.spawn_multistream("4")).pack(anchor="w", ipady=8, ipadx=20, pady=5)
                tk.Button(extra_content, text="Spawn Multi-Stream 5 (Port 5005)", font=("Segoe UI", 11, "bold"), bg="#8B5CF6", fg="white", activebackground="#7C3AED", activeforeground="white", bd=0, cursor="hand2", command=lambda: self.spawn_multistream("5")).pack(anchor="w", ipady=8, ipadx=20, pady=5)
            else:
                tk.Label(extra_content, text=f"[active] this is currently multi-stream {instance_id-1} running on port {flask_port}.", font=("Segoe UI", 11, "bold"), bg="#18181B", fg="#8B5CF6").pack(anchor="w", pady=10)

            tk.Label(extra_content, text="MULTI-STREAM VIDEO IDS", font=("Segoe UI", 12, "bold"), bg="#18181B", fg="#10B981").pack(anchor="w", pady=(25, 5))
            tk.Label(extra_content, text="Optional pool of additional YouTube video IDs the bot can rotate/monitor for multi-stream setups.", font=("Segoe UI", 10), bg="#18181B", fg="#A1A1AA").pack(anchor="w", pady=(0, 10))
            ms_list_frame = tk.Frame(extra_content, bg="#27272A", bd=1)
            ms_list_frame.pack(fill="x", pady=(0, 8))
            self.ms_video_listbox = tk.Listbox(ms_list_frame, font=("Consolas", 10), bg="#09090B", fg=self.accent_main, bd=0, highlightthickness=0, height=5, selectbackground="#27272A")
            self.ms_video_listbox.pack(fill="x", padx=1, pady=1)
            for vid in multi_stream_config.get("video_ids", []): self.ms_video_listbox.insert("end", vid)

            def add_ms_video():
                vid = _simpledialog.askstring("Add Video ID", "YouTube video ID (or full URL):", parent=self.root)
                if vid and vid.strip():
                    multi_stream_config.setdefault("video_ids", []).append(vid.strip())
                    save_multi_stream_config()
                    self.ms_video_listbox.insert("end", vid.strip())

            def remove_ms_video():
                sel = self.ms_video_listbox.curselection()
                if not sel: return
                ids = multi_stream_config.get("video_ids", [])
                if sel[0] < len(ids):
                    del ids[sel[0]]
                    save_multi_stream_config()
                    self.ms_video_listbox.delete(sel[0])

            ms_btn_row = tk.Frame(extra_content, bg="#18181B")
            ms_btn_row.pack(anchor="w")
            tk.Button(ms_btn_row, text="+ Add Video ID", font=("Segoe UI", 9, "bold"), bg="#10B981", fg="black", bd=0, cursor="hand2", command=add_ms_video).pack(side="left", ipady=5, ipadx=12, padx=(0, 8))
            tk.Button(ms_btn_row, text="✕ Remove Selected", font=("Segoe UI", 9, "bold"), bg="#EF4444", fg="white", bd=0, cursor="hand2", command=remove_ms_video).pack(side="left", ipady=5, ipadx=12)
        except Exception as e:
            self.log("[system]", f"[err] extra tab build error: {e}", "err")

    # ---------------- OS Voting tab ----------------
    def build_osvoting_tab(self):
        try:
            _sp = self._make_tab_scrollable(self.tab_osvote)
            wrapper = tk.Frame(_sp, bg="#09090B")
            wrapper.pack(fill="both", expand=True)
            border = tk.Frame(wrapper, bg="#27272A")
            border.pack(pady=20, padx=40, fill="both", expand=True)
            content = tk.Frame(border, bg="#18181B", padx=25, pady=20)
            content.pack(fill="both", expand=True, padx=1, pady=1)

            tk.Label(content, text="OS-SWITCH VOTING", font=("Segoe UI", 12, "bold"), bg="#18181B", fg=self.accent_main).pack(anchor="w")
            def _osvote_apply_json(data):
                global os_voting_enabled, os_list, current_os_vm
                if not isinstance(data, dict): return
                os_voting_enabled = bool(data.get("enabled", os_voting_enabled))
                os_list = data.get("os_list", os_list)[:OS_VOTE_SLOTS]
                current_os_vm = data.get("last_active_vm", current_os_vm) or current_os_vm
                save_os_voting_config()
            self.add_json_io_bar(content, self.tab_osvote, self.build_osvoting_tab,
                                  lambda: {"enabled": os_voting_enabled, "os_list": os_list, "last_active_vm": current_os_vm or ""},
                                  _osvote_apply_json, "os_voting_config")
            tk.Label(content, text=f"Chat votes with !<trigger>. {OS_VOTE_REQUIRED} unique votes switches the running VM to that OS. Add as many VM entries as you like.", font=("Segoe UI", 10), bg="#18181B", fg="#A1A1AA", wraplength=760, justify="left").pack(anchor="w", pady=(0, 12))

            top_row = tk.Frame(content, bg="#18181B")
            top_row.pack(fill="x", pady=(0, 12))
            self.var_osvote_enabled = tk.BooleanVar(value=os_voting_enabled)
            ttk.Checkbutton(top_row, text="Enable OS-switch voting", variable=self.var_osvote_enabled, style="Toggle.TCheckbutton").pack(side="left")
            tk.Button(top_row, text="+ New VM", font=("Segoe UI", 10, "bold"), bg="#10B981", fg="black", bd=0, cursor="hand2",
                      command=lambda: self._osvote_add_row()).pack(side="right", ipady=6, ipadx=16)
            tk.Button(top_row, text="Refresh VM List", font=("Segoe UI", 10, "bold"), bg="#27272A", fg="white", bd=0, cursor="hand2",
                      command=lambda: self._osvote_refresh_vm_lists()).pack(side="right", ipady=6, ipadx=16, padx=(0, 8))

            hdr = tk.Frame(content, bg="#18181B")
            hdr.pack(fill="x", pady=(0, 2))
            for txt, w in [("Trigger (!x)", 14), ("Display Name", 16), ("Backend", 10), ("VM", 26), ("OBS Switching Scene (opt.)", 20), ("OBS Live Scene (opt.)", 20), ("", 4)]:
                tk.Label(hdr, text=txt, font=("Segoe UI", 9, "bold"), bg="#18181B", fg="#A1A1AA", width=w, anchor="w").pack(side="left", padx=4)

            # scrollable rows area so an unlimited number of VMs can be added
            rows_canvas_wrap = tk.Frame(content, bg="#18181B")
            rows_canvas_wrap.pack(fill="both", expand=True, pady=(0, 10))
            self.osvote_canvas = tk.Canvas(rows_canvas_wrap, bg="#18181B", highlightthickness=0, height=260)
            osvote_scroll = ttk.Scrollbar(rows_canvas_wrap, orient="vertical", command=self.osvote_canvas.yview)
            self.osvote_rows_frame = tk.Frame(self.osvote_canvas, bg="#18181B")
            self.osvote_rows_frame.bind("<Configure>", lambda e: self.osvote_canvas.configure(scrollregion=self.osvote_canvas.bbox("all")))
            self.osvote_canvas.create_window((0, 0), window=self.osvote_rows_frame, anchor="nw")
            self.osvote_canvas.configure(yscrollcommand=osvote_scroll.set)
            self.osvote_canvas.pack(side="left", fill="both", expand=True)
            osvote_scroll.pack(side="right", fill="y")

            self.osvote_rows = []
            if os_list:
                for entry in os_list:
                    self._osvote_add_row(entry)
            else:
                self._osvote_add_row()

            btn_row = tk.Frame(content, bg="#18181B")
            btn_row.pack(fill="x", pady=(6, 0))
            tk.Button(btn_row, text="SAVE OS VOTING CONFIG", font=("Segoe UI", 11, "bold"), bg="#10B981", fg="black", bd=0, cursor="hand2",
                      command=self._osvote_save).pack(side="left", ipady=8, ipadx=20)
        except Exception as e:
            self.log("[system]", f"[err] os voting tab build error: {e}", "err")

    def _osvote_add_row(self, entry=None):
        entry = entry or {}
        row_backend = entry.get("backend", "vbox")
        row = tk.Frame(self.osvote_rows_frame, bg="#18181B")
        row.pack(fill="x", pady=3)
        e_trig = tk.Entry(row, width=14, font=("Consolas", 10), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A")
        e_trig.pack(side="left", padx=4, ipady=4)
        e_trig.insert(0, entry.get("trigger", ""))
        e_name = tk.Entry(row, width=16, font=("Consolas", 10), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A")
        e_name.pack(side="left", padx=4, ipady=4)
        e_name.insert(0, entry.get("name", ""))

        cb_backend = ttk.Combobox(row, values=["vbox", "vmware"], width=8, state="readonly", font=("Segoe UI", 9))
        cb_backend.pack(side="left", padx=4)
        cb_backend.set(row_backend)

        vm_list = get_all_vmware_vms(vmrun_cmd) if row_backend == "vmware" else get_all_vbox_vms(vbox_manage_cmd)
        cb_vm = ttk.Combobox(row, values=vm_list, width=24, font=("Segoe UI", 10))
        cb_vm.pack(side="left", padx=4)
        if entry.get("vm"): cb_vm.set(entry.get("vm", ""))
        elif vm_list: cb_vm.set(vm_list[0])

        def _on_row_backend_changed(event=None, cb_backend=cb_backend, cb_vm=cb_vm):
            new_backend = cb_backend.get()
            new_vms = get_all_vmware_vms(vmrun_cmd) if new_backend == "vmware" else get_all_vbox_vms(vbox_manage_cmd)
            cb_vm["values"] = new_vms
            if new_vms: cb_vm.set(new_vms[0])
        cb_backend.bind("<<ComboboxSelected>>", _on_row_backend_changed)

        e_obs_switch = tk.Entry(row, width=18, font=("Consolas", 10), bg="#09090B", fg="#F59E0B", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A")
        e_obs_switch.pack(side="left", padx=4, ipady=4)
        e_obs_switch.insert(0, entry.get("obs_switch_scene", ""))
        e_obs_live = tk.Entry(row, width=18, font=("Consolas", 10), bg="#09090B", fg="#10B981", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A")
        e_obs_live.pack(side="left", padx=4, ipady=4)
        e_obs_live.insert(0, entry.get("obs_live_scene", ""))
        row_ref = (row, e_trig, e_name, cb_vm, e_obs_switch, e_obs_live, cb_backend)
        tk.Button(row, text="✕", font=("Segoe UI", 9, "bold"), bg="#EF4444", fg="white", bd=0, cursor="hand2", width=3,
                  command=lambda: self._osvote_remove_row(row_ref)).pack(side="left", padx=(4, 0))
        self.osvote_rows.append(row_ref)
        return row_ref

    def _osvote_remove_row(self, row_ref):
        row, *_ = row_ref
        if row_ref in self.osvote_rows: self.osvote_rows.remove(row_ref)
        row.destroy()

    def _osvote_refresh_vm_lists(self):
        # Resolve path variables inside the function scope to prevent UI thread crashes
        try:
            current_vmrun = vmrun_cmd
        except NameError:
            current_vmrun = "vmrun"
            
        try:
            current_vbox = self.entry_vbox_new.get().strip() if hasattr(self, "entry_vbox_new") else vbox_manage_cmd
        except Exception:
            current_vbox = "VBoxManage"

        vbox_vms = get_all_vbox_vms(current_vbox)
        vmware_vms = get_all_vmware_vms(current_vmrun)
        
        for row_ref in self.osvote_rows:
            # Maintain exact native 7-item unpacking layout
            _, _, _, cb_vm, _, _, cb_backend = row_ref
            current = cb_vm.get()
            
            # Auto-detect if a VMware file structure is typed or chosen
            if "vmware" in str(cb_backend.get()).lower() or current.lower().endswith(".vmx"):
                fresh = vmware_vms
                if "vmware" not in str(cb_backend.get()).lower():
                    cb_backend.set("vmware")
            else:
                fresh = vbox_vms
                
            cb_vm["values"] = fresh
            if current in fresh:
                cb_vm.set(current)

    def _osvote_save(self):
        global os_voting_enabled, os_list
        os_voting_enabled = self.var_osvote_enabled.get()
        new_list = []
        
        for row_ref in self.osvote_rows:
            try:
                trig = row_ref[0].get().strip() if hasattr(row_ref[0], 'get') else ""
                name = row_ref[1].get().strip() if hasattr(row_ref[1], 'get') else ""
                
                # Dynamic index protection fallback
                cb_vm = row_ref[3]
                cb_backend = row_ref[6]
                
                vm = cb_vm.get().strip()
                backend = cb_backend.get().strip()
                
                scene_sw = row_ref[4].get().strip() if hasattr(row_ref[4], 'get') else ""
                scene_lv = row_ref[5].get().strip() if hasattr(row_ref[5], 'get') else ""
                
                if vm or name:
                    # Maintain backend integrity if targeting a VMX layout
                    if vm.lower().endswith(".vmx") and "vmware" not in backend.lower():
                        backend = "vmware"
                        
                    new_list.append({
                        "trigger": trig,
                        "name": name,
                        "backend": backend,
                        "vm": vm,
                        "obs_switching_scene": scene_sw,
                        "obs_live_scene": scene_lv
                    })
            except Exception:
                pass
                
        os_list = new_list
        save_os_voting_config()

    # ---------------- Real PC tab ----------------
    def build_realpc_tab(self):
        try:
            wrapper = tk.Frame(self.tab_realpc, bg="#09090B")
            wrapper.pack(fill="both", expand=True)
            realpc_canvas = tk.Canvas(wrapper, bg="#09090B", highlightthickness=0)
            realpc_scrollbar = ttk.Scrollbar(wrapper, orient="vertical", command=realpc_canvas.yview)
            border = tk.Frame(realpc_canvas, bg="#27272A")
            border_window = realpc_canvas.create_window((0, 0), window=border, anchor="nw")
            border.bind("<Configure>", lambda e: realpc_canvas.configure(scrollregion=realpc_canvas.bbox("all")))
            realpc_canvas.bind("<Configure>", lambda e: realpc_canvas.itemconfigure(border_window, width=e.width))
            realpc_canvas.configure(yscrollcommand=realpc_scrollbar.set)
            realpc_canvas.pack(side="left", fill="both", expand=True, padx=(20, 0), pady=20)
            realpc_scrollbar.pack(side="right", fill="y")
            def _realpc_mousewheel(e): realpc_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            realpc_canvas.bind("<Enter>", lambda e: realpc_canvas.bind_all("<MouseWheel>", _realpc_mousewheel))
            realpc_canvas.bind("<Leave>", lambda e: realpc_canvas.unbind_all("<MouseWheel>"))
            content = tk.Frame(border, bg="#18181B", padx=25, pady=20)
            content.pack(fill="both", expand=True, padx=1, pady=1)

            tk.Label(content, text="REAL PC / VNC REMOTE CONTROL", font=("Segoe UI", 12, "bold"), bg="#18181B", fg="#EF4444").pack(anchor="w")
            def _realpc_apply_json(data):
                if isinstance(data, dict):
                    realpc_config.update(data)
                    save_realpc_config()
            self.add_json_io_bar(content, self.tab_realpc, self.build_realpc_tab,
                                  lambda: dict(realpc_config), _realpc_apply_json, "realpc_config")
            tk.Label(content, text="Gives chat direct control of a mouse/keyboard target via VNC -- point it at this computer, a\n"
                                    "separate real PC, or a VM's own VRDE/VNC server. WARNING: the developer is not responsible for\n"
                                    "any damage caused by this feature. Supervise the stream while active.",
                     font=("Segoe UI", 9), bg="#18181B", fg="#A1A1AA", justify="left").pack(anchor="w", pady=(4, 15))

            vnc_avail_txt = "available" if vncdotool_available else "not installed (pip install vncdotool)"
            vnc_card = tk.Frame(content, bg="#0F0F12", highlightthickness=1, highlightbackground="#27272A")
            vnc_card.pack(fill="x", pady=(0, 15))
            tk.Label(vnc_card, text="VNC TARGET", font=("Segoe UI", 10, "bold"), bg="#0F0F12", fg="#8B5CF6").pack(anchor="w", padx=15, pady=(12, 4))
            tk.Label(vnc_card, text=f"vncdotool: {vnc_avail_txt}", font=("Segoe UI", 9), bg="#0F0F12", fg="#A1A1AA").pack(anchor="w", padx=15, pady=(0, 8))
            vnc_grid = tk.Frame(vnc_card, bg="#0F0F12")
            vnc_grid.pack(fill="x", padx=15, pady=(0, 12))
            def vfield(row, label, value, width=20, show=None):
                tk.Label(vnc_grid, text=label, font=("Segoe UI", 9, "bold"), bg="#0F0F12", fg="#D4D4D8").grid(row=row, column=0, sticky="e", pady=4, padx=(0, 10))
                e = tk.Entry(vnc_grid, width=width, font=("Consolas", 10), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A", show=show or "")
                e.grid(row=row, column=1, sticky="w", pady=4, ipady=4)
                e.insert(0, value)
                return e
            self.realpc_vnc_host = vfield(0, "Host / Public IP", realpc_config.get("vnc_host", ""), 24)
            self.realpc_vnc_port = vfield(1, "Port", str(realpc_config.get("vnc_port", 5900)), 8)
            self.realpc_vnc_pass = vfield(2, "Password", realpc_config.get("vnc_password", ""), 20, show="*")
            self.vnc_status_lbl = tk.Label(vnc_card, text="status: disconnected", font=("Consolas", 10, "bold"), bg="#0F0F12", fg="#EF4444")
            self.vnc_status_lbl.pack(anchor="w", padx=15, pady=(0, 8))

            def save_vnc_target():
                realpc_config["vnc_host"] = self.realpc_vnc_host.get().strip()
                try: realpc_config["vnc_port"] = int(self.realpc_vnc_port.get().strip())
                except Exception: pass
                realpc_config["vnc_password"] = self.realpc_vnc_pass.get()
                save_realpc_config()
                self.log("[system]", "[info] vnc target saved.", "sysmsg")

            def do_vnc_connect():
                save_vnc_target()
                ok = vnc_connect()
                if not ok:
                    self.log("[system]", "[warn] vnc connect failed on first try -- retrying automatically until it succeeds.", "sysmsg")
                    vnc_connect_with_retry()

            def do_vnc_disconnect():
                vnc_disconnect()

            def poll_vnc_status():
                if hasattr(self, "vnc_status_lbl"):
                    if vnc_connected: self.vnc_status_lbl.config(text="status: connected", fg="#10B981")
                    elif getattr(sys.modules[__name__], '_vnc_connect_retry_running', False): self.vnc_status_lbl.config(text="status: retrying connection...", fg="#F59E0B")
                    else: self.vnc_status_lbl.config(text="status: disconnected", fg="#EF4444")
                if self.running: self.root.after(2000, poll_vnc_status)
            poll_vnc_status()

            vnc_btn_row = tk.Frame(vnc_card, bg="#0F0F12")
            vnc_btn_row.pack(fill="x", padx=15, pady=(0, 12))
            tk.Button(vnc_btn_row, text="Save Target", font=("Segoe UI", 9, "bold"), bg="#27272A", fg="white", bd=0, cursor="hand2", command=save_vnc_target).pack(side="left", ipady=5, ipadx=12, padx=(0, 8))
            tk.Button(vnc_btn_row, text="Connect", font=("Segoe UI", 9, "bold"), bg="#10B981", fg="black", bd=0, cursor="hand2", command=do_vnc_connect).pack(side="left", ipady=5, ipadx=12, padx=(0, 8))
            tk.Button(vnc_btn_row, text="Disconnect", font=("Segoe UI", 9, "bold"), bg="#EF4444", fg="white", bd=0, cursor="hand2", command=do_vnc_disconnect).pack(side="left", ipady=5, ipadx=12)

            grid = tk.Frame(content, bg="#18181B")
            grid.pack(fill="x")
            tk.Label(grid, text="YouTube Video ID", font=("Segoe UI", 10, "bold"), bg="#18181B", fg="#D4D4D8").grid(row=0, column=0, sticky="e", pady=6, padx=(0, 10))
            self.realpc_video_id = tk.Entry(grid, width=30, font=("Consolas", 11), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A")
            self.realpc_video_id.grid(row=0, column=1, sticky="w", pady=6, ipady=5)
            self.realpc_video_id.insert(0, realpc_config.get("video_id", ""))

            tk.Label(grid, text="Cooldown (s)", font=("Segoe UI", 10, "bold"), bg="#18181B", fg="#D4D4D8").grid(row=1, column=0, sticky="e", pady=6, padx=(0, 10))
            self.realpc_cooldown = tk.Entry(grid, width=10, font=("Consolas", 11), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A")
            self.realpc_cooldown.grid(row=1, column=1, sticky="w", pady=6, ipady=5)
            self.realpc_cooldown.insert(0, str(realpc_config.get("cooldown", 1.0)))

            self.realpc_whitelist_only = tk.BooleanVar(value=realpc_config.get("whitelist_only", False))
            ttk.Checkbutton(content, text="Whitelist only (only listed users can send commands)", variable=self.realpc_whitelist_only, style="Toggle.TCheckbutton").pack(anchor="w", pady=4)
            self.realpc_failsafe = tk.BooleanVar(value=realpc_config.get("failsafe", True))
            ttk.Checkbutton(content, text="Failsafe (move mouse to top-left corner to abort)", variable=self.realpc_failsafe, style="Toggle.TCheckbutton").pack(anchor="w", pady=4)
            self.realpc_text_only = tk.BooleanVar(value=realpc_config.get("text_only", False))
            ttk.Checkbutton(content, text="Text-only mode (blocks mouse/screenshot, keyboard only)", variable=self.realpc_text_only, style="Toggle.TCheckbutton").pack(anchor="w", pady=4)

            tk.Label(content, text="Whitelist (comma-separated usernames)", font=("Segoe UI", 10, "bold"), bg="#18181B", fg="#D4D4D8").pack(anchor="w", pady=(10, 2))
            self.realpc_whitelist_entry = tk.Entry(content, font=("Consolas", 10), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A")
            self.realpc_whitelist_entry.pack(fill="x", ipady=5)
            self.realpc_whitelist_entry.insert(0, ", ".join(realpc_config.get("whitelist", [])))

            tk.Label(content, text="Blocked (comma-separated usernames)", font=("Segoe UI", 10, "bold"), bg="#18181B", fg="#D4D4D8").pack(anchor="w", pady=(10, 2))
            self.realpc_blocked_entry = tk.Entry(content, font=("Consolas", 10), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A")
            self.realpc_blocked_entry.pack(fill="x", ipady=5)
            self.realpc_blocked_entry.insert(0, ", ".join(realpc_config.get("blocked", [])))

            self.realpc_status_lbl = tk.Label(content, text="status: stopped", font=("Consolas", 11, "bold"), bg="#18181B", fg="#A1A1AA")
            self.realpc_status_lbl.pack(anchor="w", pady=(15, 5))

            def save_realpc_settings():
                realpc_config["video_id"] = self.realpc_video_id.get().strip()
                try: realpc_config["cooldown"] = float(self.realpc_cooldown.get().strip())
                except Exception: pass
                realpc_config["whitelist_only"] = self.realpc_whitelist_only.get()
                realpc_config["failsafe"] = self.realpc_failsafe.get()
                realpc_config["text_only"] = self.realpc_text_only.get()
                realpc_config["whitelist"] = [u.strip() for u in self.realpc_whitelist_entry.get().split(",") if u.strip()]
                realpc_config["blocked"] = [u.strip() for u in self.realpc_blocked_entry.get().split(",") if u.strip()]
                save_realpc_config()
                self.log("[system]", "[info] real pc settings saved.", "sysmsg")

            def start_realpc():
                save_realpc_settings()
                if not vncdotool_available:
                    messagebox.showerror("Real PC Control", "vncdotool is not installed.\nRun: pip install vncdotool")
                    return
                if not realpc_config.get("vnc_host", "").strip():
                    messagebox.showerror("Real PC Control", "Set a VNC Host/Public IP above and click Connect first.")
                    return
                if not messagebox.askyesno("Real PC Control - Warning 1/3", "This gives YouTube chat DIRECT control of the mouse and keyboard on the configured VNC target.\n\nContinue?"):
                    return
                if not messagebox.askyesno("Real PC Control - Warning 2/3", "Anyone in chat (or on the whitelist) will be able to type, click, and move the mouse on that machine.\n\nAre you sure you want to proceed?"):
                    return
                if not messagebox.askyesno("Real PC Control - Warning 3/3", "The developer is not responsible for any damage, data loss, or privacy breach caused by this feature.\n\nStart Real PC bot now?"):
                    return
                if start_realpc_bot(): self.log("[system]", "[info] real pc bot started.", "sysmsg")

            def stop_realpc():
                stop_realpc_bot()
                self.log("[system]", "[info] real pc bot stop requested.", "sysmsg")

            btn_row = tk.Frame(content, bg="#18181B")
            btn_row.pack(anchor="w", pady=5)
            tk.Button(btn_row, text="SAVE SETTINGS", font=("Segoe UI", 10, "bold"), bg="#10B981", fg="black", bd=0, cursor="hand2", command=save_realpc_settings).pack(side="left", ipady=6, ipadx=15, padx=(0, 10))
            tk.Button(btn_row, text="START REAL PC BOT", font=("Segoe UI", 10, "bold"), bg="#EF4444", fg="white", bd=0, cursor="hand2", command=start_realpc).pack(side="left", ipady=6, ipadx=15, padx=(0, 10))
            tk.Button(btn_row, text="STOP", font=("Segoe UI", 10, "bold"), bg="#27272A", fg="white", bd=0, cursor="hand2", command=stop_realpc).pack(side="left", ipady=6, ipadx=15)

            btn_row2 = tk.Frame(content, bg="#18181B")
            btn_row2.pack(anchor="w", pady=(0, 5))
            tk.Button(btn_row2, text="Connect To Chat", font=("Segoe UI", 10, "bold"), bg="#10B981", fg="black", bd=0, cursor="hand2", command=start_realpc).pack(side="left", ipady=6, ipadx=15, padx=(0, 10))
            tk.Button(btn_row2, text="Disconnect Chat", font=("Segoe UI", 10, "bold"), bg="#EF4444", fg="white", bd=0, cursor="hand2", command=stop_realpc).pack(side="left", ipady=6, ipadx=15)

            tk.Label(content, text="Now supports the FULL command set (same as the main VM control system), all routed through VNC:\n"
                                    "Input: !type, !send, !key, !enter, !space, !backspace, !combo win+r, !keydown, !keyup\n"
                                    "Mouse: !click [x y], !rclick, !mclick, !dclick, !tripleclick, !move x y, !moverel up/down/left/right, "
                                    "!scroll [n], !scrollup, !scrolldown, !drag dx dy\n"
                                    "Apps: !run <cmd>, !cmd <admin cmd>, plus all app shortcuts (!calc, !notepad, !paint, !wmp, ...) and "
                                    "combo shortcuts (!copy, !paste, !undo, !altf4, !alttab, ...) and cmd utilities (!tasklist, !cls, !ver, ...)\n"
                                    "Fun/chaos: !msgbox, !spam, !countdown, !matrix, !colorscheme, !rainbow, !notepadflood, !exeflood, "
                                    "!txtflood, !deskflood, !beep, !shake, !jiggle, !circle, !spiral, !roll, !coinflip\n"
                                    "Voice: !tts, !ttsloop, !ttsxp, !ttsxploop | Misc: !winkey <k>, !dir <path>, !taskkill <proc>, !openfile <path>, "
                                    "!screenshot, !pos, !size, !wait n\n"
                                    "Chain with spaces: !combo win+r !wait 1 !send cmd !wait 0.5 !key enter",
                     font=("Segoe UI", 9), bg="#18181B", fg="#71717A", wraplength=650, justify="left").pack(anchor="w", pady=(15, 0))

            def refresh_realpc_status():
                if hasattr(self, "realpc_status_lbl"):
                    self.realpc_status_lbl.config(text=f"status: {realpc_status_text}")
                if self.running: self.root.after(1000, refresh_realpc_status)
            refresh_realpc_status()
        except Exception as e:
            self.log("[system]", f"[err] real pc tab build error: {e}", "err")

    # ---------------- VMware tab (vmrun + VNC console target) ----------------
    def build_vmware_tab(self):
        try:
            _sp = self._make_tab_scrollable(self.tab_vmware)
            wrapper = tk.Frame(_sp, bg="#09090B")
            wrapper.pack(fill="both", expand=True)
            content = tk.Frame(wrapper, bg="#18181B", padx=25, pady=20)
            content.pack(fill="both", expand=True, padx=(20, 20), pady=20)

            tk.Label(content, text="VIRTUALBOX (VBOXMANAGE PATH)", font=("Segoe UI", 12, "bold"), bg="#18181B", fg="#EF4444").pack(anchor="w")
            tk.Label(content, text="Keyboard/mouse input to the VM goes through VirtualBox's own COM API (no VNC "
                                    "needed) -- this only needs the path to VBoxManage.exe itself.",
                     font=("Segoe UI", 9), bg="#18181B", fg="#71717A", wraplength=500, justify="left").pack(anchor="w", pady=(2, 15))
            def _vmware_apply_json(data):
                if isinstance(data, dict):
                    vbox_config.update(data)
                    save_vbox_config()
            self.add_json_io_bar(content, self.tab_vmware, self.build_vmware_tab,
                                  lambda: dict(vbox_config), _vmware_apply_json, "vbox_config")

            grid = tk.Frame(content, bg="#18181B")
            grid.pack(fill="x", pady=(15, 0))

            tk.Label(grid, text="VBoxManage Path:", font=("Segoe UI", 10, "bold"), bg="#18181B", fg="#D4D4D8").grid(row=0, column=0, sticky="e", pady=6, padx=(0, 10))
            self.vmware_vboxmanage_path = tk.Entry(grid, width=45, font=("Consolas", 11), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A")
            self.vmware_vboxmanage_path.grid(row=0, column=1, sticky="w", pady=6, ipady=5)
            self.vmware_vboxmanage_path.insert(0, vbox_config.get("vboxmanage_path", vbox_manage_cmd))

            def browse_vboxmanage():
                path = filedialog.askopenfilename(title="Select VBoxManage.exe",
                                                   filetypes=[("VBoxManage", "VBoxManage.exe" if platform.system() == "Windows" else "VBoxManage"), ("All files", "*.*")])
                if path:
                    self.vmware_vboxmanage_path.delete(0, "end")
                    self.vmware_vboxmanage_path.insert(0, path)
            tk.Button(grid, text="Browse...", font=("Segoe UI", 9), bg="#27272A", fg="white", bd=0, cursor="hand2",
                      command=browse_vboxmanage).grid(row=0, column=2, padx=(10, 0))

            def save_vmware_settings():
                global vbox_manage_cmd
                path = self.vmware_vboxmanage_path.get().strip().strip('"').strip("'") or "VBoxManage"
                vbox_config["vboxmanage_path"] = path
                vbox_manage_cmd = path
                save_vbox_config()
                self.force_session_refresh = True  # reconnect COM session with the new path next tick
                self.log("[system]", "[info] vbox settings saved.", "sysmsg")

            tk.Button(content, text="SAVE SETTINGS", font=("Segoe UI", 10, "bold"), bg="#10B981", fg="black", bd=0, cursor="hand2", command=save_vmware_settings).pack(anchor="w", pady=(15, 0), ipady=6, ipadx=15)

            divider = tk.Frame(content, bg="#27272A", height=1)
            divider.pack(fill="x", pady=(24, 20))

            tk.Label(content, text="VMWARE VNC TARGET", font=("Segoe UI", 12, "bold"), bg="#18181B", fg="#3B82F6").pack(anchor="w")
            tk.Label(content, text="VMware has no COM keyboard/mouse API like VirtualBox does, so when the current "
                                    "VM is VMware-backed, input goes through VNC instead -- this must match what's "
                                    "enabled in the VM's own .vmx (RemoteDisplay.vnc.*).",
                     font=("Segoe UI", 9), bg="#18181B", fg="#71717A", wraplength=500, justify="left").pack(anchor="w", pady=(2, 15))

            vnc_grid = tk.Frame(content, bg="#18181B")
            vnc_grid.pack(fill="x")

            def vnc_field(row, label, value, width=20, show=None):
                tk.Label(vnc_grid, text=label, font=("Segoe UI", 10, "bold"), bg="#18181B", fg="#D4D4D8").grid(row=row, column=0, sticky="e", pady=6, padx=(0, 10))
                e = tk.Entry(vnc_grid, width=width, font=("Consolas", 11), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A", show=show)
                e.grid(row=row, column=1, sticky="w", pady=6, ipady=5)
                e.insert(0, value)
                return e

            self.vmware_vnc_host_entry = vnc_field(0, "VNC Host:", vmware_panel_vnc_config.get("vnc_host", ""), 30)
            self.vmware_vnc_port_entry = vnc_field(1, "VNC Port:", str(vmware_panel_vnc_config.get("vnc_port", 5900)), 10)
            self.vmware_vnc_pass_entry = vnc_field(2, "VNC Password:", vmware_panel_vnc_config.get("vnc_password", ""), 30, show="*")

            self.vmware_vnc_status_lbl = tk.Label(content, text="", font=("Segoe UI", 9, "italic"), bg="#18181B", fg="#A1A1AA")
            self.vmware_vnc_status_lbl.pack(anchor="w", pady=(10, 6))

            def save_vmware_vnc_settings():
                vmware_panel_vnc_config["vnc_host"] = self.vmware_vnc_host_entry.get().strip()
                try: vmware_panel_vnc_config["vnc_port"] = int(self.vmware_vnc_port_entry.get().strip() or 5900)
                except Exception: vmware_panel_vnc_config["vnc_port"] = 5900
                vmware_panel_vnc_config["vnc_password"] = self.vmware_vnc_pass_entry.get()
                vbox_config["vmware_vnc"] = dict(vmware_panel_vnc_config)
                save_vbox_config()
                self.log("[system]", f"[info] VMware VNC target saved: {vmware_panel_vnc_config['vnc_host']}:{vmware_panel_vnc_config['vnc_port']}", "sysmsg")

            def test_vmware_vnc():
                global _vnc_purpose
                save_vmware_vnc_settings()
                def run():
                    _vnc_purpose = "mainvm"
                    ok = vnc_connect()
                    if ok:
                        self.vmware_vnc_status_lbl.config(text="Connected!", fg="#10B981")
                        self.log("[system]", "[info] VMware VNC test connect succeeded.", "sysmsg")
                    else:
                        self.vmware_vnc_status_lbl.config(text="Connection failed -- check host/port/password.", fg="#EF4444")
                        self.log("[system]", "[err] VMware VNC test connect failed.", "err")
                threading.Thread(target=run, daemon=True).start()

            tk.Button(content, text="Save VNC Settings", font=("Segoe UI", 9, "bold"), bg="#27272A", fg="white", bd=0, cursor="hand2",
                      command=save_vmware_vnc_settings).pack(anchor="w", ipady=5, ipadx=12, pady=(0, 6))
            tk.Button(content, text="Test Connection", font=("Segoe UI", 9, "bold"), bg="#3B82F6", fg="white", bd=0, cursor="hand2",
                      command=test_vmware_vnc).pack(anchor="w", ipady=5, ipadx=12)

            divider2 = tk.Frame(content, bg="#27272A", height=1)
            divider2.pack(fill="x", pady=(24, 20))

            tk.Label(content, text="!ENABLEINTERNET / !DISABLEINTERNET", font=("Segoe UI", 11, "bold"), bg="#18181B", fg="#F59E0B").pack(anchor="w", pady=(0, 0))
            tk.Label(content, text="Switches the VM's first network adapter's link state on/off LIVE via "
                                    "VBoxManage controlvm setlinkstate1 -- works on a running VM, no restart needed.",
                     font=("Segoe UI", 8), bg="#18181B", fg="#71717A", wraplength=500, justify="left").pack(anchor="w", pady=(2, 8))

            # ── Quick-access toggle (calls the same backend-aware vm_toggle_internet() the
            #    !enableinternet/!disableinternet chat commands already use) ──
            self.vmware_internet_status_lbl = tk.Label(content, text="", font=("Segoe UI", 9, "italic"),
                                                        bg="#18181B", fg="#A1A1AA")
            self.vmware_internet_status_lbl.pack(anchor="w", pady=(10, 6))

            def do_toggle_internet(enable):
                if not vm_name:
                    self.log("[system]", "[err] no VM configured -- set one in the VM Config panel first.", "err")
                    return
                def run():
                    res = vm_toggle_internet(vm_name, enable)
                    label = "enabled" if enable else "disabled"
                    if res.returncode == 0:
                        self.vmware_internet_status_lbl.config(text=f"Internet {label}. {(res.stdout or '').strip()}".strip(), fg="#10B981")
                        self.log("[system]", f"[info] internet {label} via GUI button.", "sysmsg")
                    else:
                        msg = (res.stderr or res.stdout or "unknown error").strip()
                        self.vmware_internet_status_lbl.config(text=f"Failed: {msg}", fg="#EF4444")
                        self.log("[system]", f"[err] internet {label} failed: {msg}", "err")
                threading.Thread(target=run, daemon=True).start()

            toggle_row = tk.Frame(content, bg="#18181B")
            toggle_row.pack(anchor="w")
            tk.Button(toggle_row, text="🌐 Enable Internet", font=("Segoe UI", 9, "bold"), bg="#10B981", fg="black",
                      bd=0, cursor="hand2", command=lambda: do_toggle_internet(True)
                      ).pack(side="left", ipady=5, ipadx=12, padx=(0, 8))
            tk.Button(toggle_row, text="🚫 Disable Internet", font=("Segoe UI", 9, "bold"), bg="#EF4444", fg="white",
                      bd=0, cursor="hand2", command=lambda: do_toggle_internet(False)
                      ).pack(side="left", ipady=5, ipadx=12)
        except Exception as e:
            self.log("[system]", f"[err] vbox tab build error: {e}", "err")

    # ---------------- Automation tab (scheduler, permissions, sound/TTS, user mgmt) ----------------
    def build_automation_tab(self):
        try:
            wrapper = tk.Frame(self.tab_automation, bg="#09090B")
            wrapper.pack(fill="both", expand=True)
            canvas = tk.Canvas(wrapper, bg="#09090B", highlightthickness=0)
            scroll_y = ttk.Scrollbar(wrapper, orient="vertical", command=canvas.yview)
            inner = tk.Frame(canvas, bg="#09090B")
            inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=inner, anchor="nw")
            canvas.configure(yscrollcommand=scroll_y.set)
            canvas.pack(side="left", fill="both", expand=True, padx=(20, 0), pady=20)
            scroll_y.pack(side="right", fill="y")
            canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

            def _automation_get_json():
                return {
                    "sound_config": dict(sound_config), "permissions_config": dict(permissions_config),
                    "scheduler_config": dict(scheduler_config),
                    "user_mgmt": {"whitelist": sorted(whitelist_users), "blocked": sorted(blocked_users_persistent)},
                }
            def _automation_apply_json(data):
                global whitelist_users, blocked_users_persistent
                if not isinstance(data, dict): return
                if isinstance(data.get("sound_config"), dict):
                    sound_config.update(data["sound_config"]); save_sound_config()
                if isinstance(data.get("permissions_config"), dict):
                    permissions_config.update(data["permissions_config"]); save_permissions_config()
                if isinstance(data.get("scheduler_config"), dict):
                    scheduler_config.update(data["scheduler_config"]); save_scheduler_config()
                um = data.get("user_mgmt")
                if isinstance(um, dict):
                    whitelist_users = set(normalize_username(u) for u in um.get("whitelist", []) if u)
                    blocked_users_persistent = set(normalize_username(u) for u in um.get("blocked", []) if u)
                    save_user_mgmt()
            self.add_json_io_bar(inner, self.tab_automation, self.build_automation_tab,
                                  _automation_get_json, _automation_apply_json, "automation_config")

            def section(title, color="#10B981"):
                b = tk.Frame(inner, bg="#27272A")
                b.pack(fill="x", pady=(0, 15), padx=(0, 20))
                c = tk.Frame(b, bg="#18181B", padx=20, pady=15)
                c.pack(fill="both", expand=True, padx=1, pady=1)
                tk.Label(c, text=title, font=("Segoe UI", 12, "bold"), bg="#18181B", fg=color).pack(anchor="w", pady=(0, 10))
                return c

            # -- Sound / TTS --
            snd = section("SOUND & TEXT-TO-SPEECH")
            self.var_tts_enabled = tk.BooleanVar(value=sound_config.get("tts_enabled", True))
            ttk.Checkbutton(snd, text="Enable text-to-speech announcements", variable=self.var_tts_enabled, style="Toggle.TCheckbutton").pack(anchor="w", pady=4)
            row = tk.Frame(snd, bg="#18181B"); row.pack(anchor="w", pady=4)
            tk.Label(row, text="TTS rate (wpm)", bg="#18181B", fg="#D4D4D8").pack(side="left", padx=(0, 8))
            self.entry_tts_rate = tk.Entry(row, width=8, bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A")
            self.entry_tts_rate.pack(side="left", ipady=4, padx=(0, 20))
            self.entry_tts_rate.insert(0, str(sound_config.get("tts_rate", 150)))
            tk.Label(row, text="TTS volume (0-100)", bg="#18181B", fg="#D4D4D8").pack(side="left", padx=(0, 8))
            self.entry_tts_vol = tk.Entry(row, width=8, bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A")
            self.entry_tts_vol.pack(side="left", ipady=4)
            self.entry_tts_vol.insert(0, str(sound_config.get("tts_volume", 100)))
            def test_tts(): speak_text("This is a test announcement.")
            def save_sound_settings():
                sound_config["tts_enabled"] = self.var_tts_enabled.get()
                try: sound_config["tts_rate"] = int(self.entry_tts_rate.get())
                except Exception: pass
                try: sound_config["tts_volume"] = int(self.entry_tts_vol.get())
                except Exception: pass
                save_sound_config()
                self.log("[system]", "[info] sound/tts settings saved.", "sysmsg")
            btnr = tk.Frame(snd, bg="#18181B"); btnr.pack(anchor="w", pady=(10, 0))
            tk.Button(btnr, text="SAVE", bg="#10B981", fg="black", bd=0, cursor="hand2", font=("Segoe UI", 9, "bold"), command=save_sound_settings).pack(side="left", ipady=5, ipadx=12, padx=(0, 8))
            tk.Button(btnr, text="TEST VOICE", bg="#27272A", fg="white", bd=0, cursor="hand2", font=("Segoe UI", 9, "bold"), command=test_tts).pack(side="left", ipady=5, ipadx=12)

            tk.Label(snd, text="EVENT SOUND FILES", font=("Segoe UI", 10, "bold"), bg="#18181B", fg="#A1A1AA").pack(anchor="w", pady=(15, 5))
            self.sound_file_entries = {}
            for key, label in [("success_sound", "Command Success"), ("revert_sound", "Revert VM"), ("restart_sound", "Restart VM"),
                                ("ban_sound", "Ban Vote Passed"), ("os_switch_sound", "OS Switch")]:
                srow = tk.Frame(snd, bg="#18181B"); srow.pack(fill="x", pady=2)
                tk.Label(srow, text=label, width=16, anchor="w", bg="#18181B", fg="#D4D4D8", font=("Segoe UI", 9)).pack(side="left")
                se = tk.Entry(srow, font=("Consolas", 9), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A")
                se.pack(side="left", fill="x", expand=True, ipady=3, padx=(0, 6))
                se.insert(0, sound_config.get(key, ""))
                self.sound_file_entries[key] = se
                tk.Button(srow, text="Browse...", font=("Segoe UI", 8, "bold"), bg="#27272A", fg="white", bd=0, cursor="hand2",
                          command=lambda e=se: self.browse_file(e, [("Audio", "*.wav *.mp3 *.ogg"), ("All files", "*")])).pack(side="left", padx=(0, 4), ipady=3, ipadx=6)
                tk.Button(srow, text="▶", font=("Segoe UI", 8, "bold"), bg="#10B981", fg="black", bd=0, cursor="hand2", width=3,
                          command=lambda k=key: play_event_sound(k)).pack(side="left", ipady=3)

            def save_event_sounds():
                for key, e in self.sound_file_entries.items():
                    sound_config[key] = e.get().strip()
                save_sound_config()
                self.log("[system]", "[info] event sound files saved.", "sysmsg")
            tk.Button(snd, text="SAVE EVENT SOUNDS", bg="#10B981", fg="black", bd=0, cursor="hand2", font=("Segoe UI", 9, "bold"), command=save_event_sounds).pack(anchor="w", pady=(10, 0), ipady=5, ipadx=12)

            # -- Log Broadcast (PowerShell TTS + type-into-a-VM) --
            lb = section("LOG BROADCAST (TTS + LOGGING VM)", color="#F59E0B")
            tk.Label(lb, text="Speaks and/or types EVERY log line (every command, every VM action, every error -- "
                               "everything that shows up in the console, the GUI, and the chat overlay) via "
                               "PowerShell and directly into a dedicated VM's own keyboard input -- the same "
                               "steps as !type {log} followed by !key enter, just aimed at a VM you pick below "
                               "instead of whichever VM is your main stream target. Off by default.",
                     font=("Segoe UI", 9), bg="#18181B", fg="#71717A", wraplength=560, justify="left").pack(anchor="w", pady=(0, 10))

            self.var_logbroadcast_enabled = tk.BooleanVar(value=LOG_BROADCAST_CONFIG.get("enabled", False))
            ttk.Checkbutton(lb, text="Enable log broadcast", variable=self.var_logbroadcast_enabled, style="Toggle.TCheckbutton",
                            command=lambda: self._on_logbroadcast_enabled_changed()).pack(anchor="w", pady=2)
            self.var_logbroadcast_tts = tk.BooleanVar(value=LOG_BROADCAST_CONFIG.get("tts_enabled", True))
            ttk.Checkbutton(lb, text="  \u2514 Speak each log line (PowerShell SAPI)", variable=self.var_logbroadcast_tts, style="Toggle.TCheckbutton").pack(anchor="w", pady=2)
            self.var_logbroadcast_vmtyping = tk.BooleanVar(value=LOG_BROADCAST_CONFIG.get("vm_typing_enabled", True))
            ttk.Checkbutton(lb, text="  \u2514 Type each log line into the logging VM below", variable=self.var_logbroadcast_vmtyping, style="Toggle.TCheckbutton").pack(anchor="w", pady=2)

            vm_row = tk.Frame(lb, bg="#18181B")
            vm_row.pack(fill="x", pady=(12, 0))
            self.lbl_logbroadcast_vm_desc = tk.Label(vm_row,
                     text="Logging VM (a dedicated VM for this -- e.g. a tiny low-RAM VM with your YouTube chat "
                          "open in a browser -- doesn't have to be your main stream VM):",
                     font=("Segoe UI", 9, "bold"), bg="#18181B", fg="#D4D4D8", wraplength=560, justify="left")
            self.lbl_logbroadcast_vm_desc.pack(anchor="w")

            self.lbl_logbroadcast_disabled_warn = tk.Label(vm_row,
                     text="\u26a0 Chat and TTS logging disabled, this is ignored",
                     font=("Segoe UI", 9, "bold"), bg="#3a2f00", fg="#FFD54A", wraplength=560, justify="left", padx=6, pady=4)
            # Not packed yet -- shown/hidden by _on_logbroadcast_enabled_changed below.

            vm_picker_row = tk.Frame(lb, bg="#18181B")
            vm_picker_row.pack(fill="x", pady=(4, 0))
            self.cb_logbroadcast_vm = ttk.Combobox(vm_picker_row, width=40, state="readonly", font=("Segoe UI", 10))
            self.cb_logbroadcast_vm.pack(side="left", padx=(0, 8))
            self.cb_logbroadcast_vm['values'] = get_all_vbox_vms(vbox_manage_cmd)
            if LOG_BROADCAST_CONFIG.get("target_vm"): self.cb_logbroadcast_vm.set(LOG_BROADCAST_CONFIG.get("target_vm"))
            tk.Button(vm_picker_row, text="Refresh", font=("Segoe UI", 9), bg="#27272A", fg="white", bd=0, cursor="hand2",
                      command=lambda: self.cb_logbroadcast_vm.configure(values=get_all_vbox_vms(vbox_manage_cmd))).pack(side="left")

            tk.Label(lb, text="Long lines are sent in 100-character chunks, 5s apart, each followed by Enter -- "
                              "same as running !type then !key enter yourself, chunk by chunk. Speech (if enabled "
                              "above) is unaffected by any of this.",
                     font=("Segoe UI", 8, "italic"), bg="#18181B", fg="#71717A", wraplength=560, justify="left").pack(anchor="w", pady=(10, 0))

            def save_logbroadcast_settings():
                LOG_BROADCAST_CONFIG["enabled"] = self.var_logbroadcast_enabled.get()
                LOG_BROADCAST_CONFIG["tts_enabled"] = self.var_logbroadcast_tts.get()
                LOG_BROADCAST_CONFIG["vm_typing_enabled"] = self.var_logbroadcast_vmtyping.get()
                LOG_BROADCAST_CONFIG["target_vm"] = self.cb_logbroadcast_vm.get().strip()
                save_log_broadcast_config()
                self.log("[system]", f"[info] log broadcast settings saved (enabled={LOG_BROADCAST_CONFIG['enabled']}, "
                                      f"vm='{LOG_BROADCAST_CONFIG['target_vm']}').", "sysmsg")
            tk.Button(lb, text="SAVE", bg="#10B981", fg="black", bd=0, cursor="hand2", font=("Segoe UI", 9, "bold"), command=save_logbroadcast_settings).pack(anchor="w", pady=(10, 0), ipady=5, ipadx=12)

            self._on_logbroadcast_enabled_changed()

            # -- Permissions -- (moved to its own "Permissions" tab, including the new
            # vote-threshold-by-% and YouTube API key options)
            perm_note = section("PERMISSIONS")
            tk.Label(perm_note, text="Vote thresholds, cooldowns, and the % of viewers threshold now live on "
                                      "the dedicated  Permissions  tab.",
                     font=("Segoe UI", 9), bg="#18181B", fg="#A1A1AA", wraplength=480, justify="left").pack(anchor="w")

            # -- Scheduler --
            sch = section("SCHEDULER", color="#8B5CF6")
            self.var_sched_enabled = tk.BooleanVar(value=scheduler_config.get("enabled", False))
            ttk.Checkbutton(sch, text="Enable scheduled tasks", variable=self.var_sched_enabled, style="Toggle.TCheckbutton").pack(anchor="w", pady=4)
            add_row = tk.Frame(sch, bg="#18181B"); add_row.pack(anchor="w", pady=6)
            tk.Label(add_row, text="Label", bg="#18181B", fg="#D4D4D8").grid(row=0, column=0, padx=4)
            self.sched_label = tk.Entry(add_row, width=14, bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A")
            self.sched_label.grid(row=1, column=0, padx=4, ipady=4)
            tk.Label(add_row, text="Action", bg="#18181B", fg="#D4D4D8").grid(row=0, column=1, padx=4)
            self.sched_action = ttk.Combobox(add_row, values=["revert", "restartvm", "shutdown"], width=10, state="readonly")
            self.sched_action.grid(row=1, column=1, padx=4)
            self.sched_action.set("revert")
            tk.Label(add_row, text="Hour", bg="#18181B", fg="#D4D4D8").grid(row=0, column=2, padx=4)
            self.sched_hour = tk.Entry(add_row, width=4, bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A")
            self.sched_hour.grid(row=1, column=2, padx=4, ipady=4)
            self.sched_hour.insert(0, "4")
            tk.Label(add_row, text="Min", bg="#18181B", fg="#D4D4D8").grid(row=0, column=3, padx=4)
            self.sched_min = tk.Entry(add_row, width=4, bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A")
            self.sched_min.grid(row=1, column=3, padx=4, ipady=4)
            self.sched_min.insert(0, "0")
            self.sched_listbox = tk.Listbox(sch, font=("Consolas", 10), bg="#09090B", fg=self.accent_main, bd=0, highlightthickness=0, height=6)
            self.sched_listbox.pack(fill="x", pady=(10, 5))

            def refresh_sched_list():
                self.sched_listbox.delete(0, "end")
                for t in scheduler_config.get("tasks", []):
                    self.sched_listbox.insert("end", f"{t.get('label')} -> {t.get('action')} @ {t.get('hour'):02d}:{t.get('minute'):02d}")
            def add_sched_task():
                try: hour, minute = int(self.sched_hour.get()), int(self.sched_min.get())
                except Exception: return
                label = self.sched_label.get().strip() or "unnamed"
                scheduler_config.setdefault("tasks", []).append({
                    "id": str(time.time()), "label": label, "action": self.sched_action.get(),
                    "days": [], "hour": hour, "minute": minute, "last_run": ""
                })
                save_scheduler_config()
                refresh_sched_list()
            def remove_sched_task():
                sel = self.sched_listbox.curselection()
                if not sel: return
                tasks = scheduler_config.get("tasks", [])
                if sel[0] < len(tasks):
                    del tasks[sel[0]]
                    save_scheduler_config()
                    refresh_sched_list()
            def save_sched_enabled():
                scheduler_config["enabled"] = self.var_sched_enabled.get()
                save_scheduler_config()
                self.log("[system]", f"[info] scheduler enabled={scheduler_config['enabled']}.", "sysmsg")
            sbtn = tk.Frame(sch, bg="#18181B"); sbtn.pack(anchor="w")
            tk.Button(sbtn, text="ADD TASK", bg="#8B5CF6", fg="white", bd=0, cursor="hand2", font=("Segoe UI", 9, "bold"), command=add_sched_task).pack(side="left", ipady=5, ipadx=12, padx=(0, 8))
            tk.Button(sbtn, text="REMOVE SELECTED", bg="#EF4444", fg="white", bd=0, cursor="hand2", font=("Segoe UI", 9, "bold"), command=remove_sched_task).pack(side="left", ipady=5, ipadx=12, padx=(0, 8))
            tk.Button(sbtn, text="SAVE ENABLED", bg="#10B981", fg="black", bd=0, cursor="hand2", font=("Segoe UI", 9, "bold"), command=save_sched_enabled).pack(side="left", ipady=5, ipadx=12)
            refresh_sched_list()

            # -- User management -- (moved to its own "Users" tab, which also now shows
            # active !ban votes/bans -- previously ban_votes existed only as a config
            # number with no actual !ban command wired up)
            um = section("USER MANAGEMENT", color="#3B82F6")
            tk.Label(um, text="Whitelist, blocked users, and active chat bans now live on the dedicated  Users  tab.",
                     font=("Segoe UI", 9), bg="#18181B", fg="#A1A1AA", wraplength=480, justify="left").pack(anchor="w")

            # -- System tray --
            tray = section("SYSTEM TRAY", color="#A1A1AA")
            tray_status = "available" if pystray_available else "not installed (pip install pystray pillow)"
            tk.Label(tray, text=f"pystray: {tray_status}", bg="#18181B", fg="#A1A1AA").pack(anchor="w", pady=(0, 8))
            def minimize_to_tray():
                if self.config.get("verbose_connection_logs", False):
                    self.log("[system]", "[tray] minimized to system tray.", "sysmsg")
                start_tray_icon()
                self.root.withdraw()
            tk.Button(tray, text="MINIMIZE TO TRAY", bg="#27272A", fg="white", bd=0, cursor="hand2", font=("Segoe UI", 9, "bold"),
                      command=minimize_to_tray).pack(anchor="w", ipady=5, ipadx=12)
        except Exception as e:
            self.log("[system]", f"[err] automation tab build error: {e}", "err")

    # ---------------- Event Log tab ----------------
    def build_eventlog_tab(self):
        try:
            _sp = self._make_tab_scrollable(self.tab_eventlog)
            wrapper = tk.Frame(_sp, bg="#09090B")
            wrapper.pack(fill="both", expand=True, padx=20, pady=20)
            top_row = tk.Frame(wrapper, bg="#09090B")
            top_row.pack(fill="x", pady=(0, 10))
            tk.Label(top_row, text="EVENT LOG", font=("Segoe UI", 12, "bold"), bg="#09090B", fg=self.accent_main).pack(side="left")
            tk.Label(top_row, text="Filter type:", font=("Segoe UI", 9, "bold"), bg="#09090B", fg="#A1A1AA").pack(side="left", padx=(20, 6))
            self.eventlog_filter = ttk.Combobox(top_row, values=["ALL", "OS_SWITCH", "SCHEDULER", "VOTE", "BAN", "COMMAND", "MUSIC"], width=14, state="readonly")
            self.eventlog_filter.set("ALL")
            self.eventlog_filter.pack(side="left")
            self.eventlog_text = scrolledtext.ScrolledText(wrapper, font=("Consolas", 10), bg="#09090B", fg="#D4D4D8", bd=0, highlightthickness=1, highlightbackground="#27272A")
            self.eventlog_text.pack(fill="both", expand=True)

            def _eventlog_get_json():
                with event_log_lock:
                    return list(event_log_entries)
            def _eventlog_apply_json(data):
                if isinstance(data, list):
                    with event_log_lock:
                        event_log_entries.clear()
                        event_log_entries.extend(data)
            self.add_json_io_bar(wrapper, self.tab_eventlog, self.build_eventlog_tab,
                                  _eventlog_get_json, _eventlog_apply_json, "event_log")

            def refresh_eventlog():
                try:
                    self.eventlog_text.config(state="normal")
                    self.eventlog_text.delete("1.0", "end")
                    with event_log_lock:
                        recent = list(event_log_entries)[-300:]
                    filt = self.eventlog_filter.get() if hasattr(self, "eventlog_filter") else "ALL"
                    for e in reversed(recent):
                        if filt != "ALL" and e.get("type") != filt: continue
                        self.eventlog_text.insert("end", f"[{e.get('time')}] [{e.get('type')}] {e.get('user')}: {e.get('detail')}\n")
                    self.eventlog_text.config(state="disabled")
                except Exception: pass
                if self.running: self.root.after(4000, refresh_eventlog)

            def clear_eventlog():
                if not messagebox.askyesno("clear event log", "clear the in-memory event log view? (the on-disk log file is kept)"): return
                with event_log_lock:
                    event_log_entries.clear()
                refresh_eventlog()

            def export_eventlog():
                save_path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile="event_log_export.txt", title="export event log", filetypes=[("text files", "*.txt")])
                if not save_path: return
                try:
                    with event_log_lock:
                        recent = list(event_log_entries)
                    with open(save_path, "w", encoding="utf-8") as f:
                        for e in recent:
                            f.write(f"[{e.get('time')}] [{e.get('type')}] {e.get('user')}: {e.get('detail')}\n")
                    messagebox.showinfo("export", f"exported {len(recent)} events.")
                except Exception as e:
                    messagebox.showerror("export failed", str(e))

            btn_row = tk.Frame(wrapper, bg="#09090B")
            btn_row.pack(fill="x", pady=(10, 0))
            tk.Button(btn_row, text="Refresh Now", font=("Segoe UI", 9, "bold"), bg="#27272A", fg="white", bd=0, cursor="hand2", command=refresh_eventlog).pack(side="left", ipady=5, ipadx=12, padx=(0, 8))
            tk.Button(btn_row, text="Apply Filter", font=("Segoe UI", 9, "bold"), bg="#3B82F6", fg="white", bd=0, cursor="hand2", command=refresh_eventlog).pack(side="left", ipady=5, ipadx=12, padx=(0, 8))
            tk.Button(btn_row, text="Export to File...", font=("Segoe UI", 9, "bold"), bg="#8B5CF6", fg="white", bd=0, cursor="hand2", command=export_eventlog).pack(side="left", ipady=5, ipadx=12, padx=(0, 8))
            tk.Button(btn_row, text="Clear View", font=("Segoe UI", 9, "bold"), bg="#EF4444", fg="white", bd=0, cursor="hand2", command=clear_eventlog).pack(side="left", ipady=5, ipadx=12)
            refresh_eventlog()
        except Exception as e:
            self.log("[system]", f"[err] event log tab build error: {e}", "err")

    # ---------------- Appearance tab ----------------
    def build_appearance_tab(self):
        try:
            wrapper = tk.Frame(self.tab_appearance, bg="#09090B")
            wrapper.pack(fill="both", expand=True)
            canvas = tk.Canvas(wrapper, bg="#09090B", highlightthickness=0)
            vscroll = ttk.Scrollbar(wrapper, orient="vertical", command=canvas.yview)
            outer = tk.Frame(canvas, bg="#09090B")
            outer.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=outer, anchor="nw")
            canvas.configure(yscrollcommand=vscroll.set)
            canvas.pack(side="left", fill="both", expand=True, padx=(20, 0), pady=20)
            vscroll.pack(side="right", fill="y")
            canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

            def card(title, color=None):
                b = tk.Frame(outer, bg="#27272A")
                b.pack(fill="x", pady=(0, 15), padx=(0, 20))
                c = tk.Frame(b, bg="#18181B", padx=20, pady=15)
                c.pack(fill="both", expand=True, padx=1, pady=1)
                tk.Label(c, text=title, font=("Segoe UI", 12, "bold"), bg="#18181B", fg=color or self.accent_main).pack(anchor="w", pady=(0, 10))
                return c

            tk.Label(outer, text="APPEARANCE", font=("Segoe UI", 14, "bold"), bg="#09090B", fg=self.accent_main).pack(anchor="w", pady=(0, 4))
            tk.Label(outer, text="Deep-customize colors, fonts, density, and layout. Changes apply after saving + restart for full effect.", font=("Segoe UI", 10), bg="#09090B", fg="#A1A1AA", wraplength=760, justify="left").pack(anchor="w", pady=(0, 15))

            def _appearance_apply_json(data):
                if isinstance(data, dict):
                    appearance_config.update(data)
                    save_appearance_config()
            self.add_json_io_bar(outer, self.tab_appearance, self.build_appearance_tab,
                                  lambda: dict(appearance_config), _appearance_apply_json, "appearance_config")

            self.appearance_swatches = {}
            DEFAULTS = {
                "accent_color": self.accent_main, "accent_hover": self.accent_hover,
                "bg_color": "#09090B", "card_color": "#18181B", "card_border_color": "#27272A",
                "text_color": "#F4F4F5", "text_dim_color": "#A1A1AA",
                "success_color": "#10B981", "error_color": "#EF4444", "warning_color": "#F59E0B", "info_color": "#3B82F6",
                "tab_bg_color": "#18181B", "tab_selected_color": self.accent_main,
                "console_bg_color": "#09090B", "console_text_color": "#D4D4D8",
                "scrollbar_color": "#27272A", "input_bg_color": "#09090B",
            }

            def color_row(parent, key, label, default):
                row = tk.Frame(parent, bg="#18181B")
                row.pack(fill="x", pady=4)
                tk.Label(row, text=label, width=20, anchor="w", font=("Segoe UI", 10), bg="#18181B", fg="#D4D4D8").pack(side="left")
                swatch = tk.Label(row, width=4, bg=(appearance_config.get(key) or default), relief="flat", bd=0)
                swatch.pack(side="left", padx=(0, 10))
                entry = tk.Entry(row, width=12, font=("Consolas", 10), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A")
                entry.pack(side="left", ipady=4)
                entry.insert(0, appearance_config.get(key) or default)
                def pick():
                    try:
                        from tkinter import colorchooser
                        c = colorchooser.askcolor(color=entry.get() or default)[1]
                        if c:
                            entry.delete(0, "end"); entry.insert(0, c)
                            swatch.configure(bg=c)
                            update_preview()
                    except Exception: pass
                def on_type(*_):
                    val = entry.get().strip()
                    if len(val) in (4, 7) and val.startswith("#"):
                        try: swatch.configure(bg=val); update_preview()
                        except Exception: pass
                entry.bind("<KeyRelease>", on_type)
                tk.Button(row, text="Pick...", font=("Segoe UI", 9), bg="#27272A", fg="white", bd=0, cursor="hand2", command=pick).pack(side="left", padx=(10, 0), ipady=3, ipadx=8)
                self.appearance_swatches[key] = (entry, swatch)

            # -- Core colors --
            core = card("CORE COLORS")
            for key, label in [("accent_color", "Accent Color"), ("accent_hover", "Accent Hover"),
                                ("bg_color", "Background"), ("card_color", "Card Background"),
                                ("card_border_color", "Card Border"), ("text_color", "Primary Text"),
                                ("text_dim_color", "Secondary Text")]:
                color_row(core, key, label, DEFAULTS[key])

            # -- Status colors --
            status = card("STATUS COLORS", color="#10B981")
            for key, label in [("success_color", "Success"), ("error_color", "Error"),
                                ("warning_color", "Warning"), ("info_color", "Info")]:
                color_row(status, key, label, DEFAULTS[key])

            # -- Component colors --
            comp = card("COMPONENT COLORS", color="#8B5CF6")
            for key, label in [("tab_bg_color", "Tab Background"), ("tab_selected_color", "Tab Selected"),
                                ("console_bg_color", "Console Background"), ("console_text_color", "Console Text"),
                                ("scrollbar_color", "Scrollbar"), ("input_bg_color", "Input Box Background")]:
                color_row(comp, key, label, DEFAULTS[key])

            # -- Presets --
            presets_card = card("QUICK THEME PRESETS", color="#F59E0B")
            tk.Label(presets_card, text="One-click color palettes. Overwrites the fields above (remember to Save afterward).", font=("Segoe UI", 9), bg="#18181B", fg="#A1A1AA").pack(anchor="w", pady=(0, 10))
            PRESETS = {
                "Cyan (default)": {"accent_color": "#00E5FF", "accent_hover": "#00B3CC", "bg_color": "#09090B", "card_color": "#18181B"},
                "Purple": {"accent_color": "#8B5CF6", "accent_hover": "#7C3AED", "bg_color": "#09090B", "card_color": "#18181B"},
                "Emerald": {"accent_color": "#10B981", "accent_hover": "#059669", "bg_color": "#09090B", "card_color": "#14171B"},
                "Crimson": {"accent_color": "#EF4444", "accent_hover": "#DC2626", "bg_color": "#0B0909", "card_color": "#1B1818"},
                "Amber": {"accent_color": "#F59E0B", "accent_hover": "#D97706", "bg_color": "#0B0A09", "card_color": "#1B1917"},
                "Midnight Blue": {"accent_color": "#3B82F6", "accent_hover": "#2563EB", "bg_color": "#090A0F", "card_color": "#161821"},
                "Light Mode": {"accent_color": "#2563EB", "accent_hover": "#1D4ED8", "bg_color": "#F4F4F5", "card_color": "#FFFFFF", "text_color": "#18181B", "text_dim_color": "#52525B"},
                "Monochrome": {"accent_color": "#D4D4D8", "accent_hover": "#A1A1AA", "bg_color": "#09090B", "card_color": "#18181B"},
            }
            preset_grid = tk.Frame(presets_card, bg="#18181B")
            preset_grid.pack(fill="x")
            def apply_preset(vals):
                for key, val in vals.items():
                    if key in self.appearance_swatches:
                        entry, swatch = self.appearance_swatches[key]
                        entry.delete(0, "end"); entry.insert(0, val)
                        swatch.configure(bg=val)
                update_preview()
            for i, (name, vals) in enumerate(PRESETS.items()):
                tk.Button(preset_grid, text=name, font=("Segoe UI", 9, "bold"), bg=vals.get("accent_color", "#27272A"),
                          fg="black" if name != "Monochrome" else "black", bd=0, cursor="hand2",
                          command=lambda v=vals: apply_preset(v)).grid(row=i // 4, column=i % 4, padx=4, pady=4, sticky="we", ipady=6)
            for c in range(4): preset_grid.columnconfigure(c, weight=1)

            # -- Typography & layout --
            typo = card("TYPOGRAPHY & LAYOUT", color="#3B82F6")
            font_row = tk.Frame(typo, bg="#18181B")
            font_row.pack(fill="x", pady=4)
            tk.Label(font_row, text="Font Family", width=20, anchor="w", font=("Segoe UI", 10), bg="#18181B", fg="#D4D4D8").pack(side="left")
            self.cb_font_family = ttk.Combobox(font_row, values=["Segoe UI", "Consolas", "Arial", "Verdana", "Tahoma", "Calibri", "Helvetica"], width=20, state="readonly")
            self.cb_font_family.set(appearance_config.get("font_family", "Segoe UI"))
            self.cb_font_family.pack(side="left")

            font_size_row = tk.Frame(typo, bg="#18181B")
            font_size_row.pack(fill="x", pady=4)
            tk.Label(font_size_row, text="Base Font Size", width=20, anchor="w", font=("Segoe UI", 10), bg="#18181B", fg="#D4D4D8").pack(side="left")
            self.entry_font_size = tk.Entry(font_size_row, width=6, font=("Consolas", 10), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A")
            self.entry_font_size.pack(side="left", ipady=4)
            self.entry_font_size.insert(0, str(appearance_config.get("font_size", 10)))

            density_row = tk.Frame(typo, bg="#18181B")
            density_row.pack(fill="x", pady=8)
            tk.Label(density_row, text="Layout Density", width=20, anchor="w", font=("Segoe UI", 10), bg="#18181B", fg="#D4D4D8").pack(side="left")
            self.var_density = tk.StringVar(value=appearance_config.get("density", "comfortable"))
            for val, lbl in [("compact", "Compact"), ("comfortable", "Comfortable"), ("spacious", "Spacious")]:
                tk.Radiobutton(density_row, text=lbl, variable=self.var_density, value=val, bg="#18181B", fg="white", selectcolor="#09090B", activebackground="#18181B", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))

            corner_row = tk.Frame(typo, bg="#18181B")
            corner_row.pack(fill="x", pady=8)
            tk.Label(corner_row, text="Card Corner Style", width=20, anchor="w", font=("Segoe UI", 10), bg="#18181B", fg="#D4D4D8").pack(side="left")
            self.var_corner = tk.StringVar(value=appearance_config.get("corner_style", "sharp"))
            for val, lbl in [("sharp", "Sharp"), ("rounded", "Rounded")]:
                tk.Radiobutton(corner_row, text=lbl, variable=self.var_corner, value=val, bg="#18181B", fg="white", selectcolor="#09090B", activebackground="#18181B", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))

            anim_row = tk.Frame(typo, bg="#18181B")
            anim_row.pack(fill="x", pady=8)
            self.var_reduce_motion = tk.BooleanVar(value=appearance_config.get("reduce_motion", False))
            ttk.Checkbutton(anim_row, text="Reduce motion / flashing effects (chaos commands tone down visually)", variable=self.var_reduce_motion, style="Toggle.TCheckbutton").pack(anchor="w")

            # -- Live preview --
            preview_card = card("LIVE PREVIEW", color="#A1A1AA")
            self.appearance_preview_frame = tk.Frame(preview_card, bg=(appearance_config.get("bg_color") or "#09090B"), padx=15, pady=15, highlightthickness=1, highlightbackground=(appearance_config.get("card_border_color") or "#27272A"))
            self.appearance_preview_frame.pack(fill="x")
            self.preview_inner = tk.Frame(self.appearance_preview_frame, bg=(appearance_config.get("card_color") or "#18181B"), padx=15, pady=15)
            self.preview_inner.pack(fill="x")
            self.preview_title = tk.Label(self.preview_inner, text="Sample Card Title", font=("Segoe UI", 12, "bold"), bg=(appearance_config.get("card_color") or "#18181B"), fg=(appearance_config.get("accent_color") or self.accent_main))
            self.preview_title.pack(anchor="w")
            self.preview_body = tk.Label(self.preview_inner, text="This is what body text looks like with your chosen colors.", font=("Segoe UI", 10), bg=(appearance_config.get("card_color") or "#18181B"), fg=(appearance_config.get("text_color") or "#F4F4F5"))
            self.preview_body.pack(anchor="w", pady=(4, 10))
            self.preview_btn_row = tk.Frame(self.preview_inner, bg=(appearance_config.get("card_color") or "#18181B"))
            self.preview_btn_row.pack(anchor="w")
            self.preview_btn1 = tk.Button(self.preview_btn_row, text="Primary Button", bg=(appearance_config.get("accent_color") or self.accent_main), fg="black", bd=0, font=("Segoe UI", 9, "bold"))
            self.preview_btn1.pack(side="left", padx=(0, 8), ipady=5, ipadx=12)
            self.preview_btn2 = tk.Button(self.preview_btn_row, text="Success", bg=(appearance_config.get("success_color") or "#10B981"), fg="black", bd=0, font=("Segoe UI", 9, "bold"))
            self.preview_btn2.pack(side="left", padx=(0, 8), ipady=5, ipadx=12)
            self.preview_btn3 = tk.Button(self.preview_btn_row, text="Error", bg=(appearance_config.get("error_color") or "#EF4444"), fg="white", bd=0, font=("Segoe UI", 9, "bold"))
            self.preview_btn3.pack(side="left", ipady=5, ipadx=12)

            def update_preview():
                try:
                    def g(k, d): return self.appearance_swatches[k][0].get().strip() or d if k in self.appearance_swatches else d
                    self.appearance_preview_frame.configure(bg=g("bg_color", "#09090B"), highlightbackground=g("card_border_color", "#27272A"))
                    self.preview_inner.configure(bg=g("card_color", "#18181B"))
                    self.preview_title.configure(bg=g("card_color", "#18181B"), fg=g("accent_color", self.accent_main))
                    self.preview_body.configure(bg=g("card_color", "#18181B"), fg=g("text_color", "#F4F4F5"))
                    self.preview_btn_row.configure(bg=g("card_color", "#18181B"))
                    self.preview_btn1.configure(bg=g("accent_color", self.accent_main))
                    self.preview_btn2.configure(bg=g("success_color", "#10B981"))
                    self.preview_btn3.configure(bg=g("error_color", "#EF4444"))
                except Exception: pass

            # -- Import / export --
            io_card = card("IMPORT / EXPORT THEME", color="#F59E0B")
            def export_theme():
                path = filedialog.asksaveasfilename(defaultextension=".json", initialfile="appearance_theme.json", title="export theme", filetypes=[("JSON", "*.json")])
                if not path: return
                try:
                    with open(path, "w", encoding="utf-8") as f: json.dump(appearance_config, f, indent=4)
                    messagebox.showinfo("export", "theme exported.")
                except Exception as e:
                    messagebox.showerror("export failed", str(e))
            def import_theme():
                path = filedialog.askopenfilename(title="import theme", filetypes=[("JSON", "*.json")])
                if not path: return
                try:
                    with open(path, "r", encoding="utf-8") as f: data = json.load(f)
                    appearance_config.update(data)
                    for key, (entry, swatch) in self.appearance_swatches.items():
                        if key in data:
                            entry.delete(0, "end"); entry.insert(0, data[key])
                            try: swatch.configure(bg=data[key])
                            except Exception: pass
                    update_preview()
                    messagebox.showinfo("import", "theme imported. click SAVE APPEARANCE to persist it.")
                except Exception as e:
                    messagebox.showerror("import failed", str(e))
            io_row = tk.Frame(io_card, bg="#18181B"); io_row.pack(fill="x")
            tk.Button(io_row, text="Export Theme to File...", font=("Segoe UI", 9, "bold"), bg="#27272A", fg="white", bd=0, cursor="hand2", command=export_theme).pack(side="left", ipady=6, ipadx=14, padx=(0, 8))
            tk.Button(io_row, text="Import Theme from File...", font=("Segoe UI", 9, "bold"), bg="#27272A", fg="white", bd=0, cursor="hand2", command=import_theme).pack(side="left", ipady=6, ipadx=14)

            def save_appearance():
                for key, (entry, swatch) in self.appearance_swatches.items():
                    val = entry.get().strip()
                    if val: appearance_config[key] = val
                try: appearance_config["font_size"] = int(self.entry_font_size.get())
                except Exception: pass
                appearance_config["font_family"] = self.cb_font_family.get()
                appearance_config["density"] = self.var_density.get()
                appearance_config["corner_style"] = self.var_corner.get()
                appearance_config["reduce_motion"] = self.var_reduce_motion.get()
                save_appearance_config()
                self.log("[system]", "[info] appearance settings saved. restart the app to fully apply the new theme.", "sysmsg")

            def reset_appearance():
                for key, (entry, swatch) in self.appearance_swatches.items():
                    entry.delete(0, "end")
                    entry.insert(0, DEFAULTS.get(key, ""))
                    swatch.configure(bg=DEFAULTS.get(key, "#18181B"))
                self.cb_font_family.set("Segoe UI")
                self.entry_font_size.delete(0, "end"); self.entry_font_size.insert(0, "10")
                self.var_density.set("comfortable")
                self.var_corner.set("sharp")
                self.var_reduce_motion.set(False)
                update_preview()

            btnr = tk.Frame(outer, bg="#09090B")
            btnr.pack(fill="x", pady=(5, 30))
            tk.Button(btnr, text="SAVE APPEARANCE", font=("Segoe UI", 11, "bold"), bg="#10B981", fg="black", bd=0, cursor="hand2", command=save_appearance).pack(side="left", ipady=8, ipadx=20, padx=(0, 10))
            tk.Button(btnr, text="RESET TO DEFAULTS", font=("Segoe UI", 10, "bold"), bg="#27272A", fg="white", bd=0, cursor="hand2", command=reset_appearance).pack(side="left", ipady=8, ipadx=20)
            update_preview()
        except Exception as e:
            self.log("[system]", f"[err] appearance tab build error: {e}", "err")

    # ---------------- OBS integration tab ----------------
    GUIDE_FLAG_FILE = "guide_seen.flag"

    def show_welcome_guide(self, force=False):
        if not force and os.path.exists(self.GUIDE_FLAG_FILE):
            return

        BG, BG2, BG3, BORDER = "#09090B", "#18181B", "#27272A", "#3F3F46"
        TEXT, TEXTDIM = "#F4F4F5", "#A1A1AA"
        ACCENT, ACCENT2 = self.accent_main, "#00E5FF" if self.is_multistream else "#8B5CF6"
        YELLOW, GREEN = "#F59E0B", "#10B981"

        W, H = 820, 580
        dlg = tk.Toplevel(self.root)
        dlg.title("📖  ChatPlays — User Guide")
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.grab_set()
        self.root.update_idletasks()
        rx = self.root.winfo_x() + (self.root.winfo_width()  - W) // 2
        ry = self.root.winfo_y() + (self.root.winfo_height() - H) // 2
        dlg.geometry(f"{W}x{H}+{rx}+{ry}")

        hdr = tk.Frame(dlg, bg=ACCENT, height=54)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📖  ChatPlays Control Panel — User Guide",
                 bg=ACCENT, fg="#ffffff",
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=18, pady=10)
        tk.Label(hdr, text=f"v{VERSION}",
                 bg=ACCENT, fg="#eeeeee",
                 font=("Segoe UI", 9)).pack(side="right", padx=18)

        body = tk.Frame(dlg, bg=BG)
        body.pack(fill="both", expand=True)

        sidebar_outer = tk.Frame(body, bg=BG2, width=220)
        sidebar_outer.pack(side="left", fill="y")
        sidebar_outer.pack_propagate(False)

        tk.Label(sidebar_outer, text="CHAPTERS", bg=BG2, fg=TEXTDIM,
                 font=("Segoe UI", 7, "bold")).pack(anchor="w", padx=12, pady=(10, 2))

        sb_canvas = tk.Canvas(sidebar_outer, bg=BG2, highlightthickness=0)
        sb_scroll = ttk.Scrollbar(sidebar_outer, orient="vertical", command=sb_canvas.yview)
        sb_canvas.configure(yscrollcommand=sb_scroll.set)
        sb_scroll.pack(side="right", fill="y")
        sb_canvas.pack(side="left", fill="both", expand=True)

        sidebar = tk.Frame(sb_canvas, bg=BG2)
        sidebar_window = sb_canvas.create_window((0, 0), window=sidebar, anchor="nw")

        def _on_sidebar_configure(event):
            sb_canvas.configure(scrollregion=sb_canvas.bbox("all"))
            sb_canvas.itemconfig(sidebar_window, width=event.width)

        sidebar.bind("<Configure>", lambda e: sb_canvas.configure(
            scrollregion=sb_canvas.bbox("all")))
        sb_canvas.bind("<Configure>", _on_sidebar_configure)
        sb_canvas.bind("<MouseWheel>",
            lambda e: sb_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        sidebar.bind("<MouseWheel>",
            lambda e: sb_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        right_pane = tk.Frame(body, bg=BG)
        right_pane.pack(side="left", fill="both", expand=True)
        txt_frame = tk.Frame(right_pane, bg=BORDER, bd=1)
        txt_frame.pack(fill="both", expand=True, padx=10, pady=10)
        txt = tk.Text(txt_frame, bg=BG3, fg=TEXT,
                      font=("Segoe UI", 10), wrap="word",
                      relief="flat", bd=0, padx=16, pady=12,
                      state="disabled", cursor="arrow",
                      selectbackground=ACCENT)
        sb = ttk.Scrollbar(txt_frame, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(fill="both", expand=True)

        txt.tag_configure("h1",   font=("Segoe UI", 15, "bold"), foreground=ACCENT2, spacing1=4,  spacing3=6)
        txt.tag_configure("h2",   font=("Segoe UI", 11, "bold"), foreground=YELLOW,  spacing1=12, spacing3=3)
        txt.tag_configure("body", font=("Segoe UI", 10),          foreground=TEXT,    spacing1=2,  lmargin1=4, lmargin2=4)
        txt.tag_configure("code", font=("Consolas", 9),           foreground=GREEN,   background=BG2, spacing1=1, lmargin1=16, lmargin2=16)
        txt.tag_configure("tip",  font=("Segoe UI", 9, "italic"), foreground=TEXTDIM, spacing1=3,  lmargin1=4)

        CHAPTERS = [
            ("🚀  Getting Started", [
                ("h1",   "🚀  Getting Started"),
                ("body", "Welcome to ChatPlays! This guide covers every tab so you can get live fast."),
                ("h2",   "First-time setup"),
                ("body", "1.  Go to the  Dashboard  tab and paste your channel/video into  YOUTUBE STREAM LINK."),
                ("body", "2.  Pick your target VM -- click the  target: ...  button to cycle through registered VMs, or set the exact path on the  VM Config  tab."),
                ("body", "3.  Click  Connect Chat  -- the bot connects to chat and starts listening."),
                ("h2",   "Stopping"),
                ("body", "Click  Disconnect Chat.  The VM keeps running; only the chat listener stops."),
                ("h2",   "Multi-streaming"),
                ("body", "The  Extra Things  tab can spawn up to 5 additional listener instances (ports 5001-5005) so you can run several streams/video IDs from one setup."),
            ]),
            ("⌨️  Chat Commands", [
                ("h1",   "⌨️  Chat Commands"),
                ("body", "Viewers type commands in your live chat. Every command starts with  !"),
                ("h2",   "Keyboard & mouse"),
                ("code", "  !type hello / !send hello   →  type text (send also presses Enter)"),
                ("code", "  !combo win+r                →  key combo"),
                ("code", "  !key enter                  →  single key"),
                ("code", "  !keydown / !keyup shift     →  hold / release a key"),
                ("code", "  !click / !rclick             →  left / right click"),
                ("code", "  !move 500 300 / !abs         →  move cursor"),
                ("code", "  !scroll 3                    →  scroll (negative = down)"),
                ("h2",   "Music / Video / Soundboard"),
                ("body", "See the dedicated chapters for these -- each has its own tab and command set."),
                ("h2",   "Voting"),
                ("body", "Restart, revert, and ban all use a vote system with a configurable threshold -- set thresholds and whitelist/blocked users on the  Automation  tab."),
                ("tip",  "Tip: the stream owner and whitelisted admins bypass vote requirements."),
            ]),
            ("📊  Dashboard", [
                ("h1",   "📊  Dashboard"),
                ("body", "Your home base -- connection controls, live stats, and quick system actions."),
                ("h2",   "YouTube Stream Link"),
                ("body", "Paste your channel handle or video URL, then  Connect Chat  /  Disconnect Chat."),
                ("h2",   "System Status"),
                ("body", "Shows the bot's current state and the active VM target. Click the target button to cycle between registered VMs -- this is disabled/ignored while OS Voting is enabled, since OS Voting decides the active VM instead."),
                ("h2",   "Live Stats"),
                ("body", "Uptime, Commands Run (with failure count), Viewers, and Likes, refreshed continuously."),
                ("h2",   "System Controls"),
                ("body", "One-click buttons for common admin actions (restart, revert, etc.) without needing to type chat commands yourself."),
            ]),
            ("🖥️  VM Config", [
                ("h1",   "🖥️  VM Config"),
                ("body", "Where the bot's virtual machine connection actually lives."),
                ("h2",   "VBoxManage Path"),
                ("body", "The full path to VBoxManage.exe -- Browse to find it if it's not auto-detected."),
                ("h2",   "Target VM Name"),
                ("body", "The specific VM this bot controls, by its registered VirtualBox name. Combined with a snapshot name for  !revert."),
                ("tip",  "Tip: this tab uses the same JSON import/export bar as most other tabs -- handy for backing up or copying a config to another machine."),
            ]),
            ("⚙️  Settings", [
                ("h1",   "⚙️  Settings"),
                ("body", "Core behavior tuning for the whole bot."),
                ("h2",   "Key options"),
                ("code", "  command_prefix        →  what character starts a command (default !)"),
                ("code", "  keyboard_layout        →  match your VM's actual keyboard layout"),
                ("code", "  auto_start             →  auto-connect chat on launch"),
                ("code", "  enable_chat            →  master on/off switch for command processing"),
                ("code", "  say_admin_only         →  restrict !say to admins"),
                ("code", "  strict_live_check      →  refuse to start if the stream isn't actually live"),
                ("code", "  enable_ocr             →  computer-vision checks (if configured)"),
                ("code", "  ultra_speed            →  faster input timing, less safe on slow VMs"),
                ("code", "  typing_speed / key_delay / mouse_delay  →  fine-tune input timing"),
            ]),
            ("🧩  Extra Things", [
                ("h1",   "🧩  Extra Things"),
                ("body", "Multi-streaming setup -- run more than one chat listener at once."),
                ("h2",   "Spawn Multi-Stream 1-5"),
                ("body", "Each button launches an additional instance bound to its own port (5001-5005), so several YouTube video IDs can be handled simultaneously."),
                ("h2",   "Multi-Stream Video IDs"),
                ("body", "+ Add Video ID  to queue another stream to listen on; select and  ✕ Remove Selected  to drop one."),
            ]),
            ("🗳️  OS Voting", [
                ("h1",   "🗳️  OS Voting"),
                ("body", "Let chat vote to switch between different VMs/operating systems live."),
                ("h2",   "Setup"),
                ("body", "1.  Tick  Enable OS-switch voting."),
                ("body", "2.  Fill in rows: name, chat trigger, VM path -- click  + New VM  to add another row, or  Refresh VM List  to repopulate the dropdown from registered VMs."),
                ("body", "3.  Click  Save OS Voting Config."),
                ("h2",   "How it works"),
                ("body", "Viewers type the trigger (e.g.  !win7). Once enough votes land, the bot switches to that VM."),
                ("tip",  "Tip: while OS Voting is on, the Dashboard's VM target button is ignored -- OS Voting owns which VM is active."),
            ]),
            ("🖱️  Real PC", [
                ("h1",   "🖱️  Real PC"),
                ("body", "Gives chat direct control of the HOST machine over VNC -- not a VM. Use with real caution."),
                ("h2",   "VNC Target"),
                ("body", "Host / port / password for the VNC session, plus  Connect  /  Disconnect  and a live status indicator."),
                ("h2",   "Safety controls"),
                ("body", "Cooldown between commands, Whitelist-only mode, Failsafe (move mouse to a screen corner to abort), and Text-only mode (blocks mouse/screenshot access, keyboard only)."),
                ("h2",   "Whitelist / Blocked"),
                ("body", "Comma-separated usernames -- combine with Start/Stop Real PC Bot to control exactly who can touch your real computer and when."),
                ("tip",  "Tip: this is the most powerful and most dangerous feature here. Keep the whitelist tight."),
            ]),
            ("💾  VBox (VBoxManage + Internet)", [
                ("h1",   "💾  VBox"),
                ("body", "The path to VBoxManage.exe, plus live internet control for the target VM."),
                ("h2",   "VBoxManage Path"),
                ("body", "Keyboard/mouse input to the VM goes through VirtualBox's own COM API, not VNC -- this tab just needs to know where VBoxManage.exe lives."),
                ("h2",   "!enableinternet / !disableinternet"),
                ("body", "Switches the VM's first network adapter's link state on/off LIVE via VBoxManage controlvm setlinkstate1 -- works on a running VM, no restart needed."),
            ]),
            ("🔁  Automation", [
                ("h1",   "🔁  Automation"),
                ("body", "TTS, event sounds, scheduled tasks, and access control, all in one tab."),
                ("h2",   "Text-to-Speech"),
                ("body", "Enable announcements, tune rate (wpm) and volume, Test Voice before going live."),
                ("h2",   "Event Sound Files"),
                ("body", "Browse and preview (▶) a sound file per event type, then Save Event Sounds."),
                ("h2",   "Scheduled Tasks"),
                ("body", "Enable scheduled tasks, then Add Task with a label, action, and hour/minute -- Remove Selected to delete one."),
                ("h2",   "Access Control"),
                ("body", "Whitelist and Blocked lists (comma-separated) apply bot-wide -- this is also where vote-threshold-related access rules live."),
                ("h2",   "Minimize to Tray"),
                ("body", "Keep the bot running in the background; right-click the tray icon to restore or fully exit."),
            ]),
            ("📋  Event Log", [
                ("h1",   "📋  Event Log"),
                ("body", "A running record of everything the bot does."),
                ("body", "Filter by type, Refresh Now / Apply Filter, Export to File for a permanent copy, or Clear View to reset what's shown (the underlying log file is untouched)."),
            ]),
            ("🎨  Appearance", [
                ("h1",   "🎨  Appearance"),
                ("body", "Customize the look of this control panel itself."),
                ("body", "Pick colors, Font Family, Base Font Size, Layout Density, and Card Corner Style -- a live sample card shows your changes before you commit."),
                ("body", "Export Theme to File / Import Theme from File to reuse a look across setups, Save Appearance to apply, Reset to Defaults to undo."),
            ]),
            ("📡  OBS", [
                ("h1",   "📡  OBS"),
                ("body", "Connects to OBS over its WebSocket (OBS 28+, requires obsws-python) and switches named scenes automatically for key events."),
                ("h2",   "Connection"),
                ("body", "Host / Port / Password, then Connect. If the first attempt fails, it retries automatically in the background."),
                ("h2",   "Scene Names"),
                ("body", "Main, Starting, BRB, Reverting, Restarting, Error, and Shutdown scenes -- each maps to a moment in the bot's lifecycle. Use the Test buttons to confirm each one switches correctly before you're live."),
                ("tip",  "Tip: Save your settings once connection + all scene names look right -- they persist across restarts."),
            ]),
            ("🎵  Music / 🎬 Video / 🔉 Soundboard", [
                ("h1",   "🎵  Music / Video / Soundboard"),
                ("body", "Three dedicated tabs for VLC-powered playback triggered from chat, independent of the VM."),
                ("h2",   "Music & Video"),
                ("body", "Queue-based song/video requests with their own enable toggles and playback controls in each tab."),
                ("h2",   "Soundboard"),
                ("body", "Web-search based sound clips, played instantly on the host's speakers."),
            ]),
            ("⚙️  Commands", [
                ("h1",   "⚙️  Commands"),
                ("body", "Every built-in command this bot recognizes, all in one place. Prefix is whatever's set on the Settings tab (default !)."),
                ("h2",   "Keyboard / Mouse primitives"),
                ("code", "  !type text / !send text   -- type (send also presses Enter)"),
                ("code", "  !key name / !combo a+b+c   -- single key / key combo"),
                ("code", "  !keydown name / !keyup name -- hold / release a key"),
                ("code", "  !click / !rclick / !mclick [count] -- left/right/middle click"),
                ("code", "  !move dx dy / !abs x y      -- relative / absolute mouse move"),
                ("code", "  !scroll amount / !drag x1 y1 x2 y2"),
                ("code", "  !wait seconds"),
                ("code", "  !run program / !cmd command -- Win+R launch / admin cmd"),
                ("code", "  !winkey key / !dir path / !taskkill name.exe / !openfile path"),
                ("h2",   "Chaos / Fun"),
                ("code", "  !roll / !coinflip"),
                ("code", "  !shake [amt] / !jiggle [amt] / !circle [radius] / !spiral"),
                ("code", "  !msgbox text / !spam text [count] / !countdown [n]"),
                ("code", "  !matrix / !colorscheme HH / !rainbow / !beep [freq] [ms]"),
                ("code", "  !notepadflood [n] / !exeflood / !txtflood / !deskflood [n]"),
                ("h2",   "Voice (types into the VM via Win+R -- see Log Broadcast on Automation for host-side TTS of the bot's own logs instead)"),
                ("code", "  !tts text / !ttsloop text / !ttsxp text / !ttsxploop text"),
                ("h2",   "App Launchers (!name -- opens straight up)"),
                ("code", "  notepad, calc, paint, wordpad, cmdnew, powershell, regedit, explorer,"),
                ("code", "  ie, wmp, control, devmgr, taskmgrapp, sticky, snip, magnify, narrator,"),
                ("code", "  osk, charmap, eventvwr, perfmon, resmon, defrag, cleanmgr, msconfig,"),
                ("code", "  dxdiag, sndvol, dvdmaker, solitaire, minesweeper, hearts, spider,"),
                ("code", "  freecell, mahjong, chess, inkball, purble"),
                ("h2",   "Combo Shortcuts (!name -- fires the key combo directly)"),
                ("code", "  altf4, alttab, copy, paste, cut, undo, redo, selectall, save, saveas,"),
                ("code", "  find, replace, new, closetab, zoomin, zoomout, zoomreset, fullscreen,"),
                ("code", "  refresh, hardrefresh, back, forward, bold, italic, underline, capslock,"),
                ("code", "  numlock, scrolllock, prtsc, altprintscreen, desktop, lock, taskman, startmenu"),
                ("h2",   "CMD Utilities (open !cmdnew first, then these type into it)"),
                ("code", "  tasklist, cls, tree, ver, date, time, diskpart, chkdsk, sfc,"),
                ("code", "  gpupdate, abortshutdown, logoff, hibernate"),
                ("h2",   "VM Lifecycle (follows whichever backend the current VM uses)"),
                ("code", "  !startvm / !shutdown / !killvm / !poweroff / !restartvm / !revert"),
                ("code", "  !makesnapshot [name] / !deletesnapshot / !forcefixvm / !efail"),
                ("code", "  !pausevm / !resumevm / !vmsavestate / !vmstatus"),
                ("code", "  !acpishutdown / !acpirestart / !discardvmwarestate"),
                ("code", "  !enableinternet / !disableinternet -- follows the CURRENT vm's backend"),
                ("code", "  !enableinternetvmware / !disableinternetvmware -- always the VMware NAT Service"),
                ("code", "  !enableinternetvbox / !disableinternetvbox -- always VBoxManage setlinkstate1"),
                ("code", "  !closevmwarewindow -- sends Enter to a VMware dialog, no focus needed"),
                ("h2",   "Info"),
                ("code", "  !ping / !uptime / !help / !stats / !history / !leaderboard / !queue / !status"),
                ("h2",   "Moderation / Admin"),
                ("code", "  !pausechat / !enablechat / !enablecv / !votestop / !clear / !say text"),
                ("code", "  !ban @user  -- chat-vote (or instant for admins) temporary command ban"),
                ("h2",   "Music / Video / Soundboard"),
                ("code", "  !sr / !skipsr / !clearsr / !findsr    -- song requests"),
                ("code", "  !vr / !skipvr / !clearvr / !findvr    -- video requests"),
                ("code", "  !sb / !sbid / !gtts                    -- soundboard / Google TTS"),
                ("tip",  "Tip: most of these are vote-gated or admin-only depending on your Permissions tab settings -- check there if a command seems to be ignored."),
            ]),
        ]

        _chapter_btns = []

        def _show_chapter(idx):
            _, sections = CHAPTERS[idx]
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            for tag, content in sections:
                txt.insert("end", content + "\n", tag)
            txt.configure(state="disabled")
            txt.yview_moveto(0)
            for i, btn in enumerate(_chapter_btns):
                btn.configure(
                    bg=ACCENT if i == idx else BG2,
                    fg="#ffffff" if i == idx else TEXT,
                )

        for i, (title, _) in enumerate(CHAPTERS):
            btn = tk.Button(
                sidebar, text=title,
                bg=BG2, fg=TEXT,
                activebackground=ACCENT, activeforeground="#fff",
                relief="flat", bd=0, anchor="w",
                font=("Segoe UI", 9), padx=12, pady=7, cursor="hand2",
                command=lambda idx=i: _show_chapter(idx),
            )
            btn.pack(fill="x", pady=1)
            btn.bind("<MouseWheel>",
                lambda e: sb_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
            _chapter_btns.append(btn)

        _show_chapter(0)

        footer = tk.Frame(dlg, bg=BG2, pady=8)
        footer.pack(fill="x", side="bottom")

        dont_show_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            footer, text="Don't show this guide on startup",
            variable=dont_show_var,
            bg=BG2, fg=TEXTDIM,
            selectcolor=BG3,
            activebackground=BG2, activeforeground=TEXT,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=16)

        def _close_guide():
            if dont_show_var.get():
                try:
                    with open(self.GUIDE_FLAG_FILE, "w") as f:
                        f.write("seen")
                except Exception:
                    pass
            dlg.destroy()

        tk.Button(footer, text="✔  Got it, close guide",
                  font=("Segoe UI", 10, "bold"), bg=GREEN, fg="black",
                  activebackground="#0EA271", activeforeground="black",
                  bd=0, cursor="hand2",
                  command=_close_guide).pack(side="right", padx=16, ipady=5, ipadx=10)

        dlg.protocol("WM_DELETE_WINDOW", _close_guide)


    # ---------------- Stats tab ----------------
    def build_stats_tab(self):
        try:
            BG, BG2, BG3, TEXT, TEXTDIM = "#09090B", "#18181B", "#27272A", "#F4F4F5", "#A1A1AA"
            _sp = self._make_tab_scrollable(self.tab_stats)
            wrapper = tk.Frame(_sp, bg=BG)
            wrapper.pack(fill="both", expand=True)
            border = tk.Frame(wrapper, bg=BG3)
            border.pack(pady=30, padx=40, fill="both", expand=True)
            content = tk.Frame(border, bg=BG2, padx=25, pady=25)
            content.pack(fill="both", expand=True, padx=1, pady=1)

            tk.Label(content, text="📊  STATISTICS", font=("Segoe UI", 12, "bold"),
                     bg=BG2, fg=self.accent_main).pack(anchor="w")
            tk.Label(content, text="Real-time tracking, refreshed every 2 seconds.",
                     font=("Segoe UI", 9), bg=BG2, fg=TEXTDIM).pack(anchor="w", pady=(0, 18))

            grid = tk.Frame(content, bg=BG2)
            grid.pack(fill="x")
            for c in range(4):
                grid.columnconfigure(c, weight=1)

            def stat_card(parent, row, col, title, colorfg):
                card = tk.Frame(parent, bg=BG3, padx=16, pady=14)
                card.grid(row=row, column=col, sticky="we", padx=6, pady=6)
                tk.Label(card, text=title, font=("Segoe UI", 8, "bold"), bg=BG3, fg=TEXTDIM).pack(anchor="w")
                val = tk.Label(card, text="—", font=("Consolas", 18, "bold"), bg=BG3, fg=colorfg)
                val.pack(anchor="w", pady=(4, 0))
                return val

            self.stat_uptime_val    = stat_card(grid, 0, 0, "UPTIME", TEXT)
            self.stat_commands_val  = stat_card(grid, 0, 1, "COMMANDS RUN", self.accent_main)
            self.stat_failed_val    = stat_card(grid, 0, 2, "FAILED", "#EF4444")
            self.stat_viewers_val   = stat_card(grid, 0, 3, "VIEWERS", "#10B981")
            self.stat_likes_val     = stat_card(grid, 1, 0, "LIKES", "#10B981")
            self.stat_leaderboard_hdr = tk.Label(content, text="TOP COMMAND USERS", font=("Segoe UI", 10, "bold"),
                                                 bg=BG2, fg="#8B5CF6")
            self.stat_leaderboard_hdr.pack(anchor="w", pady=(20, 6))
            self.stat_leaderboard_list = tk.Listbox(content, font=("Consolas", 10), bg=BG,
                                                    fg=self.accent_main, bd=0, highlightthickness=0, height=8)
            self.stat_leaderboard_list.pack(fill="both", expand=True)

            def refresh_stats():
                if not hasattr(self, 'stat_uptime_val'):
                    return
                try:
                    up = int(time.time() - script_start_time)
                    d, r = divmod(up, 86400); h, r = divmod(r, 3600); m, s = divmod(r, 60)
                    self.stat_uptime_val.config(text=(f"{d}d {h}h {m}m" if d else f"{h}h {m}m {s}s"))
                    self.stat_commands_val.config(text=str(total_commands_executed))
                    self.stat_failed_val.config(text=str(total_commands_failed))
                    self.stat_viewers_val.config(text=str(current_viewers))
                    self.stat_likes_val.config(text=str(current_likes))
                    self.stat_leaderboard_list.delete(0, "end")
                    counts = getattr(self, "user_cmd_counts", {}) or {}
                    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
                    if not top:
                        self.stat_leaderboard_list.insert("end", "  no commands recorded yet this session")
                    for u, c in top:
                        self.stat_leaderboard_list.insert("end", f"  {u}: {c}")
                except Exception:
                    pass
                if self.running: self.root.after(2000, refresh_stats)
            refresh_stats()
        except Exception as e:
            self.log("[system]", f"[err] stats tab build error: {e}", "err")

    # ---------------- Permissions tab (extracted + advanced from Automation) ----------------
    def build_permissions_tab(self):
        try:
            BG, BG2, BG3, TEXT, TEXTDIM = "#09090B", "#18181B", "#27272A", "#F4F4F5", "#A1A1AA"
            wrapper = tk.Frame(self.tab_permissions, bg=BG)
            wrapper.pack(fill="both", expand=True)
            canvas = tk.Canvas(wrapper, bg=BG, highlightthickness=0)
            scrollbar = ttk.Scrollbar(wrapper, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True, padx=(24, 0), pady=20)
            scrollbar.pack(side="right", fill="y")
            outer = tk.Frame(canvas, bg=BG)
            outer_window = canvas.create_window((0, 0), window=outer, anchor="nw")
            outer.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.bind("<Configure>", lambda e: canvas.itemconfigure(outer_window, width=e.width - 20))
            def _perm_wheel(e): canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _perm_wheel))
            canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

            tk.Label(outer, text="🔒  Permissions", font=("Segoe UI", 13, "bold"),
                     bg=BG, fg=self.accent_main).pack(anchor="w", padx=4)
            tk.Label(outer, text="Vote thresholds, cooldowns, and command spam protection.",
                     font=("Segoe UI", 9), bg=BG, fg=TEXTDIM).pack(anchor="w", padx=4, pady=(2, 14))

            card = ttk.Frame(outer, style="Card.TFrame", padding=16)
            card.pack(fill="x", pady=(0, 14))
            tk.Label(card, text="Vote Thresholds & Cooldowns", font=("Segoe UI", 11, "bold"),
                     bg=BG2, fg=TEXT).pack(anchor="w")
            tk.Label(card, text="'Spam' fields: if the SAME command is used that many times within that many seconds "
                                 "(by anyone), that one command locks out for 10s -- everything else keeps working.",
                     font=("Segoe UI", 8), bg=BG2, fg=TEXTDIM, wraplength=560, justify="left").pack(anchor="w", pady=(4, 12))

            self.perm_entries = {}
            grid = tk.Frame(card, bg=BG2)
            grid.pack(fill="x")
            perm_fields = [("restart_votes", "Restart votes needed"), ("revert_votes", "Revert votes needed"),
                           ("ban_votes", "Ban votes needed"), ("action_cooldown", "Action cooldown (s)"),
                           ("command_spam_threshold", "Spam: uses before cooldown"), ("command_spam_window", "Spam: within (s)")]
            for i, (key, label) in enumerate(perm_fields):
                cell = tk.Frame(grid, bg=BG2)
                cell.grid(row=i // 3, column=i % 3, sticky="w", padx=(0, 24), pady=6)
                tk.Label(cell, text=label.upper(), font=("Segoe UI", 8, "bold"), bg=BG2, fg=TEXTDIM).pack(anchor="w")
                e = tk.Entry(cell, width=10, font=("Consolas", 10), bg=BG, fg="white", insertbackground="white",
                             bd=0, highlightthickness=1, highlightbackground=BG3)
                e.pack(ipady=5, pady=(2, 0))
                e.insert(0, str(permissions_config.get(key, "")))
                self.perm_entries[key] = e

            def save_perm_settings():
                for key, e in self.perm_entries.items():
                    try: permissions_config[key] = int(e.get())
                    except Exception: pass
                permissions_config["vote_threshold_percent_enabled"] = self.perm_pct_enabled_var.get()
                try: permissions_config["vote_threshold_percent"] = max(1, min(100, int(self.perm_pct_var.get())))
                except Exception: pass
                permissions_config["youtube_api_key"] = self.perm_api_key_var.get().strip()
                save_permissions_config()
                self.log("[system]", "[info] permissions saved.", "sysmsg")

            tk.Button(card, text="SAVE", bg="#10B981", fg="black", bd=0, cursor="hand2",
                      font=("Segoe UI", 9, "bold"), command=save_perm_settings
                      ).pack(anchor="w", pady=(14, 0), ipady=5, ipadx=14)

            # ── Vote Threshold by % of Viewers ──
            pct_card = ttk.Frame(outer, style="Card.TFrame", padding=16)
            pct_card.pack(fill="x", pady=(0, 14))
            tk.Label(pct_card, text="Vote Threshold by % of Viewers", font=("Segoe UI", 11, "bold"),
                     bg=BG2, fg="#8B5CF6").pack(anchor="w")
            tk.Label(pct_card,
                     text="When enabled, restart/revert/ban votes need this % of current live viewers instead of "
                          "a fixed count above. Requires a YouTube Data API v3 key -- falls back to the fixed "
                          "counts if no live viewer number is available yet.",
                     font=("Segoe UI", 8), bg=BG2, fg=TEXTDIM, wraplength=560, justify="left").pack(anchor="w", pady=(4, 10))

            self.perm_pct_enabled_var = tk.BooleanVar(value=permissions_config.get("vote_threshold_percent_enabled", False))
            ttk.Checkbutton(pct_card, text="Enable % of viewers threshold", variable=self.perm_pct_enabled_var,
                            style="Toggle.TCheckbutton").pack(anchor="w")

            pct_row = tk.Frame(pct_card, bg=BG2)
            pct_row.pack(anchor="w", pady=(8, 0))
            tk.Label(pct_row, text="Percent of viewers required:", bg=BG2, fg=TEXT,
                     font=("Segoe UI", 9)).pack(side="left", padx=(0, 8))
            self.perm_pct_var = tk.IntVar(value=permissions_config.get("vote_threshold_percent", 30))
            tk.Spinbox(pct_row, textvariable=self.perm_pct_var, from_=1, to=100, width=5,
                      bg=BG, fg=TEXT, insertbackground=TEXT, buttonbackground=BG3,
                      font=("Segoe UI", 11, "bold"), relief="flat", bd=1).pack(side="left")
            tk.Label(pct_row, text="%", bg=BG2, fg=TEXT, font=("Segoe UI", 9)).pack(side="left", padx=(4, 0))

            api_row = tk.Frame(pct_card, bg=BG2)
            api_row.pack(anchor="w", pady=(12, 0), fill="x")
            tk.Label(api_row, text="YouTube Data API v3 key:", bg=BG2, fg=TEXT,
                     font=("Segoe UI", 9)).pack(side="left", padx=(0, 8))
            self.perm_api_key_var = tk.StringVar(value=permissions_config.get("youtube_api_key", ""))
            tk.Entry(api_row, textvariable=self.perm_api_key_var, width=40, show="•",
                     font=("Consolas", 9), bg=BG, fg="white", insertbackground="white",
                     bd=0, highlightthickness=1, highlightbackground=BG3).pack(side="left", ipady=4)
        except Exception as e:
            self.log("[system]", f"[err] permissions tab build error: {e}", "err")

    # ---------------- Users tab (extracted + advanced from Automation) ----------------
    def build_users_tab(self):
        try:
            BG, BG2, BG3, TEXT, TEXTDIM = "#09090B", "#18181B", "#27272A", "#F4F4F5", "#A1A1AA"
            wrapper = tk.Frame(self.tab_users, bg=BG)
            wrapper.pack(fill="both", expand=True)
            canvas = tk.Canvas(wrapper, bg=BG, highlightthickness=0)
            scrollbar = ttk.Scrollbar(wrapper, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True, padx=(24, 0), pady=20)
            scrollbar.pack(side="right", fill="y")
            outer = tk.Frame(canvas, bg=BG)
            outer_window = canvas.create_window((0, 0), window=outer, anchor="nw")
            outer.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.bind("<Configure>", lambda e: canvas.itemconfigure(outer_window, width=e.width - 20))
            def _users_wheel(e): canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _users_wheel))
            canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

            tk.Label(outer, text="🚫  Users", font=("Segoe UI", 13, "bold"),
                     bg=BG, fg=self.accent_main).pack(anchor="w", padx=4)
            tk.Label(outer, text="Whitelist, blocked users, and active/expired chat bans.",
                     font=("Segoe UI", 9), bg=BG, fg=TEXTDIM).pack(anchor="w", padx=4, pady=(2, 14))

            um_card = ttk.Frame(outer, style="Card.TFrame", padding=16)
            um_card.pack(fill="x", pady=(0, 14))
            tk.Label(um_card, text="Whitelist (comma-separated)", bg=BG2, fg=TEXT,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w")
            self.um_whitelist = tk.Entry(um_card, font=("Consolas", 10), bg=BG, fg="white",
                                         insertbackground="white", bd=0, highlightthickness=1, highlightbackground=BG3)
            self.um_whitelist.pack(fill="x", ipady=5, pady=(2, 10))
            self.um_whitelist.insert(0, ", ".join(sorted(whitelist_users)))
            tk.Label(um_card, text="Blocked (comma-separated, permanent)", bg=BG2, fg=TEXT,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w")
            self.um_blocked = tk.Entry(um_card, font=("Consolas", 10), bg=BG, fg="white",
                                       insertbackground="white", bd=0, highlightthickness=1, highlightbackground=BG3)
            self.um_blocked.pack(fill="x", ipady=5, pady=(2, 10))
            self.um_blocked.insert(0, ", ".join(sorted(blocked_users_persistent)))

            def save_user_mgmt_ui():
                global whitelist_users, blocked_users_persistent
                whitelist_users = set(normalize_username(u) for u in self.um_whitelist.get().split(",") if u.strip())
                blocked_users_persistent = set(normalize_username(u) for u in self.um_blocked.get().split(",") if u.strip())
                save_user_mgmt()
                self.log("[system]", "[info] user management lists saved.", "sysmsg")
            tk.Button(um_card, text="SAVE", bg="#10B981", fg="black", bd=0, cursor="hand2",
                      font=("Segoe UI", 9, "bold"), command=save_user_mgmt_ui).pack(anchor="w", ipady=5, ipadx=14)

            # ── Active chat bans (!ban votes) ──
            ban_card = ttk.Frame(outer, style="Card.TFrame", padding=16)
            ban_card.pack(fill="both", expand=True)
            tk.Label(ban_card, text="Active Chat Bans", font=("Segoe UI", 11, "bold"),
                     bg=BG2, fg="#EF4444").pack(anchor="w")
            tk.Label(ban_card, text=f"!ban @user needs {permissions_config.get('ban_votes', 3)} chat votes to temporarily "
                                     f"ban someone from using commands. Unban here any time.",
                     font=("Segoe UI", 8), bg=BG2, fg=TEXTDIM, wraplength=560, justify="left").pack(anchor="w", pady=(4, 10))

            self.banned_users_listbox = tk.Listbox(ban_card, font=("Consolas", 10), bg=BG, fg="#EF4444",
                                                    bd=0, highlightthickness=0, height=8)
            self.banned_users_listbox.pack(fill="both", expand=True, pady=(0, 10))

            def refresh_banned_list():
                if not hasattr(self, 'banned_users_listbox'):
                    return
                self.banned_users_listbox.delete(0, "end")
                now = time.time()
                active = {u: t for u, t in banned_users_chat.items() if t > now}
                if not active:
                    self.banned_users_listbox.insert("end", "  no active bans")
                for u, until in sorted(active.items(), key=lambda kv: -kv[1]):
                    remaining = int(until - now)
                    self.banned_users_listbox.insert("end", f"  {u}  --  {remaining // 60}m {remaining % 60}s remaining")
                if self.running: self.root.after(3000, refresh_banned_list)
            refresh_banned_list()

            def unban_selected():
                sel = self.banned_users_listbox.curselection()
                if not sel: return
                line = self.banned_users_listbox.get(sel[0])
                if "--" not in line: return
                uname = line.strip().split("  --")[0].strip()
                if uname in banned_users_chat:
                    del banned_users_chat[uname]
                    save_user_mgmt()
                    self.log("[system]", f"[info] unbanned {uname}.", "sysmsg")
                    refresh_banned_list()

            tk.Button(ban_card, text="UNBAN SELECTED", bg="#F59E0B", fg="black", bd=0, cursor="hand2",
                      font=("Segoe UI", 9, "bold"), command=unban_selected).pack(anchor="w", ipady=5, ipadx=14)
        except Exception as e:
            self.log("[system]", f"[err] users tab build error: {e}", "err")


    def build_obs_tab(self):
        try:
            BG, BG2, BG3 = "#09090B", "#18181B", "#27272A"
            TEXT, TEXTDIM = "#F4F4F5", "#A1A1AA"

            # Scrollable wrapper, matching the pattern used on VM Config / Settings tabs
            wrapper = tk.Frame(self.tab_obs, bg=BG)
            wrapper.pack(fill="both", expand=True)
            canvas = tk.Canvas(wrapper, bg=BG, highlightthickness=0)
            scrollbar = ttk.Scrollbar(wrapper, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True, padx=(24, 0), pady=20)
            scrollbar.pack(side="right", fill="y")
            outer = tk.Frame(canvas, bg=BG)
            outer_window = canvas.create_window((0, 0), window=outer, anchor="nw")
            outer.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.bind("<Configure>", lambda e: canvas.itemconfigure(outer_window, width=e.width - 20))
            def _obs_mousewheel(e): canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
            canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _obs_mousewheel))
            canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

            # ── Header ──
            hdr = tk.Frame(outer, bg=BG)
            hdr.pack(fill="x", padx=4, pady=(0, 14))
            avail_txt = "available" if obs_available else "not installed (pip install obsws-python)"
            tk.Label(hdr, text="📡  OBS Integration", font=("Segoe UI", 13, "bold"),
                     bg=BG, fg=self.accent_main).pack(anchor="w")
            tk.Label(hdr, text=f"obsws-python: {avail_txt}. Requires OBS Websocket enabled in OBS 28+.",
                     font=("Segoe UI", 9), bg=BG, fg=TEXTDIM).pack(anchor="w", pady=(2, 0))

            def _obs_apply_json(data):
                if isinstance(data, dict):
                    obs_config.update(data)
                    save_obs_config()
            self.add_json_io_bar(outer, self.tab_obs, self.build_obs_tab,
                                  lambda: dict(obs_config), _obs_apply_json, "obs_config")

            def field(parent, label, value, width=16, row=None, col=None, **grid_kw):
                cell = tk.Frame(parent, bg=BG2)
                if row is not None:
                    cell.grid(row=row, column=col, sticky="w", padx=(0, 20), pady=6, **grid_kw)
                else:
                    cell.pack(side="left", padx=(0, 16))
                tk.Label(cell, text=label, font=("Segoe UI", 8, "bold"), bg=BG2, fg=TEXTDIM).pack(anchor="w")
                e = tk.Entry(cell, width=width, font=("Consolas", 10), bg=BG, fg="white",
                             insertbackground="white", bd=0, highlightthickness=1,
                             highlightbackground=BG3, highlightcolor=self.accent_main)
                e.pack(ipady=5, pady=(2, 0))
                e.insert(0, value)
                return e

            # ── Connection card ──
            conn_card = ttk.Frame(outer, style="Card.TFrame", padding=16)
            conn_card.pack(fill="x", pady=(0, 14))
            tk.Label(conn_card, text="Connection", font=("Segoe UI", 11, "bold"),
                     bg=BG2, fg=TEXT).pack(anchor="w", pady=(0, 10))

            conn_row = tk.Frame(conn_card, bg=BG2)
            conn_row.pack(fill="x")
            self.obs_entry_host = field(conn_row, "HOST", obs_host, 14)
            self.obs_entry_port = field(conn_row, "PORT", str(obs_port), 6)
            self.obs_entry_pass = field(conn_row, "PASSWORD", obs_password, 16)
            self.obs_entry_pass.configure(show="*")

            self.obs_status_lbl = tk.Label(conn_card, text=f"status: {'connected' if obs_connected else 'disconnected'}",
                                           font=("Segoe UI", 9, "bold"), bg=BG2,
                                           fg=("#10B981" if obs_connected else "#EF4444"))
            self.obs_status_lbl.pack(anchor="w", pady=(12, 8))

            def do_connect():
                global obs_host, obs_port, obs_password
                obs_host = self.obs_entry_host.get().strip() or "localhost"
                try: obs_port = int(self.obs_entry_port.get())
                except Exception: pass
                obs_password = self.obs_entry_pass.get()
                ok = obs_connect()
                if ok:
                    self.obs_status_lbl.config(text="status: connected", fg="#10B981")
                    self.log("[system]", "[info] obs connect succeeded.", "sysmsg")
                else:
                    self.obs_status_lbl.config(text="status: failed, retrying in background...", fg="#F59E0B")
                    self.log("[system]", "[warn] obs connect failed on first try -- retrying automatically until it succeeds.", "sysmsg")
                    obs_connect_with_retry()

            def poll_obs_status():
                if hasattr(self, 'obs_status_lbl'):
                    if obs_connected:
                        self.obs_status_lbl.config(text="status: connected", fg="#10B981")
                    elif getattr(sys.modules[__name__], '_obs_connect_retry_running', False):
                        self.obs_status_lbl.config(text="status: retrying connection...", fg="#F59E0B")
                if self.running: self.root.after(2000, poll_obs_status)
            poll_obs_status()

            def do_disconnect():
                obs_disconnect()
                self.obs_status_lbl.config(text="status: disconnected", fg="#EF4444")

            btn_row = tk.Frame(conn_card, bg=BG2)
            btn_row.pack(fill="x")
            tk.Button(btn_row, text="Connect", font=("Segoe UI", 9, "bold"), bg="#10B981", fg="black",
                      bd=0, cursor="hand2", command=do_connect).pack(side="left", ipady=5, ipadx=14, padx=(0, 8))
            tk.Button(btn_row, text="Disconnect", font=("Segoe UI", 9, "bold"), bg="#EF4444", fg="white",
                      bd=0, cursor="hand2", command=do_disconnect).pack(side="left", ipady=5, ipadx=14)

            # ── Scene Names card ──
            scene_card = ttk.Frame(outer, style="Card.TFrame", padding=16)
            scene_card.pack(fill="x", pady=(0, 14))
            tk.Label(scene_card, text="Scene Names", font=("Segoe UI", 11, "bold"),
                     bg=BG2, fg="#8B5CF6").pack(anchor="w")
            tk.Label(scene_card, text="Each maps to a moment in the bot's lifecycle. Use Test to confirm before you're live.",
                     font=("Segoe UI", 8), bg=BG2, fg=TEXTDIM).pack(anchor="w", pady=(2, 10))

            scene_grid = tk.Frame(scene_card, bg=BG2)
            scene_grid.pack(fill="x")

            scene_defs = [
                ("Main Scene",       obs_scene_main),
                ("Starting Scene",   obs_config.get("scene_starting", "Starting")),
                ("BRB Scene",        obs_config.get("scene_brb", "BRB")),
                ("Reverting Scene",  obs_config.get("scene_reverting", "")),
                ("Restarting Scene", obs_config.get("scene_restarting", "")),
                ("Error Scene",      obs_config.get("scene_error", "")),
                ("Shutdown Scene",   obs_config.get("scene_shutdown", "")),
            ]
            scene_entries = []
            for i, (label, value) in enumerate(scene_defs):
                e = field(scene_grid, label.upper(), value, 18, row=i // 3, col=i % 3)
                scene_entries.append((label, e))
            (self.obs_scene_main_e, self.obs_scene_start_e, self.obs_scene_brb_e,
             self.obs_scene_revert_e, self.obs_scene_restart_e,
             self.obs_scene_error_e, self.obs_scene_shutdown_e) = [e for _, e in scene_entries]

            def test_switch(entry): set_obs_scene(entry.get().strip())
            test_row = tk.Frame(scene_card, bg=BG2)
            test_row.pack(fill="x", pady=(10, 0))
            for label, entry in scene_entries:
                tk.Button(test_row, text=f"Test {label.replace(' Scene', '')}", font=("Segoe UI", 8),
                          bg=BG3, fg="white", bd=0, cursor="hand2",
                          command=lambda en=entry: test_switch(en)
                          ).pack(side="left", padx=(0, 6), pady=(4, 0), ipady=3, ipadx=8)

            def save_obs():
                global obs_scene_main
                obs_config["host"], obs_config["port"], obs_config["password"] = self.obs_entry_host.get().strip(), int(self.obs_entry_port.get() or obs_port), self.obs_entry_pass.get()
                obs_scene_main = self.obs_scene_main_e.get().strip() or "main"
                obs_config["scene_main"] = obs_scene_main
                obs_config["scene_starting"] = self.obs_scene_start_e.get().strip()
                obs_config["scene_brb"] = self.obs_scene_brb_e.get().strip()
                obs_config["scene_reverting"] = self.obs_scene_revert_e.get().strip()
                obs_config["scene_restarting"] = self.obs_scene_restart_e.get().strip()
                obs_config["scene_error"] = self.obs_scene_error_e.get().strip()
                obs_config["scene_shutdown"] = self.obs_scene_shutdown_e.get().strip()
                save_obs_config()
                self.log("[system]", "[info] obs settings saved.", "sysmsg")

            tk.Button(outer, text="💾  SAVE OBS SETTINGS", font=("Segoe UI", 10, "bold"), bg="#10B981",
                      fg="black", bd=0, cursor="hand2", command=save_obs
                      ).pack(anchor="w", ipady=7, ipadx=18, pady=(0, 20))
        except Exception as e:
            self.log("[system]", f"[err] obs tab build error: {e}", "err")

    # ---------------- Music tab (yt-dlp + vlc) ----------------
    def build_music_tab(self):
        try:
            _sp = self._make_tab_scrollable(self.tab_music)
            wrapper = tk.Frame(_sp, bg="#09090B")
            wrapper.pack(fill="both", expand=True, padx=20, pady=15)

            avail = []
            if not ytdlp_available: avail.append("yt-dlp not installed (pip install yt-dlp)")
            if not vlc_available: avail.append("python-vlc not installed (pip install python-vlc, and install VLC itself)")
            if avail:
                tk.Label(wrapper, text=" / ".join(avail), font=("Segoe UI", 9, "bold"), bg="#09090B", fg="#EF4444").pack(anchor="w", pady=(0, 8))

            # ---- top bar: title (left) + change-hours box (top right corner) ----
            top_bar = tk.Frame(wrapper, bg="#09090B")
            top_bar.pack(fill="x", pady=(0, 12))
            tk.Label(top_bar, text="MUSIC PANEL", font=("Segoe UI", 14, "bold"), bg="#09090B", fg=self.accent_main).pack(side="left")

            def _music_apply_json(data):
                if isinstance(data, dict):
                    music_config.update(data)
                    save_music_config()
            self.add_json_io_bar(wrapper, self.tab_music, self.build_music_tab,
                                  lambda: dict(music_config), _music_apply_json, "music_config")

            hours_card = tk.Frame(top_bar, bg="#18181B", padx=12, pady=8, highlightthickness=1, highlightbackground="#27272A")
            hours_card.pack(side="right")
            tk.Label(hours_card, text="Music/Playlist Change Hours", font=("Segoe UI", 9, "bold"), bg="#18181B", fg="#D4D4D8").pack(side="left", padx=(0, 8))
            self.music_hours_entry = tk.Entry(hours_card, width=6, font=("Consolas", 11), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A", justify="center")
            self.music_hours_entry.pack(side="left", ipady=4, padx=(0, 8))
            self.music_hours_entry.insert(0, str(music_config.get("change_hours", 1)))
            def save_hours():
                try:
                    hrs = float(self.music_hours_entry.get())
                    if hrs <= 0: raise ValueError
                except Exception:
                    self.log("[system]", "[err] change hours must be a positive number.", "err")
                    return
                music_config["change_hours"] = hrs
                save_music_config()
                self.log("[system]", f"[info] music schedule will now advance every {hrs} hour(s).", "sysmsg")
            tk.Button(hours_card, text="Save", font=("Segoe UI", 9, "bold"), bg="#10B981", fg="black", bd=0, cursor="hand2", command=save_hours).pack(side="left", ipady=4, ipadx=10)

            enable_row = tk.Frame(wrapper, bg="#09090B")
            enable_row.pack(fill="x", pady=(0, 12))
            self.var_music_enabled = tk.BooleanVar(value=music_config.get("enabled", False))
            def toggle_music_enabled():
                music_config["enabled"] = self.var_music_enabled.get()
                save_music_config()
                if music_config["enabled"]:
                    start_music_player()
                    self.log("[system]", "[info] music player enabled.", "sysmsg")
                else:
                    stop_music_player()
                    self.log("[system]", "[info] music player disabled.", "sysmsg")
            ttk.Checkbutton(enable_row, text="Enable automatic music playback", variable=self.var_music_enabled, style="Toggle.TCheckbutton", command=toggle_music_enabled).pack(side="left")
            self.music_now_playing_lbl = tk.Label(enable_row, text=f"now playing: {music_current_desc or '(nothing)'}", font=("Segoe UI", 9), bg="#09090B", fg="#A1A1AA")
            self.music_now_playing_lbl.pack(side="right")

            controls_row = tk.Frame(wrapper, bg="#18181B", highlightthickness=1, highlightbackground="#27272A")
            controls_row.pack(fill="x", pady=(0, 12))
            tk.Label(controls_row, text="PLAYBACK CONTROLS", font=("Segoe UI", 9, "bold"), bg="#18181B", fg="#A1A1AA").pack(side="left", padx=10, pady=8)
            tk.Button(controls_row, text="▶ Play Selected Schedule", font=("Segoe UI", 9, "bold"), bg="#10B981", fg="black", bd=0, cursor="hand2",
                      command=lambda: self._music_play_selected_schedule()).pack(side="left", padx=4, ipady=5, ipadx=10)
            tk.Button(controls_row, text="⏭ Skip Track", font=("Segoe UI", 9, "bold"), bg="#27272A", fg="white", bd=0, cursor="hand2",
                      command=lambda: (music_skip_track(), self.log("[system]", "[info] skipped to next track.", "sysmsg"))).pack(side="left", padx=4, ipady=5, ipadx=10)
            tk.Button(controls_row, text="⏸ Pause/Resume", font=("Segoe UI", 9, "bold"), bg="#27272A", fg="white", bd=0, cursor="hand2",
                      command=lambda: music_pause_toggle()).pack(side="left", padx=4, ipady=5, ipadx=10)
            tk.Button(controls_row, text="⏹ Stop", font=("Segoe UI", 9, "bold"), bg="#EF4444", fg="white", bd=0, cursor="hand2",
                      command=lambda: (stop_music_player(), self.log("[system]", "[info] music stopped.", "sysmsg"))).pack(side="left", padx=4, ipady=5, ipadx=10)
            tk.Label(controls_row, text="Volume", font=("Segoe UI", 9, "bold"), bg="#18181B", fg="#D4D4D8").pack(side="left", padx=(20, 4))
            self.music_volume_scale = tk.Scale(controls_row, from_=0, to=100, orient="horizontal", length=140, bg="#18181B", fg="white",
                                                troughcolor="#09090B", highlightthickness=0, bd=0, showvalue=True,
                                                command=lambda v: music_set_volume(v))
            self.music_volume_scale.set(int(music_config.get("volume", 90)))
            self.music_volume_scale.pack(side="left", padx=(0, 10))

            # ---- main area: left = schedule column, right = 2 big boxes horizontally ----
            main_area = tk.Frame(wrapper, bg="#09090B")
            main_area.pack(fill="both", expand=True)

            # -- LEFT: schedule column (upper + bottom boxes) --
            left_col = tk.Frame(main_area, bg="#18181B", width=300, highlightthickness=1, highlightbackground="#27272A")
            left_col.pack(side="left", fill="y", padx=(0, 15))
            left_col.pack_propagate(False)

            tk.Label(left_col, text="MUSIC SCHEDULE (ORDER)", font=("Segoe UI", 10, "bold"), bg="#18181B", fg="#8B5CF6").pack(anchor="w", padx=10, pady=(10, 4))
            tk.Button(left_col, text="+ Add New Music Schedule", font=("Segoe UI", 9, "bold"), bg="#8B5CF6", fg="white", bd=0, cursor="hand2",
                      command=lambda: self._music_open_add_schedule_dialog()).pack(fill="x", padx=10, pady=(0, 8), ipady=6)

            # upper box: the ordered schedule list
            sched_upper_frame = tk.Frame(left_col, bg="#09090B", highlightthickness=1, highlightbackground="#27272A")
            sched_upper_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))
            self.music_schedule_listbox = tk.Listbox(sched_upper_frame, font=("Consolas", 9), bg="#09090B", fg=self.accent_main, bd=0, highlightthickness=0, selectbackground="#27272A")
            self.music_schedule_listbox.pack(fill="both", expand=True, padx=4, pady=4)

            # bottom box: status / now-playing log
            tk.Label(left_col, text="STATUS / HISTORY", font=("Segoe UI", 9, "bold"), bg="#18181B", fg="#A1A1AA").pack(anchor="w", padx=10, pady=(4, 2))
            sched_lower_frame = tk.Frame(left_col, bg="#09090B", highlightthickness=1, highlightbackground="#27272A")
            sched_lower_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))
            self.music_status_listbox = tk.Listbox(sched_lower_frame, font=("Consolas", 9), bg="#09090B", fg="#A1A1AA", bd=0, highlightthickness=0)
            self.music_status_listbox.pack(fill="both", expand=True, padx=4, pady=4)

            sched_btn_row = tk.Frame(left_col, bg="#18181B")
            sched_btn_row.pack(fill="x", padx=10, pady=(0, 10))
            tk.Button(sched_btn_row, text="Save", font=("Segoe UI", 9, "bold"), bg="#10B981", fg="black", bd=0, cursor="hand2",
                      command=lambda: self._music_save_schedule()).pack(side="left", expand=True, fill="x", padx=(0, 4), ipady=6)
            tk.Button(sched_btn_row, text="Remove", font=("Segoe UI", 9, "bold"), bg="#EF4444", fg="white", bd=0, cursor="hand2",
                      command=lambda: self._music_remove_schedule_entry()).pack(side="left", expand=True, fill="x", padx=(4, 0), ipady=6)

            # -- RIGHT: two big boxes side by side horizontally (Musics / Playlists) --
            right_area = tk.Frame(main_area, bg="#09090B")
            right_area.pack(side="left", fill="both", expand=True)

            musics_box = tk.Frame(right_area, bg="#18181B", highlightthickness=1, highlightbackground="#27272A")
            musics_box.pack(side="left", fill="both", expand=True, padx=(0, 8))
            playlists_box = tk.Frame(right_area, bg="#18181B", highlightthickness=1, highlightbackground="#27272A")
            playlists_box.pack(side="left", fill="both", expand=True, padx=(8, 0))

            # Musics box
            tk.Label(musics_box, text="MUSICS (SINGLE TRACKS)", font=("Segoe UI", 10, "bold"), bg="#18181B", fg=self.accent_main).pack(anchor="w", padx=10, pady=(10, 4))
            m_list_frame = tk.Frame(musics_box, bg="#09090B", highlightthickness=1, highlightbackground="#27272A")
            m_list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))
            self.music_tracks_listbox = tk.Listbox(m_list_frame, font=("Consolas", 9), bg="#09090B", fg="white", bd=0, highlightthickness=0, selectbackground="#27272A")
            self.music_tracks_listbox.pack(fill="both", expand=True, padx=4, pady=4)
            m_btn_row = tk.Frame(musics_box, bg="#18181B")
            m_btn_row.pack(fill="x", padx=10, pady=(0, 10), anchor="w")
            tk.Button(m_btn_row, text="+ Add", font=("Segoe UI", 9, "bold"), bg="#10B981", fg="black", bd=0, cursor="hand2",
                      command=lambda: self._music_add_url("tracks")).pack(side="left", ipady=5, ipadx=14, padx=(0, 6))
            tk.Button(m_btn_row, text="✕ Remove Music", font=("Segoe UI", 9, "bold"), bg="#EF4444", fg="white", bd=0, cursor="hand2",
                      command=lambda: self._music_remove_url("tracks")).pack(side="left", ipady=5, ipadx=14)

            # Playlists box
            tk.Label(playlists_box, text="PLAYLISTS (SHUFFLE + LOOP)", font=("Segoe UI", 10, "bold"), bg="#18181B", fg="#F59E0B").pack(anchor="w", padx=10, pady=(10, 4))
            p_list_frame = tk.Frame(playlists_box, bg="#09090B", highlightthickness=1, highlightbackground="#27272A")
            p_list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))
            self.music_playlists_listbox = tk.Listbox(p_list_frame, font=("Consolas", 9), bg="#09090B", fg="white", bd=0, highlightthickness=0, selectbackground="#27272A")
            self.music_playlists_listbox.pack(fill="both", expand=True, padx=4, pady=4)
            p_btn_row = tk.Frame(playlists_box, bg="#18181B")
            p_btn_row.pack(fill="x", padx=10, pady=(0, 10), anchor="w")
            tk.Button(p_btn_row, text="+ Add", font=("Segoe UI", 9, "bold"), bg="#10B981", fg="black", bd=0, cursor="hand2",
                      command=lambda: self._music_add_url("playlists")).pack(side="left", ipady=5, ipadx=14, padx=(0, 6))
            tk.Button(p_btn_row, text="✕ Remove Music", font=("Segoe UI", 9, "bold"), bg="#EF4444", fg="white", bd=0, cursor="hand2",
                      command=lambda: self._music_remove_url("playlists")).pack(side="left", ipady=5, ipadx=14)

            self._music_refresh_all_lists()
            self._music_poll_status()
        except Exception as e:
            self.log("[system]", f"[err] music tab build error: {e}", "err")

    def _music_play_selected_schedule(self):
        sel = self.music_schedule_listbox.curselection()
        sched = music_config.get("schedule", [])
        if not sched:
            messagebox.showinfo("music", "add a schedule entry first.")
            return
        item = sched[sel[0]] if sel else sched[0]
        if not music_config.get("enabled", False):
            self.var_music_enabled.set(True)
            music_config["enabled"] = True
            save_music_config()
            start_music_player()
        threading.Thread(target=lambda: music_play_url(item.get("url", ""), shuffle_loop=(item.get("type") == "playlist")), daemon=True).start()
        self.log("[system]", f"[info] manually playing schedule entry: {item.get('url')}", "sysmsg")

    def _music_refresh_all_lists(self):
        self.music_tracks_listbox.delete(0, "end")
        for u in music_config.get("tracks", []): self.music_tracks_listbox.insert("end", u)
        self.music_playlists_listbox.delete(0, "end")
        for u in music_config.get("playlists", []): self.music_playlists_listbox.insert("end", u)
        self.music_schedule_listbox.delete(0, "end")
        for i, item in enumerate(music_config.get("schedule", []), 1):
            self.music_schedule_listbox.insert("end", f"{i}. [{item.get('type')}] {item.get('url')}")

    def _music_add_url(self, kind):
        url = _simpledialog.askstring("Add YouTube URL", f"Paste the YouTube {'video' if kind == 'tracks' else 'playlist'} URL:", parent=self.root)
        if not url or not url.strip(): return
        music_config.setdefault(kind, []).append(url.strip())
        save_music_config()
        self._music_refresh_all_lists()
        self.log("[system]", f"[info] added {kind[:-1]}: {url.strip()}", "sysmsg")

    def _music_remove_url(self, kind):
        lb = self.music_tracks_listbox if kind == "tracks" else self.music_playlists_listbox
        sel = lb.curselection()
        if not sel: return
        items = music_config.get(kind, [])
        if sel[0] < len(items):
            removed = items.pop(sel[0])
            save_music_config()
            self._music_refresh_all_lists()
            self.log("[system]", f"[info] removed {kind[:-1]}: {removed}", "sysmsg")

    def _music_open_add_schedule_dialog(self):
        if len(music_config.get("schedule", [])) >= MUSIC_SCHEDULE_MAX:
            messagebox.showinfo("music schedule", f"maximum of {MUSIC_SCHEDULE_MAX} schedule entries reached.")
            return
        dlg = tk.Toplevel(self.root)
        dlg.title("Add New Music Schedule")
        dlg.configure(bg="#18181B")
        dlg.geometry("420x180")
        dlg.transient(self.root)
        tk.Label(dlg, text="Type", bg="#18181B", fg="#D4D4D8", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15, pady=(15, 4))
        type_var = tk.StringVar(value="track")
        trow = tk.Frame(dlg, bg="#18181B"); trow.pack(anchor="w", padx=15)
        tk.Radiobutton(trow, text="Music (single track)", variable=type_var, value="track", bg="#18181B", fg="white", selectcolor="#09090B", activebackground="#18181B").pack(side="left", padx=(0, 10))
        tk.Radiobutton(trow, text="Playlist (shuffle+loop)", variable=type_var, value="playlist", bg="#18181B", fg="white", selectcolor="#09090B", activebackground="#18181B").pack(side="left")
        tk.Label(dlg, text="URL", bg="#18181B", fg="#D4D4D8", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15, pady=(15, 4))
        url_cb = ttk.Combobox(dlg, width=45, font=("Consolas", 10))
        url_cb.pack(padx=15, fill="x")
        def refresh_choices(*_):
            src = music_config.get("tracks", []) if type_var.get() == "track" else music_config.get("playlists", [])
            url_cb["values"] = src
            if src: url_cb.set(src[0])
            else: url_cb.set("")
        type_var.trace_add("write", refresh_choices)
        refresh_choices()
        def confirm():
            url = url_cb.get().strip()
            if not url:
                messagebox.showwarning("music schedule", "pick or type a URL first (add it in the Musics/Playlists box below if it's not listed).")
                return
            music_config.setdefault("schedule", []).append({"type": type_var.get(), "url": url})
            save_music_config()
            self._music_refresh_all_lists()
            dlg.destroy()
        btnrow = tk.Frame(dlg, bg="#18181B"); btnrow.pack(pady=15)
        tk.Button(btnrow, text="Add to Schedule", font=("Segoe UI", 10, "bold"), bg="#8B5CF6", fg="white", bd=0, cursor="hand2", command=confirm).pack(side="left", ipady=5, ipadx=14, padx=(0, 8))
        tk.Button(btnrow, text="Cancel", font=("Segoe UI", 10, "bold"), bg="#27272A", fg="white", bd=0, cursor="hand2", command=dlg.destroy).pack(side="left", ipady=5, ipadx=14)

    def _music_remove_schedule_entry(self):
        sel = self.music_schedule_listbox.curselection()
        if not sel: return
        sched = music_config.get("schedule", [])
        if sel[0] < len(sched):
            removed = sched.pop(sel[0])
            save_music_config()
            self._music_refresh_all_lists()
            self.log("[system]", f"[info] removed schedule entry: {removed.get('url')}", "sysmsg")

    def _music_save_schedule(self):
        # persists the current schedule order/hours (list itself is edited via add/remove)
        try:
            hrs = float(self.music_hours_entry.get())
            if hrs > 0: music_config["change_hours"] = hrs
        except Exception: pass
        save_music_config()
        self.log("[system]", "[info] music schedule saved.", "sysmsg")

    def _music_poll_status(self):
        try:
            if hasattr(self, "music_now_playing_lbl"):
                self.music_now_playing_lbl.config(text=f"now playing: {music_current_desc or '(nothing)'} — {music_status_text}")
            if hasattr(self, "music_status_listbox"):
                last = self.music_status_listbox.get(0) if self.music_status_listbox.size() else None
                if music_status_text and music_status_text != last:
                    self.music_status_listbox.insert(0, f"[{time.strftime('%H:%M:%S')}] {music_status_text}")
                    while self.music_status_listbox.size() > 50:
                        self.music_status_listbox.delete("end")
        except Exception: pass
        if self.running: self.root.after(3000, self._music_poll_status)

    # ---------------- Video tab (yt-dlp + python-vlc, rendered into a movable window) ----------------
    def build_video_tab(self):
        try:
            _sp = self._make_tab_scrollable(self.tab_video)
            wrapper = tk.Frame(_sp, bg="#09090B")
            wrapper.pack(fill="both", expand=True, padx=20, pady=15)

            avail = []
            if not ytdlp_available: avail.append("yt-dlp not installed (pip install yt-dlp)")
            if not vlc_available: avail.append("python-vlc not installed (pip install python-vlc, and install VLC itself)")
            if avail:
                tk.Label(wrapper, text=" / ".join(avail), font=("Segoe UI", 9, "bold"), bg="#09090B", fg="#EF4444").pack(anchor="w", pady=(0, 8))

            # ---- top bar: title (left) + change-hours box (top right corner) ----
            top_bar = tk.Frame(wrapper, bg="#09090B")
            top_bar.pack(fill="x", pady=(0, 12))
            tk.Label(top_bar, text="VIDEO PANEL", font=("Segoe UI", 14, "bold"), bg="#09090B", fg=self.accent_main).pack(side="left")

            def _video_apply_json(data):
                if isinstance(data, dict):
                    video_config.update(data)
                    save_video_config()
            self.add_json_io_bar(wrapper, self.tab_video, self.build_video_tab,
                                  lambda: dict(video_config), _video_apply_json, "video_config")

            hours_card = tk.Frame(top_bar, bg="#18181B", padx=12, pady=8, highlightthickness=1, highlightbackground="#27272A")
            hours_card.pack(side="right")
            tk.Label(hours_card, text="Video/Playlist Change Hours", font=("Segoe UI", 9, "bold"), bg="#18181B", fg="#D4D4D8").pack(side="left", padx=(0, 8))
            self.video_hours_entry = tk.Entry(hours_card, width=6, font=("Consolas", 11), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A", justify="center")
            self.video_hours_entry.pack(side="left", ipady=4, padx=(0, 8))
            self.video_hours_entry.insert(0, str(video_config.get("change_hours", 1)))
            def save_hours():
                try:
                    hrs = float(self.video_hours_entry.get())
                    if hrs <= 0: raise ValueError
                except Exception:
                    self.log("[system]", "[err] change hours must be a positive number.", "err")
                    return
                video_config["change_hours"] = hrs
                save_video_config()
                self.log("[system]", f"[info] video schedule will now advance every {hrs} hour(s).", "sysmsg")
            tk.Button(hours_card, text="Save", font=("Segoe UI", 9, "bold"), bg="#10B981", fg="black", bd=0, cursor="hand2", command=save_hours).pack(side="left", ipady=4, ipadx=10)

            enable_row = tk.Frame(wrapper, bg="#09090B")
            enable_row.pack(fill="x", pady=(0, 12))
            self.var_video_enabled = tk.BooleanVar(value=video_config.get("enabled", False))
            def toggle_video_enabled():
                video_config["enabled"] = self.var_video_enabled.get()
                save_video_config()
                if video_config["enabled"]:
                    start_video_player()
                    self.log("[system]", "[info] video player enabled.", "sysmsg")
                else:
                    stop_video_player()
                    self.log("[system]", "[info] video player disabled.", "sysmsg")
            ttk.Checkbutton(enable_row, text="Enable automatic video playback", variable=self.var_video_enabled, style="Toggle.TCheckbutton", command=toggle_video_enabled).pack(side="left")
            self.video_now_playing_lbl = tk.Label(enable_row, text=f"now playing: {video_current_desc or '(nothing)'}", font=("Segoe UI", 9), bg="#09090B", fg="#A1A1AA")
            self.video_now_playing_lbl.pack(side="right")

            controls_row = tk.Frame(wrapper, bg="#18181B", highlightthickness=1, highlightbackground="#27272A")
            controls_row.pack(fill="x", pady=(0, 12))
            tk.Label(controls_row, text="PLAYBACK CONTROLS", font=("Segoe UI", 9, "bold"), bg="#18181B", fg="#A1A1AA").pack(side="left", padx=10, pady=8)
            tk.Button(controls_row, text="▶ Play Selected Schedule", font=("Segoe UI", 9, "bold"), bg="#10B981", fg="black", bd=0, cursor="hand2",
                      command=lambda: self._video_play_selected_schedule()).pack(side="left", padx=4, ipady=5, ipadx=10)
            tk.Button(controls_row, text="⏭ Skip Clip", font=("Segoe UI", 9, "bold"), bg="#27272A", fg="white", bd=0, cursor="hand2",
                      command=lambda: (video_skip_track(), self.log("[system]", "[info] skipped to next clip.", "sysmsg"))).pack(side="left", padx=4, ipady=5, ipadx=10)
            tk.Button(controls_row, text="⏸ Pause/Resume", font=("Segoe UI", 9, "bold"), bg="#27272A", fg="white", bd=0, cursor="hand2",
                      command=lambda: video_pause_toggle()).pack(side="left", padx=4, ipady=5, ipadx=10)
            tk.Button(controls_row, text="⏹ Stop", font=("Segoe UI", 9, "bold"), bg="#EF4444", fg="white", bd=0, cursor="hand2",
                      command=lambda: (stop_video_player(), self.log("[system]", "[info] video stopped.", "sysmsg"))).pack(side="left", padx=4, ipady=5, ipadx=10)
            tk.Button(controls_row, text="🗗 Show Window", font=("Segoe UI", 9, "bold"), bg="#27272A", fg="white", bd=0, cursor="hand2",
                      command=lambda: self.ensure_video_window()).pack(side="left", padx=4, ipady=5, ipadx=10)
            self.var_video_ontop = tk.BooleanVar(value=video_config.get("always_on_top", False))
            def toggle_video_ontop():
                video_config["always_on_top"] = self.var_video_ontop.get()
                save_video_config()
                try:
                    if getattr(self, "video_toplevel", None) and self.video_toplevel.winfo_exists():
                        self.video_toplevel.attributes("-topmost", video_config["always_on_top"])
                except Exception: pass
            ttk.Checkbutton(controls_row, text="Always on top", variable=self.var_video_ontop, style="Toggle.TCheckbutton", command=toggle_video_ontop).pack(side="left", padx=(10, 4))
            tk.Label(controls_row, text="Volume", font=("Segoe UI", 9, "bold"), bg="#18181B", fg="#D4D4D8").pack(side="left", padx=(20, 4))
            self.video_volume_scale = tk.Scale(controls_row, from_=0, to=100, orient="horizontal", length=140, bg="#18181B", fg="white",
                                                troughcolor="#09090B", highlightthickness=0, bd=0, showvalue=True,
                                                command=lambda v: video_set_volume(v))
            self.video_volume_scale.set(int(video_config.get("volume", 90)))
            self.video_volume_scale.pack(side="left", padx=(0, 10))

            # ---- main area: left = schedule column, right = 2 big boxes horizontally ----
            main_area = tk.Frame(wrapper, bg="#09090B")
            main_area.pack(fill="both", expand=True)

            # -- LEFT: schedule column (upper + bottom boxes) --
            left_col = tk.Frame(main_area, bg="#18181B", width=300, highlightthickness=1, highlightbackground="#27272A")
            left_col.pack(side="left", fill="y", padx=(0, 15))
            left_col.pack_propagate(False)

            tk.Label(left_col, text="VIDEO SCHEDULE (ORDER)", font=("Segoe UI", 10, "bold"), bg="#18181B", fg="#8B5CF6").pack(anchor="w", padx=10, pady=(10, 4))
            tk.Button(left_col, text="+ Add New Video Schedule", font=("Segoe UI", 9, "bold"), bg="#8B5CF6", fg="white", bd=0, cursor="hand2",
                      command=lambda: self._video_open_add_schedule_dialog()).pack(fill="x", padx=10, pady=(0, 8), ipady=6)

            # upper box: the ordered schedule list
            sched_upper_frame = tk.Frame(left_col, bg="#09090B", highlightthickness=1, highlightbackground="#27272A")
            sched_upper_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))
            self.video_schedule_listbox = tk.Listbox(sched_upper_frame, font=("Consolas", 9), bg="#09090B", fg=self.accent_main, bd=0, highlightthickness=0, selectbackground="#27272A")
            self.video_schedule_listbox.pack(fill="both", expand=True, padx=4, pady=4)

            # bottom box: status / now-playing log
            tk.Label(left_col, text="STATUS / HISTORY", font=("Segoe UI", 9, "bold"), bg="#18181B", fg="#A1A1AA").pack(anchor="w", padx=10, pady=(4, 2))
            sched_lower_frame = tk.Frame(left_col, bg="#09090B", highlightthickness=1, highlightbackground="#27272A")
            sched_lower_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))
            self.video_status_listbox = tk.Listbox(sched_lower_frame, font=("Consolas", 9), bg="#09090B", fg="#A1A1AA", bd=0, highlightthickness=0)
            self.video_status_listbox.pack(fill="both", expand=True, padx=4, pady=4)

            sched_btn_row = tk.Frame(left_col, bg="#18181B")
            sched_btn_row.pack(fill="x", padx=10, pady=(0, 10))
            tk.Button(sched_btn_row, text="Save", font=("Segoe UI", 9, "bold"), bg="#10B981", fg="black", bd=0, cursor="hand2",
                      command=lambda: self._video_save_schedule()).pack(side="left", expand=True, fill="x", padx=(0, 4), ipady=6)
            tk.Button(sched_btn_row, text="Remove", font=("Segoe UI", 9, "bold"), bg="#EF4444", fg="white", bd=0, cursor="hand2",
                      command=lambda: self._video_remove_schedule_entry()).pack(side="left", expand=True, fill="x", padx=(4, 0), ipady=6)

            # -- RIGHT: two big boxes side by side horizontally (Videos / Playlists) --
            right_area = tk.Frame(main_area, bg="#09090B")
            right_area.pack(side="left", fill="both", expand=True)

            videos_box = tk.Frame(right_area, bg="#18181B", highlightthickness=1, highlightbackground="#27272A")
            videos_box.pack(side="left", fill="both", expand=True, padx=(0, 8))
            playlists_box = tk.Frame(right_area, bg="#18181B", highlightthickness=1, highlightbackground="#27272A")
            playlists_box.pack(side="left", fill="both", expand=True, padx=(8, 0))

            # Videos box
            tk.Label(videos_box, text="VIDEOS (SINGLE CLIPS)", font=("Segoe UI", 10, "bold"), bg="#18181B", fg=self.accent_main).pack(anchor="w", padx=10, pady=(10, 4))
            v_list_frame = tk.Frame(videos_box, bg="#09090B", highlightthickness=1, highlightbackground="#27272A")
            v_list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))
            self.video_tracks_listbox = tk.Listbox(v_list_frame, font=("Consolas", 9), bg="#09090B", fg="white", bd=0, highlightthickness=0, selectbackground="#27272A")
            self.video_tracks_listbox.pack(fill="both", expand=True, padx=4, pady=4)
            v_btn_row = tk.Frame(videos_box, bg="#18181B")
            v_btn_row.pack(fill="x", padx=10, pady=(0, 10), anchor="w")
            tk.Button(v_btn_row, text="+ Add", font=("Segoe UI", 9, "bold"), bg="#10B981", fg="black", bd=0, cursor="hand2",
                      command=lambda: self._video_add_url("tracks")).pack(side="left", ipady=5, ipadx=14, padx=(0, 6))
            tk.Button(v_btn_row, text="✕ Remove Video", font=("Segoe UI", 9, "bold"), bg="#EF4444", fg="white", bd=0, cursor="hand2",
                      command=lambda: self._video_remove_url("tracks")).pack(side="left", ipady=5, ipadx=14)

            # Playlists box
            tk.Label(playlists_box, text="PLAYLISTS (SHUFFLE + LOOP)", font=("Segoe UI", 10, "bold"), bg="#18181B", fg="#F59E0B").pack(anchor="w", padx=10, pady=(10, 4))
            p_list_frame = tk.Frame(playlists_box, bg="#09090B", highlightthickness=1, highlightbackground="#27272A")
            p_list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))
            self.video_playlists_listbox = tk.Listbox(p_list_frame, font=("Consolas", 9), bg="#09090B", fg="white", bd=0, highlightthickness=0, selectbackground="#27272A")
            self.video_playlists_listbox.pack(fill="both", expand=True, padx=4, pady=4)
            p_btn_row = tk.Frame(playlists_box, bg="#18181B")
            p_btn_row.pack(fill="x", padx=10, pady=(0, 10), anchor="w")
            tk.Button(p_btn_row, text="+ Add", font=("Segoe UI", 9, "bold"), bg="#10B981", fg="black", bd=0, cursor="hand2",
                      command=lambda: self._video_add_url("playlists")).pack(side="left", ipady=5, ipadx=14, padx=(0, 6))
            tk.Button(p_btn_row, text="✕ Remove Video", font=("Segoe UI", 9, "bold"), bg="#EF4444", fg="white", bd=0, cursor="hand2",
                      command=lambda: self._video_remove_url("playlists")).pack(side="left", ipady=5, ipadx=14)

            self._video_refresh_all_lists()
            self._video_poll_status()
        except Exception as e:
            self.log("[system]", f"[err] video tab build error: {e}", "err")

    # ---- the actual movable window the video is rendered into ----
    def ensure_video_window(self):
        try:
            if getattr(self, "video_toplevel", None) is not None and self.video_toplevel.winfo_exists():
                self.video_toplevel.deiconify()
                self.video_toplevel.lift()
                return
            win = tk.Toplevel(self.root)
            win.title(f"Video Panel - {video_current_desc}" if video_current_desc else "Video Panel")
            w = int(video_config.get("window_w", 640) or 640)
            h = int(video_config.get("window_h", 360) or 360)
            x, y = video_config.get("window_x"), video_config.get("window_y")
            win.geometry(f"{w}x{h}+{int(x)}+{int(y)}" if x is not None and y is not None else f"{w}x{h}")
            win.configure(bg="black")
            win.minsize(160, 90)
            try: win.attributes("-topmost", bool(video_config.get("always_on_top", False)))
            except Exception: pass
            canvas = tk.Frame(win, bg="black")
            canvas.pack(fill="both", expand=True)
            self.video_toplevel = win
            self.video_canvas = canvas
            win.bind("<Configure>", lambda e: self._video_save_geometry_debounced() if e.widget is win else None)
            win.protocol("WM_DELETE_WINDOW", self._on_video_window_close)
        except Exception as e:
            self.log("[system]", f"[err] couldn't open video window: {e}", "err")

    def set_video_window_title(self, desc):
        try:
            if getattr(self, "video_toplevel", None) and self.video_toplevel.winfo_exists():
                self.video_toplevel.title(f"Video Panel - {desc}" if desc else "Video Panel")
        except Exception: pass

    def _video_save_geometry_debounced(self):
        if getattr(self, "_video_geom_after_id", None):
            try: self.root.after_cancel(self._video_geom_after_id)
            except Exception: pass
        self._video_geom_after_id = self.root.after(500, self._video_save_geometry_now)

    def _video_save_geometry_now(self):
        try:
            if getattr(self, "video_toplevel", None) and self.video_toplevel.winfo_exists():
                video_config["window_x"] = self.video_toplevel.winfo_x()
                video_config["window_y"] = self.video_toplevel.winfo_y()
                video_config["window_w"] = self.video_toplevel.winfo_width()
                video_config["window_h"] = self.video_toplevel.winfo_height()
                save_video_config()
        except Exception: pass

    def _on_video_window_close(self):
        # closing the window stops the clip -- a video with nowhere to render into makes no
        # sense, unlike Music which is happy to keep playing audio-only in the background.
        try: self._video_save_geometry_now()
        except Exception: pass
        try: self.video_toplevel.destroy()
        except Exception: pass
        self.video_toplevel = None
        self.video_canvas = None
        threading.Thread(target=video_stop_current, daemon=True).start()
        self.log("[system]", "[info] video window closed, playback stopped.", "sysmsg")

    def _video_play_selected_schedule(self):
        sel = self.video_schedule_listbox.curselection()
        sched = video_config.get("schedule", [])
        if not sched:
            messagebox.showinfo("video", "add a schedule entry first.")
            return
        item = sched[sel[0]] if sel else sched[0]
        if not video_config.get("enabled", False):
            self.var_video_enabled.set(True)
            video_config["enabled"] = True
            save_video_config()
            start_video_player()
        threading.Thread(target=lambda: video_play_url(item.get("url", ""), shuffle_loop=(item.get("type") == "playlist")), daemon=True).start()
        self.log("[system]", f"[info] manually playing schedule entry: {item.get('url')}", "sysmsg")

    def _video_refresh_all_lists(self):
        self.video_tracks_listbox.delete(0, "end")
        for u in video_config.get("tracks", []): self.video_tracks_listbox.insert("end", u)
        self.video_playlists_listbox.delete(0, "end")
        for u in video_config.get("playlists", []): self.video_playlists_listbox.insert("end", u)
        self.video_schedule_listbox.delete(0, "end")
        for i, item in enumerate(video_config.get("schedule", []), 1):
            self.video_schedule_listbox.insert("end", f"{i}. [{item.get('type')}] {item.get('url')}")

    def _video_add_url(self, kind):
        url = _simpledialog.askstring("Add YouTube URL", f"Paste the YouTube {'video' if kind == 'tracks' else 'playlist'} URL:", parent=self.root)
        if not url or not url.strip(): return
        video_config.setdefault(kind, []).append(url.strip())
        save_video_config()
        self._video_refresh_all_lists()
        self.log("[system]", f"[info] added {kind[:-1]}: {url.strip()}", "sysmsg")

    def _video_remove_url(self, kind):
        lb = self.video_tracks_listbox if kind == "tracks" else self.video_playlists_listbox
        sel = lb.curselection()
        if not sel: return
        items = video_config.get(kind, [])
        if sel[0] < len(items):
            removed = items.pop(sel[0])
            save_video_config()
            self._video_refresh_all_lists()
            self.log("[system]", f"[info] removed {kind[:-1]}: {removed}", "sysmsg")

    def _video_open_add_schedule_dialog(self):
        if len(video_config.get("schedule", [])) >= VIDEO_SCHEDULE_MAX:
            messagebox.showinfo("video schedule", f"maximum of {VIDEO_SCHEDULE_MAX} schedule entries reached.")
            return
        dlg = tk.Toplevel(self.root)
        dlg.title("Add New Video Schedule")
        dlg.configure(bg="#18181B")
        dlg.geometry("420x180")
        dlg.transient(self.root)
        tk.Label(dlg, text="Type", bg="#18181B", fg="#D4D4D8", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15, pady=(15, 4))
        type_var = tk.StringVar(value="track")
        trow = tk.Frame(dlg, bg="#18181B"); trow.pack(anchor="w", padx=15)
        tk.Radiobutton(trow, text="Video (single clip)", variable=type_var, value="track", bg="#18181B", fg="white", selectcolor="#09090B", activebackground="#18181B").pack(side="left", padx=(0, 10))
        tk.Radiobutton(trow, text="Playlist (shuffle+loop)", variable=type_var, value="playlist", bg="#18181B", fg="white", selectcolor="#09090B", activebackground="#18181B").pack(side="left")
        tk.Label(dlg, text="URL", bg="#18181B", fg="#D4D4D8", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=15, pady=(15, 4))
        url_cb = ttk.Combobox(dlg, width=45, font=("Consolas", 10))
        url_cb.pack(padx=15, fill="x")
        def refresh_choices(*_):
            src = video_config.get("tracks", []) if type_var.get() == "track" else video_config.get("playlists", [])
            url_cb["values"] = src
            if src: url_cb.set(src[0])
            else: url_cb.set("")
        type_var.trace_add("write", refresh_choices)
        refresh_choices()
        def confirm():
            url = url_cb.get().strip()
            if not url:
                messagebox.showwarning("video schedule", "pick or type a URL first (add it in the Videos/Playlists box below if it's not listed).")
                return
            video_config.setdefault("schedule", []).append({"type": type_var.get(), "url": url})
            save_video_config()
            self._video_refresh_all_lists()
            dlg.destroy()
        btnrow = tk.Frame(dlg, bg="#18181B"); btnrow.pack(pady=15)
        tk.Button(btnrow, text="Add to Schedule", font=("Segoe UI", 10, "bold"), bg="#8B5CF6", fg="white", bd=0, cursor="hand2", command=confirm).pack(side="left", ipady=5, ipadx=14, padx=(0, 8))
        tk.Button(btnrow, text="Cancel", font=("Segoe UI", 10, "bold"), bg="#27272A", fg="white", bd=0, cursor="hand2", command=dlg.destroy).pack(side="left", ipady=5, ipadx=14)

    def _video_remove_schedule_entry(self):
        sel = self.video_schedule_listbox.curselection()
        if not sel: return
        sched = video_config.get("schedule", [])
        if sel[0] < len(sched):
            removed = sched.pop(sel[0])
            save_video_config()
            self._video_refresh_all_lists()
            self.log("[system]", f"[info] removed schedule entry: {removed.get('url')}", "sysmsg")

    def _video_save_schedule(self):
        # persists the current schedule order/hours (list itself is edited via add/remove)
        try:
            hrs = float(self.video_hours_entry.get())
            if hrs > 0: video_config["change_hours"] = hrs
        except Exception: pass
        save_video_config()
        self.log("[system]", "[info] video schedule saved.", "sysmsg")

    def _video_poll_status(self):
        try:
            if hasattr(self, "video_now_playing_lbl"):
                self.video_now_playing_lbl.config(text=f"now playing: {video_current_desc or '(nothing)'} — {video_status_text}")
            if hasattr(self, "video_status_listbox"):
                last = self.video_status_listbox.get(0) if self.video_status_listbox.size() else None
                if video_status_text and video_status_text != last:
                    self.video_status_listbox.insert(0, f"[{time.strftime('%H:%M:%S')}] {video_status_text}")
                    while self.video_status_listbox.size() > 50:
                        self.video_status_listbox.delete("end")
        except Exception: pass
        if self.running: self.root.after(3000, self._video_poll_status)

    # ---------------- Soundboard tab (web search only via python-vlc) ----------------
    def build_soundboard_tab(self):
        try:
            _sp = self._make_tab_scrollable(self.tab_soundboard)
            wrapper = tk.Frame(_sp, bg="#09090B")
            wrapper.pack(fill="both", expand=True, padx=20, pady=15)

            if not vlc_available:
                tk.Label(wrapper, text="python-vlc not installed (pip install python-vlc, and install VLC itself)", font=("Segoe UI", 9, "bold"), bg="#09090B", fg="#EF4444").pack(anchor="w", pady=(0, 8))

            top_bar = tk.Frame(wrapper, bg="#09090B")
            top_bar.pack(fill="x", pady=(0, 12))
            tk.Label(top_bar, text="SOUNDBOARD PANEL", font=("Segoe UI", 14, "bold"), bg="#09090B", fg=self.accent_main).pack(side="left")
            tk.Label(top_bar, text="Web search only (myinstants.com) -- no local files.", font=("Segoe UI", 9), bg="#09090B", fg="#71717A").pack(side="left", padx=(12, 0))

            def _sb_apply_json(data):
                if isinstance(data, dict):
                    soundboard_config.update(data)
                    save_soundboard_config()
            self.add_json_io_bar(wrapper, self.tab_soundboard, self.build_soundboard_tab,
                                  lambda: dict(soundboard_config), _sb_apply_json, "soundboard_config")

            self.sb_status_lbl = tk.Label(wrapper, text=f"status: {soundboard_status_text}", font=("Segoe UI", 9), bg="#09090B", fg="#A1A1AA")
            self.sb_status_lbl.pack(anchor="w", pady=(0, 12))

            web_row = tk.Frame(wrapper, bg="#18181B", highlightthickness=1, highlightbackground="#27272A")
            web_row.pack(fill="x", pady=(0, 12))
            tk.Label(web_row, text="WEB SEARCH (!sb)", font=("Segoe UI", 9, "bold"), bg="#18181B", fg="#F59E0B").pack(side="left", padx=10, pady=8)
            self.sb_web_search_entry = tk.Entry(web_row, width=30, font=("Consolas", 10), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A")
            self.sb_web_search_entry.pack(side="left", ipady=5, padx=(0, 8))
            def do_web_search_test():
                term = self.sb_web_search_entry.get().strip()
                if not term: return
                self.log("[system]", f"[info] searching myinstants for '{term}'...", "sysmsg")
                def _run():
                    ok, info = soundboard_web_search_and_play(term)
                    if ok: self.log("[system]", f"[info] played web result: {info}", "sysmsg")
                    else: self.log("[system]", f"[err] web search failed: {info}", "err")
                threading.Thread(target=_run, daemon=True).start()
            self.sb_web_search_entry.bind("<Return>", lambda e: do_web_search_test())
            tk.Button(web_row, text="Search & Play 1st Result", font=("Segoe UI", 9, "bold"), bg="#F59E0B", fg="black", bd=0, cursor="hand2", command=do_web_search_test).pack(side="left", ipady=5, ipadx=10)
            tk.Label(web_row, text="Same lookup chat's !sb <term> uses -- results are cached to soundboard_web_cache/.", font=("Segoe UI", 8), bg="#18181B", fg="#71717A").pack(side="left", padx=(12, 0))

            controls_row = tk.Frame(wrapper, bg="#18181B", highlightthickness=1, highlightbackground="#27272A")
            controls_row.pack(fill="x", pady=(0, 12))
            tk.Label(controls_row, text="PLAYBACK CONTROLS", font=("Segoe UI", 9, "bold"), bg="#18181B", fg="#A1A1AA").pack(side="left", padx=10, pady=8)
            tk.Button(controls_row, text="⏹ Stop All", font=("Segoe UI", 9, "bold"), bg="#EF4444", fg="white", bd=0, cursor="hand2",
                      command=lambda: (soundboard_stop_all(), self.log("[system]", "[info] stopped all soundboard clips.", "sysmsg"))).pack(side="left", padx=4, ipady=5, ipadx=10)
            tk.Label(controls_row, text="Volume", font=("Segoe UI", 9, "bold"), bg="#18181B", fg="#D4D4D8").pack(side="left", padx=(20, 4))
            self.sb_volume_scale = tk.Scale(controls_row, from_=0, to=100, orient="horizontal", length=140, bg="#18181B", fg="white",
                                             troughcolor="#09090B", highlightthickness=0, bd=0, showvalue=True,
                                             command=lambda v: soundboard_set_volume(v))
            self.sb_volume_scale.set(int(soundboard_config.get("volume", 90)))
            self.sb_volume_scale.pack(side="left", padx=(0, 10))

            status_box = tk.Frame(wrapper, bg="#18181B", highlightthickness=1, highlightbackground="#27272A")
            status_box.pack(fill="both", expand=True)
            tk.Label(status_box, text="STATUS / HISTORY", font=("Segoe UI", 9, "bold"), bg="#18181B", fg="#A1A1AA").pack(anchor="w", padx=10, pady=(10, 4))
            st_list_frame = tk.Frame(status_box, bg="#09090B", highlightthickness=1, highlightbackground="#27272A")
            st_list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            self.sb_status_listbox = tk.Listbox(st_list_frame, font=("Consolas", 9), bg="#09090B", fg="#A1A1AA", bd=0, highlightthickness=0)
            self.sb_status_listbox.pack(fill="both", expand=True, padx=4, pady=4)

            self._sb_poll_status()
        except Exception as e:
            self.log("[system]", f"[err] soundboard tab build error: {e}", "err")

    def _sb_poll_status(self):
        try:
            if hasattr(self, "sb_status_lbl"):
                self.sb_status_lbl.config(text=f"status: {soundboard_status_text}")
            if hasattr(self, "sb_status_listbox"):
                last = self.sb_status_listbox.get(0) if self.sb_status_listbox.size() else None
                if soundboard_status_text and soundboard_status_text != last:
                    self.sb_status_listbox.insert(0, f"[{time.strftime('%H:%M:%S')}] {soundboard_status_text}")
                    while self.sb_status_listbox.size() > 50:
                        self.sb_status_listbox.delete("end")
        except Exception: pass
        if self.running: self.root.after(2000, self._sb_poll_status)

    def build_commands_tab(self):
        try:
            _sp = self._make_tab_scrollable(self.tab_cmds)
            cmd_wrapper = tk.Frame(_sp, bg="#09090B")
            cmd_wrapper.pack(fill="both", expand=True, padx=20, pady=20)
            left_col = tk.Frame(cmd_wrapper, bg="#18181B", width=420)
            left_col.pack(side="left", fill="y", padx=(0, 10))
            left_col.pack_propagate(False)
            tk.Label(left_col, text="BUILT-IN COMMANDS", font=("Segoe UI", 12, "bold"), bg="#18181B", fg=self.accent_main).pack(pady=(15, 10))
            help_text_core = (
                "── MOUSE / KEYBOARD ──\n"
                "!type (!t) (text)       Types raw text into the VM.\n"
                "!send (!s) (text)       Types text (alias of !type).\n"
                "!key (!k) (key)         Presses a single key (e.g. !k enter)\n"
                "!combo (!c) (k)+(k)     Key combo (e.g. !c win+r)\n"
                "!keydown (!kd) (key)    Holds a key down.\n"
                "!keyup (!ku) (key)      Releases a held key.\n"
                "!winkey (key)           Windows key + (key) combo.\n"
                "!click (!lc) [n]        Left clicks mouse [n] times.\n"
                "!dclick                 Double left click.\n"
                "!tripleclick            Triple left click.\n"
                "!rclick (!rc)           Right clicks mouse.\n"
                "!mclick                 Middle clicks mouse.\n"
                "!move (!m) (dir) (amt)  Moves cursor by amount.\n"
                "!abs (x) (y)            Moves cursor to exact coords.\n"
                "!scroll (amt)           Scrolls mouse wheel.\n"
                "!scrollup [amt]         Scrolls up.\n"
                "!scrolldown [amt]       Scrolls down.\n"
                "!drag (!d) (dx) (dy)    Clicks and drags mouse.\n"
                "!wait (!w/!sleep/!delay) (s)   Pauses the action chain.\n\n"
                "── VM / SYSTEM CONTROL ──\n"
                "!startvm                Boots the selected VM.\n"
                "!restartvm              Force restarts the VM.\n"
                "!shutdown               Powers off the VM.\n"
                "!killvm (!forceshutdown) Force kills the VM process.\n"
                "!revert                 Restores the target snapshot.\n"
                "!makesnapshot (!snapshot) (name)  Creates a new snapshot.\n"
                "!forcefixvm             Force-reboots the VMware backend itself.\n"
                "!pausevm                Pauses the VM (suspend).\n"
                "!resumevm               Resumes a paused VM.\n"
                "!vmsavestate            Saves VM state and stops it.\n"
                "!vmstatus               Reports current VM power state.\n"
                "!enableinternet         [MOD ONLY] Enables the VM's network adapters via vmrun.\n"
                "!disableinternet        [MOD ONLY] Disables the VM's network adapters via vmrun.\n"
                "!cmd (command)          Runs a command in admin CMD.\n"
                "!run (command)          Runs a command via Win+R dialog.\n"
                "!dir (path)             Opens a folder in Explorer.\n"
                "!taskkill (process)     Force-kills a process by name.\n"
                "!openfile (path)        Opens a file with its default app.\n\n"
                "── VOICE / SOUND ──\n"
                "!tts (text)             Speaks text once (TTS).\n"
                "!ttsloop (text)         Speaks text on a loop.\n"
                "!ttsxp (text)           Classic Windows-XP-style TTS voice.\n"
                "!ttsxploop (text)       Looping XP-style TTS voice.\n"
                "!beep                   Plays a system beep.\n\n"
                "── FUN / CHAOS ──\n"
                "!roll                   Rolls a random number 1-100.\n"
                "!coinflip               Flips heads or tails.\n"
                "!shake                  Shakes the mouse cursor.\n"
                "!circle                 Moves the mouse in a circle.\n"
                "!spiral                 Moves the mouse in a spiral.\n"
                "!jiggle                 Small random mouse jiggles.\n"
                "!msgbox (text)          Pops up a message box in the VM.\n"
                "!spam (text) [n]        Types text repeatedly [n] times.\n"
                "!countdown              Runs an on-screen countdown.\n"
                "!matrix                 Matrix-style screen effect.\n"
                "!colorscheme            Randomizes the Windows color scheme.\n"
                "!rainbow                Cycles rainbow color effects.\n"
                "!notepadflood           Floods the desktop with Notepad windows.\n"
                "!exeflood               Floods the desktop with random apps.\n"
                "!txtflood               Floods a text file with junk text.\n"
                "!deskflood              Combined desktop chaos flood.\n\n"
                "── INFO / CHAT ──\n"
                "!ping                   Replies pong (bot alive check).\n"
                "!uptime                 Shows how long the stream/bot has run.\n"
                "!help                   Shows a short in-chat help message.\n"
                "!stats                  Shows session command/vote stats.\n"
                "!history                Shows recent command history.\n"
                "!leaderboard            Shows the top command users.\n"
                "!queue                  Shows the pending command queue size.\n"
                "!status                 Shows current bot/VM status.\n\n"
                "── MUSIC ──\n"
                "!sr (video id/url or playlist id/url)   Song request -- plays at the\n"
                "                        next scheduled music change (playlists too).\n"
                "!findsr (search term)   Searches YouTube, queues the 1st result --\n"
                "                        no id/url needed, just describe the song.\n"
                "!skipsr                 [MOD ONLY] Skips the current song and drops the\n"
                "                        next queued request, if any.\n"
                "!clearsr                [MOD ONLY] Clears the ENTIRE pending song request\n"
                "                        queue (doesn't touch what's currently playing).\n"
                "!sb (search term)      Searches myinstants.com, plays the 1st result\n"
                "                        (web only -- no local files, cached for repeats).\n"
                "!sbid (myinstants id)   Plays that EXACT sound by its myinstants.com/en/instant/(id)/\n"
                "                        id -- no search, no guessing which result you get.\n"
                "!gtts (text)            Google TTS -- speaks text out loud on the HOST's\n"
                "                        speakers (unlike !tts, which speaks inside the VM).\n\n"
                "── VIDEO ──\n"
                "!vr (video id/url or playlist id/url)   Video request -- plays at the\n"
                "                        next scheduled video change (playlists too), in a\n"
                "                        movable on-screen window.\n"
                "!findvr (search term)   Searches YouTube, queues the 1st result --\n"
                "                        no id/url needed, just describe the video.\n"
                "!skipvr                 [MOD ONLY] Skips the current video and drops the\n"
                "                        next queued request, if any.\n"
                "!clearvr                [MOD ONLY] Clears the ENTIRE pending video request\n"
                "                        queue (doesn't touch what's currently playing).\n\n"
                "── ADMIN ONLY ──\n"
                "!pausechat (!disablechat)  Pauses all chat commands.\n"
                "!enablechat             Resumes chat commands.\n"
                "!enablecv               Enables computer-vision/OCR checks.\n"
                "!votestop               Cancels any active vote.\n"
                "!clear                  Clears the on-screen chat overlay.\n"
                "!say (text)             Announces text as the bot/host.\n"
                "!efail                  Forces an error-state test.\n"
                "!poweroff               Powers off the host machine (careful!).\n"
                "!discardvmwarestate     [MOD ONLY] Powers the VM off (hard) and reverts it\n"
                "                        to the current snapshot, then leaves it OFF -- unlike\n"
                "                        !revert, it does NOT boot back up afterward.\n\n"
                "── APPS (!(name) launches it) ──\n"
            ) + ", ".join(f"!{k}" for k in sorted(APP_RUN_MAP.keys())) + (
                "\n\n── SHORTCUTS (!(name) sends the combo) ──\n"
            ) + ", ".join(f"!{k}" for k in sorted(COMBO_SHORTCUTS.keys())) + (
                "\n\n── CMD UTILITIES (use after !cmdnew) ──\n"
            ) + ", ".join(f"!{k}" for k in sorted(CMD_TYPED_MAP.keys())) + (
                "\n\n── OS VOTING TRIGGERS ──\n"
                "Any trigger configured on the OS Voting tab (e.g. !win7, !win10) counts a vote toward switching the running VM to that OS.\n\n"
                "── ALIASES ──\n"
                "!c=combo  !k=key  !t=type  !s=send  !m=move  !d=drag  !w/!sleep/!delay=wait\n"
                "!kd=keydown  !ku=keyup  !lc/!lclick=click  !rc=rclick\n"
                "!snapshot=makesnapshot  !disablechat=pausechat\n"
                "!forcereboot/!forcerestart/!forcerebootvirtualbox=forcefixvm  !forceshutdown=killvm\n"
            )
            help_text = help_text_core
            self.cmd_search_var = tk.StringVar()
            search_row = tk.Frame(left_col, bg="#18181B")
            search_row.pack(fill="x", padx=15, pady=(0, 8))
            tk.Label(search_row, text="Search:", font=("Segoe UI", 9, "bold"), bg="#18181B", fg="#A1A1AA").pack(side="left", padx=(0, 6))
            search_entry = tk.Entry(search_row, textvariable=self.cmd_search_var, font=("Consolas", 10), bg="#09090B", fg="white", insertbackground="white", bd=0, highlightthickness=1, highlightbackground="#27272A")
            search_entry.pack(side="left", fill="x", expand=True, ipady=4)
            ht = scrolledtext.ScrolledText(left_col, font=("Consolas", 9), bg="#09090B", fg="#D4D4D8", bd=0, highlightthickness=1, highlightbackground="#27272A", wrap="word")
            ht.pack(fill="both", expand=True, padx=15, pady=(0, 15))
            ht.insert("1.0", help_text)
            ht.config(state="disabled")
            self._cmd_help_full_text = help_text
            self._cmd_help_widget = ht
            def filter_help(*_):
                q = self.cmd_search_var.get().strip().lower()
                ht.config(state="normal")
                ht.delete("1.0", "end")
                if not q:
                    ht.insert("1.0", self._cmd_help_full_text)
                else:
                    matched_lines = [ln for ln in self._cmd_help_full_text.split("\n") if q in ln.lower()]
                    ht.insert("1.0", "\n".join(matched_lines) if matched_lines else "(no matching commands)")
                ht.config(state="disabled")
            self.cmd_search_var.trace_add("write", filter_help)
            right_col = tk.Frame(cmd_wrapper, bg="#18181B")
            right_col.pack(side="right", fill="both", expand=True, padx=(10, 0))
            tk.Label(right_col, text="CUSTOM COMMAND BUILDER (MACROS)", font=("Segoe UI", 12, "bold"), bg="#18181B", fg="#10B981").pack(anchor="w", padx=20, pady=(15, 5))
            tk.Label(right_col, text="Create your own commands by chaining built-in commands (e.g. !t hello !k enter)", font=("Segoe UI", 10), bg="#18181B", fg="#A1A1AA").pack(anchor="w", padx=20, pady=(0, 15))

            def _cmds_apply_json(data):
                if isinstance(data, dict):
                    self.custom_commands.clear()
                    self.custom_commands.update(data)
                    self.config["custom_commands"] = self.custom_commands
                    self.save_settings()
            io_bar_parent = tk.Frame(right_col, bg="#18181B")
            io_bar_parent.pack(fill="x", padx=20)
            self.add_json_io_bar(io_bar_parent, self.tab_cmds, self.build_commands_tab,
                                  lambda: dict(self.custom_commands), _cmds_apply_json, "custom_commands")
            form_frame = tk.Frame(right_col, bg="#18181B")
            form_frame.pack(fill="x", padx=20)
            tk.Label(form_frame, text="Trigger (e.g., !hack)", font=("Segoe UI", 11, "bold"), bg="#18181B", fg="#D4D4D8").grid(row=0, column=0, sticky="w", pady=8)
            self.entry_macro_name = tk.Entry(form_frame, font=("Consolas", 12), bg="#09090B", fg="white", bd=0, highlightthickness=1, highlightbackground="#27272A", highlightcolor="#10B981")
            self.entry_macro_name.grid(row=0, column=1, sticky="we", padx=(15, 0), pady=8, ipady=6)
            tk.Label(form_frame, text="Action Chain", font=("Segoe UI", 11, "bold"), bg="#18181B", fg="#D4D4D8").grid(row=1, column=0, sticky="w", pady=8)
            self.entry_macro_actions = tk.Entry(form_frame, font=("Consolas", 12), bg="#09090B", fg="white", bd=0, highlightthickness=1, highlightbackground="#27272A", highlightcolor="#10B981")
            self.entry_macro_actions.grid(row=1, column=1, sticky="we", padx=(15, 0), pady=8, ipady=6)
            form_frame.columnconfigure(1, weight=1)
            btn_frame = tk.Frame(right_col, bg="#18181B")
            btn_frame.pack(fill="x", padx=20, pady=15)
            tk.Button(btn_frame, text="SAVE COMMAND", font=("Segoe UI", 10, "bold"), bg="#10B981", fg="black", bd=0, cursor="hand2", command=self.save_custom_cmd).pack(side="left", ipady=5, ipadx=15)
            tk.Button(btn_frame, text="DELETE SELECTED", font=("Segoe UI", 10, "bold"), bg="#EF4444", fg="white", bd=0, cursor="hand2", command=self.delete_custom_cmd).pack(side="right", ipady=5, ipadx=15)
            list_frame = tk.Frame(right_col, bg="#27272A", bd=1)
            list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
            self.macro_listbox = tk.Listbox(list_frame, font=("Consolas", 12), bg="#09090B", fg=self.accent_main, bd=0, highlightthickness=0, selectbackground="#27272A")
            self.macro_listbox.pack(side="left", fill="both", expand=True, padx=1, pady=1)
            scroll = ttk.Scrollbar(list_frame, command=self.macro_listbox.yview)
            scroll.pack(side="right", fill="y")
            self.macro_listbox.config(yscrollcommand=scroll.set)
            self.macro_listbox.bind('<<ListboxSelect>>', self.on_macro_select)
            self.refresh_macro_list()
        except Exception as e:
            self.log("[system]", f"[err] commands tab build error: {e}", "err")

    def save_custom_cmd(self):
        name = self.entry_macro_name.get().strip().lower()
        actions = self.entry_macro_actions.get().strip()
        if not name or not actions: return
        if not name.startswith(self.command_prefix): name = self.command_prefix + name
        self.custom_commands[name] = {"type": "chain", "value": actions}
        self.config["custom_commands"] = self.custom_commands
        self.save_settings()
        self.refresh_macro_list()
        self.entry_macro_name.delete(0, 'end')
        self.entry_macro_actions.delete(0, 'end')

    def delete_custom_cmd(self):
        sel = self.macro_listbox.curselection()
        if not sel: return
        val = self.macro_listbox.get(sel[0])
        name = val.split(" -> ")[0].strip()
        if name in self.custom_commands:
            del self.custom_commands[name]
            self.config["custom_commands"] = self.custom_commands
            self.save_settings()
            self.refresh_macro_list()

    def refresh_macro_list(self):
        self.macro_listbox.delete(0, 'end')
        for k, v in self.custom_commands.items():
            if isinstance(v, dict) and "value" in v: self.macro_listbox.insert('end', f"{k} -> {v['value']}")
            elif isinstance(v, str): self.macro_listbox.insert('end', f"{k} -> {v}")

    def on_macro_select(self, evt):
        sel = self.macro_listbox.curselection()
        if not sel: return
        val = self.macro_listbox.get(sel[0])
        if " -> " not in val: return
        name, actions = val.split(" -> ", 1)
        self.entry_macro_name.delete(0, 'end')
        self.entry_macro_name.insert(0, name)
        self.entry_macro_actions.delete(0, 'end')
        self.entry_macro_actions.insert(0, actions)

    def auto_refresh_vbox_ui(self):
        try:
            vms = get_all_vbox_vms(self.entry_vbox_new.get().strip() or vbox_manage_cmd)
            if vms:
                current_vm_val = self.cb_vm_new.get()
                self.cb_vm_new['values'] = vms
                if current_vm_val not in vms and vm_name in vms: self.cb_vm_new.set(vm_name)
            active_vm = self.cb_vm_new.get()
            if active_vm:
                snaps = get_vbox_snapshots(self.entry_vbox_new.get().strip() or vbox_manage_cmd, active_vm)
                self.cb_snap_vbox['values'] = snaps if snaps else [""]
                if self.current_snapshot not in snaps and snaps:
                    self.current_snapshot = snaps[-1]
                    self.cb_snap_vbox.set(self.current_snapshot)
        except Exception: pass

    def update_say_admin(self):
        self.say_admin_only = self.say_admin_var.get()

    def save_vbox_settings(self):
        backend = self.var_vm_backend.get()
        self.config["vm_backend"] = backend
        self.config["vm_name"] = self.cb_vm_new.get()
        self.current_snapshot = self.cb_snap_vbox.get()
        global vm_name, vbox_manage_cmd, vmrun_cmd, current_vm_backend
        vm_name = self.config["vm_name"]
        current_vm_backend = backend
        if backend == "vmware":
            self.config["vmrun_path"] = self.entry_vbox_new.get()
            vmrun_cmd = self.config["vmrun_path"]
        else:
            self.config["vbox_path"] = self.entry_vbox_new.get()
            vbox_manage_cmd = self.config["vbox_path"]
        self.root.title(f"{self.config.get('app_name', 'YT2VM')} {version}: {vm_name} ({backend})")
        if hasattr(self, 'btn_vm'): self.btn_vm.configure(text=f"target: {vm_name}")
        self.refresh_vm_target_display()
        try:
            with open(snap_file, "w") as f: f.write(self.current_snapshot)
        except: pass
        self.save_settings()
        self.force_session_refresh = True 
        self.log("[system]", f"[info] saved {backend} configuration -- VM: {vm_name}", "sysmsg")

    def save_general_settings(self):
        self.config["auto_start"] = self.var_auto_new.get()
        self.config["enable_chat"] = self.var_chat_new.get()
        self.config["keyboard_layout"] = self.cb_layout_new.get()
        self.config["command_prefix"] = self.entry_prefix_new.get()
        self.config["enable_starting_scene"] = self.var_starting_scene.get()
        self.config["strict_live_check"] = self.var_strict_live.get()
        self.config["app_name"] = self.cb_app_name.get()
        self.config["ultra_speed"] = self.var_ultra_speed.get()
        self.config["enable_ocr"] = self.var_ocr.get()
        self.config["verbose_connection_logs"] = self.var_verbose_conn_logs.get()
        try: self.config["stats_interval"] = float(self.entry_stats_int.get())
        except: self.config["stats_interval"] = 15
        try: self.config["typing_speed"] = float(self.entry_type_spd.get())
        except: self.config["typing_speed"] = 0.015
        try: self.config["key_delay"] = float(self.entry_key_del.get())
        except: self.config["key_delay"] = 0.015
        try: self.config["mouse_delay"] = float(self.entry_mouse_del.get())
        except: self.config["mouse_delay"] = 0.005
        self.save_settings()
        global keyboard_layout
        keyboard_layout = self.config["keyboard_layout"]
        self.command_prefix = self.config["command_prefix"]
        self.listening_to_chat = self.config["enable_chat"]
        self.twenty_four_seven_mode = self.config["auto_start"]
        self.app_name = self.config["app_name"]
        self.ultra_speed = self.config["ultra_speed"]
        self.enable_ocr = self.config["enable_ocr"]
        self.root.title(f"{self.app_name} {version}: {vm_name}")

    def update_status_display(self, text, is_error=False):
        global current_status
        if not hasattr(self, '_last_status'): self._last_status = ""
        text_lower = text.lower()
        if self._last_status != text_lower:
            self._last_status = text_lower
            current_status = text_lower
            if hasattr(self, 'lbl_status'): self.lbl_status.configure(text=text_lower.upper(), fg="#EF4444" if is_error else "#10B981")
            gui_log_queue.put_nowait(("status", text_lower))

    def toggle_overlay_chat(self):
        global overlay_chat_visible
        overlay_chat_visible = not overlay_chat_visible

    def toggle_split_overlay(self):
        global split_overlay_mode
        split_overlay_mode = not split_overlay_mode

    def toggle_247(self):
        self.twenty_four_seven_mode = not self.twenty_four_seven_mode
        self.config["auto_start"] = self.twenty_four_seven_mode
        self.save_settings()

    def toggle_chat(self):
        self.listening_to_chat = not self.listening_to_chat
        self.config["enable_chat"] = self.listening_to_chat
        self.save_settings()

    def cycle_layout(self):
        global keyboard_layout
        try:
            current_index = available_layouts.index(keyboard_layout)
            next_index = (current_index + 1) % len(available_layouts)
        except ValueError: next_index = 0
        keyboard_layout = available_layouts[next_index]

    def refresh_vm_target_display(self):
        if not hasattr(self, 'btn_vm'): return
        try:
            if os_voting_enabled:
                self.btn_vm.configure(state="disabled", bg="#1F1F23", fg="#5C5C64", disabledforeground="#5C5C64", activebackground="#1F1F23")
                self.lbl_vm_voting_warning.pack(fill="x", pady=(4, 0), ipady=3)
            else:
                self.lbl_vm_voting_warning.pack_forget()
                self.btn_vm.configure(state="normal", bg="#27272A", fg="white", activebackground="#3F3F46")
        except Exception: pass

    def cycle_vm(self):
        global vm_name, available_vms
        try:
            fresh_vms = get_all_vbox_vms(vbox_manage_cmd)
            if fresh_vms: available_vms = fresh_vms
        except: pass
        try:
            current_index = available_vms.index(vm_name)
            next_index = (current_index + 1) % len(available_vms)
        except ValueError: next_index = 0
        vm_name = available_vms[next_index]
        snaps = get_vbox_snapshots(vbox_manage_cmd, vm_name)
        if snaps: self.current_snapshot = snaps[-1]
        else: self.current_snapshot = ""
        self.config["vm_name"] = vm_name
        self.save_settings()
        self.root.title(f"{self.config.get('app_name', 'YT2VM')} {version}: {vm_name}")
        if hasattr(self, 'btn_vm'): self.btn_vm.configure(text=f"target: {vm_name}")
        self.refresh_vm_target_display()

    def go_live(self):
        try:
            url = self.entry_url.get().strip()
            if url:
                if self.active_url != url: self.yt_bot_chat_id = None
                self.active_url = url
                self.force_connect = True
                self.config["youtube_url"] = url
                self.save_settings()
                if self.config.get("verbose_connection_logs", False):
                    self.log("[system]", f"[gui] connect requested for url: {url}", "sysmsg")
                if hasattr(self, 'lbl_status'): self.lbl_status.configure(text="Connected", fg="#10B981")
                self.log("[system]", "connected to chat", "sysmsg")
        except Exception as e:
            self.log("[system]", f"[err] go live error: {e}", "err")

    def disconnect_chat(self):
        try:
            if self.config.get("verbose_connection_logs", False):
                self.log("[system]", f"[gui] disconnect requested (was connected to: {self.active_url or '(nothing)'})", "sysmsg")
            self.active_url = ""
            self.force_connect = False
            # bumping listener_id invalidates the currently-running chat_listener_loop iteration --
            # it exits its while-loop on the next check and terminates the pytchat connection itself.
            # clearing active_url also stops the connection-watchdog in start_app_threads from
            # silently reconnecting the moment it notices the listener thread ended.
            self.listener_id = getattr(self, 'listener_id', 0) + 1
            if hasattr(self, 'lbl_status'): self.lbl_status.configure(text="DISCONNECTED", fg="#EF4444")
            self.log("[system]", "[info] chat disconnected.", "sysmsg")
        except Exception as e:
            self.log("[system]", f"[err] disconnect chat error: {e}", "err")

    def resolve_live_video_id(self, url):
        if url.startswith("[DEBUG_MODE]"): return url
        if "v=" in url: return url.split("v=")[1].split("&")[0]
        if "youtu.be/" in url: return url.split("youtu.be/")[1].split("?")[0]
        if "@" in url or "channel/" in url or "c/" in url:
            try:
                check_url = url
                if not check_url.startswith("http"): check_url = "https://www.youtube.com/" + check_url.lstrip("/")
                req = urllib.request.Request(check_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    html = response.read().decode('utf-8').lower()
                match = re.search(r'"videoid":"([a-zA-Z0-9_-]{11})"', html)
                if match: return match.group(1)
            except: pass
        return url
        
    def is_video_currently_live(self, vid):
        if vid == "[DEBUG_MODE]": return True
        try:
            req = urllib.request.Request(f"https://www.youtube.com/watch?v={vid}", headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8').lower()
            if '"islive":true' in html or '\\"islive\\":true' in html or 'watching now' in html: return True
            if 'live_stream_offline' in html and '"islive":true' not in html: return False
            return True
        except Exception: return True

    def process_vote(self, user, vote_type, target=2):
        if getattr(self, 'vm_maintenance', False):
            self.log("[system]", "[warn] vm is processing commands. votes paused.", "sysmsg")
            return
        with self.vote_lock:
            if vote_type in self.active_votes:
                vote = self.active_votes[vote_type]
                if target < vote["target"]: vote["target"] = target
                if user not in vote["voters"]:
                    vote["voters"].add(user)
                    current_votes = len(vote["voters"])
                    self.log("[system]", f"[vote] [alert] {vote_type.lower()} progress: {current_votes}/{vote['target']}!", "sysmsg")
                    log_vote_action("vote_progress", user, vote_type, vote['target'], current_votes)
                    if current_votes >= vote["target"]:
                        self.log("[system]", f"[vote] [success] {vote_type.lower()} passed! executing now...", "sysmsg")
                        log_vote_action("vote_passed", user, vote_type, vote['target'], current_votes)
                        clean_cmd = vote_type
                        if clean_cmd.startswith(self.command_prefix): clean_cmd = clean_cmd[len(self.command_prefix):]
                        self.active_votes.clear()
                        self.trigger_command((clean_cmd, "", "vote_passed"))
                        return
                return
            if len(self.active_votes) < 3:
                self.log("[system]", f"[vote] [started] {vote_type.lower()} vote started by {user}! progress: 1/{target}.", "sysmsg")
                self.active_votes[vote_type] = {"voters": {user}, "target": target, "start_time": time.time()}
                log_vote_action("vote_started", user, vote_type, target, 1)

    def on_manual_cmd(self, event=None):
        try:
            cmd = self.entry_cmd.get().strip()
            if cmd:
                if not cmd.startswith(self.command_prefix) and not cmd.startswith("!"): cmd = self.command_prefix + cmd
                elif cmd.startswith("!") and not cmd.startswith(self.command_prefix): cmd = self.command_prefix + cmd[1:]
                self.log("[console]", cmd, "user", is_mod=True, is_owner=True)
                self.parse_command(cmd, "[console]", is_mod=True, is_owner=True)
                self.entry_cmd.delete(0, 'end')
        except Exception as e:
            self.log("[system]", f"[err] manual cmd error: {e}", "err")

    def log(self, user, message, tag="sysmsg", is_mod=False, is_owner=False): 
        if not isinstance(message, str): message = str(message)
        if not isinstance(user, str): user = str(user)
        message = _capitalize_each_word(message)
        if user == "[system]" or user.lower() == "system":
            user = "[system]"
            is_mod = True
            is_owner = True
        gui_log_queue.put_nowait((tag.upper(), f"[{time.strftime('%H:%M:%S')}] [{user}] {message}"))
        add_to_history(user, message, tag, is_mod, is_owner)

    def _broadcast_log_everywhere(self, msg_type, data):
        """Queues this log line for PowerShell TTS + typing into the logging VM, if enabled.
        Runs through a background worker (see _log_broadcast_worker) so this never blocks
        the GUI's queue-draining tick, and lines are processed one at a time, in order, not
        piled up concurrently during a burst of chat activity."""
        if not LOG_BROADCAST_CONFIG.get("enabled", False):
            return
        try:
            _log_broadcast_queue.put_nowait((msg_type, data))
            _ensure_log_broadcast_worker()
        except queue.Full:
            pass  # backed up -- drop rather than block or grow unbounded
    
    def set_status(self, text): 
        self.update_status_display(text)

    def process_ui_queue(self):
        try:
            uptime_sec = int(time.time() - script_start_time)
            m, s = divmod(uptime_sec, 60)
            h, m = divmod(m, 60)
            if hasattr(self, 'lbl_uptime_val'):
                self.lbl_uptime_val.config(text=f"{h}h {m}m {s}s")
                self.lbl_cmds_val.config(text=f"{total_commands_executed} ({total_commands_failed} failed)")
                self.lbl_viewers_val.config(text=str(current_viewers))
                self.lbl_likes_val.config(text=str(current_likes))
            if time.time() - self.last_gc_time > 60:
                self.last_gc_time = time.time()
                gc.collect()
            if time.time() - getattr(self, 'last_vbox_refresh', 0) > 10:
                self.last_vbox_refresh = time.time()
                self.auto_refresh_vbox_ui()
            global current_vote_info
            
            # Single drain pass -- console display, status handling, and log broadcast all
            # happen for each queued item here, in order. This USED to be two separate
            # while-loops (one in update_gui_console(), one here) both draining the same
            # gui_log_queue -- whichever ran first consumed everything, which meant the
            # second loop (and therefore _broadcast_log_everywhere, i.e. the whole TTS/VM
            # log broadcast feature) never actually saw any messages in practice.
            self.console_text.configure(state='normal')
            while not gui_log_queue.empty():
                try:
                    msg_type, data = gui_log_queue.get_nowait()
                except queue.Empty:
                    break
                try:
                    if msg_type == "status":
                        self.update_status_display(data, "broke" in data)
                        display_data = _capitalize_each_word(data)
                        display_line = f"[{time.strftime('%H:%M:%S')}] [status] {display_data}"
                        self.console_text.insert(tk.END, display_line + "\n")
                        self._broadcast_log_everywhere(msg_type, display_data)
                    else:
                        if msg_type in ["SYSTEM", "ERROR", "EXEC", "CHAT"]:
                            self.console_text.insert(tk.END, data + "\n", msg_type)
                        else:
                            self.console_text.insert(tk.END, data + "\n")
                        self._broadcast_log_everywhere(msg_type, data)
                except Exception:
                    pass
            try:
                self.console_text.see(tk.END)
                line_count = int(self.console_text.index('end-1c').split('.')[0])
                if line_count > 300: self.console_text.delete('1.0', f'{line_count - 250}.0')
            except Exception: pass
            self.console_text.configure(state='disabled')

            with self.vote_lock:
                now = time.time()
                to_remove = []
                for vtype, data in self.active_votes.items():
                     if now - data["start_time"] > vote_timeout: to_remove.append(vtype)
                for vtype in to_remove: del self.active_votes[vtype]
                if self.active_votes:
                     parts = []
                     for vtype, data in self.active_votes.items(): parts.append(f"{vtype.lower()}: {len(data['voters'])}/{data['target']}")
                     text = " | ".join(parts).lower()
                     current_vote_info = {"active": True, "text": f"[vote] {text}"}
                else: current_vote_info = {"active": False, "text": "no active votes"}
        except Exception: pass
        finally:
            if self.running: self.root.after(refresh_rate, self.process_ui_queue)

    def save_session_data_threadsafe(self):
        try:
            url = self.active_url if self.active_url else ""
            mode = str(self.twenty_four_seven_mode)
            layout = str(keyboard_layout)
            with open(session_file, "w") as f: f.write(f"{url}|{mode}|{layout}")
        except: pass

    def _async_cmd_runner(self, action_chain):
        with self.chains_lock: self.active_chains += 1
        try:
            try:
                if 'pythoncom' in sys.modules: pythoncom.CoInitialize()
            except: pass

            for action in action_chain:
                if getattr(self, 'cancel_macros', False): break
                cmd_type, arg, user = action
                if cmd_type == "wait":
                    try:
                        w_time = min(float(arg), 3600.0)
                        if w_time > 0: time.sleep(w_time)
                    except Exception: pass
                else:
                    self.run_cmd_worker(action)

            try:
                if 'pythoncom' in sys.modules: pythoncom.CoUninitialize()
            except: pass
        finally:
            with self.chains_lock: self.active_chains = max(0, self.active_chains - 1)

    def trigger_command(self, action_tuple):
        threading.Thread(target=self._async_cmd_runner, args=([action_tuple],), daemon=True).start()

    def trigger_command_chain(self, action_chain):
        threading.Thread(target=self._async_cmd_runner, args=(action_chain,), daemon=True).start()

    def clear_commands(self):
        self.cancel_macros = True
        self.root.after(2000, lambda: setattr(self, 'cancel_macros', False))

    def _on_restart_bot_clicked(self):
        """Restart Bot button. NOTE: unlike the VMware/VBox nexovative scripts, this file
        has no auto-update/version-check pipeline to reuse (no trigger_relaunch_pipeline,
        no version.json checking, no signature verification anywhere in this codebase) --
        so this is a simpler, self-contained restart rather than a port of a mechanism
        that doesn't exist here. os.execv() replaces the current process image with a
        fresh launch of this same script and arguments -- no separate shell script or
        Terminal window needed, since there's no download/verify step to wait through
        first, just a straight restart."""
        if not messagebox.askyesno("Restart Bot", "This will restart the bot now.\n\nContinue?"):
            return
        self.log("[system]", "[info] Manual restart requested via GUI button.", "sysmsg")
        def _do_restart():
            time.sleep(0.3)  # let the log line above actually get drawn first
            try:
                os.execv(sys.executable, [sys.executable] + sys.argv)
            except Exception as e:
                console_log("ERROR", f"[Restart] os.execv failed: {e}")
        threading.Thread(target=_do_restart, daemon=True).start()

    def cancel_command_queue(self):
        """Cancels any in-flight/queued command chain(s) so the bot immediately drops back to
        listening for chat commands instead of grinding through the rest of a macro."""
        self.cancel_macros = True
        self.root.after(2000, lambda: setattr(self, 'cancel_macros', False))
        self.listening_to_chat = True
        self.log("[system]", "[info] command queue cancelled -- moving on to chat.", "sysmsg")

    def discard_vmware_state(self, triggered_by="[console]"):
        """Powers the VM off (hard) and reverts it to the current snapshot, then leaves it
        OFF -- unlike !revert (which reverts AND boots back up), this just discards whatever
        state the VM was in and puts it back to a clean, powered-off baseline. Targets the
        same VM/snapshot as every other lifecycle action (Start/Restart/Revert/etc.) on the
        Dashboard -- i.e. whatever's configured in the VM Config panel, not the separate
        VMware VNC-input panel. Runs on a background thread so it never blocks chat/GUI."""
        if not vm_name:
            self.log("[system]", "[err] no VM configured -- set one in the VM Config panel first.", "err")
            return
        self.log("[system]", f"[info] {triggered_by} is discarding VM state -- powering off and reverting...", "sysmsg")
        threading.Thread(target=self._do_vm_maintenance, args=("discardvmwarestate", self.current_snapshot), daemon=True).start()

    def toggle_vm_control(self):
        """Flips whether VM-related chat commands (!startvm, !revert, !shutdown, etc.) are
        accepted from chat/console. Everything else -- soundboard, tts, keyboard/mouse, music --
        keeps working either way. The Dashboard's direct VM buttons also still work regardless,
        since this only gates parse_command (chat-typed commands), not the buttons themselves."""
        self.vm_control_enabled = not getattr(self, 'vm_control_enabled', True)
        self._refresh_vm_control_btn()
        state = "ENABLED" if self.vm_control_enabled else "DISABLED"
        self.log("[system]", f"[info] VM control is now {state} (other commands are unaffected).", "sysmsg")

    def _refresh_vm_control_btn(self):
        if not hasattr(self, 'btn_vm_control_toggle'): return
        if getattr(self, 'vm_control_enabled', True):
            self.btn_vm_control_toggle.configure(text="Turn OFF VM Control", bg="#27272A", fg="white", activebackground="#3F3F46", activeforeground="white")
        else:
            self.btn_vm_control_toggle.configure(text="VM Control OFF -- Click to Re-enable", bg="#EF4444", fg="white", activebackground="#DC2626", activeforeground="white")

    def parse_command(self, msg, user, is_mod=False, is_owner=False):
        global total_commands_executed, web_chat_history
        self.last_command_time = time.time()
        if not msg.startswith(self.command_prefix): return
        
        first_word = msg.split()[0].lower()
        if first_word in self.custom_commands:
            macro_chain = self.custom_commands[first_word]
            val = macro_chain.get("value", macro_chain)
            val = re.sub(r'\s*\|\s*(?=' + re.escape(self.command_prefix) + r')', ' ', val)
            val = re.sub(r'\+\s*(?=' + re.escape(self.command_prefix) + r')', ' ', val)
            val = re.sub(r'(?<=\S)' + re.escape(self.command_prefix), ' ' + self.command_prefix, val)
            self.parse_command(val, user, is_mod, is_owner)
            return
            
        clean_user = user.replace("@", "").lower().strip()
        if clean_user in self.blacklisted_users: return 
        for t in self.blocked_terms:
            if t in msg.lower(): return

        pre_admin = (is_owner or is_mod or user in ("[console]", "[CONSOLE]")
                     or clean_user in owners or clean_user in admins or clean_user == "reallyiron")
        if not pre_admin:
            if clean_user in blocked_users_persistent:
                return
            ban_until = banned_users_chat.get(clean_user)
            if ban_until:
                if ban_until > time.time():
                    return
                else:
                    del banned_users_chat[clean_user]  # expired -- clean it up lazily
            now_t = time.time()
            if now_t - self.user_last_cmd_time.get(clean_user, 0) < self.cmd_cooldown:
                return
            self.user_last_cmd_time[clean_user] = now_t

        clean_msg = re.sub(r'\s*\|\s*(?=' + re.escape(self.command_prefix) + r')', ' ', msg)
        clean_msg = re.sub(r'\+\s*(?=' + re.escape(self.command_prefix) + r')', ' ', clean_msg)
        clean_msg = re.sub(r'(?<=\S)' + re.escape(self.command_prefix), ' ' + self.command_prefix, clean_msg)
        
        cmds = []
        tokens = clean_msg.split()
        curr = []
        for t in tokens:
            if t.startswith(self.command_prefix):
                if curr: cmds.append(" ".join(curr))
                curr = [t]
            else: curr.append(t)
        if curr: cmds.append(" ".join(curr))
            
        action_chain = []
        for c in cmds:
            parts = c.strip().split(maxsplit=1)
            if not parts: continue
            raw_cmd = parts[0].lower()
            if not raw_cmd.startswith(self.command_prefix): continue
            cmd = "!" + raw_cmd[len(self.command_prefix):]
            
            aliases = {
                "!c": "!combo", "!k": "!key", "!t": "!type", "!s": "!send", "!m": "!move", "!d": "!drag", 
                "!w": "!wait", "!sleep": "!wait", "!delay": "!wait", "!kd": "!keydown", "!ku": "!keyup",
                "!lc": "!click", "!lclick": "!click", "!rc": "!rclick",
                "!snapshot": "!makesnapshot", "!disablechat": "!pausechat",
                "!forcerebootvirtualbox": "!forcefixvm", "!forcereboot": "!forcefixvm", "!forcerestart": "!forcefixvm",
                "!forceshutdown": "!killvm"
            }
            if cmd in aliases: cmd = aliases[cmd]
            arg = parts[1].strip() if len(parts) > 1 else ""

            # Small commands that just repackage into an existing primitive + arg.
            if cmd == "!dclick": cmd, arg = "!click", "2"
            elif cmd == "!tripleclick": cmd, arg = "!click", "3"
            elif cmd == "!scrollup": cmd, arg = "!scroll", (arg if arg else "5")
            elif cmd == "!scrolldown":
                try: amt = str(-abs(int(arg))) if arg else "-5"
                except ValueError: amt = "-5"
                cmd, arg = "!scroll", amt

            core_cmd = cmd.lstrip("!").lower()

            now_spam_t = time.time()
            with command_spam_lock:
                cooldown_until = command_cooldown_until.get(cmd, 0)
                if now_spam_t < cooldown_until:
                    continue  # this specific command is cooling down -- silently drop, other commands still work
                uses = command_usage_log.setdefault(cmd, [])
                window = float(permissions_config.get("command_spam_window", 10))
                threshold = int(permissions_config.get("command_spam_threshold", 5))
                cutoff = now_spam_t - window
                while uses and uses[0] < cutoff: uses.pop(0)
                uses.append(now_spam_t)
                if len(uses) >= threshold:
                    command_cooldown_until[cmd] = now_spam_t + 10
                    uses.clear()
                    self.log("[system]", f"[warn] {cmd} used {threshold}+ times within {window:.0f}s -- cooling down for 10s.", "sysmsg")
                    continue

            if os_voting_enabled and core_cmd in get_os_trigger_map():
                target_entry = get_os_trigger_map()[core_cmd]
                # Same bypass as restart/revert/ban: admins, the owner, mods, and the
                # console all switch instantly instead of needing to accumulate
                # OS_VOTE_REQUIRED votes first (is_admin isn't computed yet at this point
                # in the function, so this checks the same underlying pieces directly).
                if is_owner or is_mod or user in ("[console]", "[CONSOLE]") or clean_user in admins:
                    with os_vote_lock:
                        os_votes.pop(core_cmd, None)
                    self.log("[system]", f"[vote] admin/mod bypass -- switching to {target_entry.get('name')} instantly.", "sysmsg")
                    threading.Thread(target=switch_os, args=(target_entry, user), daemon=True).start()
                else:
                    process_os_vote(clean_user, core_cmd, target_entry)
                continue

            valid_user_cmds = [
                "run", "startvm", "type", "send", "key", "combo", "keydown", "keyup", "move", "abs", "click",
                "rclick", "mclick", "scroll", "drag", "wait", "cmd", "roll", "coinflip", "tts", "ttsloop",
                "ttsxp", "ttsxploop", "winkey", "dir", "taskkill", "openfile",
                "shake", "circle", "spiral", "jiggle",
                "msgbox", "spam", "countdown", "matrix", "colorscheme", "rainbow",
                "notepadflood", "exeflood", "txtflood", "deskflood", "beep",
                "pausevm", "resumevm", "vmsavestate", "vmstatus", "acpishutdown", "acpirestart", "deletesnapshot",
                "closevmwarewindow",
                "sr", "sb", "sbid", "gtts", "findsr", "vr", "findvr",
            ] + list(APP_RUN_MAP.keys()) + list(COMBO_SHORTCUTS.keys()) + list(CMD_TYPED_MAP.keys())
            info_cmds = ["ping", "uptime", "help", "stats", "history", "leaderboard", "queue", "status"]
            all_valid_cmds = valid_user_cmds + info_cmds + [
                "pausechat", "enablechat", "enablecv", "votestop", "clear", "say", "shutdown", "killvm",
                "makesnapshot", "restartvm", "revert", "forcefixvm", "efail", "poweroff", "ban",
                "enableinternet", "disableinternet", "skipsr", "clearsr", "skipvr", "clearvr", "discardvmwarestate",
                "enableinternetvmware", "disableinternetvmware", "enableinternetvbox", "disableinternetvbox",
            ]
            
            if core_cmd not in all_valid_cmds:
                self.log("[system]", f"[err] Can't find command: {self.command_prefix}{core_cmd}", "err")
                continue

            req_args = [
                "type", "send", "key", "combo", "keydown", "keyup", "move", "abs", "drag", "wait", "cmd",
                "makesnapshot", "tts", "ttsloop", "ttsxp", "ttsxploop", "winkey", "taskkill", "openfile",
                "msgbox", "spam", "sr", "sb", "sbid", "gtts", "findsr", "vr", "findvr",
            ]
            examples = {
                "type": f"{self.command_prefix}type hello world", "send": f"{self.command_prefix}send hello world",
                "key": f"{self.command_prefix}key enter", "combo": f"{self.command_prefix}combo win r",
                "keydown": f"{self.command_prefix}keydown shift", "keyup": f"{self.command_prefix}keyup shift",
                "move": f"{self.command_prefix}move left 50", "abs": f"{self.command_prefix}abs 960 540",
                "drag": f"{self.command_prefix}drag 100 100", "wait": f"{self.command_prefix}wait 5",
                "cmd": f"{self.command_prefix}cmd echo hello", "run": f"{self.command_prefix}run calc",
                "makesnapshot": f"{self.command_prefix}makesnapshot Backup1",
                "tts": f"{self.command_prefix}tts hello there", "ttsloop": f"{self.command_prefix}ttsloop spam message",
                "ttsxp": f"{self.command_prefix}ttsxp windows xp speech", "ttsxploop": f"{self.command_prefix}ttsxploop loop this xp",
                "winkey": f"{self.command_prefix}winkey d", "taskkill": f"{self.command_prefix}taskkill notepad.exe",
                "openfile": f"{self.command_prefix}openfile C:\\test.txt", "msgbox": f"{self.command_prefix}msgbox hello chat",
                "spam": f"{self.command_prefix}spam hi 5",
                "sr": f"{self.command_prefix}sr dQw4w9WgXcQ  (or a full video/playlist url)",
                "sb": f"{self.command_prefix}sb airhorn  (searches myinstants.com)",
                "sbid": f"{self.command_prefix}sbid mlg-air-horn  (exact myinstants.com/en/instant/(id)/ id, no search)",
                "findsr": f"{self.command_prefix}findsr never gonna give you up  (searches youtube, queues the 1st result)",
                "gtts": f"{self.command_prefix}gtts hello chat, this is google tts",
                "vr": f"{self.command_prefix}vr dQw4w9WgXcQ  (or a full video/playlist url)",
                "findvr": f"{self.command_prefix}findvr never gonna give you up  (searches youtube, queues the 1st result)",
            }
            if core_cmd in req_args and not arg:
                self.log("[system]", f"[info] Invalid args! Example: {examples.get(core_cmd, f'{self.command_prefix}{core_cmd} [args]')}", "sysmsg")
                continue

            total_commands_executed += 1
            self.user_cmd_counts[clean_user] += 1
            if clean_user in owners or clean_user == "reallyiron": is_owner = True
            is_admin = is_owner or is_mod or user == "[console]" or user == "[CONSOLE]" or clean_user in admins
            
            if cmd == "!pausechat":
                if is_owner:
                    self.chat_paused = True
                    self.log("[system]", "chat has been paused by owner. only owners can send commands.", "sysmsg")
                continue
            if cmd == "!enablechat":
                if is_owner:
                    self.chat_paused = False
                    self.log("[system]", "chat has been unpaused. everyone can send commands again.", "sysmsg")
                continue
            if self.chat_paused and not is_owner: continue
            
            append_to_json_log(logs_file, user, f"{cmd} {arg}".strip())
            if is_admin: append_to_json_log(modlogs_file, user, f"{cmd} {arg}".strip())

            # --- Info commands: chat/GUI only, no VM interaction ---
            if cmd == "!ping":
                self.log("[system]", "pong! chat control is active.", "sysmsg")
                continue
            if cmd == "!uptime":
                uptime_sec = int(time.time() - script_start_time)
                m, s = divmod(uptime_sec, 60)
                h, m = divmod(m, 60)
                self.log("[system]", f"bot uptime: {h}h {m}m {s}s", "sysmsg")
                continue
            if cmd == "!help":
                self.log("[system]", "commands: keyboard (!type !key !combo !winkey), mouse (!click !move !scroll !drag !shake !circle), "
                                      "apps (!notepad !calc !paint ...), fun (!msgbox !spam !countdown !matrix !beep), "
                                      "vm votes (!revert !restartvm !poweroff), info (!stats !history !leaderboard !queue !status). "
                                      "chain commands in one message, e.g. !notepad !wait 1 !type hello !key enter", "sysmsg")
                continue
            if cmd == "!stats":
                self.log("[system]", f"commands run: {total_commands_executed} | failed: {total_commands_failed} | active chains: {self.active_chains}", "sysmsg")
                continue
            if cmd == "!status":
                self.log("[system]", f"status: {current_status} | viewers: {current_viewers} | likes: {current_likes} | chat paused: {self.chat_paused} | vm busy: {self.vm_maintenance}", "sysmsg")
                continue
            if cmd == "!history":
                with history_lock: recent = list(web_chat_history)[-5:]
                if recent:
                    summary = " || ".join(f"{m['u']}: {m['m']}" for m in recent)[:400]
                    self.log("[system]", f"recent: {summary}", "sysmsg")
                else:
                    self.log("[system]", "no history yet.", "sysmsg")
                continue
            if cmd == "!leaderboard":
                top = self.user_cmd_counts.most_common(5)
                if top:
                    board = " | ".join(f"{u}:{c}" for u, c in top)
                    self.log("[system]", f"top chatters: {board}", "sysmsg")
                else:
                    self.log("[system]", "no commands run yet.", "sysmsg")
                continue
            if cmd == "!queue":
                self.log("[system]", f"active command chains running: {self.active_chains}", "sysmsg")
                continue

            if cmd == "!enablecv":
                 if is_owner: self.changevm_enabled = True
                 return

            if cmd in VM_CONTROL_COMMANDS and not getattr(self, 'vm_control_enabled', True):
                self.log("[system]", f"[info] {cmd} ignored -- VM control is currently turned off (see Dashboard).", "sysmsg")
                continue

            if cmd in self.disabled_commands and not is_admin: continue
            
            if cmd in ["!votestop", "!clear", "!say", "!shutdown", "!killvm", "!makesnapshot", "!forcefixvm", "!enableinternet", "!disableinternet", "!skipsr", "!clearsr", "!skipvr", "!clearvr", "!discardvmwarestate"]:
                if cmd == "!say" and not self.say_admin_only:
                     if any(bad_word in arg.lower() for bad_word in banned_words): pass
                     else: self.log("[announcement]", arg, "sysmsg")
                     continue
                if is_admin:
                    if cmd == "!votestop":
                        with self.vote_lock: self.active_votes.clear()
                    elif cmd == "!clear":
                        with history_lock: web_chat_history.clear()
                    elif cmd == "!say": self.log("[announcement]", arg, "sysmsg")
                    elif cmd == "!shutdown": action_chain.append(("shutdown", "", user))
                    elif cmd == "!killvm": action_chain.append(("killvm", "", user))
                    elif cmd == "!forcefixvm": action_chain.append(("forcefixvm", "", user))
                    elif cmd == "!enableinternet": action_chain.append(("enableinternet", "", user))
                    elif cmd == "!disableinternet": action_chain.append(("disableinternet", "", user))
                    elif cmd == "!skipsr":
                        with music_lock:
                            skipped = music_song_requests.pop(0) if music_song_requests else None
                        music_skip_track()
                        if skipped: self.log("[system]", f"[info] {user} skipped the current song and dropped the next queued request ({skipped.get('raw', '')}).", "sysmsg")
                        else: self.log("[system]", f"[info] {user} skipped the current song.", "sysmsg")
                    elif cmd == "!clearsr":
                        with music_lock:
                            cleared = len(music_song_requests)
                            music_song_requests.clear()
                        self.log("[system]", f"[info] {user} cleared the song request queue ({cleared} pending request(s) dropped).", "sysmsg")
                    elif cmd == "!skipvr":
                        with video_lock:
                            skipped = video_requests.pop(0) if video_requests else None
                        video_skip_track()
                        if skipped: self.log("[system]", f"[info] {user} skipped the current video and dropped the next queued request ({skipped.get('raw', '')}).", "sysmsg")
                        else: self.log("[system]", f"[info] {user} skipped the current video.", "sysmsg")
                    elif cmd == "!clearvr":
                        with video_lock:
                            cleared = len(video_requests)
                            video_requests.clear()
                        self.log("[system]", f"[info] {user} cleared the video request queue ({cleared} pending request(s) dropped).", "sysmsg")
                    elif cmd == "!discardvmwarestate":
                        self.discard_vmware_state(user)
                else:
                    if cmd == "!forcefixvm":
                        self.process_vote(user, f"{self.command_prefix}forcefixvm", 2)
                    elif cmd in ("!enableinternet", "!disableinternet", "!skipsr", "!clearsr", "!skipvr", "!clearvr", "!discardvmwarestate"):
                        self.log("[system]", f"[err] {cmd} is moderator-only.", "err")
                if is_owner and cmd == "!makesnapshot":
                    action_chain.append(("makesnapshot", arg, user))
                continue
                
            if cmd in ["!restartvm", "!revert", "!efail", "!poweroff"]:
                display_vote_cmd = cmd.replace("!", self.command_prefix)
                vote_key = {"!restartvm": "restart_votes", "!revert": "revert_votes"}.get(cmd, "restart_votes")
                required = get_vote_threshold(vote_key, 2)
                if is_admin: 
                    with self.vote_lock:
                        if display_vote_cmd in self.active_votes:
                            del self.active_votes[display_vote_cmd]
                            self.log("[system]", f"[info] admin forced {cmd.replace('!', '')}, cancelled ongoing vote.", "sysmsg")
                    action_chain.append((cmd.replace("!", ""), "", user))
                else: 
                    self.process_vote(user, display_vote_cmd, required)
                continue

            if cmd == "!ban":
                target = normalize_username(arg.lstrip("@").strip())
                if not target:
                    self.log("[system]", "[err] !ban needs a username, e.g. !ban @someuser", "err")
                    continue
                required = get_vote_threshold("ban_votes", 3)
                vote_key = f"{self.command_prefix}ban:{target}"
                if is_admin:
                    banned_users_chat[target] = time.time() + 1800  # 30 min
                    save_user_mgmt()
                    self.log("[system]", f"[info] {target} banned by admin for 30 minutes.", "sysmsg")
                else:
                    self.process_vote(user, vote_key, required)
                continue

            # --- App launchers (Win+R), key-combo shortcuts, and cmd.exe-typed utilities ---
            if core_cmd in APP_RUN_MAP:
                run_arg = APP_RUN_MAP[core_cmd] + (f" {arg}" if arg else "")
                action_chain.append(("run", run_arg, user))
                continue
            if core_cmd in COMBO_SHORTCUTS:
                action_chain.append(("combo", COMBO_SHORTCUTS[core_cmd], user))
                continue
            if core_cmd in CMD_TYPED_MAP:
                action_chain.append(("send", CMD_TYPED_MAP[core_cmd] + (f" {arg}" if arg else ""), user))
                continue
            if core_cmd == "winkey":
                action_chain.append(("combo", f"win+{arg}", user))
                continue
            if core_cmd == "dir":
                action_chain.append(("send", f"dir {arg}".strip(), user))
                continue
            if core_cmd == "taskkill":
                proc = arg if arg.lower().endswith(".exe") else f"{arg}.exe"
                action_chain.append(("send", f"taskkill /F /IM {proc}", user))
                continue
            if core_cmd == "openfile":
                action_chain.append(("send", f"start {arg}", user))
                continue

            if core_cmd in valid_user_cmds: action_chain.append((core_cmd, arg, user))
            
        if action_chain:
            self.trigger_command_chain(action_chain)

    def chat_listener_loop(self, thread_id=0):
        if not pytchat_available: return
        chat = None
        connected_url = None
        retry_delay = 2 
        error_count = 0
        chat_start_time = time.time()
        is_first_fetch = True
        is_connected = False
        first_connect = True
        
        while self.running and getattr(self, 'listener_id', 0) == thread_id:
            try:
                target_url = getattr(self, "active_url", None)
                if (target_url and target_url != connected_url) or (target_url and getattr(self, "force_connect", False)):
                    self.force_connect = False
                    if target_url == "[DEBUG_MODE]":
                        chat = "[DEBUG_MODE]"
                        connected_url = target_url
                        retry_delay = 2 
                    else:
                        try:
                            vid = self.resolve_live_video_id(target_url)
                            if vid and len(vid) == 11:
                                if self.config.get("strict_live_check", True) and not self.is_video_currently_live(vid):
                                    if getattr(self, "last_live_warn_time", 0) < time.time() - 30:
                                        self.log("[system]", f"[warn] video {vid} appears offline! (Uncheck 'Strict Live Check' in Settings if this is wrong)", "err")
                                        self.last_live_warn_time = time.time()
                                    time.sleep(5)
                                    continue
                            if chat and hasattr(chat, 'terminate'):
                                try: chat.terminate()
                                except: pass
                            if self.config.get("verbose_connection_logs", False):
                                console_log("INFO", f"[pytchat] attempting connection to video id {vid}...")
                            chat = pytchat.create(video_id=vid, interruptable=False)
                            if chat.is_alive():
                                connected_url = target_url
                                retry_delay = 2 
                                chat_start_time = time.time()
                                is_first_fetch = True
                                self.start_stats_thread()
                                if not is_connected:
                                    is_connected = True
                                    first_connect = False
                                    self.log("[system]", "connected to chat", "sysmsg")
                                    if hasattr(self, 'lbl_status'): self.lbl_status.configure(text="Connected", fg="#10B981")
                            else:
                                 time.sleep(retry_delay)
                                 retry_delay = min(retry_delay * 2, 60) 
                                 if is_connected:
                                     self.log("[system]", "disconnected from yt connecting to stream", "sysmsg")
                                     is_connected = False
                        except Exception as parse_err:
                            err_msg = str(parse_err)
                            if "ReadTimeout" in err_msg or "timeout" in err_msg.lower() or "429" in err_msg or "11001" in err_msg or "getaddrinfo" in err_msg.lower() or "name or service not known" in err_msg.lower(): 
                                self.log("[system]", f"[warn] connection dropped. retrying in {retry_delay}s...", "sysmsg")
                            else:
                                console_log("ERROR", f"chat init error: {parse_err}\n{traceback.format_exc()}")
                                self.log("[system]", f"[error] chat init error: {parse_err}", "err")
                            chat = None
                            time.sleep(retry_delay)
                            retry_delay = min(retry_delay * 2, 60) 
                            if is_connected:
                                self.log("[system]", "disconnected from yt connecting to stream", "sysmsg")
                                is_connected = False
                try:
                    if chat == "[DEBUG_MODE]": pass
                    elif chat and chat.is_alive():
                        if retry_delay > 2: retry_delay = 2
                        if time.time() - chat_start_time > 21600:
                            if hasattr(self, 'resolved_id_cache'): self.resolved_id_cache.clear()
                            if hasattr(chat, 'terminate'):
                                try: chat.terminate()
                                except: pass
                            chat = None
                            connected_url = None
                            chat_start_time = time.time()
                            continue
                            
                        try: chat_data = chat.get()
                        except Exception as e:
                            chat_data = None
                            time.sleep(1)
                            
                        if chat_data:
                            error_count = 0
                            if is_first_fetch:
                                is_first_fetch = False
                                for c in chat_data.items:
                                    if hasattr(c, 'id'): self.processed_msg_ids.add(c.id)
                                continue
                            new_items = [c for c in chat_data.items if hasattr(c, 'id') and c.id not in self.processed_msg_ids]
                            for c in new_items:
                                self.processed_msg_ids.add(c.id)
                                if not self.listening_to_chat: continue 
                                msg_lower = c.message.lower().strip()
                                clean_name = c.author.name.replace("@", "").lower().strip()
                                if clean_name == "nightbot": continue
                                if clean_name in ["reallybotyt", "system"]:
                                    c.author.name = "[system]"
                                    is_owner = True
                                    is_mod = True
                                else:
                                    is_owner = c.author.isChatOwner or clean_name in owners or clean_name == "reallyiron"
                                    is_mod = is_owner or c.author.isChatModerator or clean_name in admins
                                pfp_url = ""
                                try: pfp_url = getattr(c.author, "imageUrl", "") or ""
                                except Exception: pass
                                add_to_history(c.author.name, c.message, "user", is_mod, is_owner, pfp_url=pfp_url)
                                console_log("CHAT", f"[{c.author.name}]: {c.message}")
                                append_to_all_msgs_log(c.author.name, c.message)
                                if self.listening_to_chat:
                                    try: self.parse_command(c.message, c.author.name, is_mod, is_owner)
                                    except Exception as parse_err: self.log("[system]", f"[err] command parsing error: {parse_err}", "err")
                            if len(self.processed_msg_ids) > 5000: self.processed_msg_ids = set(list(self.processed_msg_ids)[-1000:])
                    elif chat and not chat.is_alive():
                        if is_connected:
                            self.log("[system]", "disconnected from yt connecting to stream", "sysmsg")
                            is_connected = False
                        if hasattr(self, 'resolved_id_cache'): self.resolved_id_cache.clear()
                        if hasattr(chat, 'terminate'):
                            try: chat.terminate()
                            except: pass
                        chat = None
                        connected_url = None
                        chat_start_time = time.time()
                except Exception as e:
                    self.log("[system]", f"[err] chat listener error: {e}", "err")
                    error_count += 1
                    if error_count > 5:
                        if hasattr(self, 'resolved_id_cache'): self.resolved_id_cache.clear()
                        if chat and hasattr(chat, 'terminate'):
                            try: chat.terminate()
                            except: pass
                        chat = None
                        connected_url = None
                        error_count = 0
                        chat_start_time = time.time()
                time.sleep(0.5)
            except Exception as e:
                self.log("[system]", f"[err] critical chat error: {e}", "err")
                error_count += 1
                if error_count > 5:
                    if hasattr(self, 'resolved_id_cache'): self.resolved_id_cache.clear()
                    connected_url = None
                    if chat and hasattr(chat, 'terminate'):
                        try: chat.terminate()
                        except: pass
                    chat = None
                    error_count = 0
                time.sleep(2)
        if chat and hasattr(chat, 'terminate'):
            try: chat.terminate()
            except: pass

    def _kill_vbox_tasks(self):
        try:
            res = vm_stop(vm_name, current_vm_backend, hard=True)
            if res.returncode != 0:
                self.log("[system]", f"[err] Native shutdown failed: {(res.stderr or res.stdout or '').strip()[:150]}", "err")
        except Exception as ex: 
            self.log("[system]", f"[err] Native shutdown failed: {ex}", "err")
        time.sleep(2)

    def _kill_all_vbox_processes(self):
        try:
            backend = current_vm_backend
            self.log("[system]", f"[warn] force-killing the stuck {backend} guest process...", "sysmsg")
            if platform.system() == "Windows":
                if backend == "vmware":
                    # Deliberately NOT killing vmware.exe (the Workstation application shell
                    # itself) -- only vmware-vmx.exe (the actual per-VM guest worker process)
                    # and its network helpers, so Workstation's own window stays open and the
                    # rest of your VMs (if any) are untouched.
                    subprocess.run(["taskkill", "/F", "/IM", "vmware-vmx.exe", "/IM", "vmnat.exe", "/IM", "vmnetdhcp.exe", "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
                else:
                    subprocess.run(["taskkill", "/F", "/IM", "VBoxHeadless.exe", "/IM", "VirtualBoxVM.exe", "/IM", "VBoxSVC.exe", "/IM", "VBoxSDS.exe", "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            else:
                proc_names = ["vmware-vmx", "vmnet-natd", "vmnet-dhcpd"] if backend == "vmware" else ["VBoxHeadless", "VirtualBoxVM", "VBoxSVC"]
                for proc_name in proc_names:
                    subprocess.run(["pkill", "-9", "-f", proc_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        except Exception as ex: 
            self.log("[system]", f"[err] Process annihilation failed: {ex}", "err")
        time.sleep(3)

    def _do_vm_maintenance(self, cmd_type, target_snap=None):
        if self.vm_maintenance: return
        self.vm_maintenance = True
        
        # --- PATH-BASED BACKEND SAFEGUARD ---
        if str(vm_name).lower().endswith(".vmx"):
            backend = "vmware"
        else:
            backend = current_vm_backend
            
        self.log("[system]", f"[info] Executing: {cmd_type}... (backend: {backend})", "sysmsg")
        try:
            self.shared_session = None
            self.shared_kb = None
            self.shared_mouse = None

            if cmd_type == "startvm":
                res = vm_start(vm_name, backend)
                if res.returncode == 0: self.log("[system]", f"[info] {backend} VM started successfully.", "sysmsg")
                else: self.log("[system]", f"[err] {backend} start failed: {res.stderr[:100]}", "err")
            elif cmd_type == "pausevm":
                res = vm_pause(vm_name, backend)
                if res.returncode == 0: self.log("[system]", "[info] VM paused.", "sysmsg")
                else: self.log("[system]", f"[err] pause failed: {res.stderr[:100]}", "err")
            elif cmd_type == "resumevm":
                res = vm_unpause(vm_name, backend)
                if res.returncode == 0: self.log("[system]", "[info] VM resumed.", "sysmsg")
                else: self.log("[system]", f"[err] resume failed: {res.stderr[:100]}", "err")
            elif cmd_type == "vmsavestate":
                res = vm_suspend(vm_name, backend)
                if res.returncode == 0: self.log("[system]", "[info] VM state saved (suspended).", "sysmsg")
                else: self.log("[system]", f"[err] savestate failed: {res.stderr[:100]}", "err")
            elif cmd_type in ("enableinternet", "disableinternet"):
                enable = cmd_type == "enableinternet"
                notes = []

                res1 = vm_toggle_internet(vm_name, enable, backend)
                if res1.returncode == 0:
                    notes.append(f"VM adapter -- {res1.stdout}")
                else:
                    detail1 = ((res1.stdout or "") + " " + (res1.stderr or "")).strip()
                    notes.append(f"VM adapter FAILED: {detail1[:200] or '(unknown error)'}")

                if backend == "vmware":
                    host_iface = vbox_config.get("host_vmnet_interface", "").strip() or "VMware Network Adapter VMnet1"
                    res2 = toggle_host_vmnet_adapter(host_iface, enable)
                    if res2.returncode == 0:
                        notes.append(f"host adapter '{host_iface}' {'enabled' if enable else 'disabled'} via netsh (affects EVERY VM on that vnet).")
                    else:
                        detail2 = ((res2.stdout or "") + " " + (res2.stderr or "")).strip()
                        notes.append(f"host adapter '{host_iface}' FAILED: {detail2[:200] or '(unknown error)'}")
                    ok = res1.returncode == 0 or res2.returncode == 0
                else:
                    ok = res1.returncode == 0

                tag = "sysmsg" if ok else "err"
                prefix = "[info]" if ok else "[err]"
                self.log("[system]", f"{prefix} VM internet {'enabled' if enable else 'disabled'} -- {' | '.join(notes)}", tag)
            elif cmd_type == "acpishutdown":
                set_obs_scene(obs_config.get("scene_shutdown", ""))
                res = vm_stop(vm_name, backend, hard=False)
                if res.returncode == 0: self.log("[system]", f"[info] Graceful shutdown signal sent (via {'VMware Tools' if backend == 'vmware' else 'Guest Additions'}).", "sysmsg")
                else: self.log("[system]", f"[err] graceful shutdown failed: {res.stderr[:100]}", "err")
            elif cmd_type == "acpirestart":
                set_obs_scene(obs_config.get("scene_restarting", ""))
                self.log("[system]", "[info] sending graceful shutdown signal, then will reboot the VM...", "sysmsg")
                vm_stop(vm_name, backend, hard=False)
                waited = 0
                running = True
                while waited < 60:
                    time.sleep(2); waited += 2
                    running = vm_is_running(vm_name, backend)
                    if not running: break
                if running:
                    self.log("[system]", "[warn] guest didn't shut down gracefully in time, forcing poweroff...", "err")
                    vm_stop(vm_name, backend, hard=True)
                    time.sleep(2)
                res = vm_start(vm_name, backend)
                if res.returncode == 0: self.log("[system]", "[info] restart complete, VM booting back up.", "sysmsg")
                else: self.log("[system]", f"[err] restart-side start failed: {res.stderr[:100]}", "err")
            elif cmd_type == "deletesnapshot":
                snaps = vm_get_snapshots(vm_name, backend)
                if not snaps:
                    self.log("[system]", "[err] no snapshots found to delete.", "err")
                else:
                    recent = snaps[-1]
                    self.log("[system]", f"[info] deleting most recent snapshot '{recent}'...", "sysmsg")
                    res = vm_delete_snapshot(vm_name, recent, backend)
                    if res.returncode == 0: self.log("[system]", f"[info] snapshot '{recent}' deleted.", "sysmsg")
                    else: self.log("[system]", f"[err] delete snapshot failed: {res.stderr[:100]}", "err")
            elif cmd_type in ["shutdown", "killvm", "restartvm", "revert", "forcefixvm", "efail", "poweroff", "discardvmwarestate"]:
                if cmd_type in ("revert", "discardvmwarestate"): set_obs_scene(obs_config.get("scene_reverting", ""))
                elif cmd_type == "restartvm": set_obs_scene(obs_config.get("scene_restarting", ""))
                elif cmd_type == "efail": set_obs_scene(obs_config.get("scene_error", ""))
                elif cmd_type in ("shutdown", "killvm", "poweroff"): set_obs_scene(obs_config.get("scene_shutdown", ""))
                elif cmd_type == "forcefixvm": set_obs_scene(obs_config.get("scene_restarting", ""))
                if cmd_type in ["efail", "killvm", "poweroff"]:
                    self._kill_all_vbox_processes()
                else:
                    vm_stop(vm_name, backend, hard=True)
                    if backend == "vmware":
                        # vmrun's own stop is clean and doesn't need a dialog dismissed --
                        # but VMware Workstation's UI sometimes throws up a confirmation
                        # prompt anyway ("This VM appears to be in use..." etc). Auto-dismiss
                        # it without stealing focus, so the window never looks stuck/closed.
                        time.sleep(1)
                        _send_enter_to_vmware_window()
                    time.sleep(2)
                
                if cmd_type in ["revert", "forcefixvm", "efail", "discardvmwarestate"]:
                    snap = target_snap
                    if not snap:
                        snaps = vm_get_snapshots(vm_name, backend)
                        if snaps: snap = snaps[-1]
                    if snap:
                        self.log("[system]", f"[info] Restoring {backend} snapshot '{snap}'...", "sysmsg")
                        res = vm_revert_to_snapshot(vm_name, snap, backend)
                        if res.returncode == 0: self.log("[system]", f"[info] {backend} restore successful.", "sysmsg")
                        else: self.log("[system]", f"[err] {backend} restore failed: {res.stderr[:100]}", "err")
                        if backend == "vmware":
                            time.sleep(1)
                            _send_enter_to_vmware_window()
                    else:
                        self.log("[system]", "[err] no snapshot found to discard back to.", "err")
                
                # discardvmwarestate deliberately stops here -- unlike revert/forcefixvm/efail,
                # it leaves the VM powered OFF instead of booting it back up.
                if cmd_type in ["startvm", "restartvm", "revert", "forcefixvm", "efail"]:
                    vm_start(vm_name, backend)
                    if backend == "vmware":
                        time.sleep(1)
                        _send_enter_to_vmware_window()
                elif cmd_type == "discardvmwarestate":
                    self.log("[system]", "[info] VM state discarded -- reverted and left powered off.", "sysmsg")
                    
            elif cmd_type.startswith("ban:"):
                target_user = cmd_type.split(":", 1)[1]
                banned_users_chat[target_user] = time.time() + 1800  # 30 min
                save_user_mgmt()
                self.log("[system]", f"[info] {target_user} banned by chat vote for 30 minutes.", "sysmsg")

            elif cmd_type == "makesnapshot":
                snap_name = target_snap if target_snap else f"ManualSnap_{int(time.time())}"
                self.log("[system]", f"[info] Creating {backend} snapshot '{snap_name}'...", "sysmsg")
                res = vm_snapshot(vm_name, snap_name, backend)
                if res.returncode == 0:
                    self.current_snapshot = snap_name
                    with open(snap_file, "w") as f: f.write(snap_name)
                    self.log("[system]", f"[info] Snapshot '{snap_name}' created and set as active!", "sysmsg")
                else: self.log("[system]", f"[err] Snapshot failed: {res.stderr[:100]}", "err")
                    
        except Exception as e:
            self.log("[system]", f"[err] Maintenance Error: {e}", "err")
        finally:
            self.vm_maintenance = False
            # After the action completes, return to THIS vm's own live scene if OS Voting
            # has an entry for it (each row can have its own obs_live_scene) -- falling back
            # to the single generic scene only in single-VM (non-OS-voting) mode.
            restore_scene = obs_scene_main
            for e in os_list:
                if e.get("vm") == vm_name:
                    row_live_scene = (e.get("obs_live_scene") or "").strip()
                    if row_live_scene:
                        restore_scene = row_live_scene
                    break
            set_obs_scene(restore_scene)
            self.log("[system]", "[info] Maintenance complete.", "sysmsg")

    def _run_vnc_input_action(self, core_cmd, arg, user):
        """Translates a parsed chat command into VNC keyboard/mouse calls against the
        configured target (see _vnc_target_config() -- Real PC or VMware panel, whichever
        has a VNC Host filled in)."""
        global _vnc_purpose
        _vnc_purpose = "mainvm"
        try:
            if core_cmd == "type":
                text = arg[1:-1] if len(arg) >= 2 and arg.startswith('"') and arg.endswith('"') else arg
                vnc_type_text(text)
            elif core_cmd == "send":
                text = arg[1:-1] if len(arg) >= 2 and arg.startswith('"') and arg.endswith('"') else arg
                vnc_type_text(text)
                vnc_key_press("enter")
            elif core_cmd == "combo":
                if arg.strip(): vnc_combo(arg)
            elif core_cmd == "keydown":
                if arg.strip(): vnc_key_down(arg.strip())
            elif core_cmd == "keyup":
                if arg.strip(): vnc_key_up(arg.strip())
            elif core_cmd == "key":
                if arg.strip(): vnc_key_press(arg.strip())
            elif core_cmd == "click":
                count = int(arg) if arg.strip().isdigit() else 1
                vnc_click(1, count)
            elif core_cmd == "rclick":
                count = int(arg) if arg.strip().isdigit() else 1
                vnc_click(3, count)
            elif core_cmd == "mclick":
                count = int(arg) if arg.strip().isdigit() else 1
                vnc_click(2, count)
            elif core_cmd == "move":
                parts = arg.split()
                if len(parts) == 2:
                    try:
                        direction, amt = parts[0].lower(), int(parts[1])
                        dx = -amt if direction == "left" else (amt if direction == "right" else 0)
                        dy = -amt if direction == "up" else (amt if direction == "down" else 0)
                        vnc_move_rel(dx, dy)
                    except ValueError: pass
            elif core_cmd == "abs":
                parts = arg.split()
                if len(parts) == 2:
                    try: vnc_move_abs(int(parts[0]), int(parts[1]))
                    except ValueError: pass
            elif core_cmd == "drag":
                parts = arg.split()
                if len(parts) == 4:
                    try:
                        x1, y1, x2, y2 = (int(p) for p in parts)
                        vnc_drag(x1, y1, x2, y2)
                    except ValueError: pass
                elif len(parts) == 2:
                    try:
                        dx, dy = int(parts[0]), int(parts[1])
                        vnc_drag(vnc_cursor_x, vnc_cursor_y, vnc_cursor_x + dx, vnc_cursor_y + dy)
                    except ValueError: pass
            elif core_cmd == "scroll":
                scroll_arg = arg.strip()
                words = scroll_arg.split()
                if words and words[0].lower() in ("up", "down"):
                    direction = words[0].lower()
                    try: magnitude = int(words[1]) if len(words) > 1 else 5
                    except ValueError: magnitude = 5
                    vnc_scroll(magnitude if direction == "up" else -magnitude)
                else:
                    try: vnc_scroll(int(scroll_arg))
                    except ValueError: pass

            elif core_cmd in ("run", "cmd", "open_app"):
                is_admin = (core_cmd == "cmd")
                full_cmd = f"cmd /c {arg}" if is_admin else arg
                vnc_combo(["super", "r"])           # open the Run dialog
                time.sleep(0.5)
                if core_cmd == "run" and not arg.strip():
                    return  # bare !run: just pop the Run dialog open, nothing typed/submitted
                vnc_type_text(full_cmd)
                time.sleep(0.1)
                if is_admin:
                    vnc_combo(["ctrl", "shift", "return"])  # run-as-admin from the Run dialog
                    time.sleep(0.6)
                    vnc_key_press("left")                    # UAC prompt: select "Yes"
                    time.sleep(0.1)
                    vnc_key_press("return")
                else:
                    vnc_key_press("return")

            elif core_cmd == "shake":
                try: sh_amp = max(5, min(int(arg), 150)) if arg else 30
                except Exception: sh_amp = 30
                for _ in range(10):
                    if getattr(self, 'cancel_macros', False): break
                    vnc_move_rel(random.choice([-1, 1]) * sh_amp, random.choice([-1, 1]) * sh_amp)
                    time.sleep(0.02)

            elif core_cmd == "jiggle":
                try: ji_amp = max(2, min(int(arg), 40)) if arg else 8
                except Exception: ji_amp = 8
                for _ in range(14):
                    if getattr(self, 'cancel_macros', False): break
                    vnc_move_rel(random.randint(-ji_amp, ji_amp), random.randint(-ji_amp, ji_amp))
                    time.sleep(0.03)

            elif core_cmd == "circle":
                try: ci_radius = max(10, min(int(arg), 200)) if arg else 60
                except Exception: ci_radius = 60
                ci_steps = 16
                prev_x, prev_y = float(ci_radius), 0.0
                for i in range(1, ci_steps + 1):
                    if getattr(self, 'cancel_macros', False): break
                    angle = 2 * math.pi * i / ci_steps
                    x, y = ci_radius * math.cos(angle), ci_radius * math.sin(angle)
                    vnc_move_rel(int(x - prev_x), int(y - prev_y))
                    prev_x, prev_y = x, y
                    time.sleep(0.02)

            elif core_cmd == "spiral":
                sp_steps = 20
                prev_x, prev_y = 0.0, 0.0
                for i in range(1, sp_steps + 1):
                    if getattr(self, 'cancel_macros', False): break
                    angle = 2 * math.pi * i / 5
                    radius = i * 4
                    x, y = radius * math.cos(angle), radius * math.sin(angle)
                    vnc_move_rel(int(x - prev_x), int(y - prev_y))
                    prev_x, prev_y = x, y
                    time.sleep(0.02)
        except Exception as e:
            self.log("[system]", f"[err] vnc input '{core_cmd}' failed: {e}", "err")

    def run_cmd_worker(self, action_tuple):
        cmd, arg, user = action_tuple
        try:
            cmd_clean = cmd if cmd.startswith(self.command_prefix) else self.command_prefix + cmd
            core_cmd = cmd_clean.lstrip("!").lstrip(self.command_prefix).lower()
            if core_cmd == "admin_cmd": core_cmd = "cmd"
            maintenance_cmds = ["startvm", "shutdown", "killvm", "restartvm", "revert", "makesnapshot", "forcefixvm", "efail", "poweroff", "pausevm", "resumevm", "vmsavestate", "acpishutdown", "acpirestart", "deletesnapshot", "enableinternet", "disableinternet", "discardvmwarestate"]
            
            if self.vm_maintenance: return
            
            display_cmd = f"{self.command_prefix}{core_cmd}"
            if core_cmd not in maintenance_cmds:
                self.log("[system]", f"running: {display_cmd} {arg}".strip(), "sysmsg")
                
            self.active_com_time = time.time()
            self.is_com_active = True

            lm = getattr(self, 'lag_multiplier', 1.0)
            try:
                if self.ultra_speed: base_type_spd, base_key_del, base_mouse_del = 0.001, 0.001, 0.001
                else:
                    base_type_spd = float(self.config.get("typing_speed", 0.02))
                    base_key_del = float(self.config.get("key_delay", 0.02))
                    base_mouse_del = float(self.config.get("mouse_delay", 0.005))
            except: base_type_spd, base_key_del, base_mouse_del = 0.02, 0.02, 0.005

            def get_release_codes(codes):
                return [c if c in (224, 225) else c | 0x80 for c in codes]

            def handle_input_error(err_obj, action="input"):
                self.force_session_refresh = True
                raise Exception(f"ABORT {err_obj}")

            # Keyboard/mouse input goes through VirtualBox's own COM API (self.shared_kb /
            # self.shared_mouse, obtained and kept fresh by executor_loop) -- no VNC needed
            # for the main VM. Real PC (a separate, arbitrary machine) still uses VNC via its
            # own _realpc_execute() pathway, untouched by any of this.
            def safe_put_scancodes(codes):
                if getattr(self, 'force_session_refresh', False) and getattr(self, 'shared_kb', None) is None: raise Exception("ABORT")
                for attempt in range(100):
                    kb_obj = getattr(self, 'shared_kb', None)
                    if kb_obj:
                        try:
                            int_codes = [int(c) for c in codes]
                            if hasattr(kb_obj, 'put_scancodes'): kb_obj.put_scancodes(int_codes)
                            else: kb_obj.putScancodes(int_codes)
                            return
                        except Exception as e:
                            time.sleep(0.01 * lm)
                            self.last_e = e
                    else:
                        self.force_session_refresh = True
                        time.sleep(0.1 * lm)
                try: handle_input_error(getattr(self, 'last_e', "COM Lost"), "scancodes")
                except: raise Exception("ABORT Scancodes dropped")

            def safe_put_mouse_event(dx, dy, dz, dw, button_state):
                if getattr(self, 'force_session_refresh', False) and getattr(self, 'shared_mouse', None) is None: raise Exception("ABORT")
                for attempt in range(100):
                    mouse_obj = getattr(self, 'shared_mouse', None)
                    if mouse_obj:
                        try:
                            if hasattr(mouse_obj, 'put_mouse_event'): mouse_obj.put_mouse_event(int(dx), int(dy), int(dz), int(dw), int(button_state))
                            else: mouse_obj.putMouseEvent(int(dx), int(dy), int(dz), int(dw), int(button_state))
                            return
                        except Exception as e:
                            time.sleep(0.01 * lm)
                            self.last_e = e
                    else:
                        self.force_session_refresh = True
                        time.sleep(0.1 * lm)
                try: handle_input_error(getattr(self, 'last_e', "COM Lost"), "mouse")
                except: raise Exception("ABORT Mouse dropped")

            def safe_put_mouse_event_absolute(x, y, dz, dw, button_state):
                if getattr(self, 'force_session_refresh', False) and getattr(self, 'shared_mouse', None) is None: raise Exception("ABORT")
                for attempt in range(100):
                    mouse_obj = getattr(self, 'shared_mouse', None)
                    if mouse_obj:
                        try:
                            if hasattr(mouse_obj, 'put_mouse_event_absolute'): mouse_obj.put_mouse_event_absolute(int(x), int(y), int(dz), int(dw), int(button_state))
                            else: mouse_obj.putMouseEventAbsolute(int(x), int(y), int(dz), int(dw), int(button_state))
                            return
                        except Exception as e:
                            time.sleep(0.01 * lm)
                            self.last_e = e
                    else:
                        self.force_session_refresh = True
                        time.sleep(0.1 * lm)
                try: handle_input_error(getattr(self, 'last_e', "COM Lost"), "mouse_abs")
                except: raise Exception("ABORT Mouse abs dropped")

            def do_mouse_click(btn_code, count_str):
                if getattr(self, 'force_session_refresh', False): raise Exception("ABORT")
                count = 1
                if count_str.isdigit(): count = int(count_str)
                with self.input_lock:
                    for _ in range(min(count, 50)):
                        safe_put_mouse_event(0, 0, 0, 0, self.vbox_mouse_btns | btn_code)
                        time.sleep(base_mouse_del * lm)
                        safe_put_mouse_event(0, 0, 0, 0, self.vbox_mouse_btns & ~btn_code)
                        time.sleep(base_mouse_del * lm)

            if core_cmd in maintenance_cmds:
                self.clear_commands()
                self._do_vm_maintenance(core_cmd, arg if core_cmd == "makesnapshot" else self.current_snapshot)
                return

            # Every keyboard/mouse primitive below, plus the handful of commands that touch
            # hardware directly instead of recursing through a primitive (run/cmd opens Win+R
            # itself; the mouse-pattern chaos commands drive the mouse directly), goes through
            # VirtualBox's COM API via safe_put_scancodes/safe_put_mouse_event when the CURRENT
            # VM is VBox-backed. Everything else (msgbox, spam, colorscheme, rainbow,
            # notepadflood, beep, tts, roll, coinflip, etc.) is built out of these primitives
            # via recursive self.run_cmd_worker(...) calls, so it automatically goes through
            # whichever backend is active too, once its building blocks do -- no extra listing
            # needed. Real PC's VNC target (a separate, arbitrary machine) is untouched -- it
            # has its own dedicated _realpc_execute() pathway and never routes through here.
            #
            # VMware has no equivalent of VBox's COM keyboard/mouse API -- vmrun can only
            # start/stop/snapshot a VM, not send it input. So when the CURRENT VM is
            # VMware-backed, input goes through VNC instead (_run_vnc_input_action, using the
            # VMware panel's own VNC Host/Port/Password), while VM lifecycle above this point
            # is untouched either way (that's what _do_vm_maintenance's backend branch is for).
            _vnc_input_cmds = {"type", "send", "combo", "keydown", "keyup", "key", "click", "rclick", "mclick",
                                "move", "abs", "drag", "scroll", "run", "cmd", "open_app",
                                "shake", "jiggle", "circle", "spiral"}
            if current_vm_backend == "vmware" and core_cmd in _vnc_input_cmds:
                self._run_vnc_input_action(core_cmd, arg, user)
                return

            with self.input_lock:
                def type_char_smart(char, type_delay=base_type_spd):
                    if getattr(self, 'force_session_refresh', False): raise Exception("ABORT")
                    modifiers, base_code = get_typed_codes(char, keyboard_layout)
                    if base_code == [0]: return
                    for mod in modifiers:
                        safe_put_scancodes(mod)
                        time.sleep(0.002 * lm) 
                    safe_put_scancodes(base_code)
                    time.sleep(type_delay * lm) 
                    safe_put_scancodes(get_release_codes(base_code))
                    for mod in reversed(modifiers):
                        time.sleep(0.002 * lm)
                        if mod == [0x2A]: safe_put_scancodes([0xAA])
                        elif mod == [0xE0, 0x38]: safe_put_scancodes([0xE0, 0xB8])
                        else: safe_put_scancodes(get_release_codes(mod))
                        time.sleep(0.002 * lm)
                    dead_keys = {"DANISH": ['~', '^', '`', '´', '¨'], "GERMAN": ['^', '`', '´'], "FRENCH": ['^', '¨'], "TURKISH": ['~', '^', '`', '´', '¨'], "UK": ['`']}
                    if char in dead_keys.get(keyboard_layout, []):
                        time.sleep(0.01 * lm)
                        safe_put_scancodes([0x39])
                        time.sleep(type_delay * lm)
                        safe_put_scancodes([0xB9])

                if core_cmd == "roll":
                    res = str(random.randint(1, 100))
                    self.run_cmd_worker(("type", f"rolling... {res}", user))
                    time.sleep(0.1)
                    self.run_cmd_worker(("key", "enter", user))
                    return
                elif core_cmd == "coinflip":
                    res = random.choice(["heads", "tails"])
                    self.run_cmd_worker(("type", res, user))
                    time.sleep(0.1)
                    self.run_cmd_worker(("key", "enter", user))
                    return

                elif core_cmd == "vmstatus":
                    try:
                        state = "running" if vm_is_running(vm_name, current_vm_backend) else "poweroff"
                        self.log("[system]", f"vm '{vm_name}' ({current_vm_backend}) state: {state}", "sysmsg")
                    except Exception as e:
                        self.log("[system]", f"[err] vmstatus failed: {e}", "err")
                    return

                elif core_cmd == "closevmwarewindow":
                    # Posts Enter to the VMware Workstation window without needing it
                    # focused, to dismiss a blocking prompt ("this VM may have been moved
                    # or copied", etc.) -- works whether or not it currently has focus.
                    ok = _send_enter_to_vmware_window()
                    if ok:
                        self.log("[system]", "[info] sent Enter to VMware Workstation window.", "sysmsg")
                    else:
                        self.log("[system]", "[err] could not send Enter to VMware Workstation window (see error above).", "err")
                    return

                elif core_cmd in ("enableinternetvmware", "disableinternetvmware"):
                    # Explicit, backend-specific -- unlike !enableinternet/!disableinternet
                    # (which follow whichever backend the CURRENT vm uses), these always hit
                    # the host-wide "VMware NAT Service" Windows service directly, regardless
                    # of current_vm_backend or which VM is active.
                    enable = core_cmd == "enableinternetvmware"
                    res = toggle_vmware_nat_service(enable)
                    label = "started" if enable else "stopped"
                    if res.returncode == 0:
                        self.log("[system]", f"[info] VMware NAT Service {label}.", "sysmsg")
                    else:
                        detail = ((res.stdout or "") + " " + (res.stderr or "")).strip()
                        self.log("[system]", f"[err] VMware NAT Service {'start' if enable else 'stop'} failed: {detail[:200] or '(unknown error)'}", "err")
                    return

                elif core_cmd in ("enableinternetvbox", "disableinternetvbox"):
                    # Explicit, backend-specific -- always targets vm_name via VBoxManage's
                    # setlinkstate1 directly, regardless of current_vm_backend. Only makes
                    # sense while a VBox VM is actually the active one (vm_name needs to be
                    # a real VBox VM name, not a .vmx path) -- refuses clearly otherwise
                    # instead of sending a VBoxManage call that would just fail confusingly.
                    if current_vm_backend != "vbox":
                        self.log("[system]", f"[err] current VM is {current_vm_backend}-backed, not VBox -- "
                                              f"nothing to target for !{core_cmd}.", "err")
                        return
                    enable = core_cmd == "enableinternetvbox"
                    res = vbox_toggle_internet(vm_name, enable)
                    label = "enabled" if enable else "disabled"
                    if res.returncode == 0:
                        self.log("[system]", f"[info] VBox internet {label} for '{vm_name}'.", "sysmsg")
                    else:
                        detail = ((res.stdout or "") + " " + (res.stderr or "")).strip()
                        self.log("[system]", f"[err] VBox internet {label} failed: {detail[:200] or '(unknown error)'}", "err")
                    return

                elif core_cmd == "sr":
                    req_arg = arg.strip()
                    if not req_arg:
                        self.log("[system]", "[err] !sr needs a video id/url or playlist id/url.", "err")
                        return
                    result = queue_song_request(req_arg, user=user)
                    if not result:
                        self.log("[system]", f"[err] !sr couldn't parse '{req_arg}'.", "err")
                        return
                    _, is_playlist = result
                    kind = "playlist" if is_playlist else "song"
                    self.log("[system]", f"[info] {kind} request from {user} queued -- plays at the next music change.", "sysmsg")
                    return

                elif core_cmd == "findsr":
                    search_term = arg.strip()
                    if not search_term:
                        self.log("[system]", "[err] !findsr needs a search term, e.g. !findsr never gonna give you up.", "err")
                        return
                    def _run_findsr():
                        self.log("[system]", f"[info] searching youtube for '{search_term}'...", "sysmsg")
                        vid = find_youtube_video_id(search_term)
                        if not vid:
                            self.log("[system]", f"[err] !findsr couldn't find any results for '{search_term}'.", "err")
                            return
                        result = queue_song_request(vid, user=user)
                        if not result:
                            self.log("[system]", f"[err] !findsr found a video but couldn't queue it.", "err")
                            return
                        self.log("[system]", f"[info] found & queued '{search_term}' (youtube.com/watch?v={vid}) for {user} -- plays at the next music change.", "sysmsg")
                    threading.Thread(target=_run_findsr, daemon=True).start()
                    return

                elif core_cmd == "vr":
                    req_arg = arg.strip()
                    if not req_arg:
                        self.log("[system]", "[err] !vr needs a video id/url or playlist id/url.", "err")
                        return
                    result = queue_video_request(req_arg, user=user)
                    if not result:
                        self.log("[system]", f"[err] !vr couldn't parse '{req_arg}'.", "err")
                        return
                    _, is_playlist = result
                    kind = "playlist" if is_playlist else "video"
                    self.log("[system]", f"[info] {kind} request from {user} queued -- plays at the next video change.", "sysmsg")
                    return

                elif core_cmd == "findvr":
                    search_term = arg.strip()
                    if not search_term:
                        self.log("[system]", "[err] !findvr needs a search term, e.g. !findvr never gonna give you up.", "err")
                        return
                    def _run_findvr():
                        self.log("[system]", f"[info] searching youtube for '{search_term}'...", "sysmsg")
                        vid = find_youtube_video_id(search_term)
                        if not vid:
                            self.log("[system]", f"[err] !findvr couldn't find any results for '{search_term}'.", "err")
                            return
                        result = queue_video_request(vid, user=user)
                        if not result:
                            self.log("[system]", f"[err] !findvr found a video but couldn't queue it.", "err")
                            return
                        self.log("[system]", f"[info] found & queued '{search_term}' (youtube.com/watch?v={vid}) for {user} -- plays at the next video change.", "sysmsg")
                    threading.Thread(target=_run_findvr, daemon=True).start()
                    return

                elif core_cmd == "sb":
                    sb_name = arg.strip()
                    if not sb_name:
                        self.log("[system]", "[err] !sb needs a soundboard search term, e.g. !sb airhorn.", "err")
                        return
                    if not vlc_available:
                        self.log("[system]", "[err] python-vlc is not installed -- run: pip install python-vlc", "err")
                        return
                    def _run_sb_search():
                        ok, info = soundboard_web_search_and_play(sb_name, user=user)
                        if ok: self.log("[system]", f"[info] {user} played soundboard result: {info}", "sysmsg")
                        else: self.log("[system]", f"[err] !sb failed: {info}", "err")
                    threading.Thread(target=_run_sb_search, daemon=True).start()
                    return

                elif core_cmd == "sbid":
                    sbid_val = arg.strip()
                    if not sbid_val:
                        self.log("[system]", "[err] !sbid needs a myinstants id, e.g. !sbid mlg-air-horn.", "err")
                        return
                    if not vlc_available:
                        self.log("[system]", "[err] python-vlc is not installed -- run: pip install python-vlc", "err")
                        return
                    def _run_sbid():
                        ok, info = soundboard_web_id_and_play(sbid_val, user=user)
                        if ok: self.log("[system]", f"[info] {user} played soundboard id '{sbid_val}': {info}", "sysmsg")
                        else: self.log("[system]", f"[err] !sbid failed: {info}", "err")
                    threading.Thread(target=_run_sbid, daemon=True).start()
                    return

                elif core_cmd == "gtts":
                    gtts_text = arg.strip()
                    if not gtts_text:
                        self.log("[system]", "[err] !gtts needs some text to speak, e.g. !gtts hello chat.", "err")
                        return
                    if not gtts_available:
                        self.log("[system]", "[err] gTTS is not installed -- run: pip install gTTS", "err")
                        return
                    if not vlc_available:
                        self.log("[system]", "[err] python-vlc is not installed -- run: pip install python-vlc", "err")
                        return
                    def _run_gtts():
                        ok, info = gtts_speak(gtts_text)
                        if ok: self.log("[system]", f"[info] {user} used !gtts: {info}", "sysmsg")
                        else: self.log("[system]", f"[err] !gtts failed: {info}", "err")
                    threading.Thread(target=_run_gtts, daemon=True).start()
                    return

                elif core_cmd == "msgbox":
                    safe_text = arg.replace("'", "").replace('"', "")
                    payload = f"powershell -c \"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('{safe_text}')\""
                    self.run_cmd_worker(("run", payload, user))
                    return

                elif core_cmd == "spam":
                    spam_parts = arg.rsplit(" ", 1)
                    spam_text, spam_n = arg, 5
                    if len(spam_parts) == 2 and spam_parts[1].isdigit():
                        spam_text, spam_n = spam_parts[0], int(spam_parts[1])
                    spam_n = max(1, min(spam_n, 20))
                    for _ in range(spam_n):
                        if getattr(self, 'cancel_macros', False): break
                        self.run_cmd_worker(("send", spam_text, user))
                        time.sleep(0.15 * lm)
                    return

                elif core_cmd == "countdown":
                    try: cd_n = int(arg)
                    except Exception: cd_n = 10
                    cd_n = max(1, min(cd_n, 60))
                    for i in range(cd_n, 0, -1):
                        if getattr(self, 'cancel_macros', False): break
                        self.log("[countdown]", str(i), "sysmsg")
                        time.sleep(1)
                    self.log("[countdown]", "go!", "sysmsg")
                    return

                elif core_cmd == "matrix":
                    mx_chars = "01ｱｲｳｴｵｶｷｸｹｺABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    for _ in range(6):
                        line = "".join(random.choice(mx_chars) for _ in range(random.randint(10, 24)))
                        self.log("[matrix]", line, "sysmsg")
                        time.sleep(0.15)
                    return

                elif core_cmd == "colorscheme":
                    code = re.sub(r'[^0-9A-Fa-f]', '', arg)[:2] or "0A"
                    if len(code) < 2: code = (code + "0A")[:2]
                    self.run_cmd_worker(("send", f"color {code}", user))
                    return

                elif core_cmd == "rainbow":
                    for code in ["4E", "1F", "2A", "5C", "6D", "0A"]:
                        if getattr(self, 'cancel_macros', False): break
                        self.run_cmd_worker(("send", f"color {code}", user))
                        time.sleep(0.4 * lm)
                    return

                elif core_cmd == "notepadflood":
                    try: nf_n = int(arg)
                    except Exception: nf_n = 5
                    nf_n = max(1, min(nf_n, 15))
                    for _ in range(nf_n):
                        if getattr(self, 'cancel_macros', False): break
                        self.run_cmd_worker(("run", "notepad", user))
                        time.sleep(0.3 * lm)
                    return

                elif core_cmd == "exeflood":
                    for _ in range(8):
                        if getattr(self, 'cancel_macros', False): break
                        self.run_cmd_worker(("run", random.choice(_FLOOD_APP_POOL), user))
                        time.sleep(0.3 * lm)
                    return

                elif core_cmd == "txtflood":
                    tf_words = ["chaos", "lol", "bruh", "pog", "haha", "yo", "wow", "nice", "gg", "wat"]
                    for _ in range(5):
                        if getattr(self, 'cancel_macros', False): break
                        line = " ".join(random.choice(tf_words) for _ in range(random.randint(3, 8)))
                        self.run_cmd_worker(("send", line, user))
                        time.sleep(0.2 * lm)
                    return

                elif core_cmd == "deskflood":
                    try: df_n = int(arg)
                    except Exception: df_n = 6
                    df_n = max(1, min(df_n, 15))
                    for _ in range(df_n):
                        if getattr(self, 'cancel_macros', False): break
                        self.run_cmd_worker(("run", random.choice(_FLOOD_APP_POOL), user))
                        time.sleep(0.25 * lm)
                    return

                elif core_cmd == "beep":
                    beep_bits = arg.split()
                    try: beep_freq = int(beep_bits[0]) if beep_bits else 800
                    except Exception: beep_freq = 800
                    try: beep_ms = int(beep_bits[1]) if len(beep_bits) > 1 else 300
                    except Exception: beep_ms = 300
                    beep_freq = max(37, min(beep_freq, 32767))
                    beep_ms = max(50, min(beep_ms, 5000))
                    self.run_cmd_worker(("run", f"powershell -c [console]::beep({beep_freq},{beep_ms})", user))
                    return

                elif core_cmd == "shake":
                    try: sh_amp = max(5, min(int(arg), 150)) if arg else 30
                    except Exception: sh_amp = 30
                    for _ in range(10):
                        if getattr(self, 'cancel_macros', False): break
                        safe_put_mouse_event(random.choice([-1, 1]) * sh_amp, random.choice([-1, 1]) * sh_amp, 0, 0, self.vbox_mouse_btns)
                        time.sleep(base_mouse_del * lm)
                    return

                elif core_cmd == "jiggle":
                    try: ji_amp = max(2, min(int(arg), 40)) if arg else 8
                    except Exception: ji_amp = 8
                    for _ in range(14):
                        if getattr(self, 'cancel_macros', False): break
                        safe_put_mouse_event(random.randint(-ji_amp, ji_amp), random.randint(-ji_amp, ji_amp), 0, 0, self.vbox_mouse_btns)
                        time.sleep(0.03 * lm)
                    return

                elif core_cmd == "circle":
                    try: ci_radius = max(10, min(int(arg), 200)) if arg else 60
                    except Exception: ci_radius = 60
                    ci_steps = 16
                    prev_x, prev_y = float(ci_radius), 0.0
                    for i in range(1, ci_steps + 1):
                        if getattr(self, 'cancel_macros', False): break
                        angle = 2 * math.pi * i / ci_steps
                        x, y = ci_radius * math.cos(angle), ci_radius * math.sin(angle)
                        safe_put_mouse_event(int(x - prev_x), int(y - prev_y), 0, 0, self.vbox_mouse_btns)
                        prev_x, prev_y = x, y
                        time.sleep(base_mouse_del * lm)
                    return

                elif core_cmd == "spiral":
                    sp_steps = 20
                    prev_x, prev_y = 0.0, 0.0
                    for i in range(1, sp_steps + 1):
                        if getattr(self, 'cancel_macros', False): break
                        angle = 2 * math.pi * i / 5
                        radius = i * 4
                        x, y = radius * math.cos(angle), radius * math.sin(angle)
                        safe_put_mouse_event(int(x - prev_x), int(y - prev_y), 0, 0, self.vbox_mouse_btns)
                        prev_x, prev_y = x, y
                        time.sleep(base_mouse_del * lm)
                    return

                elif core_cmd in ["tts", "ttsloop", "ttsxp", "ttsxploop"]:
                    safe_text = arg.replace("'", "").replace('"', "")
                    if core_cmd == "tts":
                        payload = f"powershell -c \"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe_text}')\""
                    elif core_cmd == "ttsloop":
                        payload = f"powershell -c \"Add-Type -AssemblyName System.Speech; $s=(New-Object System.Speech.Synthesis.SpeechSynthesizer); while($true){{$s.Speak('{safe_text}')}}\""
                    elif core_cmd == "ttsxp":
                        payload = f'mshta vbscript:Execute("CreateObject(""SAPI.SpVoice"").Speak(""{safe_text}"")(window.close)")'
                    elif core_cmd == "ttsxploop":
                        payload = f'mshta vbscript:Execute("Set s=CreateObject(""SAPI.SpVoice""):Do:s.Speak(""{safe_text}""):Loop")'
                    self.run_cmd_worker(("run", payload, user))
                    return
                elif core_cmd == "cmd" or core_cmd in ["run", "open_app"]:
                    is_admin = (core_cmd == "cmd")
                    full_cmd = f"cmd /c {arg}" if is_admin else arg
                    safe_put_scancodes(scancodes.get('win', [224, 91]))
                    time.sleep(0.2 * lm)
                    modifiers, base_code = get_typed_codes('r', keyboard_layout)
                    safe_put_scancodes(base_code)
                    time.sleep(base_key_del * lm)
                    safe_put_scancodes(get_release_codes(base_code))
                    safe_put_scancodes(get_release_codes(scancodes.get('win', [224, 91])))

                    if core_cmd == "run" and not arg.strip():
                        return  # bare !run: just pop the Run dialog open, nothing typed/submitted

                    time.sleep(0.5 * lm) 
                    self.run_cmd_worker(("type", full_cmd, user))
                    time.sleep(0.1 * lm) 
                    
                    if is_admin:
                        safe_put_scancodes(scancodes['lctrl'])
                        safe_put_scancodes(scancodes['lshift'])
                        time.sleep(0.1 * lm)
                        safe_put_scancodes(scancodes['enter'])
                        time.sleep(base_key_del * lm)
                        safe_put_scancodes(get_release_codes(scancodes['enter']))
                        time.sleep(0.1 * lm)
                        safe_put_scancodes(get_release_codes(scancodes['lshift']))
                        safe_put_scancodes(get_release_codes(scancodes['lctrl']))
                        time.sleep(0.5 * lm)
                        safe_put_scancodes(scancodes['left'])
                        time.sleep(base_key_del * lm)
                        safe_put_scancodes(get_release_codes(scancodes['left']))
                        time.sleep(0.1 * lm)
                        safe_put_scancodes(scancodes['enter'])
                        time.sleep(base_key_del * lm)
                        safe_put_scancodes(get_release_codes(scancodes['enter']))
                    else:
                        self.run_cmd_worker(("key", "enter", user))
                    return

                elif core_cmd == "type":
                    if len(arg) >= 2 and arg.startswith('"') and arg.endswith('"'): arg = arg[1:-1]
                    for char in arg: 
                        type_char_smart(char, type_delay=base_type_spd)
                        time.sleep(0.005 * lm) 

                elif core_cmd == "send":
                    self.run_cmd_worker(("type", arg, user))
                    time.sleep(0.1 * lm)
                    self.run_cmd_worker(("key", "enter", user))

                elif core_cmd == "combo":
                    keys = parse_combo_keys(arg)
                    pressed_codes = []
                    valid_combo = True
                    for k in keys:
                        k = k.strip()
                        if k.lower() in scancodes:
                            codes = scancodes[k.lower()]
                            safe_put_scancodes(codes)
                            pressed_codes.append(codes)
                            time.sleep(0.1 * lm) 
                        else:
                            self.log("[system]", f"[err] key '{k}' not found.", "err")
                            valid_combo = False
                            break
                    if valid_combo: time.sleep(0.1 * lm) 
                    for codes in reversed(pressed_codes):
                        safe_put_scancodes(get_release_codes(codes))
                        time.sleep(0.02 * lm) 
                    time.sleep(0.5 * lm)

                elif core_cmd == "keydown":
                    if arg.lower() in scancodes: safe_put_scancodes(scancodes[arg.lower()])
                    else: self.log("[system]", f"[err] key '{arg}' not found.", "err")

                elif core_cmd == "keyup":
                    if arg.lower() in scancodes: safe_put_scancodes(get_release_codes(scancodes[arg.lower()]))
                    else: self.log("[system]", f"[err] key '{arg}' not found.", "err")

                elif core_cmd == "key":
                    if arg.lower() in scancodes:
                        safe_put_scancodes(scancodes[arg.lower()])
                        time.sleep(max(0.1, base_key_del * lm))
                        safe_put_scancodes(get_release_codes(scancodes[arg.lower()]))
                        if arg.lower() in ['win', 'lwin', 'rwin', 'cmd', 'super', 'menu', 'esc', 'enter', 'return']: time.sleep(0.5 * lm)
                    elif len(arg) == 1: type_char_smart(arg, type_delay=base_type_spd)
                    else: self.log("[system]", f"[err] key '{arg}' not found.", "err")

                elif core_cmd == "click": do_mouse_click(0x01, arg)
                elif core_cmd == "rclick": do_mouse_click(0x02, arg)
                elif core_cmd == "mclick": do_mouse_click(0x04, arg)

                elif core_cmd == "move":
                    args = arg.split()
                    if len(args) == 2:
                        try:
                            dir = args[0].lower()
                            amt = int(args[1])
                            dx = -amt if dir == "left" else (amt if dir == "right" else 0)
                            dy = -amt if dir == "up" else (amt if dir == "down" else 0)
                            safe_put_mouse_event(dx, dy, 0, 0, self.vbox_mouse_btns)
                        except ValueError: pass

                elif core_cmd == "abs":
                    args = arg.split()
                    if len(args) == 2:
                        try:
                            x, y = int(args[0]), int(args[1])
                            safe_put_mouse_event_absolute(x, y, 0, 0, self.vbox_mouse_btns)
                        except ValueError: pass

                elif core_cmd == "drag":
                    args = arg.split()
                    if len(args) == 4:
                        try:
                            x1, y1, x2, y2 = (int(a) for a in args)
                            safe_put_mouse_event_absolute(x1, y1, 0, 0, self.vbox_mouse_btns)
                            time.sleep(base_mouse_del * lm)
                            safe_put_mouse_event_absolute(x1, y1, 0, 0, self.vbox_mouse_btns | 0x01)
                            time.sleep(base_mouse_del * lm)
                            steps = 5
                            for i in range(1, steps + 1):
                                ix = x1 + (x2 - x1) * i // steps
                                iy = y1 + (y2 - y1) * i // steps
                                safe_put_mouse_event_absolute(ix, iy, 0, 0, self.vbox_mouse_btns | 0x01)
                                time.sleep(base_mouse_del * lm)
                            safe_put_mouse_event_absolute(x2, y2, 0, 0, self.vbox_mouse_btns & ~0x01)
                        except ValueError: pass
                    elif len(args) == 2:
                        try:
                            dx, dy = int(args[0]), int(args[1])
                            safe_put_mouse_event(0, 0, 0, 0, self.vbox_mouse_btns | 0x01)
                            time.sleep(base_mouse_del * lm)
                            steps = 5
                            for i in range(1, steps + 1):
                                step_x = dx // steps
                                step_y = dy // steps
                                safe_put_mouse_event(step_x, step_y, 0, 0, self.vbox_mouse_btns | 0x01)
                                time.sleep(base_mouse_del * lm)
                            safe_put_mouse_event(0, 0, 0, 0, self.vbox_mouse_btns & ~0x01)
                        except ValueError: pass

                elif core_cmd == "scroll":
                    scroll_arg = arg.strip()
                    scroll_words = scroll_arg.split()
                    if scroll_words and scroll_words[0].lower() in ("up", "down"):
                        direction = scroll_words[0].lower()
                        magnitude_str = scroll_words[1] if len(scroll_words) > 1 else "5"
                        try: magnitude = int(magnitude_str)
                        except ValueError: magnitude = 5
                        scroll_arg = str(magnitude if direction == "up" else -magnitude)
                    try:
                        amt = int(scroll_arg)
                        btn = 8 if amt > 0 else 16
                        for _ in range(min(abs(amt), 50)):
                            safe_put_mouse_event(0, 0, 0, 0, self.vbox_mouse_btns | btn)
                            time.sleep(base_mouse_del * lm)
                            safe_put_mouse_event(0, 0, 0, 0, self.vbox_mouse_btns & ~btn)
                            time.sleep(base_mouse_del * lm)
                    except ValueError: pass
                    
            self.consecutive_failures = 0
            self.last_success_time = time.time()
        except Exception as loop_e:
            err_str = str(loop_e).lower()
            if "0x80004005" in err_str or "e_fail" in err_str or "-2147467259" in err_str or "unspecified error" in err_str:
                self.log("[system]", "[error] FATAL E_FAIL DETECTED! Auto-Triggering Global Nuke...", "err")
                self.clear_commands()
                threading.Thread(target=self._do_vm_maintenance, args=("efail", self.current_snapshot), daemon=True).start()
            elif "abort" not in err_str.upper():
                global total_commands_failed
                total_commands_failed += 1
                self.consecutive_failures = getattr(self, 'consecutive_failures', 0) + 1
                err_msg = str(loop_e).replace("\n", " ")[:100]
                if time.time() - getattr(self, 'last_err_spam', 0) > 2.0:
                    console_log("ERROR", f"execution failed: {display_cmd} {arg}: {loop_e}\n{traceback.format_exc()}")
                    self.log("[system]", f"[err] cmd fault: {err_msg}", "err")
                    self.last_err_spam = time.time()
        finally:
            self.is_com_active = False

    def executor_loop(self, thread_id=0):
        try: signal.signal = lambda *args, **kwargs: None
        except Exception: pass
        try:
            if 'pythoncom' in sys.modules: pythoncom.CoInitialize()
        except Exception: pass

        while self.running and getattr(self, 'executor_id', 0) == thread_id:
            if 'pythoncom' in sys.modules:
                try: pythoncom.PumpWaitingMessages()
                except: pass
            
            self.executor_tick = time.time()
            
            try:
                if getattr(self, 'vm_maintenance', False):
                    time.sleep(0.5)
                    continue

                if current_vm_backend == "vmware":
                    # VMware has no COM session to maintain -- input goes through VNC instead
                    # (_run_vnc_input_action), which connects per-action. Just keep status and
                    # the main-scene switch current, and make sure no stale VBox session/handles
                    # are hanging around from a previous VBox-backed VM.
                    if getattr(self, 'shared_session', None) or getattr(self, 'shared_kb', None) or getattr(self, 'vbox', None):
                        try:
                            if getattr(self, 'shared_session', None):
                                if vbox_pkg == "virtualbox": self.shared_session.unlock_machine()
                                else: self.shared_session.unlockMachine()
                        except: pass
                        self.shared_session = None
                        self.shared_kb = None
                        self.shared_mouse = None
                        self.vbox = None

                    if time.time() - getattr(self, 'last_vmrun_poll', 0) > 3:
                        self.last_vmrun_poll = time.time()
                        try:
                            is_running = vm_is_running(vm_name, "vmware")
                            self.set_status("running" if is_running else "stopped")
                            if is_running and getattr(self, 'force_session_refresh', False):
                                set_obs_scene(_get_current_os_live_scene())
                                self.force_session_refresh = False
                            self.com_fail_count = 0
                        except Exception:
                            self.set_status("not found")
                    time.sleep(0.5)
                    continue

                if getattr(self, 'force_session_refresh', False) or self.shared_kb is None:
                    self.force_session_refresh = False
                    
                    if getattr(self, 'shared_session', None):
                        try:
                            if vbox_pkg == "virtualbox": self.shared_session.unlock_machine()
                            else: self.shared_session.unlockMachine()
                        except: pass
                    
                    self.shared_session = None
                    self.shared_kb = None
                    self.shared_mouse = None
                    
                    if getattr(self, 'vbox', None): del self.vbox
                    self.vbox = None
                    
                    try:
                        if 'pythoncom' in sys.modules: pythoncom.CoFreeUnusedLibraries()
                    except: pass
                    gc.collect()

                    try:
                        if vbox_pkg == "virtualbox": self.vbox = virtualbox.VirtualBox()
                        elif vbox_pkg == "vboxapi":
                            self.mgr = VirtualBoxManager(None, None)
                            self.vbox = self.mgr.getVirtualBox()
                    except Exception as e:
                        self.set_status("vbox api error")
                        self.com_fail_count = getattr(self, 'com_fail_count', 0) + 1
                        if self.com_fail_count > 15:
                            self.log("[system]", "[error] VBox API permanently dead! Auto-recovering...", "err")
                            self.com_fail_count = 0
                            self.clear_commands()
                            threading.Thread(target=self._do_vm_maintenance, args=("efail", self.current_snapshot), daemon=True).start()
                        time.sleep(2)
                        continue
                    
                    if self.vbox:
                        try:
                            if vbox_pkg == "virtualbox": machine = self.vbox.find_machine(vm_name)
                            else: machine = self.vbox.findMachine(vm_name)
                            
                            try: m_state = machine.state
                            except: m_state = "unknown"
                            
                            state_str = str(m_state).lower()
                            is_running = ("running" in state_str) or ("5" in state_str)
                            
                            if not is_running:
                                try:
                                    chk = subprocess.run([vbox_manage_cmd, "list", "runningvms"], capture_output=True, text=True, timeout=1)
                                    if f'"{vm_name}"' in chk.stdout:
                                        is_running = True
                                except: pass

                            if is_running:
                                if vbox_pkg == "virtualbox": session = virtualbox.Session()
                                else: session = self.mgr.getSessionObject(self.vbox)
                                
                                lock_success = False
                                for _ in range(15):
                                    try:
                                        if vbox_pkg == "virtualbox":
                                            if session.state != virtualbox.library.SessionState.locked:
                                                machine.lock_machine(session, virtualbox.library.LockType.shared)
                                            lock_success = True
                                        else:
                                            if session.state != self.mgr.constants.SessionState_Locked:
                                                machine.lockMachine(session, self.mgr.constants.LockType_Shared)
                                            lock_success = True
                                        break
                                    except Exception:
                                        time.sleep(0.2)

                                if lock_success:
                                    self.shared_session = session
                                    self.shared_kb = session.console.keyboard
                                    self.shared_mouse = session.console.mouse
                                    self.set_status("running")
                                    set_obs_scene(_get_current_os_live_scene())
                                    self.com_fail_count = 0
                                else:
                                    self.set_status("lock failed")
                                    self.com_fail_count = getattr(self, 'com_fail_count', 0) + 1
                                    if self.com_fail_count > 15:
                                        self.log("[system]", "[error] COM API lock permanently dead! Rebooting system...", "err")
                                        self.com_fail_count = 0
                                        self.clear_commands()
                                        threading.Thread(target=self._do_vm_maintenance, args=("efail", self.current_snapshot), daemon=True).start()
                                    time.sleep(1)
                            else:
                                self.set_status("stopped")
                                self.com_fail_count = 0
                                time.sleep(1)
                        except Exception as e:
                            self.set_status("not found")
                            self.com_fail_count = 0
                            time.sleep(1)

                try:
                    if time.time() - getattr(self, 'last_unstick_time', 0) > 300:
                        self.last_unstick_time = time.time()
                        if getattr(self, 'shared_kb', None):
                            with self.input_lock:
                                for mod in [42, 29, 56, 224, 91]: 
                                    try:
                                        if hasattr(self.shared_kb, 'put_scancodes'): self.shared_kb.put_scancodes([mod | 0x80])
                                        else: self.shared_kb.putScancodes([mod | 0x80])
                                    except: pass
                except: pass

                time.sleep(0.5)
            except Exception as loop_e:
                time.sleep(0.5)

        try:
            if 'pythoncom' in sys.modules: pythoncom.CoUninitialize()
        except Exception: pass

    def ocr_watchdog_loop(self):
        while self.running:
            if getattr(self, 'vm_maintenance', False) or not getattr(self, 'enable_ocr', False):
                time.sleep(5)
                continue
            
            if not ocr_available and getattr(self, 'enable_ocr', False):
                self.log("[system]", "[error] Screen check enabled but pytesseract/PIL is missing! Run: pip install pytesseract pillow", "err")
                self.enable_ocr = False
                self.var_ocr.set(False)
                self.save_settings()
                continue
                
            try:
                if not getattr(self, 'is_com_active', False): 
                    snap_path = f"boot_check_{instance_id}.png"
                    shot_ok = vmware_vnc_capture_screen(snap_path)
                    
                    if shot_ok and os.path.exists(snap_path):
                        img = Image.open(snap_path)
                        img_crop = img.crop((0, 0, img.width, img.height // 2))
                        try:
                            text = pytesseract.image_to_string(img_crop).lower()
                            if "ipxe" in text or "booting from lan" in text or "no bootable" in text or "fatal" in text:
                                self.log("[system]", "[error] iPXE / Boot freeze detected via Screen Check! Auto-reverting...", "err")
                                self.trigger_command(("revert", "", "watchdog"))
                                time.sleep(45) 
                        except pytesseract.TesseractNotFoundError:
                            self.log("[system]", "[error] Tesseract-OCR software is not installed on your PC! Disabling screen check.", "err")
                            self.enable_ocr = False
                            self.var_ocr.set(False)
                            self.save_settings()
                        img.close()
                        try: os.remove(snap_path)
                        except: pass
            except Exception:
                pass
            time.sleep(10)

    def error_watcher_loop(self):
        if platform.system() != "Windows": return
        user32 = ctypes.windll.user32
        wndenumproc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows.argtypes = [wndenumproc, wintypes.LPARAM]
        user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.IsHungAppWindow.argtypes = [wintypes.HWND]
        user32.IsHungAppWindow.restype = wintypes.BOOL
        user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        wm_close = 0x0010
        hung_state = {"found": False}
        @wndenumproc
        def foreach_window(hwnd, lParam):
            if not user32.IsWindowVisible(hwnd): return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0: return True
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.lower()
            class_buff = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, class_buff, 256)
            cls_name = class_buff.value
            
            fatal_errors = ["vmware workstation - error", "application error", "fatal:", "guru meditation"]
            dismiss_only = ["vmware workstation - information", "vmware workstation - question", "vmware workstation - warning"]
            
            if any(err in title for err in fatal_errors) or (cls_name == "#32770" and "vmware" in title and not any(d in title for d in dismiss_only)):
                self.vm_crashed = True
                user32.PostMessageW(hwnd, wm_close, 0, 0)
                return True
                
            if any(warn in title for warn in dismiss_only):
                self.log("[system]", f"[info] Auto-dismissed VMware Popup: {title[:100]}", "sysmsg")
                user32.PostMessageW(hwnd, wm_close, 0, 0)
                return True

            if os.path.splitext(os.path.basename(vm_name))[0].lower() in title and "vmware" in title:
                if user32.IsHungAppWindow(hwnd): hung_state["found"] = True
            return True
            
        while self.running:
            if getattr(self, 'vm_maintenance', False):
                self.vm_frozen_since = None
                self.executor_tick = time.time()
                self.active_com_time = time.time()
                time.sleep(1.0)
                continue
            hung_state["found"] = False
            try: user32.EnumWindows(foreach_window, 0)
            except Exception: pass
            
            log_crash_found = False
            if not getattr(self, 'vm_maintenance', False):
                try:
                    if vm_name and os.path.exists(vm_name):
                        log_dir = os.path.dirname(vm_name)
                        log_file = os.path.join(log_dir, "vmware.log")
                        if os.path.exists(log_file):
                            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                                lines = f.readlines()[-30:]
                                for l in lines:
                                    l_low = l.lower()
                                    if "booting from lan" in l_low or "ipxe" in l_low or "no bootable medium" in l_low:
                                        if getattr(self, 'last_log_error', "") != l_low:
                                            self.last_log_error = l_low
                                            self.log("[system]", "[error] iPXE or broken boot detected via VMware Logs!", "err")
                                        log_crash_found = True
                                        break
                except Exception: pass
            
            api_frozen_timeout = (time.time() - getattr(self, 'executor_tick', time.time())) > 25 and not getattr(self, 'is_com_active', False)
            com_stuck = getattr(self, 'is_com_active', False) and (time.time() - getattr(self, 'active_com_time', time.time())) > 90
            is_frozen = hung_state["found"] or api_frozen_timeout or com_stuck or log_crash_found
            
            if is_frozen:
                if getattr(self, 'vm_frozen_since', None) is None:
                    self.vm_frozen_since = time.time()
                    reason = "ui" if hung_state["found"] else ("iPXE boot" if log_crash_found else ("com stuck" if com_stuck else "api"))
                    self.log("[system]", f"[warn] vmware {reason} frozen. watchdog active...", "sysmsg")
                else:
                    frozen_duration = time.time() - self.vm_frozen_since
                    if frozen_duration >= 20:
                        time_since_last_action = time.time() - getattr(self, 'last_watchdog_action_time', 0)
                        if time_since_last_action > 120: self.watchdog_action_level = 0
                        if getattr(self, 'watchdog_action_level', 0) == 0:
                            self.log("[system]", "[error] vm frozen for 20s! auto-reverting...", "sysmsg")
                            self.watchdog_action_level = 1
                            self.last_watchdog_action_time = time.time()
                            self.vm_frozen_since = None
                            self.clear_commands()
                            threading.Thread(target=self._do_vm_maintenance, args=("revert", self.current_snapshot), daemon=True).start()
                        else:
                            self.log("[system]", "[error] vm still frozen! killing tasks...", "sysmsg")
                            self.watchdog_action_level = 2
                            self.last_watchdog_action_time = time.time()
                            self.vm_frozen_since = None
                            
                            vm_stop(vm_name, current_vm_backend, hard=True)
                            subprocess.Popen([vbox_manage_cmd, "startvm", vm_name, "--type", "gui"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            time.sleep(15)
                            set_obs_scene(_get_current_os_live_scene())
                            self.watchdog_action_level = 0
            else:
                if getattr(self, 'vm_frozen_since', None) is not None:
                    self.log("[system]", "vmware recovered.", "sysmsg")
                    self.vm_frozen_since = None
                    self.watchdog_action_level = 0
            if getattr(self, 'consecutive_failures', 0) >= 10 and (time.time() - getattr(self, 'last_success_time', time.time())) >= 20:
                time_since_last_api_action = time.time() - getattr(self, 'last_api_watchdog_action_time', 0)
                if time_since_last_api_action > 120: self.api_watchdog_level = 0
                if getattr(self, 'api_watchdog_level', 0) == 0:
                    self.log("[system]", "[error] vmrun unresponsive! auto-reverting...", "sysmsg")
                    self.api_watchdog_level = 1
                    self.last_api_watchdog_action_time = time.time()
                    self.last_success_time = time.time()
                    self.consecutive_failures = 0
                    self.clear_commands()
                    threading.Thread(target=self._do_vm_maintenance, args=("revert", self.current_snapshot), daemon=True).start()
                else:
                    self.log("[system]", f"[error] {current_vm_backend} api still dead! killing tasks...", "sysmsg")
                    self.api_watchdog_level = 2
                    self.last_api_watchdog_action_time = time.time()
                    self.last_success_time = time.time()
                    self.consecutive_failures = 0
                    
                    vm_stop(vm_name, current_vm_backend, hard=True)
                    
                    if self.config.get("enable_starting_scene", True): set_obs_scene(obs_scene_starting)
                    subprocess.Popen([vbox_manage_cmd, "startvm", vm_name, "--type", "gui"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(15)
                    set_obs_scene(_get_current_os_live_scene())
                    self.api_watchdog_level = 0
            time.sleep(1.0)

    def start_app_threads(self):
        try:
            curr = time.time()
            if not hasattr(self, 'listener_thread') or not self.listener_thread.is_alive() or curr - getattr(self, 'listener_tick', curr) > 120:
                self.listener_tick = curr
                self.listener_id = getattr(self, 'listener_id', 0) + 1
                self.listener_thread = threading.Thread(target=self.chat_listener_loop, args=(self.listener_id,), daemon=True)
                self.listener_thread.start()
            if not hasattr(self, 'executor_thread') or not self.executor_thread.is_alive() or curr - getattr(self, 'executor_tick', curr) > 120:
                self.executor_tick = curr
                self.executor_id = getattr(self, 'executor_id', 0) + 1
                self.executor_thread = threading.Thread(target=self.executor_loop, args=(self.executor_id,), daemon=True)
                self.executor_thread.start()
            if not hasattr(self, 'error_watcher_thread') or not self.error_watcher_thread.is_alive():
                self.error_watcher_thread = threading.Thread(target=self.error_watcher_loop, daemon=True)
                self.error_watcher_thread.start()
            if not hasattr(self, 'ocr_thread') or not self.ocr_thread.is_alive():
                self.ocr_thread = threading.Thread(target=self.ocr_watchdog_loop, daemon=True)
                self.ocr_thread.start()
            if flask_available and (not hasattr(self, 'flask_thread') or not self.flask_thread.is_alive()):
                console_log("INFO", "[flask] spawning web/overlay server thread...")
                self.flask_thread = threading.Thread(target=start_flask, daemon=True)
                self.flask_thread.start()
            if not hasattr(self, 'scheduler_thread') or not self.scheduler_thread.is_alive():
                self.scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
                self.scheduler_thread.start()
            if not hasattr(self, 'osvote_timeout_thread') or not self.osvote_timeout_thread.is_alive():
                self.osvote_timeout_thread = threading.Thread(target=os_vote_timeout_checker, daemon=True)
                self.osvote_timeout_thread.start()
        except Exception as e:
            console_log("ERROR", f"start threads crashed: {e}\n{traceback.format_exc()}")
            self.log("[system]", f"[error] start threads crashed: {e}", "err")

    def start_stats_thread(self):
        if hasattr(self, 'stats_thread') and self.stats_thread.is_alive(): return
        self.stats_thread = threading.Thread(target=self.stats_loop, daemon=True)
        self.stats_thread.start()

    def stats_loop(self):
        global current_viewers, current_likes
        while self.running:
            try: stats_interval = max(3, int(self.config.get("stats_interval", 5)))
            except: stats_interval = 5
            if self.active_url and "[DEBUG_MODE]" not in self.active_url:
                vid = self.resolve_live_video_id(self.active_url)
                if vid:
                    try:
                        req = urllib.request.Request(f"https://www.youtube.com/watch?v={vid}", headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                        with urllib.request.urlopen(req, timeout=5) as response: html = response.read().decode('utf-8')
                        v_match = re.search(r'"concurrentViewers":\s*\{\s*"simpleText":\s*"([^"]+)"', html)
                        if not v_match: v_match = re.search(r'"concurrentViewers"\s*:\s*\{\s*"simpleText"\s*:\s*"([\d,]+)"', html)
                        if not v_match: v_match = re.search(r'([\d,]+)\s*watching now', html, re.IGNORECASE)
                        if v_match:
                            num = ''.join(filter(str.isdigit, v_match.group(1)))
                            if num: current_viewers = num
                        l_match = re.search(r'"likeCount":\s*"(\d+)"', html)
                        if not l_match: l_match = re.search(r'"label":\s*"([\d,]+)\s+likes"', html)
                        if l_match:
                            num = ''.join(filter(str.isdigit, l_match.group(1)))
                            if num: current_likes = num
                    except Exception: pass
            if self.active_url == "[DEBUG_MODE]":
                 if random.random() < 0.1:
                      current_viewers = str(random.randint(100, 5000))
                      current_likes = str(random.randint(10, 500))
            save_stats()
            time.sleep(stats_interval)

if __name__ == "__main__":
    try:
        main_ui_root = tk.Tk()
        main_gui_application = ChatPlaysApp(main_ui_root)
        main_gui_application.show_welcome_guide()   # show user guide on first launch

        # Continuous auto-update watcher + file-edit hot-reload watchdog. Both run for
        # the lifetime of the process.
        threading.Thread(target=_autoupdate_watcher, daemon=True, name="autoupdate_watcher").start()
        threading.Thread(target=_file_edit_watchdog, daemon=True, name="file_edit_watchdog").start()
        start_tray_icon()

        # If this instance was launched by the auto-update/hot-reload relaunch pipeline
        # (--autostart-everything), self-start the bot from video_id.json with no one
        # at the keyboard.
        if _AUTOSTART_EVERYTHING:
            def _auto_start_everything():
                time.sleep(1.0)
                try:
                    vid_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "video_id.json")
                    with open(vid_path, "r", encoding="utf-8") as f:
                        saved_url = json.load(f).get("video_id", "")
                    if saved_url:
                        main_gui_application.entry_url.delete(0, "end")
                        main_gui_application.entry_url.insert(0, saved_url)
                        main_gui_application.go_live()
                        print(f"[AutoStart] Self-started bot on '{saved_url}' from video_id.json.")
                    else:
                        print("[AutoStart] video_id.json had no video_id -- start the bot manually.")
                except Exception as e:
                    print(f"[AutoStart] Could not self-start from video_id.json: {e}")
                if realpc_config.get("enabled"):
                    print("[AutoStart] NOTE: Real PC Control was enabled before this restart. "
                          "For safety it does NOT auto-resume -- go to the Real PC Control "
                          "tab and click Start to re-confirm and resume it.")
            threading.Thread(target=_auto_start_everything, daemon=True).start()

        main_ui_root.mainloop()
    except Exception as fatal_error:
        print("\n" + "="*60 + "\nscript crashed:\n" + "="*60)
        traceback.print_exc()
        print("="*60 + "\n")
        try:
            err_root = tk.Tk()
            err_root.withdraw()
            messagebox.showerror("error", f"crashed during startup.\n\nerror: {fatal_error}\n\ncheck black console for exact line.")
            err_root.destroy()
        except: pass
        input("press enter to exit...")
