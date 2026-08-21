"""
pyqt_gui.py -- PyQt6 front end for UltraBot.

Design: bot.py stays exactly what it always was (VM control, chat/command
handling, Music/Video engines, Flask server, Streamer.bot client) -- nothing in
it was rewritten for this. This file provides a new GUI, `UltraBotGUIQt`, that:

  1. Exposes the small Tkinter-shaped surface bot.py's backend calls directly
     on `_gui_app` (see pyqt_compat.py for why/how).
  2. Reuses three of the original Tkinter GUI class's methods completely
     unchanged -- `_run_bot`, `_stop_bot`, and `_vm_set_last` -- by binding them
     onto this class with `types.MethodType`. Those methods only ever touch
     `self.<simple attribute>`, never a raw Tkinter call, so this works safely.
     (Methods that call Tkinter's `messagebox` directly, like `_start_bot` and
     the `_vm_*` action methods, are re-implemented natively below with
     QMessageBox instead -- everything they call *into* is still the original
     backend function.)
  3. Builds every tab fresh with real Qt widgets and a modern dark theme.

STATUS: Main, VM Controls, Music, Video, Permissions, and Scheduler tabs are
fully wired to the backend below. The remaining backend configuration pages
are editable native Qt pages.
"""
import json
import math
import os
import random
import sys
import time
import types
import threading
import traceback

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt

try:
    from modules import bot
    _BOT_IMPORT_ERROR = None
except ImportError as exc:
    bot = None
    _BOT_IMPORT_ERROR = exc
from modules.pyqt_compat import TkAfterShim, TkTextShim, GetSetProxy

THEMES = {
    "Dark (Default)": {
        "BG": "#0f0f1a", "BG2": "#16162a", "BG3": "#1e1e35",
        "ACCENT": "#60cdff", "ACCENT2": "#8dd8ff",
        "GREEN": "#6cc88e", "RED": "#e6505f", "YELLOW": "#f0c060",
        "TEXT": "#e0e8ef", "TEXTDIM": "#7a8a96",
        "PANEL": "rgba(32,44,56,240)", "PANEL_BORDER": "rgba(255,255,255,18)",
        "TAB_BG": "rgba(16,24,34,140)", "TAB_BORDER": "rgba(255,255,255,8)",
        "BTN_BG": "#202c3c", "BTN_BORDER": "rgba(255,255,255,14)",
        "INPUT_BG": "#0c1218", "INPUT_BORDER": "rgba(255,255,255,12)",
        "SCROLLBAR_BG": "rgba(255,255,255,4)", "SCROLLBAR_HANDLE": "rgba(255,255,255,30)",
        "TITLEBAR_BG": "rgba(28,40,52,220)", "GRADIENT_STOPS": "stop:0 rgba(32,44,56,240),stop:0.5 rgba(20,32,44,242),stop:1 rgba(14,22,32,245)",
    },
    "Light": {
        "BG": "#f5f5f5", "BG2": "#e8e8e8", "BG3": "#dcdcdc",
        "ACCENT": "#0078d4", "ACCENT2": "#106ebe",
        "GREEN": "#107c10", "RED": "#d13438", "YELLOW": "#f7630c",
        "TEXT": "#1a1a1a", "TEXTDIM": "#616161",
        "PANEL": "rgba(255,255,255,240)", "PANEL_BORDER": "rgba(0,0,0,18)",
        "TAB_BG": "rgba(245,245,245,240)", "TAB_BORDER": "rgba(0,0,0,8)",
        "BTN_BG": "#e1e1e1", "BTN_BORDER": "rgba(0,0,0,14)",
        "INPUT_BG": "#ffffff", "INPUT_BORDER": "rgba(0,0,0,12)",
        "SCROLLBAR_BG": "rgba(0,0,0,4)", "SCROLLBAR_HANDLE": "rgba(0,0,0,30)",
        "TITLEBAR_BG": "rgba(240,240,240,220)", "GRADIENT_STOPS": "stop:0 rgba(250,250,250,240),stop:0.5 rgba(240,240,240,242),stop:1 rgba(230,230,230,245)",
    },
    "High Contrast 2026": {
        "BG": "#000000", "BG2": "#0a0a0a", "BG3": "#1a1a1a",
        "ACCENT": "#00ffff", "ACCENT2": "#80ffff",
        "GREEN": "#00ff00", "RED": "#ff0000", "YELLOW": "#ffff00",
        "TEXT": "#ffffff", "TEXTDIM": "#cccccc",
        "PANEL": "rgba(0,0,0,255)", "PANEL_BORDER": "rgba(0,255,255,120)",
        "TAB_BG": "rgba(10,10,10,255)", "TAB_BORDER": "rgba(0,255,255,80)",
        "BTN_BG": "#1a1a1a", "BTN_BORDER": "rgba(0,255,255,60)",
        "INPUT_BG": "#000000", "INPUT_BORDER": "rgba(0,255,255,80)",
        "SCROLLBAR_BG": "rgba(0,255,255,10)", "SCROLLBAR_HANDLE": "rgba(0,255,255,80)",
        "TITLEBAR_BG": "rgba(0,0,0,255)", "GRADIENT_STOPS": "stop:0 rgba(0,0,0,255),stop:0.5 rgba(10,10,10,255),stop:1 rgba(0,0,0,255)",
    },
    "Midnight Purple": {
        "BG": "#12091e", "BG2": "#1a1030", "BG3": "#241840",
        "ACCENT": "#a855f7", "ACCENT2": "#c084fc",
        "GREEN": "#4ade80", "RED": "#f87171", "YELLOW": "#fbbf24",
        "TEXT": "#ede9fe", "TEXTDIM": "#8b7faa",
        "PANEL": "rgba(26,16,48,240)", "PANEL_BORDER": "rgba(168,85,247,30)",
        "TAB_BG": "rgba(18,9,30,240)", "TAB_BORDER": "rgba(168,85,247,20)",
        "BTN_BG": "#241840", "BTN_BORDER": "rgba(168,85,247,25)",
        "INPUT_BG": "#0d0618", "INPUT_BORDER": "rgba(168,85,247,20)",
        "SCROLLBAR_BG": "rgba(168,85,247,8)", "SCROLLBAR_HANDLE": "rgba(168,85,247,50)",
        "TITLEBAR_BG": "rgba(26,16,48,220)", "GRADIENT_STOPS": "stop:0 rgba(26,16,48,240),stop:0.5 rgba(18,10,36,242),stop:1 rgba(12,6,24,245)",
    },
    "Ocean Blue": {
        "BG": "#0a1929", "BG2": "#0d2137", "BG3": "#132d46",
        "ACCENT": "#2196f3", "ACCENT2": "#64b5f6",
        "GREEN": "#66bb6a", "RED": "#ef5350", "YELLOW": "#ffa726",
        "TEXT": "#e3f2fd", "TEXTDIM": "#6a9ec0",
        "PANEL": "rgba(13,33,55,240)", "PANEL_BORDER": "rgba(33,150,243,30)",
        "TAB_BG": "rgba(10,25,41,240)", "TAB_BORDER": "rgba(33,150,243,20)",
        "BTN_BG": "#132d46", "BTN_BORDER": "rgba(33,150,243,25)",
        "INPUT_BG": "#061320", "INPUT_BORDER": "rgba(33,150,243,20)",
        "SCROLLBAR_BG": "rgba(33,150,243,8)", "SCROLLBAR_HANDLE": "rgba(33,150,243,50)",
        "TITLEBAR_BG": "rgba(13,33,55,220)", "GRADIENT_STOPS": "stop:0 rgba(13,33,55,240),stop:0.5 rgba(10,25,41,242),stop:1 rgba(8,20,33,245)",
    },
    "Red Alert": {
        "BG": "#1a0a0a", "BG2": "#2a1010", "BG3": "#3a1818",
        "ACCENT": "#f44336", "ACCENT2": "#e57373",
        "GREEN": "#66bb6a", "RED": "#ff1744", "YELLOW": "#ffc107",
        "TEXT": "#ffebee", "TEXTDIM": "#c07070",
        "PANEL": "rgba(42,16,16,240)", "PANEL_BORDER": "rgba(244,67,54,30)",
        "TAB_BG": "rgba(26,10,10,240)", "TAB_BORDER": "rgba(244,67,54,20)",
        "BTN_BG": "#3a1818", "BTN_BORDER": "rgba(244,67,54,25)",
        "INPUT_BG": "#120606", "INPUT_BORDER": "rgba(244,67,54,20)",
        "SCROLLBAR_BG": "rgba(244,67,54,8)", "SCROLLBAR_HANDLE": "rgba(244,67,54,50)",
        "TITLEBAR_BG": "rgba(42,16,16,220)", "GRADIENT_STOPS": "stop:0 rgba(42,16,16,240),stop:0.5 rgba(30,10,10,242),stop:1 rgba(20,6,6,245)",
    },
}

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
_THEME_FILE = os.path.join(_CONFIG_DIR, "gui_theme.json")

def _build_theme_stylesheet(name):
    t = THEMES.get(name, THEMES["Dark (Default)"])
    return f"""
*, *::before, *::after {{ font-family: 'Segoe UI Variable Display', 'Segoe UI', system-ui, sans-serif; }}
QMainWindow, QWidget {{ background: transparent; color: {t['TEXT']}; font-size: 14px; }}
QLabel {{ color: {t['TEXT']}; background: transparent; }}
#appFrame {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, {t['GRADIENT_STOPS']});
    border: 1px solid {t['PANEL_BORDER']};
    border-radius: 8px;
}}
#titleBar {{
    background: {t['TITLEBAR_BG']};
    border-bottom: 1px solid rgba(255,255,255,10);
    border-top-left-radius: 7px; border-top-right-radius: 7px;
}}
#titleBar QLabel {{ color: {t['TEXT']}; font-size: 12px; font-weight: 600; letter-spacing: 1px; }}
#windowButton {{
    background: transparent; border: none; border-radius: 4px; padding: 0;
    color: {t['TEXTDIM']}; font-size: 14px; font-weight: 400;
}}
#windowButton:hover {{ background: rgba(255,255,255,22); color: {t['TEXT']}; }}
#windowButton:pressed {{ background: rgba(255,255,255,12); }}
#windowCloseButton {{
    background: transparent; border: none; border-radius: 4px; padding: 0;
    color: {t['TEXTDIM']}; font-size: 14px; font-weight: 400;
}}
#windowCloseButton:hover {{ background: {t['RED']}; color: white; }}
#windowCloseButton:pressed {{ background: {t['RED']}; }}
QTabWidget, QTabWidget::pane {{ background: transparent; }}
QTabWidget::pane {{
    border: 1px solid {t['TAB_BORDER']};
    background: {t['TAB_BG']};
    border-radius: 6px;
}}
QTabBar::tab {{
    background: transparent; color: {t['TEXTDIM']}; padding: 8px 18px;
    border: none; border-bottom: 2px solid transparent;
    font-size: 12px; font-weight: 600;
}}
QTabBar::tab:selected {{
    color: {t['ACCENT']}; border-bottom: 2px solid {t['ACCENT']};
}}
QTabBar::tab:hover {{
    color: {t['TEXT']}; background: rgba(255,255,255,8);
}}
QGroupBox {{
    border: 1px solid {t['BTN_BORDER']};
    border-radius: 8px; margin-top: 12px; padding: 16px 12px 12px 12px;
    background: {t['PANEL']};
}}
QGroupBox::title {{
    subcontrol-origin: margin; left: 12px; padding: 0 6px;
    color: {t['ACCENT']}; font-size: 12px; font-weight: 700;
}}
QPushButton {{
    background: {t['BTN_BG']}; border: 1px solid {t['BTN_BORDER']};
    border-radius: 6px; padding: 6px 16px; color: {t['TEXT']};
    font-size: 13px; font-weight: 600;
}}
QPushButton:hover {{ background: rgba(255,255,255,18); border-color: rgba(255,255,255,30); }}
QPushButton:pressed {{ background: rgba(255,255,255,10); }}
QPushButton#green {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {t['GREEN']},stop:1 #4a9a6a);
    border-color: {t['GREEN']}; color: #ffffff;
}}
QPushButton#green:hover {{ background: {t['GREEN']}; }}
QPushButton#red {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {t['RED']},stop:1 #b33040);
    border-color: {t['RED']}; color: #ffffff;
}}
QPushButton#red:hover {{ background: {t['RED']}; }}
QPushButton#accent {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {t['ACCENT']},stop:1 #4a9dc8);
    border-color: {t['ACCENT']}; color: #ffffff;
}}
QPushButton#accent:hover {{ background: {t['ACCENT']}; }}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {{
    background: {t['INPUT_BG']}; border: 1px solid {t['INPUT_BORDER']};
    border-radius: 6px; padding: 6px 10px; color: {t['TEXT']};
    selection-background-color: {t['ACCENT']};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {t['ACCENT']};
}}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ image: none; border: none; }}
QComboBox QAbstractItemView {{
    background: {t['BG2']}; color: {t['TEXT']}; border: 1px solid {t['BTN_BORDER']};
    selection-background-color: {t['ACCENT']}; padding: 4px;
}}
QCheckBox {{
    spacing: 8px; color: {t['TEXT']};
}}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 4px;
    border: 2px solid {t['BTN_BORDER']}; background: {t['INPUT_BG']};
}}
QCheckBox::indicator:checked {{
    background: {t['ACCENT']}; border-color: {t['ACCENT']};
}}
QCheckBox::indicator:hover {{ border-color: {t['ACCENT']}; }}
QRadioButton {{
    spacing: 8px; color: {t['TEXT']};
}}
QRadioButton::indicator {{
    width: 16px; height: 16px; border-radius: 8px;
    border: 2px solid {t['BTN_BORDER']}; background: {t['INPUT_BG']};
}}
QRadioButton::indicator:checked {{
    background: {t['ACCENT']}; border-color: {t['ACCENT']};
}}
QScrollBar:vertical {{
    background: {t['SCROLLBAR_BG']}; width: 8px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {t['SCROLLBAR_HANDLE']}; border-radius: 4px; min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {t['SCROLLBAR_BG']}; height: 8px; margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {t['SCROLLBAR_HANDLE']}; border-radius: 4px; min-width: 30px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QSlider::groove:horizontal {{
    background: {t['BTN_BORDER']}; height: 4px; border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {t['ACCENT']}; width: 14px; height: 14px;
    margin: -5px 0; border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{ background: {t['ACCENT2']}; }}
QSplitter::handle {{ background: rgba(255,255,255,6); width: 2px; }}
QStatusBar {{
    background: {t['TITLEBAR_BG']}; color: {t['TEXTDIM']};
    border-top: 1px solid rgba(255,255,255,8);
    font-size: 12px;
}}
QProgressBar {{
    background: {t['INPUT_BG']}; border: 1px solid {t['INPUT_BORDER']};
    border-radius: 4px; height: 6px; text-align: center; color: transparent;
}}
QProgressBar::chunk {{
    background: {t['ACCENT']}; border-radius: 3px;
}}
QListWidget {{
    background: {t['INPUT_BG']}; border: 1px solid {t['INPUT_BORDER']};
    border-radius: 6px; color: {t['TEXT']}; padding: 4px;
}}
QListWidget::item:selected {{
    background: {t['ACCENT']}; color: #ffffff;
}}
QListWidget::item:hover {{
    background: rgba(255,255,255,8);
}}
"""

def _load_saved_theme():
    try:
        if os.path.exists(_THEME_FILE):
            with open(_THEME_FILE, "r") as f:
                data = json.load(f)
            return data.get("theme", "Dark (Default)")
    except Exception:
        pass
    return "Dark (Default)"

def _save_theme(name):
    try:
        os.makedirs(_CONFIG_DIR, exist_ok=True)
        with open(_THEME_FILE, "w") as f:
            json.dump({"theme": name}, f)
    except Exception:
        pass

def _detect_tpm_and_encryption(vmx_path):
    if not vmx_path or not os.path.isfile(vmx_path):
        return False, False
    try:
        with open(vmx_path, "r") as f:
            content = f.read()
        has_tpm = 'vpmc.0.present = "TRUE"' in content
        has_encryption = any(
            line.strip().lower().startswith("encryption.") and '= "true"' in line.lower()
            for line in content.splitlines()
        )
        return has_tpm, has_encryption
    except Exception:
        return False, False

def _validate_encryption_password(vmx_path, password):
    if not vmx_path or not password:
        return False
    try:
        import subprocess
        result = subprocess.run(
            ["vmrun", "-T", "ws", "-vp", password, "listSnapshots", vmx_path],
            capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False

PLACEHOLDER_TABS = [
    "OS Voting", "Appearance", "OBS", "Statistics", "User Management",
    "Event Log", "Sound / TTS", "Real PC Control",
    "Reconnect", "Soundboard", "VNC / Web", "Fun", "MrTristinAI",
    "Command Builder", "YT Relay", "Host Switch",
]

STYLE_SHEET = """
/* ── Windows 11 / WinUI 3 inspired dark theme ─────────────────────── */
*, *::before, *::after { font-family: 'Segoe UI Variable Display', 'Segoe UI', system-ui, sans-serif; }

QMainWindow, QWidget { background: transparent; color: #fafafa; font-size: 14px; }
QLabel { color: #e0e0e0; background: transparent; }

#appFrame {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(32, 44, 56, 240), stop:0.5 rgba(20, 32, 44, 242), stop:1 rgba(14, 22, 32, 245));
    border: 1px solid rgba(255,255,255,18);
    border-radius: 8px;
}

/* ── Title bar ──────────────────────────────────────────────────── */
#titleBar {
    background: rgba(28, 40, 52, 220);
    border-bottom: 1px solid rgba(255,255,255,10);
    border-top-left-radius: 7px;
    border-top-right-radius: 7px;
}
#titleBar QLabel { color: #c8d6e0; font-size: 12px; font-weight: 600; letter-spacing: 1px; }

#windowButton {
    background: transparent; border: none; border-radius: 4px; padding: 0;
    color: #b0bec5; font-size: 14px; font-weight: 400;
}
#windowButton:hover { background: rgba(255,255,255,22); color: #ffffff; }
#windowButton:pressed { background: rgba(255,255,255,12); }

#windowCloseButton {
    background: transparent; border: none; border-radius: 4px; padding: 0;
    color: #b0bec5; font-size: 14px; font-weight: 400;
}
#windowCloseButton:hover { background: #c42b1c; color: white; }
#windowCloseButton:pressed { background: #a51d12; }

/* ── Tabs (WinUI Pivot style) ──────────────────────────────────── */
QTabWidget, QTabWidget::pane { background: transparent; }
QTabWidget::pane {
    border: 1px solid rgba(255,255,255,8);
    background: rgba(16, 24, 34, 140);
    border-radius: 6px;
    top: -1px;
}
QTabBar::tab {
    background: rgba(255,255,255,5); color: #8e9eab; padding: 10px 18px;
    margin-right: 2px; border: none; border-bottom: 2px solid transparent;
    font-weight: 600; font-size: 13px;
}
QTabBar::tab:selected {
    background: rgba(255,255,255,8); color: #ffffff;
    border-bottom: 2px solid #60cdff;
}
QTabBar::tab:hover:!selected { color: #d0dce8; background: rgba(255,255,255,7); }

/* ── GroupBox ───────────────────────────────────────────────────── */
QGroupBox {
    border: 1px solid rgba(255,255,255,12); border-radius: 8px;
    margin-top: 16px; padding: 18px 14px 14px 14px;
    background: rgba(255,255,255,3); font-weight: 600; color: #b0c4d0;
}
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 8px; color: #7ec8e3; }

/* ── Buttons (WinUI 3 style with press animation) ──────────────── */
QPushButton {
    background: rgba(255,255,255,7); color: #e0e8ef;
    border: 1px solid rgba(255,255,255,12); border-radius: 6px;
    min-height: 36px; padding: 0 16px; font-weight: 600; font-size: 13px;
}
QPushButton:hover {
    background: rgba(255,255,255,12); border-color: rgba(255,255,255,20);
}
QPushButton:pressed {
    background: rgba(255,255,255,4); border-color: rgba(255,255,255,8);
    padding-top: 1px; padding-left: 1px;
}
QPushButton:disabled { color: #505a62; border-color: rgba(255,255,255,5); background: rgba(255,255,255,2); }
QPushButton:focus { outline: none; border: 1px solid #60cdff; }

QPushButton#green {
    background: rgba(108, 200, 142, 45); border-color: rgba(108, 200, 142, 80);
    color: #9ff5c0;
}
QPushButton#green:hover { background: rgba(108, 200, 142, 70); border-color: rgba(108, 200, 142, 120); }
QPushButton#green:pressed { background: rgba(108, 200, 142, 30); }

QPushButton#red {
    background: rgba(230, 80, 95, 45); border-color: rgba(230, 80, 95, 80);
    color: #ffb0b8;
}
QPushButton#red:hover { background: rgba(230, 80, 95, 70); border-color: rgba(230, 80, 95, 120); }
QPushButton#red:pressed { background: rgba(230, 80, 95, 30); }

QPushButton#accent {
    background: rgba(96, 205, 255, 35); border-color: rgba(96, 205, 255, 70);
    color: #b8e4ff;
}
QPushButton#accent:hover { background: rgba(96, 205, 255, 55); border-color: rgba(96, 205, 255, 110); }
QPushButton#accent:pressed { background: rgba(96, 205, 255, 20); }

/* ── Inputs ─────────────────────────────────────────────────────── */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTextEdit, QListWidget {
    background: rgba(0, 0, 0, 80); color: #e8eef3;
    border: 1px solid rgba(255,255,255,12); border-radius: 6px;
    min-height: 32px; padding: 5px 10px; selection-background-color: rgba(96, 205, 255, 100);
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
QPlainTextEdit:focus, QTextEdit:focus, QListWidget:focus {
    border: 1px solid rgba(96, 205, 255, 160);
}
QComboBox::drop-down { border: none; width: 24px; }
QListWidget::item:selected { background: rgba(96, 205, 255, 35); color: #ffffff; }
QListWidget::item:hover { background: rgba(255,255,255,5); }

/* ── CheckBox ───────────────────────────────────────────────────── */
QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 18px; height: 18px; border-radius: 4px;
    border: 1.5px solid rgba(255,255,255,30); background: rgba(0,0,0,60);
}
QCheckBox::indicator:checked {
    background: #0078d4; border-color: #0078d4;
}
QCheckBox::indicator:hover { border-color: rgba(96, 205, 255, 140); }

/* ── Labels ─────────────────────────────────────────────────────── */
QLabel#dim { color: #7a8a96; font-size: 12px; }
QLabel#h1 { color: #60cdff; font-size: 18px; font-weight: 700; }
QLabel#h2 { color: #e0e8ef; font-size: 13px; font-weight: 700; }

/* ── Scrollbar (WinUI thin style) ───────────────────────────────── */
QScrollBar:vertical {
    background: transparent; width: 10px; margin: 2px;
}
QScrollBar::handle:vertical {
    background: rgba(255,255,255,30); border-radius: 5px; min-height: 32px;
}
QScrollBar::handle:vertical:hover { background: rgba(255,255,255,50); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }

/* ── Slider ─────────────────────────────────────────────────────── */
QSlider::groove:horizontal {
    background: rgba(255,255,255,12); height: 4px; border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #60cdff; width: 16px; margin: -6px 0; border-radius: 8px;
}
QSlider::handle:horizontal:hover { background: #8dd8ff; }

/* ── Splitter ───────────────────────────────────────────────────── */
QSplitter::handle { background: rgba(255,255,255,10); width: 2px; }

/* ── Status bar ─────────────────────────────────────────────────── */
QStatusBar {
    background: rgba(0,0,0,100);
    border-top: 1px solid rgba(255,255,255,8);
    color: #7a8a96;
}

/* ── Editor ─────────────────────────────────────────────────────── */
QPlainTextEdit#configEditor { font-family: Consolas, monospace; font-size: 12px; border-radius: 8px; }

/* ── RadioButton (WinUI toggle) ─────────────────────────────────── */
QRadioButton::indicator {
    width: 18px; height: 18px; border-radius: 9px;
    border: 1.5px solid rgba(255,255,255,30); background: rgba(0,0,0,60);
}
QRadioButton::indicator:checked {
    background: #0078d4; border-color: #0078d4;
}
QRadioButton::indicator:hover { border-color: rgba(96, 205, 255, 140); }
"""


class _SplashParticle:
    __slots__ = ("x", "y", "r", "vx", "vy", "alpha", "color")
    def __init__(self, w, h, accent):
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        self.r = random.uniform(1, 4)
        self.vx = random.uniform(-0.3, 0.3)
        self.vy = random.uniform(-0.5, -0.1)
        self.alpha = random.uniform(40, 140)
        self.color = accent

class GlassSplashScreen(QtWidgets.QWidget):
    PHASES = [
        (0, "Initializing subsystems...", 5),
        (1500, "Loading backend modules...", 20),
        (3000, "Preparing the control room...", 40),
        (5000, "Building liquid-glass interface...", 60),
        (7000, "Configuring workspace...", 80),
        (8500, "Almost ready...", 95),
        (9500, "Ready", 100),
    ]

    def __init__(self):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.SplashScreen)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(520, 300)
        self.setWindowTitle("YouTubeChatUsesVM-Windows-VMware")
        self._elapsed = 0
        self._particles = []
        self._accent = "#60cdff"
        self._phase_idx = 0
        self._done = False
        self._on_done = None
        self._apply_round_mask()

        self._tick_timer = QtCore.QTimer(self)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(30)

        self._start_time = time.time()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(34, 28, 34, 28)
        panel = QtWidgets.QFrame()
        panel.setObjectName("splashPanel")
        panel.setStyleSheet(
            "#splashPanel { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #1c2c3c,stop:1 #0e1620); border: 1px solid rgba(96,205,255,40);"
            "border-radius: 14px; }")
        inner = QtWidgets.QVBoxLayout(panel)
        inner.setContentsMargins(32, 28, 32, 28)
        brand = QtWidgets.QLabel("ULTRABOT")
        brand.setStyleSheet("color:#60cdff; font-size:12px; font-weight:800; letter-spacing:3px;")
        title = QtWidgets.QLabel("Control Panel")
        title.setStyleSheet("color:#ffffff; font-size:28px; font-weight:700;")
        credit = QtWidgets.QLabel("Script by MrTristin, Nexovative, ReallyIron, and NickyTheKitty2")
        credit.setStyleSheet("color:#7a8a96; font-size:10px; font-weight:600;")
        credit.setWordWrap(True)
        self.status = QtWidgets.QLabel("Preparing the control room...")
        self.status.setObjectName("dim")
        self.status.setStyleSheet("color:#7a8a96; font-size:11px;")
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(5)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(
            "QProgressBar { background:#0a1018; border:0; border-radius:4px; height:6px; }"
            "QProgressBar::chunk { background:#60cdff; border-radius:4px; }")
        inner.addWidget(brand)
        inner.addWidget(title)
        inner.addWidget(credit)
        inner.addSpacing(14)
        inner.addWidget(self.status)
        inner.addSpacing(4)
        inner.addWidget(self.progress)
        layout.addWidget(panel)

        for _ in range(24):
            self._particles.append(_SplashParticle(520, 300, self._accent))

    def _apply_round_mask(self):
        painter_path = QtGui.QPainterPath()
        painter_path.addRoundedRect(QtCore.QRectF(self.rect()), 16, 16)
        self.setMask(QtGui.QRegion(painter_path.toFillPolygon().toPolygon()))

    def set_on_done(self, callback):
        self._on_done = callback

    def _tick(self):
        self._elapsed = int((time.time() - self._start_time) * 1000)
        for p in self._particles:
            p.x += p.vx
            p.y += p.vy
            if p.y < -10:
                p.y = 310
                p.x = random.uniform(0, 520)
            if p.x < -10 or p.x > 530:
                p.x = random.uniform(0, 520)
        while self._phase_idx < len(self.PHASES) and self._elapsed >= self.PHASES[self._phase_idx][0]:
            _, text, val = self.PHASES[self._phase_idx]
            self.status.setText(text)
            self.progress.setValue(val)
            self._phase_idx += 1
        if self._elapsed >= 10000 and not self._done:
            self._done = True
            self._tick_timer.stop()
            if self._on_done:
                self._on_done()
        self.update()

    def paintEvent(self, event):
        try:
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            for pt in self._particles:
                color = QtGui.QColor(pt.color)
                color.setAlpha(int(pt.alpha * (0.5 + 0.5 * math.sin(self._elapsed / 800 + pt.x))))
                p.setBrush(color)
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QtCore.QPointF(pt.x, pt.y), pt.r, pt.r)
            p.end()
        except Exception:
            pass

    def update_status(self, text, value):
        self.status.setText(text)
        self.progress.setValue(value)
        QtWidgets.QApplication.processEvents()


class CheckBox(QtWidgets.QCheckBox):
    """Windows-style checkbox with an explicit visible checkmark."""
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        try:
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            box = QtCore.QRect(1, max(1, (self.height() - 18) // 2), 18, 18)
            painter.setPen(QtGui.QPen(QtGui.QColor("#86d8cc"), 1.5))
            painter.setBrush(QtGui.QColor("#18303a"))
            painter.drawRoundedRect(box, 4, 4)
            if self.isChecked():
                painter.setPen(QtGui.QPen(QtGui.QColor("#b9fff2"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                painter.drawLine(5, box.center().y(), 8, box.bottom() - 4)
                painter.drawLine(8, box.bottom() - 4, 15, box.top() + 4)
            painter.setPen(QtGui.QColor("#f2f6fa"))
            painter.setFont(self.font())
            painter.drawText(28, 0, self.width() - 28, self.height(), Qt.AlignmentFlag.AlignVCenter, self.text())
        except Exception:
            pass
        finally:
            painter.end()

    def sizeHint(self):
        size = super().sizeHint()
        size.setWidth(size.width() + 4)
        return size


class BackendConfigTab(QtWidgets.QWidget):
    """Visual editor for scalar and list settings shared by the backend."""
    def __init__(self, name, config_names, parent=None):
        super().__init__(parent)
        self.name = name
        self.config_names = config_names
        self._bindings = []
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        heading = QtWidgets.QLabel(name)
        heading.setObjectName("h1")
        layout.addWidget(heading)
        note = QtWidgets.QLabel("Settings are shown as controls and saved to the bot automatically.")
        note.setObjectName("dim")
        layout.addWidget(note)
        self.form_scroll = QtWidgets.QScrollArea()
        self.form_scroll.setWidgetResizable(True)
        self.form_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.form_host = QtWidgets.QWidget()
        self.form = QtWidgets.QFormLayout(self.form_host)
        self.form.setContentsMargins(8, 8, 8, 8)
        self.form.setVerticalSpacing(10)
        self.form_scroll.setWidget(self.form_host)
        layout.addWidget(self.form_scroll, 1)
        buttons = QtWidgets.QHBoxLayout()
        load = QtWidgets.QPushButton("Reload")
        save = QtWidgets.QPushButton("Save Changes")
        save.setObjectName("green")
        load.clicked.connect(self.load_config)
        save.clicked.connect(self.save_config)
        buttons.addWidget(load)
        buttons.addWidget(save)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        self.load_config()

    def _clear_form(self):
        while self.form.count():
            item = self.form.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._bindings.clear()

    def _add_dict(self, prefix, values):
        for key, value in values.items():
            if key in {"video_id", "video_ids"}:
                continue
            path = prefix + (key,)
            label = str(key).replace("_", " ").title()
            if isinstance(value, dict):
                group = QtWidgets.QGroupBox(label)
                group_form = QtWidgets.QFormLayout(group)
                group_form.setVerticalSpacing(8)
                self._add_nested(group_form, path, value)
                self.form.addRow(group)
            else:
                widget = self._make_widget(path, value)
                if widget is not None:
                    self.form.addRow(label, widget)

    def _add_nested(self, form, prefix, values):
        for key, value in values.items():
            if key in {"video_id", "video_ids"}:
                continue
            path = prefix + (key,)
            label = str(key).replace("_", " ").title()
            if isinstance(value, dict):
                group = QtWidgets.QGroupBox(label)
                nested = QtWidgets.QFormLayout(group)
                self._add_nested(nested, path, value)
                form.addRow(group)
            else:
                widget = self._make_widget(path, value)
                if widget is not None:
                    form.addRow(label, widget)

    def _make_widget(self, path, value):
        if isinstance(value, bool):
            widget = CheckBox()
            widget.setChecked(value)
            kind = "bool"
        elif isinstance(value, int) and not isinstance(value, bool):
            widget = QtWidgets.QSpinBox()
            widget.setRange(-1000000000, 1000000000)
            widget.setValue(value)
            kind = "int"
        elif isinstance(value, float):
            widget = QtWidgets.QDoubleSpinBox()
            widget.setRange(-1000000000.0, 1000000000.0)
            widget.setDecimals(3)
            widget.setValue(value)
            kind = "float"
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
            widget = QtWidgets.QLineEdit(", ".join(value))
            widget.setPlaceholderText("Separate entries with commas")
            kind = "str_list"
        elif isinstance(value, str):
            widget = QtWidgets.QLineEdit(value)
            key_lower = str(path[-1]).lower() if path else ""
            if any(s in key_lower for s in ("password", "secret", "token", "auth_code", "api_key")):
                widget.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
            kind = "str"
        else:
            return None
        self._bindings.append((path, widget, kind))
        return widget

    @staticmethod
    def _read_widget(widget, kind):
        if kind == "bool":
            return widget.isChecked()
        if kind == "int":
            return widget.value()
        if kind == "float":
            return widget.value()
        if kind == "str_list":
            return [item.strip() for item in widget.text().split(",") if item.strip()]
        return widget.text()

    @staticmethod
    def _write_path(target, path, value):
        current = target
        for key in path[:-1]:
            current = current[key]
        current[path[-1]] = value

    def load_config(self):
        self._clear_form()
        for name in self.config_names:
            value = getattr(bot, name, None)
            if isinstance(value, dict):
                self._add_dict((name,), value)
            else:
                label = QtWidgets.QLabel(f"{name} is not a dictionary-backed setting.")
                label.setObjectName("dim")
                self.form.addRow(label)

    def save_config(self):
        try:
            savers = {
                "custom_commands": "save_custom_commands",
                "soundboard_config": "save_soundboard_config",
                "fun_high_scores": "save_fun_high_scores",
                "gemini_config": "save_gemini_config",
                "REALPC_CONFIG": "save_realpc_config",
                "RECONNECT_CONFIG": "save_reconnect_config",
                "SOUND_CONFIG": "save_sound_config",
                "MULTI_STREAM_CONFIG": "save_multi_stream_config",
                "SCHEDULER_CONFIG": "save_scheduler_config",
                "OBS_CONFIG": "save_obs_config",
                "VNC_CONFIG": "save_vnc_config",
                "FLASK_CONFIG": "save_flask_config",
                "PERMISSIONS_CONFIG": "save_permissions_config",
                "HOST_SWITCH_CONFIG": "save_host_switch_config",
                "YT_LOG_RELAY_CONFIG": "save_yt_log_relay_config",
                "INTERNET_CONFIG": "save_internet_config",
            }
            reloads = {
                "VNC_CONFIG": "load_vnc_config",
                "OBS_CONFIG": "load_obs_config",
                "SOUND_CONFIG": "load_sound_config",
                "RECONNECT_CONFIG": "load_reconnect_config",
                "REALPC_CONFIG": "load_realpc_config",
                "HOST_SWITCH_CONFIG": "load_host_switch_config",
                "YT_LOG_RELAY_CONFIG": "load_yt_log_relay_config",
                "MULTI_STREAM_CONFIG": "load_multi_stream_config",
            }
            touched = set()
            for path, widget, kind in self._bindings:
                name = path[0]
                target = getattr(bot, name, None)
                if isinstance(target, dict):
                    self._write_path(target, path[1:], self._read_widget(widget, kind))
                    touched.add(name)
            for name in touched:
                saver = getattr(bot, savers.get(name, ""), None)
                if callable(saver):
                    saver()
                reload_fn = getattr(bot, reloads.get(name, ""), None)
                if callable(reload_fn):
                    reload_fn()
            QtWidgets.QMessageBox.information(self, "Saved", f"{self.name} settings saved.")
            if self.parent() is not None and hasattr(self.parent(), "_set_feedback"):
                self.parent()._set_feedback(f"{self.name} settings saved")
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Invalid settings", str(exc))


class FeatureTab(QtWidgets.QWidget):
    """Native controls for backend state that is not stored in one dictionary."""
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(20, 18, 20, 18)
        title = QtWidgets.QLabel(name)
        title.setObjectName("h1")
        self.layout.addWidget(title)
        self._build()
        self.layout.addStretch(1)

    def _build(self):
        if self.name == "Statistics":
            self.stats = QtWidgets.QLabel()
            self.stats.setWordWrap(True)
            self.layout.addWidget(self.stats)
            refresh = QtWidgets.QPushButton("Refresh Statistics")
            reset = QtWidgets.QPushButton("Reset Session")
            reset.setObjectName("red")
            refresh.clicked.connect(self.refresh_stats)
            reset.clicked.connect(self.reset_stats)
            self.layout.addWidget(refresh, alignment=Qt.AlignmentFlag.AlignLeft)
            self.layout.addWidget(reset, alignment=Qt.AlignmentFlag.AlignLeft)
            self.refresh_stats()
        elif self.name == "Event Log":
            self.events = QtWidgets.QListWidget()
            self.layout.addWidget(self.events, 1)
            refresh = QtWidgets.QPushButton("Refresh Event Log")
            refresh.clicked.connect(self.refresh_events)
            self.layout.addWidget(refresh, alignment=Qt.AlignmentFlag.AlignLeft)
            self.refresh_events()
        elif self.name == "Appearance":
            form = QtWidgets.QFormLayout()
            self.font_size = QtWidgets.QSpinBox()
            self.font_size.setRange(8, 24)
            self.font_size.setValue(int(getattr(bot.UltraBotGUI, "_FONT_SIZE", 10)))
            form.addRow("Font size", self.font_size)
            self.colors = {}
            for key in ("BG", "BG2", "BG3", "ACCENT", "ACCENT2", "TEXT", "TEXTDIM", "CONSOLE", "BORDER"):
                edit = QtWidgets.QLineEdit(str(getattr(bot.UltraBotGUI, key, "")))
                self.colors[key] = edit
                form.addRow(key, edit)
            self.layout.addLayout(form)
            save = QtWidgets.QPushButton("Save Appearance")
            save.setObjectName("green")
            save.clicked.connect(self.save_appearance)
            self.layout.addWidget(save, alignment=Qt.AlignmentFlag.AlignLeft)
        elif self.name == "OS Voting":
            self.enabled = CheckBox("Enable OS voting")
            self.enabled.setChecked(bool(getattr(bot, "OS_VOTING_ENABLED", False)))
            self.layout.addWidget(self.enabled)
            form = QtWidgets.QFormLayout()
            self.required = QtWidgets.QSpinBox()
            self.required.setRange(1, 99)
            self.required.setValue(int(getattr(bot, "OS_VOTE_REQUIRED", 3)))
            form.addRow("Votes required", self.required)
            self.layout.addLayout(form)
            save = QtWidgets.QPushButton("Save OS Voting")
            save.setObjectName("green")
            save.clicked.connect(self.save_os_voting)
            self.layout.addWidget(save, alignment=Qt.AlignmentFlag.AlignLeft)
            self.layout.addWidget(QtWidgets.QLabel("Detailed OS rows can be added from the original configuration file or the Tk interface."))
        elif self.name == "User Management":
            self.whitelist = QtWidgets.QLineEdit(", ".join(sorted(getattr(bot, "whitelist_users", set()))))
            self.whitelist.setPlaceholderText("Comma-separated allowed usernames")
            self.layout.addWidget(QtWidgets.QLabel("Whitelist users"))
            self.layout.addWidget(self.whitelist)
            save = QtWidgets.QPushButton("Save User Management")
            save.setObjectName("green")
            save.clicked.connect(self.save_users)
            self.layout.addWidget(save, alignment=Qt.AlignmentFlag.AlignLeft)
        elif self.name == "Command Builder":
            self.command_list = QtWidgets.QListWidget()
            self.command_list.addItems(sorted(getattr(bot, "custom_commands", {}).keys()))
            self.layout.addWidget(self.command_list, 1)
            row = QtWidgets.QHBoxLayout()
            self.command_name = QtWidgets.QLineEdit()
            self.command_name.setPlaceholderText("!command")
            add = QtWidgets.QPushButton("Add Command")
            remove = QtWidgets.QPushButton("Remove Selected")
            remove.setObjectName("red")
            row.addWidget(self.command_name, 1)
            row.addWidget(add)
            row.addWidget(remove)
            self.layout.addLayout(row)
            add.clicked.connect(self.add_command)
            remove.clicked.connect(self.remove_command)
        else:
            label = QtWidgets.QLabel(f"{self.name} is ready for native controls.")
            label.setObjectName("dim")
            self.layout.addWidget(label)

    def refresh_stats(self):
        stats = getattr(bot, "_stats", {})
        self.stats.setText("\n".join(f"{key.replace('_', ' ').title()}: {value}" for key, value in stats.items()))

    def reset_stats(self):
        bot._reset_session_stats()
        self.refresh_stats()

    def refresh_events(self):
        self.events.clear()
        for event in getattr(bot, "_event_log", [])[-500:]:
            self.events.addItem(f"{event.get('ts', '')}  {event.get('type', '')}  {event.get('user', '')}  {event.get('detail', '')}")

    def save_appearance(self):
        colors = {key: edit.text().strip() for key, edit in self.colors.items()}
        for key, value in colors.items():
            setattr(bot.UltraBotGUI, key, value)
        bot.UltraBotGUI._FONT_SIZE = self.font_size.value()
        bot.save_appearance_config(colors, self.font_size.value())
        self._feedback("Appearance saved")

    def save_os_voting(self):
        bot.OS_VOTING_ENABLED = self.enabled.isChecked()
        bot.OS_VOTE_REQUIRED = self.required.value()
        bot.save_os_voting_config()
        self._feedback("OS voting settings saved")

    def save_users(self):
        bot.whitelist_users = {item.strip().lower().lstrip("@") for item in self.whitelist.text().split(",") if item.strip()}
        bot.save_user_mgmt()
        self._feedback("User management saved")

    def add_command(self):
        name = self.command_name.text().strip()
        if not name:
            return
        if not name.startswith("!"):
            name = "!" + name
        bot.custom_commands.setdefault(name, [])
        bot.save_custom_commands()
        self.command_list.addItem(name)
        self.command_name.clear()
        self._feedback("Command added")

    def remove_command(self):
        item = self.command_list.currentItem()
        if item is not None:
            bot.custom_commands.pop(item.text(), None)
            bot.save_custom_commands()
            self.command_list.takeItem(self.command_list.row(item))
            self._feedback("Command removed")

    def _feedback(self, text):
        if self.parent() is not None and hasattr(self.parent(), "_set_feedback"):
            self.parent()._set_feedback(text)


class ObsTab(QtWidgets.QWidget):
    """Native equivalent of the Tk OBS tab, including add/remove trigger rows."""
    EVENTS = ("bot_start", "bot_stop", "restart", "restart_done", "revert_start",
              "revert_done", "os_switch", "ban", "scheduler", "vm_starting",
              "start_done", "vm_shutdown", "error_occurred_with_script")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        title = QtWidgets.QLabel("OBS WebSocket Integration")
        title.setObjectName("h1")
        layout.addWidget(title)
        intro = QtWidgets.QLabel("Connect to OBS 28+ and map bot events to scenes. Add or remove rows as needed.")
        intro.setObjectName("dim")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        connection = QtWidgets.QGroupBox("Connection")
        form = QtWidgets.QFormLayout(connection)
        self.enabled = CheckBox("Enable OBS integration")
        self.enabled.setChecked(bool(bot.OBS_CONFIG.get("enabled", False)))
        form.addRow(self.enabled)
        self.host = QtWidgets.QLineEdit(str(bot.OBS_CONFIG.get("host", "localhost")))
        self.port = QtWidgets.QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(int(bot.OBS_CONFIG.get("port", 4455)))
        self.password = QtWidgets.QLineEdit(str(bot.OBS_CONFIG.get("password", "")))
        self.password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        form.addRow("Host", self.host)
        form.addRow("Port", self.port)
        form.addRow("Password", self.password)
        buttons = QtWidgets.QHBoxLayout()
        connect = QtWidgets.QPushButton("Connect")
        connect.setObjectName("green")
        disconnect = QtWidgets.QPushButton("Disconnect")
        disconnect.setObjectName("red")
        connect.clicked.connect(self.connect_obs)
        disconnect.clicked.connect(bot.obs_disconnect)
        buttons.addWidget(connect)
        buttons.addWidget(disconnect)
        buttons.addStretch(1)
        form.addRow(buttons)
        layout.addWidget(connection)

        trigger_box = QtWidgets.QGroupBox("Scene Triggers")
        trigger_layout = QtWidgets.QVBoxLayout(trigger_box)
        self.trigger_host = QtWidgets.QWidget()
        self.trigger_form = QtWidgets.QFormLayout(self.trigger_host)
        self.trigger_form.setVerticalSpacing(6)
        trigger_layout.addWidget(self.trigger_host)
        add = QtWidgets.QPushButton("+ Add Trigger")
        add.setObjectName("green")
        add.clicked.connect(lambda: self.add_trigger_row())
        trigger_layout.addWidget(add, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(trigger_box, 1)

        save = QtWidgets.QPushButton("Save OBS Settings")
        save.setObjectName("green")
        save.clicked.connect(self.save_obs)
        layout.addWidget(save, alignment=Qt.AlignmentFlag.AlignLeft)
        saved = bot.OBS_CONFIG.get("triggers", {}) or {}
        for event, scene in saved.items():
            self.add_trigger_row(event, scene)
        if not self.rows:
            for event in self.EVENTS[:6]:
                self.add_trigger_row(event, "")

    def add_trigger_row(self, event="", scene=""):
        row = QtWidgets.QWidget()
        row_layout = QtWidgets.QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        event_edit = QtWidgets.QComboBox()
        event_edit.setEditable(True)
        event_edit.addItems(self.EVENTS)
        event_edit.setCurrentText(event)
        scene_edit = QtWidgets.QLineEdit(scene)
        scene_edit.setPlaceholderText("OBS scene name")
        remove = QtWidgets.QPushButton("Remove")
        remove.setObjectName("red")
        row_layout.addWidget(event_edit, 1)
        row_layout.addWidget(scene_edit, 2)
        row_layout.addWidget(remove)
        self.trigger_form.addRow("Event", row)
        entry = (row, event_edit, scene_edit)
        self.rows.append(entry)
        remove.clicked.connect(lambda: self.remove_trigger_row(entry))

    def remove_trigger_row(self, entry):
        if entry in self.rows:
            self.rows.remove(entry)
        entry[0].deleteLater()

    def connect_obs(self):
        bot.OBS_CONFIG.update({"host": self.host.text().strip(), "port": self.port.value(),
                               "password": self.password.text(), "enabled": self.enabled.isChecked()})
        bot.obs_connect()

    def save_obs(self):
        triggers = {}
        for _, event_edit, scene_edit in self.rows:
            event = event_edit.currentText().strip().lstrip("!")
            scene = scene_edit.text().strip()
            if event:
                triggers[event] = scene
        bot.OBS_CONFIG.update({"enabled": self.enabled.isChecked(), "host": self.host.text().strip(),
                               "port": self.port.value(), "password": self.password.text(),
                               "triggers": triggers})
        bot.save_obs_config()
        self.parent()._set_feedback("OBS settings saved")


class VideoRenderSurface(QtWidgets.QWidget):
    """Qt surface exposing the Tk-shaped native handle expected by VLC."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors, False)
        self.setStyleSheet("background: black;")

    def winfo_id(self):
        return int(self.winId())


class VideoPanelWindow(QtWidgets.QWidget):
    """The movable window video clips render into. Title is intentionally CONSTANT
    ("Video Panel") no matter what's playing -- OBS Window Capture identifies a
    window by its title string, so a changing title silently breaks the capture.
    (Same fix as the Tkinter version -- see set_video_window_title() below.)"""

    closed = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__(None, Qt.WindowType.Window)
        self.setWindowTitle("Video Panel")
        self.setStyleSheet("background: black;")
        self.resize(640, 360)
        self.setMinimumSize(160, 90)
        self._destroyed = False
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.canvas = VideoRenderSurface(self)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

    # -- Tkinter-shaped compatibility surface --
    def winfo_exists(self):
        return not self._destroyed

    def title(self):
        return self.windowTitle()

    def winfo_x(self): return self.x()
    def winfo_y(self): return self.y()
    def winfo_width(self): return self.width()
    def winfo_height(self): return self.height()

    def destroy(self):
        self._destroyed = True
        self.close()

    def closeEvent(self, event):
        self._destroyed = True
        self.closed.emit()
        super().closeEvent(event)


class UltraBotGUIQt(QtWidgets.QMainWindow):
    # Same palette as the original app, applied through a proper Qt stylesheet
    # instead of hundreds of individual widget color= kwargs.
    BG, BG2, BG3 = "#0f0f1a", "#16162a", "#1e1e35"
    ACCENT, ACCENT2 = "#60cdff", "#8dd8ff"
    GREEN, RED, YELLOW = "#6cc88e", "#e6505f", "#f0c060"
    TEXT, TEXTDIM = "#e0e8ef", "#7a8a96"
    SHIELD_BLUE = "#60cdff"

    def __init__(self, auto_start=False):
        super().__init__()
        self.setWindowTitle("UltraBot Control Panel")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._current_theme = _load_saved_theme()
        self.setStyleSheet(_build_theme_stylesheet(self._current_theme))
        t = THEMES.get(self._current_theme, THEMES["Dark (Default)"])
        self.BG, self.BG2, self.BG3 = t["BG"], t["BG2"], t["BG3"]
        self.ACCENT, self.ACCENT2 = t["ACCENT"], t["ACCENT2"]
        self.GREEN, self.RED, self.YELLOW = t["GREEN"], t["RED"], t["YELLOW"]
        self.TEXT, self.TEXTDIM = t["TEXT"], t["TEXTDIM"]
        self.SHIELD_BLUE = t["ACCENT"]
        self.resize(1440, 900)
        self.setMinimumSize(1000, 640)

        # -- Tkinter-compatibility surface the backend calls directly --
        self.root = self  # `_gui_app.root.after(...)` -> this object's .after()
        self._after_shim = TkAfterShim()

        self._bot_thread = None
        self._bot_running = False
        self._bot_instance = None
        self._console_redir = None
        self.video_toplevel = None
        self.video_canvas = None
        self._drag_pos = None
        self._auto_start = auto_start
        self._tray_icon = None
        self._vm_encryption_password = ""

        # Load all saved configs before building UI so widgets read correct values
        self._load_all_configs()

        self._bind_reused_backend_methods()
        self._build_ui()
        self._wrap_save_functions_for_dirty_tracking()
        self._wire_button_feedback()
        self._setup_qt_tray()

        bot._gui_app = self
        bot._gui_root = self

    # ============================= Tk-shaped API =============================
    def after(self, ms, func, *args, **kwargs):
        return self._after_shim.after(ms, func, *args, **kwargs)

    def after_cancel(self, job_id):
        self._after_shim.after_cancel(job_id)

    def deiconify(self):
        self.showNormal()
        self.show()

    def lift(self):
        self.raise_()
        self.activateWindow()

    def destroy(self):
        self.close()

    # ============================= Setup =============================
    def _load_all_configs(self):
        """Load every saved config from disk into the bot module globals,
        mirroring what the Tkinter GUI does in its __init__."""
        _loads = [
            "load_appearance_config", "load_os_voting_config",
            "load_auto_start_config", "load_gemini_config",
            "load_obs_config", "load_permissions_config",
            "load_sound_config", "load_multi_stream_config",
            "load_scheduler_config", "load_music_config",
            "load_video_config", "load_soundboard_config",
            "load_fun_high_scores", "load_mrtristinai_config",
            "load_custom_commands", "load_streamerbot_config",
            "load_vnc_config", "load_reconnect_config",
            "load_realpc_config", "load_flask_config",
            "load_host_switch_config", "load_current_vm",
            "load_event_log", "load_yt_log_relay_config",
            "load_user_mgmt", "load_autostart_everything_config",
            "load_internet_config",
        ]
        for name in _loads:
            func = getattr(bot, name, None)
            if func:
                try:
                    func()
                except Exception:
                    pass

    def _bind_reused_backend_methods(self):
        """Reuse these three methods from the original Tkinter GUI class verbatim --
        they never touch a raw Tkinter call, only `self.<attr>`, all of which this
        class also provides. This keeps the Streamer.bot protocol/command-dispatch
        logic (incl. the moderator-detection fix) and VM-action-label logic
        byte-for-byte identical between the two front ends."""
        self._run_bot = types.MethodType(bot.UltraBotGUI._run_bot, self)
        self._stop_bot = types.MethodType(bot.UltraBotGUI._stop_bot, self)
        # NOTE: _vm_set_last is NOT bound from Tkinter og.py because it calls
        # .configure() which is Tkinter-only. A native Qt version is defined below.

    def _wrap_save_functions_for_dirty_tracking(self):
        """Mirrors the original GUI's autosave-dirty-tracking: wrap every save_*
        function in the bot module so calling it also flips a dirty flag. Not
        currently displayed anywhere in this phase, but kept so future tabs (e.g.
        an unsaved-changes indicator) can use it without backend changes."""
        self._config_dirty = False
        save_fn_names = [n for n in dir(bot) if n.startswith("save_")]
        for name in save_fn_names:
            orig = getattr(bot, name, None)
            if not callable(orig):
                continue
            def _make_wrapper(_f):
                def _wrapper(*a, **kw):
                    try:
                        return _f(*a, **kw)
                    finally:
                        self._config_dirty = True
                return _wrapper
            try:
                setattr(bot, name, _make_wrapper(orig))
            except Exception:
                pass

    def _build_ui(self):
        central = QtWidgets.QWidget()
        central.setObjectName("appFrame")
        self.setCentralWidget(central)
        outer = QtWidgets.QVBoxLayout(central)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.setSpacing(8)

        title_bar = QtWidgets.QFrame()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(40)
        title_layout = QtWidgets.QHBoxLayout(title_bar)
        title_layout.setContentsMargins(14, 0, 6, 0)
        title_layout.addWidget(QtWidgets.QLabel("ULTRABOT  —  CONTROL PANEL"))
        title_layout.addStretch(1)
        minimize = QtWidgets.QPushButton("\u2012")
        minimize.setObjectName("windowButton")
        minimize.setToolTip("Minimize")
        minimize.clicked.connect(self.showMinimized)
        maximize = QtWidgets.QPushButton("\u25a1")
        maximize.setObjectName("windowButton")
        maximize.setToolTip("Maximize or restore")
        maximize.clicked.connect(self._toggle_maximized)
        close = QtWidgets.QPushButton("\u2715")
        close.setObjectName("windowCloseButton")
        close.setToolTip("Close")
        close.clicked.connect(self.close)
        for button in (minimize, maximize, close):
            button.setFixedSize(36, 28)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            title_layout.addWidget(button)
        title_bar.mousePressEvent = self._title_mouse_press
        title_bar.mouseMoveEvent = self._title_mouse_move
        outer.addWidget(title_bar)

        splitter = QtWidgets.QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(splitter, 1)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setUsesScrollButtons(True)
        self.tabs.tabBar().setExpanding(False)
        splitter.addWidget(self.tabs)

        self._build_main_tab()
        self._build_vm_tab()
        self._build_music_tab()
        self._build_video_tab()
        self._build_permissions_tab()
        self._build_scheduler_tab()
        self._build_settings_tab()
        for name in PLACEHOLDER_TABS:
            self._build_backend_tab(name)

        # Live Chat is a persistent side panel, not a tab -- you shouldn't have to
        # leave whatever you're doing to see what's happening in chat.
        splitter.addWidget(self._build_chat_panel())
        splitter.setSizes([1000, 420])

        # Status bar: bot running/stopped indicator, always visible.
        sb = QtWidgets.QStatusBar()
        self.setStatusBar(sb)
        self._status_dot = QtWidgets.QLabel("⬤  Stopped")
        self._status_dot.setStyleSheet(f"color: {self.RED}; font-weight: 700; padding: 2px 8px;")
        sb.addPermanentWidget(self._status_dot)
        self._feedback_label = QtWidgets.QLabel("Ready")
        self._feedback_label.setObjectName("dim")
        sb.addWidget(self._feedback_label)

        if self._auto_start:
            QtCore.QTimer.singleShot(600, self._auto_start_bot)

    def _wire_button_feedback(self):
        for button in self.findChildren(QtWidgets.QPushButton):
            if button.property("feedback_wired"):
                continue
            button.setProperty("feedback_wired", True)
            button.clicked.connect(lambda checked=False, b=button: self._button_feedback(b))

    def _button_feedback(self, button):
        text = button.text().replace("\n", " ").strip()
        lowered = text.lower()
        if any(word in lowered for word in ("save", "add", "remove", "connect", "start", "stop", "resume", "pause", "suspend", "test")):
            self._set_feedback(f"{text or 'Action'} selected")

    def _set_feedback(self, text, success=True):
        if not hasattr(self, "_feedback_label"):
            return
        self._feedback_label.setText(text)
        self._feedback_label.setStyleSheet(
            f"color: {self.GREEN if success else self.RED}; font-weight: 700; padding: 2px 8px;"
        )
        QtCore.QTimer.singleShot(3500, lambda: self._feedback_label.setText("Ready"))

    def _toggle_maximized(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _title_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def _title_mouse_move(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton and not self.isMaximized():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def resizeEvent(self, event):
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(self.rect()), 18, 18)
        self.setMask(QtGui.QRegion(path.toFillPolygon().toPolygon()))
        super().resizeEvent(event)

    # ============================= Main tab =============================
    def _build_main_tab(self):
        tab = QtWidgets.QWidget()
        self.tabs.addTab(tab, "Main")
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Top bar: pause indicator + restart/toggle buttons
        top = QtWidgets.QHBoxLayout()
        self._pausechat_lbl = QtWidgets.QLabel("")
        top.addWidget(self._pausechat_lbl)
        top.addStretch(1)
        btn_toggle_pause = QtWidgets.QPushButton("Toggle Chat Commands")
        btn_toggle_pause.clicked.connect(self._toggle_pausechat)
        top.addWidget(btn_toggle_pause)
        btn_restart = QtWidgets.QPushButton("🔄 Restart Bot")
        btn_restart.clicked.connect(self._on_restart_bot_clicked)
        top.addWidget(btn_restart)
        layout.addLayout(top)
        self._pausechat_poll()

        # Config card
        card = QtWidgets.QGroupBox("Connection")
        form = QtWidgets.QGridLayout(card)
        form.setColumnStretch(1, 1)
        form.setColumnStretch(3, 1)

        try:
            sb_port0, sb_pass0, twitch0 = bot.load_streamerbot_config()
        except Exception:
            sb_port0, sb_pass0, twitch0 = "", "", ""

        form.addWidget(QtWidgets.QLabel("Streamer.bot WS Port"), 0, 0)
        self.sb_port_edit = QtWidgets.QLineEdit(sb_port0)
        form.addWidget(self.sb_port_edit, 0, 1)
        form.addWidget(QtWidgets.QLabel("WS Password"), 0, 2)
        self.sb_pass_edit = QtWidgets.QLineEdit(sb_pass0)
        self.sb_pass_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.sb_pass_edit.setPlaceholderText("Optional WebSocket password")
        form.addWidget(self.sb_pass_edit, 0, 3)

        form.addWidget(QtWidgets.QLabel("Twitch Channel"), 1, 0)
        self.twitch_ch_edit = QtWidgets.QLineEdit(twitch0)
        form.addWidget(self.twitch_ch_edit, 1, 1)
        note = QtWidgets.QLabel("(via Streamer.bot — used for Twitch chat detection)")
        note.setObjectName("dim")
        form.addWidget(note, 1, 2, 1, 2)
        test_sb = QtWidgets.QPushButton("Test Streamer.bot")
        test_sb.setObjectName("accent")
        test_sb.clicked.connect(self._test_streamerbot)
        form.addWidget(test_sb, 0, 4, 2, 1)

        # Autosave WS password / twitch channel 1s after typing stops
        self._sb_autosave_timer = QtCore.QTimer(self)
        self._sb_autosave_timer.setSingleShot(True)
        self._sb_autosave_timer.timeout.connect(self._save_sb_fields)
        self.sb_pass_edit.textChanged.connect(lambda: self._sb_autosave_timer.start(1000))
        self.twitch_ch_edit.textChanged.connect(lambda: self._sb_autosave_timer.start(1000))

        form.addWidget(QtWidgets.QLabel("Backend"), 2, 0)
        backend_row = QtWidgets.QHBoxLayout()
        self.backend_vmware_radio = QtWidgets.QRadioButton("VMware")
        self.backend_vbox_radio = QtWidgets.QRadioButton("VBox")
        self.backend_vmware_radio.setChecked(True)
        backend_row.addWidget(self.backend_vmware_radio)
        backend_row.addWidget(self.backend_vbox_radio)
        backend_row.addStretch(1)
        backend_wrap = QtWidgets.QWidget()
        backend_wrap.setLayout(backend_row)
        form.addWidget(backend_wrap, 2, 1)
        self.backend_vmware_radio.toggled.connect(self._on_vm_backend_changed)

        form.addWidget(QtWidgets.QLabel("VM"), 3, 0)
        self.vm_combo = QtWidgets.QComboBox()
        form.addWidget(self.vm_combo, 3, 1)
        btn_refresh_vm = QtWidgets.QPushButton("🔄 Refresh")
        btn_refresh_vm.clicked.connect(self._refresh_vm_list)
        form.addWidget(btn_refresh_vm, 3, 2)

        self.auto_start_check = CheckBox("Auto-restart the VM if it's found powered off")
        self.auto_start_check.setChecked(bool(getattr(bot, "AUTO_START_ENABLED", False)))
        form.addWidget(self.auto_start_check, 4, 1, 1, 2)

        layout.addWidget(card)

        # Start/Stop
        btn_row = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton("▶  Start Bot")
        self.start_btn.setObjectName("green")
        self.start_btn.clicked.connect(self._start_bot)
        self.stop_btn = QtWidgets.QPushButton("⏹  Stop Bot")
        self.stop_btn.setObjectName("red")
        self.stop_btn.clicked.connect(self._stop_bot)
        self.tray_btn = QtWidgets.QPushButton("📌  Minimize to Tray")
        self.tray_btn.clicked.connect(self._minimize_to_tray)
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addWidget(self.tray_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        # Test mode
        self.test_mode_check = CheckBox(
            "🧪  Test Mode  (control VM from console — no chat connection needed)")
        self.test_mode_check.stateChanged.connect(self._on_test_mode_toggle)
        layout.addWidget(self.test_mode_check)

        # Admin command bar
        admin_row = QtWidgets.QHBoxLayout()
        admin_row.addWidget(QtWidgets.QLabel("Admin CMD:"))
        self.admin_cmd_edit = QtWidgets.QLineEdit()
        self.admin_cmd_edit.returnPressed.connect(self._send_admin_cmd)
        admin_row.addWidget(self.admin_cmd_edit, 1)
        send_btn = QtWidgets.QPushButton("Send")
        send_btn.clicked.connect(self._send_admin_cmd)
        admin_row.addWidget(send_btn)
        layout.addLayout(admin_row)

        # Console
        self._console_widget = QtWidgets.QPlainTextEdit()
        self._console_widget.setReadOnly(True)
        self._console_widget.setStyleSheet("background:#0a0a14; font-family: Consolas, monospace;")
        layout.addWidget(self._console_widget, 1)
        self._console = TkTextShim(self._console_widget)

        self._refresh_vm_list()

    def _save_sb_fields(self):
        bot.STREAMERBOT_WS_PASS = self.sb_pass_edit.text().strip()
        bot.TWITCH_CHANNEL = self.twitch_ch_edit.text().strip()
        bot.save_streamerbot_config()
        self._set_feedback("Streamer.bot settings saved")

    def _test_streamerbot(self):
        port = self.sb_port_edit.text().strip()
        if not port.isdigit() or not 1 <= int(port) <= 65535:
            QtWidgets.QMessageBox.warning(self, "Streamer.bot", "Enter a valid WebSocket port first.")
            return
        try:
            import websocket
            ws = websocket.create_connection(f"ws://localhost:{int(port)}/", timeout=2)
            ws.close()
            QtWidgets.QMessageBox.information(self, "Streamer.bot", f"Connected to ws://localhost:{int(port)}/")
            self._set_feedback("Streamer.bot connection successful")
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Streamer.bot", f"Connection failed:\n\n{exc}")
            self._set_feedback("Streamer.bot connection failed", success=False)

    def _on_vm_backend_changed(self):
        backend = "vmware" if self.backend_vmware_radio.isChecked() else "vbox"
        bot.current_vm_backend = backend
        self._refresh_vm_list()

    def _refresh_vm_list(self):
        self.vm_combo.clear()
        try:
            backend = "vmware" if self.backend_vmware_radio.isChecked() else "vbox"
            vms = bot.get_vm_list() if backend == "vmware" else bot.get_all_vbox_vms()
            for v in vms or []:
                self.vm_combo.addItem(v if isinstance(v, str) else v.get("name", str(v)))
        except Exception:
            self._log(f'[err] could not refresh VM list: "{traceback.format_exc()}"')

    def _on_test_mode_toggle(self):
        try:
            bot.TEST_MODE_ENABLED = self.test_mode_check.isChecked()
        except Exception:
            pass

    def _pausechat_poll(self):
        try:
            paused = bool(getattr(bot, "CHAT_COMMANDS_PAUSED", False))
            if paused:
                self._pausechat_lbl.setText("⏸  Chat commands PAUSED")
                self._pausechat_lbl.setStyleSheet(f"color:{self.YELLOW}; font-weight:700;")
            else:
                self._pausechat_lbl.setText("")
        except Exception:
            pass
        QtCore.QTimer.singleShot(1000, self._pausechat_poll)

    def _toggle_pausechat(self):
        try:
            bot.CHAT_COMMANDS_PAUSED = not bool(getattr(bot, "CHAT_COMMANDS_PAUSED", False))
            self._log(f"[info] chat commands {'paused' if bot.CHAT_COMMANDS_PAUSED else 'resumed'}.")
        except Exception:
            pass

    def _on_restart_bot_clicked(self):
        if QtWidgets.QMessageBox.question(
            self, "Restart Bot", "Stop and restart the bot now?"
        ) == QtWidgets.QMessageBox.StandardButton.Yes:
            self._stop_bot()
            QtCore.QTimer.singleShot(800, self._start_bot)

    def _minimize_to_tray(self):
        self.hide()
        if self._tray_icon:
            self._tray_icon.showMessage(
                "UltraBot",
                "Bot is still running. Right-click the tray icon to exit.",
                QtWidgets.QSystemTrayIcon.MessageIcon.Information, 2000)

    def _send_admin_cmd(self):
        text = self.admin_cmd_edit.text().strip()
        if not text:
            return
        self.admin_cmd_edit.clear()
        if not text.startswith("!"):
            text = "!" + text
        cmd_sub = text[1:].split(maxsplit=1)
        cmd = cmd_sub[0].lower()
        args = cmd_sub[1] if len(cmd_sub) > 1 else ""
        threading.Thread(
            target=bot._dispatch_vm_command,
            args=(cmd, args, "admin", True, True),
            daemon=True,
        ).start()

    # -- _start_bot re-implemented natively (the original calls Tkinter's
    #    messagebox directly, so it isn't reusable via method-binding like
    #    _run_bot/_stop_bot are -- everything it calls *into* is unchanged). --
    def _start_bot(self):
        sb_port = self.sb_port_edit.text().strip()
        sb_pass = self.sb_pass_edit.text().strip()
        twitch_ch = self.twitch_ch_edit.text().strip()
        vm = self.vm_combo.currentText().strip()

        if not sb_port:
            QtWidgets.QMessageBox.critical(self, "Missing Input", "Please enter the Streamer.bot WebSocket port.")
            return
        if self._bot_running:
            self._log("⚠️ Bot is already running!")
            return

        bot.STREAMERBOT_WS_PORT = sb_port
        bot.STREAMERBOT_WS_PASS = sb_pass
        bot.TWITCH_CHANNEL = twitch_ch
        bot.save_streamerbot_config()

        if getattr(bot, "OS_VOTING_ENABLED", False):
            valid_entries = [e for e in bot.OS_LIST if e.get("name") and e.get("trigger") and e.get("vm")]
            if len(valid_entries) < 2:
                QtWidgets.QMessageBox.critical(
                    self, "OS Voting Misconfigured",
                    "OS Voting is enabled but fewer than 2 valid OS entries are configured.\n"
                    "Go to the OS Voting tab and fix the configuration, or disable voting.")
                return
            valid_vms = [e["vm"] for e in valid_entries]
            if bot.current_os_vm and bot.current_os_vm in valid_vms:
                start_entry = next(e for e in valid_entries if e["vm"] == bot.current_os_vm)
                bot.VMX_PATH = bot.current_os_vm
            else:
                start_entry = valid_entries[0]
                bot.VMX_PATH = start_entry["vm"]
                bot.current_os_vm = start_entry["vm"]
            bot.current_vm_backend = start_entry.get("backend", "vmware")
        else:
            if not vm:
                QtWidgets.QMessageBox.critical(self, "Missing Input", "Please select a VM.")
                return
            bot.VMX_PATH = vm
            bot.current_os_vm = vm
            bot.current_vm_backend = "vmware" if self.backend_vmware_radio.isChecked() else "vbox"

        if not self._check_tpm_before_start(bot.VMX_PATH):
            return
        bot.VM_ENCRYPTION_PASSWORD = self._vm_encryption_password or ""

        self._bot_running = True
        bot.bot_stop_event.clear()
        self._set_status("Running", self.GREEN)

        self._console_redir = bot.ConsoleRedirect(self._console)
        self._console_redir.start()

        self._log(f"Starting bot → SB WS port: {bot.STREAMERBOT_WS_PORT}  |  "
                   f"Twitch: {bot.TWITCH_CHANNEL or '(none)'}  |  VM: {bot.VMX_PATH}")
        bot.notify("Bot Started",
                    f"Streamer.bot WS: {bot.STREAMERBOT_WS_PORT}\n"
                    f"Twitch: {bot.TWITCH_CHANNEL or '(none)'}\nVM: {bot.VMX_PATH}")
        bot.obs_trigger("bot_start")
        bot._reset_session_stats()
        bot._append_event("BOT_START", "system",
                           f"sb_port={bot.STREAMERBOT_WS_PORT} twitch={bot.TWITCH_CHANNEL} vm={bot.VMX_PATH}")
        try:
            self._append_chat_system(
                f"Bot started — SB WS: {bot.STREAMERBOT_WS_PORT} | Twitch: {bot.TWITCH_CHANNEL or '(none)'}")
        except Exception:
            pass

        running_names = {t.name for t in threading.enumerate()}
        if "scheduler_loop" not in running_names:
            threading.Thread(target=bot.scheduler_loop, daemon=True, name="scheduler_loop").start()

        self._bot_instance = None
        self._bot_thread = threading.Thread(target=self._run_bot, daemon=True)
        self._bot_thread.start()

    def _set_status(self, text, color):
        self._status_dot.setText(f"⬤  {text}")
        self._status_dot.setStyleSheet(f"color: {color}; font-weight: 700; padding: 2px 8px;")

    def _vm_set_last(self, text, color=None):
        """Native Qt replacement for the Tkinter _vm_set_last from og.py."""
        c = color or self.TEXT
        self._vm_action_label.setText(text)
        self._vm_action_label.setStyleSheet(f"color: {c}; font-weight: 600;")

    def _log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self._console.insert("end", f"[{ts}] {msg}\n")
        self._console.see("end")

    # ============================= VM Controls tab =============================
    def _build_vm_tab(self):
        tab = QtWidgets.QWidget()
        self.tabs.addTab(tab, "VM Controls")
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QtWidgets.QLabel("Manual VM Controls")
        title.setObjectName("h1")
        layout.addWidget(title)
        sub = QtWidgets.QLabel("Direct admin actions — no vote required.")
        sub.setObjectName("dim")
        layout.addWidget(sub)

        grid = QtWidgets.QGridLayout()
        grid.setSpacing(14)
        buttons = [
            ("▶  Start VM", "green", "Power on the virtual machine.", self._vm_start),
            ("🔄  Restart VM", "accent", "Send a reset signal to the VM.", self._vm_restart),
            ("⏮  Revert VM", "accent", f"Power off, restore snapshot '{bot.SNAPSHOT_NAME}', boot.", self._vm_revert),
            ("⏹  Shutdown VM", "red", "Force power off the virtual machine.", self._vm_shutdown),
            ("Ⅱ  Pause VM", "accent", "Pause the VM without powering it off.", self._vm_pause),
            ("▶  Resume VM", "green", "Resume a paused or suspended VM.", self._vm_resume),
            ("💾  Suspend VM", "accent", "Save VM state and suspend it.", self._vm_suspend),
        ]
        for i, (label, style, desc, fn) in enumerate(buttons):
            cell = QtWidgets.QGroupBox()
            cell_l = QtWidgets.QVBoxLayout(cell)
            btn = QtWidgets.QPushButton(label)
            btn.setObjectName(style)
            btn.clicked.connect(fn)
            cell_l.addWidget(btn)
            desc_l = QtWidgets.QLabel(desc)
            desc_l.setObjectName("dim")
            desc_l.setWordWrap(True)
            cell_l.addWidget(desc_l)
            grid.addWidget(cell, i // 2, i % 2)
        layout.addLayout(grid)

        status_row = QtWidgets.QHBoxLayout()
        status_row.addWidget(QtWidgets.QLabel("Last action:"))
        self._vm_action_label = QtWidgets.QLabel("—")
        status_row.addWidget(self._vm_action_label)
        status_row.addStretch(1)
        layout.addLayout(status_row)

        layout.addStretch(1)

    def _vm_start(self):
        if not bot.VMX_PATH:
            QtWidgets.QMessageBox.critical(self, "No VM", "Start the bot first to select a VM.")
            return
        if not self._check_tpm_before_start(bot.VMX_PATH):
            return
        bot.VM_ENCRYPTION_PASSWORD = self._vm_encryption_password
        self._vm_set_last("Starting…", self.YELLOW)
        self._log("[VM] Start requested by admin.")

        def run():
            try:
                bot.speak_text("Starting Virtual Machine...")
                bot.update_status("Starting...")
                bot.obs_trigger("vm_starting")
                bot.start_vm()
                self.after(0, lambda: self._vm_set_last("Started ✔", self.GREEN))
            except Exception as e:
                err = f"Error: {e}"
                self.after(0, lambda: self._vm_set_last(err, self.RED))
                print(f'[VM] Start error: "{traceback.format_exc()}"')
        threading.Thread(target=run, daemon=True).start()

    def _vm_restart(self):
        if not bot.VMX_PATH:
            QtWidgets.QMessageBox.critical(self, "No VM", "Start the bot first to select a VM.")
            return
        if QtWidgets.QMessageBox.question(self, "Restart VM", f"Reset '{bot.VMX_PATH}' now?") \
                != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        self._vm_set_last("Restarting…", self.YELLOW)
        self._log("[VM] Restart requested by admin.")

        def run():
            try:
                bot.speak_text("Restarting Virtual Machine...")
                bot.update_status("Restarting...")
                bot._checked(bot.vm_reset(bot.VMX_PATH, bot.current_vm_backend))
                bot.update_status("Running")
                bot.play_success_sound()
                bot.obs_trigger("restart")
                bot.obs_trigger("restart_done")
                bot.apply_current_os_scene()
                self.after(0, lambda: self._vm_set_last("Restarted ✔", self.GREEN))
            except Exception as e:
                err = f"Error: {e}"
                self.after(0, lambda: self._vm_set_last(err, self.RED))
                print(f'[VM] Restart error: "{traceback.format_exc()}"')
        threading.Thread(target=run, daemon=True).start()

    def _vm_revert(self):
        if not bot.VMX_PATH:
            QtWidgets.QMessageBox.critical(self, "No VM", "Start the bot first to select a VM.")
            return
        if QtWidgets.QMessageBox.question(
            self, "Revert VM",
            f"Power off '{bot.VMX_PATH}', restore snapshot and reboot?\n"
            "This will discard all unsaved VM state."
        ) != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        self._vm_set_last("Reverting…", self.YELLOW)
        self._log("[VM] Revert requested by admin.")

        def run():
            bot.revert_in_progress = True
            try:
                bot.speak_text("Reverting Virtual Machine...")
                bot.update_status("Reverting...")
                bot._checked(bot.vm_stop(bot.VMX_PATH, bot.current_vm_backend, hard=True))
                time.sleep(3)
                bot._checked(bot.vm_revert_to_snapshot(bot.VMX_PATH, bot.SNAPSHOT_NAME, bot.current_vm_backend))
                time.sleep(3)
                bot.obs_trigger("vm_starting")
                bot._checked(bot.vm_start(bot.VMX_PATH, bot.current_vm_backend, gui=True))
                bot.update_status("Running")
                bot.play_success_sound()
                bot.obs_trigger("revert_done")
                bot.apply_current_os_scene()
                bot.vote_revert.clear()
                bot.update_votes_json("revert", 0, 2, 0)
                self.after(0, lambda: self._vm_set_last("Reverted ✔", self.GREEN))
            except Exception as e:
                bot.update_status("Revert failed")
                err = f"Error: {e}"
                self.after(0, lambda: self._vm_set_last(err, self.RED))
                print(f'[VM] Revert error: "{traceback.format_exc()}"')
            finally:
                bot.revert_start_time = None
                bot.revert_in_progress = False
        threading.Thread(target=run, daemon=True).start()

    def _vm_shutdown(self):
        if not bot.VMX_PATH:
            QtWidgets.QMessageBox.critical(self, "No VM", "Start the bot first to select a VM.")
            return
        if QtWidgets.QMessageBox.question(
            self, "Shutdown VM",
            f"Force power off '{bot.VMX_PATH}'?\nUnsaved VM state will be lost."
        ) != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        self._vm_set_last("Shutting down…", self.YELLOW)
        self._log("[VM] Shutdown requested by admin.")

        def run():
            try:
                bot.speak_text("Shutting down Virtual Machine...")
                bot.update_status("Shutting down...")
                bot._checked(bot.vm_stop(bot.VMX_PATH, bot.current_vm_backend, hard=True))
                bot.update_status("Stopped")
                bot.obs_trigger("vm_shutdown")
                self.after(0, lambda: self._vm_set_last("Powered off ✔", self.TEXTDIM))
            except Exception as e:
                err = f"Error: {e}"
                self.after(0, lambda: self._vm_set_last(err, self.RED))
                print(f'[VM] Shutdown error: "{traceback.format_exc()}"')
        threading.Thread(target=run, daemon=True).start()

    def _vm_pause(self):
        self._run_vm_state_action("Pausing", "Paused", bot.vm_pause)

    def _vm_resume(self):
        self._run_vm_state_action("Resuming", "Resumed", bot.vm_unpause)

    def _vm_suspend(self):
        self._run_vm_state_action("Suspending", "Suspended", bot.vm_save_state)

    def _run_vm_state_action(self, working, success, action):
        if not bot.VMX_PATH:
            QtWidgets.QMessageBox.critical(self, "No VM", "Start the bot first to select a VM.")
            return
        bot.current_vm_backend = "vmware" if self.backend_vmware_radio.isChecked() else "vbox"
        self._vm_set_last(working, self.YELLOW)
        def run():
            try:
                ok, error = action()
                if not ok:
                    raise RuntimeError(str(error or "the hypervisor rejected the request"))
                self.after(0, lambda: self._vm_set_last(success + " ✔", self.GREEN))
            except Exception as exc:
                self.after(0, lambda: self._vm_set_last(f"Error: {exc}", self.RED))
        threading.Thread(target=run, daemon=True).start()

    # ============================= Music tab =============================
    def _build_music_tab(self):
        tab = QtWidgets.QWidget()
        self.tabs.addTab(tab, "Music")
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        top = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Music Panel")
        title.setObjectName("h1")
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(QtWidgets.QLabel("Change every"))
        self.music_hours_spin = QtWidgets.QDoubleSpinBox()
        self.music_hours_spin.setRange(0.1, 999)
        self.music_hours_spin.setValue(float(bot.music_config.get("change_hours", 1)))
        top.addWidget(self.music_hours_spin)
        top.addWidget(QtWidgets.QLabel("hour(s)"))
        save_hrs_btn = QtWidgets.QPushButton("Save")
        save_hrs_btn.setObjectName("green")
        save_hrs_btn.clicked.connect(self._music_save_hours)
        top.addWidget(save_hrs_btn)
        layout.addLayout(top)

        enable_row = QtWidgets.QHBoxLayout()
        self.music_enabled_check = CheckBox("Enable automatic music playback")
        self.music_enabled_check.setChecked(bool(bot.music_config.get("enabled", False)))
        self.music_enabled_check.stateChanged.connect(self._music_toggle_enabled)
        enable_row.addWidget(self.music_enabled_check)
        enable_row.addStretch(1)
        self.music_now_playing_lbl = QtWidgets.QLabel(
            f"now playing: {bot.music_current_desc or '(nothing)'}")
        self.music_now_playing_lbl.setObjectName("dim")
        enable_row.addWidget(self.music_now_playing_lbl)
        layout.addLayout(enable_row)

        controls = QtWidgets.QHBoxLayout()
        play_btn = QtWidgets.QPushButton("▶ Play Selected Schedule")
        play_btn.setObjectName("green")
        play_btn.clicked.connect(self._music_play_selected_schedule)
        skip_btn = QtWidgets.QPushButton("⏭ Skip Track")
        skip_btn.clicked.connect(lambda: (bot.music_skip_track(), self._log("[info] skipped to next track.")))
        pause_btn = QtWidgets.QPushButton("⏸ Pause/Resume")
        pause_btn.clicked.connect(lambda: bot.music_pause_toggle())
        stop_btn = QtWidgets.QPushButton("⏹ Stop")
        stop_btn.setObjectName("red")
        stop_btn.clicked.connect(lambda: (bot.stop_music_player(), self._log("[info] music stopped.")))
        controls.addWidget(play_btn)
        controls.addWidget(skip_btn)
        controls.addWidget(pause_btn)
        controls.addWidget(stop_btn)
        controls.addWidget(QtWidgets.QLabel("Volume"))
        self.music_volume_slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.music_volume_slider.setRange(0, 100)
        self.music_volume_slider.setValue(int(bot.music_config.get("volume", 90)))
        self.music_volume_slider.setFixedWidth(140)
        self.music_volume_slider.valueChanged.connect(lambda v: bot.music_set_volume(v))
        controls.addWidget(self.music_volume_slider)
        controls.addStretch(1)
        layout.addLayout(controls)

        main_area = QtWidgets.QHBoxLayout()
        layout.addLayout(main_area, 1)

        # Left: schedule
        left = QtWidgets.QVBoxLayout()
        left.addWidget(QtWidgets.QLabel("MUSIC SCHEDULE (ORDER)"))
        add_sched_btn = QtWidgets.QPushButton("+ Add New Music Schedule")
        add_sched_btn.setObjectName("accent")
        add_sched_btn.clicked.connect(self._music_open_add_schedule_dialog)
        left.addWidget(add_sched_btn)
        self.music_schedule_list = QtWidgets.QListWidget()
        left.addWidget(self.music_schedule_list, 1)
        left.addWidget(QtWidgets.QLabel("STATUS / HISTORY"))
        self.music_status_list = QtWidgets.QListWidget()
        left.addWidget(self.music_status_list, 1)
        sched_btns = QtWidgets.QHBoxLayout()
        remove_sched_btn = QtWidgets.QPushButton("Remove")
        remove_sched_btn.setObjectName("red")
        remove_sched_btn.clicked.connect(self._music_remove_schedule_entry)
        sched_btns.addWidget(remove_sched_btn)
        left.addLayout(sched_btns)
        left_w = QtWidgets.QWidget()
        left_w.setLayout(left)
        left_w.setFixedWidth(320)
        main_area.addWidget(left_w)

        # Right: tracks / playlists
        tracks_box = QtWidgets.QGroupBox("MUSICS (SINGLE TRACKS)")
        tracks_l = QtWidgets.QVBoxLayout(tracks_box)
        self.music_tracks_list = QtWidgets.QListWidget()
        tracks_l.addWidget(self.music_tracks_list)
        t_btns = QtWidgets.QHBoxLayout()
        add_t = QtWidgets.QPushButton("+ Add")
        add_t.setObjectName("green")
        add_t.clicked.connect(lambda: self._music_add_url("tracks"))
        rm_t = QtWidgets.QPushButton("✕ Remove")
        rm_t.setObjectName("red")
        rm_t.clicked.connect(lambda: self._music_remove_url("tracks"))
        t_btns.addWidget(add_t)
        t_btns.addWidget(rm_t)
        tracks_l.addLayout(t_btns)
        main_area.addWidget(tracks_box, 1)

        pl_box = QtWidgets.QGroupBox("PLAYLISTS (SHUFFLE + LOOP)")
        pl_l = QtWidgets.QVBoxLayout(pl_box)
        self.music_playlists_list = QtWidgets.QListWidget()
        pl_l.addWidget(self.music_playlists_list)
        p_btns = QtWidgets.QHBoxLayout()
        add_p = QtWidgets.QPushButton("+ Add")
        add_p.setObjectName("green")
        add_p.clicked.connect(lambda: self._music_add_url("playlists"))
        rm_p = QtWidgets.QPushButton("✕ Remove")
        rm_p.setObjectName("red")
        rm_p.clicked.connect(lambda: self._music_remove_url("playlists"))
        p_btns.addWidget(add_p)
        p_btns.addWidget(rm_p)
        pl_l.addLayout(p_btns)
        main_area.addWidget(pl_box, 1)

        self._music_refresh_all_lists()
        self._music_poll_status()

    def _music_save_hours(self):
        hrs = self.music_hours_spin.value()
        bot.music_config["change_hours"] = hrs
        bot.save_music_config()
        self._log(f"[info] music schedule will now advance every {hrs} hour(s).")

    def _music_toggle_enabled(self):
        bot.music_config["enabled"] = self.music_enabled_check.isChecked()
        bot.save_music_config()
        try:
            bot.save_autostart_everything_config(music_playback_enabled=bot.music_config["enabled"])
        except Exception:
            pass
        if bot.music_config["enabled"]:
            bot.start_music_player()
            self._log("[info] music player enabled.")
        else:
            bot.stop_music_player()
            self._log("[info] music player disabled.")

    def _music_play_selected_schedule(self):
        sched = bot.music_config.get("schedule", [])
        if not sched:
            QtWidgets.QMessageBox.information(self, "Music", "Add a schedule entry first.")
            return
        row = self.music_schedule_list.currentRow()
        item = sched[row] if row >= 0 else sched[0]
        if not bot.music_config.get("enabled", False):
            self.music_enabled_check.setChecked(True)
        threading.Thread(
            target=lambda: bot.music_play_url(item.get("url", ""), shuffle_loop=(item.get("type") == "playlist")),
            daemon=True).start()
        self._log(f"[info] manually playing schedule entry: {item.get('url')}")

    def _music_refresh_all_lists(self):
        self.music_tracks_list.clear()
        self.music_tracks_list.addItems(bot.music_config.get("tracks", []))
        self.music_playlists_list.clear()
        self.music_playlists_list.addItems(bot.music_config.get("playlists", []))
        self.music_schedule_list.clear()
        for i, item in enumerate(bot.music_config.get("schedule", []), 1):
            self.music_schedule_list.addItem(f"{i}. [{item.get('type')}] {item.get('url')}")

    def _music_add_url(self, kind):
        label = "video" if kind == "tracks" else "playlist"
        url, ok = QtWidgets.QInputDialog.getText(self, "Add YouTube URL", f"Paste the YouTube {label} URL:")
        if not ok or not url.strip():
            return
        bot.music_config.setdefault(kind, []).append(url.strip())
        bot.save_music_config()
        self._music_refresh_all_lists()
        self._log(f"[info] added {kind[:-1]}: {url.strip()}")

    def _music_remove_url(self, kind):
        lw = self.music_tracks_list if kind == "tracks" else self.music_playlists_list
        row = lw.currentRow()
        if row < 0:
            return
        items = bot.music_config.get(kind, [])
        if row < len(items):
            removed = items.pop(row)
            bot.save_music_config()
            self._music_refresh_all_lists()
            self._log(f"[info] removed {kind[:-1]}: {removed}")

    def _music_open_add_schedule_dialog(self):
        if len(bot.music_config.get("schedule", [])) >= bot.MUSIC_SCHEDULE_MAX:
            QtWidgets.QMessageBox.information(
                self, "Music Schedule", f"Maximum of {bot.MUSIC_SCHEDULE_MAX} schedule entries reached.")
            return
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Add New Music Schedule")
        v = QtWidgets.QVBoxLayout(dlg)
        v.addWidget(QtWidgets.QLabel("Type"))
        row = QtWidgets.QHBoxLayout()
        track_radio = QtWidgets.QRadioButton("Music (single track)")
        playlist_radio = QtWidgets.QRadioButton("Playlist (shuffle+loop)")
        track_radio.setChecked(True)
        row.addWidget(track_radio)
        row.addWidget(playlist_radio)
        v.addLayout(row)
        v.addWidget(QtWidgets.QLabel("URL"))
        url_combo = QtWidgets.QComboBox()
        url_combo.setEditable(True)
        v.addWidget(url_combo)

        def refresh_choices():
            src = bot.music_config.get("tracks", []) if track_radio.isChecked() else bot.music_config.get("playlists", [])
            url_combo.clear()
            url_combo.addItems(src)
        track_radio.toggled.connect(refresh_choices)
        refresh_choices()

        btn_row = QtWidgets.QHBoxLayout()
        add_btn = QtWidgets.QPushButton("Add to Schedule")
        add_btn.setObjectName("accent")
        cancel_btn = QtWidgets.QPushButton("Cancel")
        btn_row.addWidget(add_btn)
        btn_row.addWidget(cancel_btn)
        v.addLayout(btn_row)
        cancel_btn.clicked.connect(dlg.reject)

        def confirm():
            url = url_combo.currentText().strip()
            if not url:
                QtWidgets.QMessageBox.warning(
                    self, "Music Schedule",
                    "Pick or type a URL first (add it in the Musics/Playlists box if it's not listed).")
                return
            bot.music_config.setdefault("schedule", []).append(
                {"type": "track" if track_radio.isChecked() else "playlist", "url": url})
            bot.save_music_config()
            self._music_refresh_all_lists()
            dlg.accept()
        add_btn.clicked.connect(confirm)
        dlg.exec()

    def _music_remove_schedule_entry(self):
        row = self.music_schedule_list.currentRow()
        if row < 0:
            return
        sched = bot.music_config.get("schedule", [])
        if row < len(sched):
            removed = sched.pop(row)
            bot.save_music_config()
            self._music_refresh_all_lists()
            self._log(f"[info] removed schedule entry: {removed.get('url')}")

    def _music_poll_status(self):
        try:
            self.music_now_playing_lbl.setText(
                f"now playing: {bot.music_current_desc or '(nothing)'} — {bot.music_status_text}")
            last = self.music_status_list.item(0).text() if self.music_status_list.count() else None
            if bot.music_status_text and (not last or bot.music_status_text not in last):
                self.music_status_list.insertItem(0, f"[{time.strftime('%H:%M:%S')}] {bot.music_status_text}")
        except Exception:
            pass
        if not bot.bot_stop_event.is_set():
            QtCore.QTimer.singleShot(3000, self._music_poll_status)

    # ============================= Video tab =============================
    def _build_video_tab(self):
        tab = QtWidgets.QWidget()
        self.tabs.addTab(tab, "Video")
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        top = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Video Panel")
        title.setObjectName("h1")
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(QtWidgets.QLabel("Change every"))
        self.video_hours_spin = QtWidgets.QDoubleSpinBox()
        self.video_hours_spin.setRange(0.1, 999)
        self.video_hours_spin.setValue(float(bot.video_config.get("change_hours", 1)))
        top.addWidget(self.video_hours_spin)
        top.addWidget(QtWidgets.QLabel("hour(s)"))
        save_hrs_btn = QtWidgets.QPushButton("Save")
        save_hrs_btn.setObjectName("green")
        save_hrs_btn.clicked.connect(self._video_save_hours)
        top.addWidget(save_hrs_btn)
        open_win_btn = QtWidgets.QPushButton("🗔 Open Video Window")
        open_win_btn.setObjectName("accent")
        open_win_btn.clicked.connect(self.ensure_video_window)
        top.addWidget(open_win_btn)
        layout.addLayout(top)

        enable_row = QtWidgets.QHBoxLayout()
        self.video_enabled_check = CheckBox("Enable automatic video playback")
        self.video_enabled_check.setChecked(bool(bot.video_config.get("enabled", False)))
        self.video_enabled_check.stateChanged.connect(self._video_toggle_enabled)
        enable_row.addWidget(self.video_enabled_check)
        enable_row.addStretch(1)
        self.video_now_playing_lbl = QtWidgets.QLabel(
            f"now playing: {bot.video_current_desc or '(nothing)'}")
        self.video_now_playing_lbl.setObjectName("dim")
        enable_row.addWidget(self.video_now_playing_lbl)
        layout.addLayout(enable_row)

        controls = QtWidgets.QHBoxLayout()
        play_btn = QtWidgets.QPushButton("▶ Play Selected Schedule")
        play_btn.setObjectName("green")
        play_btn.clicked.connect(self._video_play_selected_schedule)
        skip_btn = QtWidgets.QPushButton("⏭ Skip Clip")
        skip_btn.clicked.connect(lambda: (bot.video_skip_track(), self._log("[info] skipped to next video clip.")))
        pause_btn = QtWidgets.QPushButton("⏸ Pause/Resume")
        pause_btn.clicked.connect(bot.video_pause_toggle)
        stop_btn = QtWidgets.QPushButton("⏹ Stop")
        stop_btn.setObjectName("red")
        stop_btn.clicked.connect(lambda: (bot.stop_video_player(), self._log("[info] video stopped.")))
        controls.addWidget(play_btn)
        controls.addWidget(skip_btn)
        controls.addWidget(pause_btn)
        controls.addWidget(stop_btn)
        controls.addWidget(QtWidgets.QLabel("Volume"))
        self.video_volume_slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        self.video_volume_slider.setRange(0, 100)
        self.video_volume_slider.setValue(int(bot.video_config.get("volume", 90)))
        self.video_volume_slider.setFixedWidth(140)
        self.video_volume_slider.valueChanged.connect(bot.video_set_volume)
        controls.addWidget(self.video_volume_slider)
        controls.addStretch(1)
        layout.addLayout(controls)

        main_area = QtWidgets.QHBoxLayout()
        layout.addLayout(main_area, 1)

        left = QtWidgets.QVBoxLayout()
        left.addWidget(QtWidgets.QLabel("VIDEO SCHEDULE (ORDER)"))
        add_sched_btn = QtWidgets.QPushButton("+ Add New Video Schedule")
        add_sched_btn.setObjectName("accent")
        add_sched_btn.clicked.connect(self._video_open_add_schedule_dialog)
        left.addWidget(add_sched_btn)
        self.video_schedule_list = QtWidgets.QListWidget()
        left.addWidget(self.video_schedule_list, 1)
        left.addWidget(QtWidgets.QLabel("STATUS / HISTORY"))
        self.video_status_list = QtWidgets.QListWidget()
        left.addWidget(self.video_status_list, 1)
        remove_sched_btn = QtWidgets.QPushButton("Remove Selected")
        remove_sched_btn.setObjectName("red")
        remove_sched_btn.clicked.connect(self._video_remove_schedule_entry)
        left.addWidget(remove_sched_btn)
        left_w = QtWidgets.QWidget()
        left_w.setLayout(left)
        left_w.setFixedWidth(320)
        main_area.addWidget(left_w)

        videos_box = QtWidgets.QGroupBox("VIDEOS (SINGLE CLIPS)")
        videos_l = QtWidgets.QVBoxLayout(videos_box)
        self.video_tracks_list = QtWidgets.QListWidget()
        videos_l.addWidget(self.video_tracks_list)
        v_btns = QtWidgets.QHBoxLayout()
        add_v = QtWidgets.QPushButton("+ Add")
        add_v.setObjectName("green")
        add_v.clicked.connect(lambda: self._video_add_url("tracks"))
        rm_v = QtWidgets.QPushButton("✕ Remove")
        rm_v.setObjectName("red")
        rm_v.clicked.connect(lambda: self._video_remove_url("tracks"))
        v_btns.addWidget(add_v)
        v_btns.addWidget(rm_v)
        videos_l.addLayout(v_btns)
        main_area.addWidget(videos_box, 1)

        pl_box = QtWidgets.QGroupBox("PLAYLISTS (SHUFFLE + LOOP)")
        pl_l = QtWidgets.QVBoxLayout(pl_box)
        self.video_playlists_list = QtWidgets.QListWidget()
        pl_l.addWidget(self.video_playlists_list)
        p_btns = QtWidgets.QHBoxLayout()
        add_p = QtWidgets.QPushButton("+ Add")
        add_p.setObjectName("green")
        add_p.clicked.connect(lambda: self._video_add_url("playlists"))
        rm_p = QtWidgets.QPushButton("✕ Remove")
        rm_p.setObjectName("red")
        rm_p.clicked.connect(lambda: self._video_remove_url("playlists"))
        p_btns.addWidget(add_p)
        p_btns.addWidget(rm_p)
        pl_l.addLayout(p_btns)
        main_area.addWidget(pl_box, 1)

        self._video_refresh_all_lists()
        self._video_poll_status()

    def _video_save_hours(self):
        hours = self.video_hours_spin.value()
        bot.video_config["change_hours"] = hours
        bot.save_video_config()
        self._log(f"[info] video schedule will now advance every {hours} hour(s).")

    def _video_play_selected_schedule(self):
        schedule = bot.video_config.get("schedule", [])
        if not schedule:
            QtWidgets.QMessageBox.information(self, "Video", "Add a schedule entry first.")
            return
        row = self.video_schedule_list.currentRow()
        item = schedule[row] if row >= 0 else schedule[0]
        if not bot.video_config.get("enabled", False):
            self.video_enabled_check.setChecked(True)
        self.ensure_video_window()
        threading.Thread(
            target=lambda: bot.video_play_url(item.get("url", ""), shuffle_loop=(item.get("type") == "playlist")),
            daemon=True,
        ).start()
        self._log(f"[info] manually playing video schedule entry: {item.get('url')}")

    def _video_open_add_schedule_dialog(self):
        if len(bot.video_config.get("schedule", [])) >= bot.VIDEO_SCHEDULE_MAX:
            QtWidgets.QMessageBox.information(self, "Video Schedule", f"Maximum of {bot.VIDEO_SCHEDULE_MAX} entries reached.")
            return
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Add New Video Schedule")
        layout = QtWidgets.QVBoxLayout(dialog)
        track_radio = QtWidgets.QRadioButton("Video (single clip)")
        playlist_radio = QtWidgets.QRadioButton("Playlist (shuffle + loop)")
        track_radio.setChecked(True)
        layout.addWidget(track_radio)
        layout.addWidget(playlist_radio)
        url_combo = QtWidgets.QComboBox()
        url_combo.setEditable(True)
        layout.addWidget(url_combo)

        def refresh_choices():
            source = bot.video_config.get("tracks", []) if track_radio.isChecked() else bot.video_config.get("playlists", [])
            url_combo.clear()
            url_combo.addItems(source)
        track_radio.toggled.connect(refresh_choices)
        refresh_choices()
        buttons = QtWidgets.QHBoxLayout()
        add = QtWidgets.QPushButton("Add to Schedule")
        add.setObjectName("accent")
        cancel = QtWidgets.QPushButton("Cancel")
        buttons.addWidget(add)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        cancel.clicked.connect(dialog.reject)

        def confirm():
            url = url_combo.currentText().strip()
            if not url:
                QtWidgets.QMessageBox.warning(dialog, "Video Schedule", "Pick or type a URL first.")
                return
            bot.video_config.setdefault("schedule", []).append({
                "type": "track" if track_radio.isChecked() else "playlist",
                "url": url,
            })
            bot.save_video_config()
            self._video_refresh_all_lists()
            self._log(f"[info] added video schedule entry: {url}")
            dialog.accept()
        add.clicked.connect(confirm)
        dialog.exec()

    def _video_remove_schedule_entry(self):
        row = self.video_schedule_list.currentRow()
        schedule = bot.video_config.get("schedule", [])
        if 0 <= row < len(schedule):
            removed = schedule.pop(row)
            bot.save_video_config()
            self._video_refresh_all_lists()
            self._log(f"[info] removed video schedule entry: {removed.get('url')}")

    def _video_toggle_enabled(self):
        bot.video_config["enabled"] = self.video_enabled_check.isChecked()
        bot.save_video_config()
        self._log(f"[info] video player {'enabled' if bot.video_config['enabled'] else 'disabled'}.")

    def _video_refresh_all_lists(self):
        self.video_tracks_list.clear()
        self.video_tracks_list.addItems(bot.video_config.get("tracks", []))
        self.video_playlists_list.clear()
        self.video_playlists_list.addItems(bot.video_config.get("playlists", []))
        self.video_schedule_list.clear()
        for i, item in enumerate(bot.video_config.get("schedule", []), 1):
            self.video_schedule_list.addItem(f"{i}. [{item.get('type')}] {item.get('url')}")

    def _video_add_url(self, kind):
        label = "video" if kind == "tracks" else "playlist"
        url, ok = QtWidgets.QInputDialog.getText(self, "Add YouTube URL", f"Paste the YouTube {label} URL:")
        if not ok or not url.strip():
            return
        bot.video_config.setdefault(kind, []).append(url.strip())
        bot.save_video_config()
        self._video_refresh_all_lists()
        self._log(f"[info] added {kind[:-1]}: {url.strip()}")

    def _video_remove_url(self, kind):
        lw = self.video_tracks_list if kind == "tracks" else self.video_playlists_list
        row = lw.currentRow()
        if row < 0:
            return
        items = bot.video_config.get(kind, [])
        if row < len(items):
            removed = items.pop(row)
            bot.save_video_config()
            self._video_refresh_all_lists()
            self._log(f"[info] removed {kind[:-1]}: {removed}")

    def _video_poll_status(self):
        try:
            self.video_now_playing_lbl.setText(
                f"now playing: {bot.video_current_desc or '(nothing)'} — {bot.video_status_text}")
            last = self.video_status_list.item(0).text() if self.video_status_list.count() else None
            if bot.video_status_text and (not last or bot.video_status_text not in last):
                self.video_status_list.insertItem(0, f"[{time.strftime('%H:%M:%S')}] {bot.video_status_text}")
        except Exception:
            pass
        if not bot.bot_stop_event.is_set():
            QtCore.QTimer.singleShot(3000, self._video_poll_status)

    # -- The movable window video renders into. Backend (bot.py) calls
    #    ensure_video_window()/set_video_window_title() and reads
    #    video_toplevel/video_canvas directly -- see pyqt_compat.py's docstring. --
    def ensure_video_window(self):
        try:
            if self.video_toplevel is not None and self.video_toplevel.winfo_exists():
                self.video_toplevel.show()
                self.video_toplevel.raise_()
                return
            win = VideoPanelWindow()
            w = int(bot.video_config.get("window_w", 640) or 640)
            h = int(bot.video_config.get("window_h", 360) or 360)
            x, y = bot.video_config.get("window_x"), bot.video_config.get("window_y")
            win.resize(w, h)
            if x is not None and y is not None:
                win.move(int(x), int(y))
            if bot.video_config.get("always_on_top", False):
                win.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
            win.closed.connect(self._on_video_window_close)
            win.show()
            win.canvas.winId()
            QtWidgets.QApplication.processEvents()
            self.video_toplevel = win
            self.video_canvas = win.canvas
            self._video_geom_timer = QtCore.QTimer(self)
            self._video_geom_timer.setSingleShot(True)
            self._video_geom_timer.timeout.connect(self._video_save_geometry_now)
            win.installEventFilter(self)
        except Exception:
            self._log(f'[err] could not open video window: "{traceback.format_exc()}"')

    def eventFilter(self, obj, event):
        if obj is self.video_toplevel and event.type() in (
            QtCore.QEvent.Type.Move, QtCore.QEvent.Type.Resize
        ):
            self._video_geom_timer.start(500)
        return super().eventFilter(obj, event)

    def _video_save_geometry_now(self):
        try:
            if self.video_toplevel is not None and self.video_toplevel.winfo_exists():
                bot.video_config["window_x"] = self.video_toplevel.winfo_x()
                bot.video_config["window_y"] = self.video_toplevel.winfo_y()
                bot.video_config["window_w"] = self.video_toplevel.winfo_width()
                bot.video_config["window_h"] = self.video_toplevel.winfo_height()
                bot.save_video_config()
        except Exception:
            pass

    def _on_video_window_close(self):
        try:
            self._video_save_geometry_now()
        except Exception:
            pass
        self.video_toplevel = None
        self.video_canvas = None
        threading.Thread(target=bot.video_stop_current, daemon=True).start()
        self._log("[info] video window closed, playback stopped.")

    def set_video_window_title(self, desc):
        # Title stays constant -- see VideoPanelWindow's docstring for why.
        pass

    # ============================= Permissions tab =============================
    def _build_permissions_tab(self):
        tab = QtWidgets.QWidget()
        self.tabs.addTab(tab, "Permissions")
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QtWidgets.QLabel("Voting & Permissions")
        title.setObjectName("h1")
        layout.addWidget(title)

        card = QtWidgets.QGroupBox("Vote Thresholds")
        form = QtWidgets.QFormLayout(card)

        self.perm_restart_spin = QtWidgets.QSpinBox()
        self.perm_restart_spin.setRange(1, 999)
        self.perm_restart_spin.setValue(int(bot.PERMISSIONS_CONFIG.get("restart_votes", 2)))
        form.addRow("Restart votes required", self.perm_restart_spin)

        self.perm_revert_spin = QtWidgets.QSpinBox()
        self.perm_revert_spin.setRange(1, 999)
        self.perm_revert_spin.setValue(int(bot.PERMISSIONS_CONFIG.get("revert_votes", 2)))
        form.addRow("Revert votes required", self.perm_revert_spin)

        self.perm_ban_spin = QtWidgets.QSpinBox()
        self.perm_ban_spin.setRange(1, 999)
        self.perm_ban_spin.setValue(int(bot.PERMISSIONS_CONFIG.get("ban_votes", 3)))
        form.addRow("Ban votes required", self.perm_ban_spin)

        self.perm_cooldown_spin = QtWidgets.QSpinBox()
        self.perm_cooldown_spin.setRange(0, 3600)
        self.perm_cooldown_spin.setValue(int(bot.PERMISSIONS_CONFIG.get("action_cooldown", 60)))
        form.addRow("Action cooldown (s)", self.perm_cooldown_spin)

        self.perm_global_cd_spin = QtWidgets.QSpinBox()
        self.perm_global_cd_spin.setRange(0, 3600)
        self.perm_global_cd_spin.setValue(int(bot.PERMISSIONS_CONFIG.get("global_command_cooldown", 60)))
        form.addRow("Global per-user command cooldown (s, 0=off)", self.perm_global_cd_spin)

        layout.addWidget(card)

        pct_card = QtWidgets.QGroupBox("Percent-Based Voting")
        pct_l = QtWidgets.QFormLayout(pct_card)
        self.perm_pct_enabled_check = CheckBox(
            "Require a % of live viewers instead of a fixed vote count")
        self.perm_pct_enabled_check.setChecked(
            bool(bot.PERMISSIONS_CONFIG.get("vote_threshold_percent_enabled", False)))
        pct_l.addRow(self.perm_pct_enabled_check)
        self.perm_pct_spin = QtWidgets.QSpinBox()
        self.perm_pct_spin.setRange(1, 100)
        self.perm_pct_spin.setValue(int(bot.PERMISSIONS_CONFIG.get("vote_threshold_percent", 30)))
        pct_l.addRow("Percent of live viewers", self.perm_pct_spin)
        layout.addWidget(pct_card)

        media_card = QtWidgets.QGroupBox("Song / Video Requests")
        media_l = QtWidgets.QVBoxLayout(media_card)
        self.perm_media_restricted_check = CheckBox(
            "Restrict !sr / !vr requests to moderators only")
        self.perm_media_restricted_check.setChecked(bool(getattr(bot, "MEDIA_REQUEST_RESTRICTED", False)))
        media_l.addWidget(self.perm_media_restricted_check)
        layout.addWidget(media_card)

        save_btn = QtWidgets.QPushButton("💾 Save Permissions")
        save_btn.setObjectName("green")
        save_btn.clicked.connect(self._save_permissions)
        layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)

    def _save_permissions(self):
        bot.PERMISSIONS_CONFIG["restart_votes"] = self.perm_restart_spin.value()
        bot.PERMISSIONS_CONFIG["revert_votes"] = self.perm_revert_spin.value()
        bot.PERMISSIONS_CONFIG["ban_votes"] = self.perm_ban_spin.value()
        bot.PERMISSIONS_CONFIG["action_cooldown"] = self.perm_cooldown_spin.value()
        bot.PERMISSIONS_CONFIG["global_command_cooldown"] = self.perm_global_cd_spin.value()
        bot.PERMISSIONS_CONFIG["vote_threshold_percent_enabled"] = self.perm_pct_enabled_check.isChecked()
        bot.PERMISSIONS_CONFIG["vote_threshold_percent"] = self.perm_pct_spin.value()
        bot.save_permissions_config()
        try:
            bot.MEDIA_REQUEST_RESTRICTED = self.perm_media_restricted_check.isChecked()
        except Exception:
            pass
        self._log("[info] permissions saved.")

    # ============================= Scheduler tab =============================
    def _build_scheduler_tab(self):
        tab = QtWidgets.QWidget()
        self.tabs.addTab(tab, "Scheduler")
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        top = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Scheduled Actions")
        title.setObjectName("h1")
        top.addWidget(title)
        top.addStretch(1)
        self.sched_enabled_check = CheckBox("Scheduler enabled")
        self.sched_enabled_check.setChecked(bool(bot.SCHEDULER_CONFIG.get("enabled", False)))
        self.sched_enabled_check.stateChanged.connect(self._sched_toggle_enabled)
        top.addWidget(self.sched_enabled_check)
        layout.addLayout(top)

        self.sched_list = QtWidgets.QListWidget()
        layout.addWidget(self.sched_list, 1)

        add_row = QtWidgets.QHBoxLayout()
        self.sched_label_edit = QtWidgets.QLineEdit()
        self.sched_label_edit.setPlaceholderText("Label (e.g. 'Nightly revert')")
        add_row.addWidget(self.sched_label_edit, 2)
        self.sched_action_combo = QtWidgets.QComboBox()
        self.sched_action_combo.addItems(["revert", "restart"])
        add_row.addWidget(self.sched_action_combo)
        self.sched_hour_spin = QtWidgets.QSpinBox()
        self.sched_hour_spin.setRange(0, 23)
        add_row.addWidget(QtWidgets.QLabel("H"))
        add_row.addWidget(self.sched_hour_spin)
        self.sched_minute_spin = QtWidgets.QSpinBox()
        self.sched_minute_spin.setRange(0, 59)
        add_row.addWidget(QtWidgets.QLabel("M"))
        add_row.addWidget(self.sched_minute_spin)
        add_btn = QtWidgets.QPushButton("+ Add Task")
        add_btn.setObjectName("green")
        add_btn.clicked.connect(self._sched_add_task)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        days_row = QtWidgets.QHBoxLayout()
        days_row.addWidget(QtWidgets.QLabel("Days:"))
        self.sched_day_checks = []
        for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            cb = CheckBox(d)
            self.sched_day_checks.append(cb)
            days_row.addWidget(cb)
        days_row.addStretch(1)
        layout.addLayout(days_row)

        remove_btn = QtWidgets.QPushButton("Remove Selected")
        remove_btn.setObjectName("red")
        remove_btn.clicked.connect(self._sched_remove_task)
        layout.addWidget(remove_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self._sched_refresh_list()

    def _sched_toggle_enabled(self):
        bot.SCHEDULER_CONFIG["enabled"] = self.sched_enabled_check.isChecked()
        bot.save_scheduler_config()
        self._log(f"[info] scheduler {'enabled' if bot.SCHEDULER_CONFIG['enabled'] else 'disabled'}.")

    def _sched_refresh_list(self):
        self.sched_list.clear()
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for t in bot.SCHEDULER_CONFIG.get("tasks", []):
            days = ",".join(day_names[d] for d in t.get("days", []) if 0 <= d < 7)
            self.sched_list.addItem(
                f"{t.get('label', '(untitled)')} — {t.get('action')} @ "
                f"{t.get('hour', 0):02d}:{t.get('minute', 0):02d} [{days}]")

    def _sched_add_task(self):
        label = self.sched_label_edit.text().strip() or "(untitled)"
        days = [i for i, cb in enumerate(self.sched_day_checks) if cb.isChecked()]
        if not days:
            QtWidgets.QMessageBox.warning(self, "Scheduler", "Pick at least one day.")
            return
        task = {
            "id": f"task_{int(time.time() * 1000)}",
            "label": label,
            "action": self.sched_action_combo.currentText(),
            "days": days,
            "hour": self.sched_hour_spin.value(),
            "minute": self.sched_minute_spin.value(),
            "last_run": "",
        }
        bot.SCHEDULER_CONFIG.setdefault("tasks", []).append(task)
        bot.save_scheduler_config()
        self._sched_refresh_list()
        self.sched_label_edit.clear()
        self._log(f"[info] added scheduled task: {label}")

    def _sched_remove_task(self):
        row = self.sched_list.currentRow()
        tasks = bot.SCHEDULER_CONFIG.get("tasks", [])
        if row < 0 or row >= len(tasks):
            return
        removed = tasks.pop(row)
        bot.save_scheduler_config()
        self._sched_refresh_list()
        self._log(f"[info] removed scheduled task: {removed.get('label')}")

    # ============================= Live Chat panel =============================
    def _build_chat_panel(self):
        box = QtWidgets.QGroupBox("Live Chat")
        v = QtWidgets.QVBoxLayout(box)
        self._chat_viewer = QtWidgets.QTextEdit()
        self._chat_viewer.setReadOnly(True)
        self._chat_viewer.setStyleSheet("background:#0a0a14; font-family: Consolas, monospace; font-size: 12px;")
        v.addWidget(self._chat_viewer, 1)
        self._chat_autoscroll_check = CheckBox("Auto-scroll")
        self._chat_autoscroll_check.setChecked(True)
        v.addWidget(self._chat_autoscroll_check)
        return box

    def _append_chat(self, user, msg, is_owner=False, is_command=False, is_banned=False, is_mod=False, platform=""):
        """Thread-safe regardless of caller (some backend call sites call this
        directly from a background thread without wrapping in .after() themselves --
        this dispatches to the GUI thread internally either way)."""
        def _do():
            ts = time.strftime("%H:%M:%S")
            esc = QtGui.QTextDocumentFragment.fromPlainText(msg).toHtml()
            msg_html = QtGui.QTextDocumentFragment.fromPlainText(msg).toHtml()
            user_html = QtGui.QTextDocumentFragment.fromPlainText(user).toHtml()
            platform = (platform or "").lower()
            pmark = ""
            pcolor = self.TEXT
            if platform == "twitch":
                pmark = '<span style="color:#9146FF; font-weight:900;">T</span> '
            elif platform in ("youtube", "yt"):
                pmark = '<span style="color:#FF0000; font-weight:900;">▶</span> '
            if is_banned:
                name_html = f'<span style="color:{self.RED}; text-decoration: line-through;">{user}</span>'
            elif is_owner:
                name_html = f'<span style="color:{self.YELLOW}; font-weight:700;">★{user}</span>'
            elif is_mod:
                name_html = f'<span style="color:{self.SHIELD_BLUE}; font-weight:700;">🛡️{user}</span>'
            elif user in getattr(bot, "vip_users", set()):
                name_html = f'<span style="color:{self.ACCENT2}; font-weight:700;">♦{user}</span>'
            else:
                name_html = f'<span style="color:{self.TEXT};">{user}</span>'
            msg_color = self.ACCENT2 if is_command else self.TEXT
            line = (f'<span style="color:{self.TEXTDIM};">[{ts}]</span> {pmark}{name_html}'
                    f'<span style="color:{self.TEXTDIM};">: </span>'
                    f'<span style="color:{msg_color};">{msg}</span>')
            self._chat_viewer.append(line)
            if self._chat_viewer.document().blockCount() > 500:
                cursor = self._chat_viewer.textCursor()
                cursor.movePosition(cursor.MoveOperation.Start)
                cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor,
                                     self._chat_viewer.document().blockCount() - 500)
                cursor.removeSelectedText()
            if self._chat_autoscroll_check.isChecked():
                sb = self._chat_viewer.verticalScrollBar()
                sb.setValue(sb.maximum())
        self.after(0, _do)

    def _append_chat_system(self, msg):
        self._append_chat("[system]", msg, is_owner=False, is_command=False)

    # ============================= Placeholder tabs =============================
    def _build_backend_tab(self, name):
        config_map = {
            "OS Voting": ["PERMISSIONS_CONFIG"],
            "Appearance": [],
            "OBS": ["OBS_CONFIG"],
            "Statistics": [],
            "User Management": [],
            "Event Log": [],
            "Sound / TTS": ["SOUND_CONFIG"],
            "Real PC Control": ["REALPC_CONFIG"],
            "Reconnect": ["RECONNECT_CONFIG"],
            "Soundboard": ["soundboard_config"],
            "VNC / Web": ["VNC_CONFIG", "FLASK_CONFIG"],
            "Fun": ["fun_high_scores"],
            "MrTristinAI": ["MRTRISTINAI_CONFIG", "gemini_config"],
            "Command Builder": [],
            "YT Relay": ["YT_LOG_RELAY_CONFIG"],
            "Host Switch": ["HOST_SWITCH_CONFIG"],
        }
        if name == "OBS":
            tab = ObsTab(self)
        elif name in {"Statistics", "Appearance", "OS Voting", "User Management", "Event Log", "Command Builder"}:
            tab = FeatureTab(name, self)
        else:
            tab = BackendConfigTab(name, config_map.get(name, []), self)
        self.tabs.addTab(tab, name)

    # ============================= Theme =============================
    def _apply_theme(self, name):
        if name not in THEMES:
            return
        self._current_theme = name
        t = THEMES[name]
        self.BG, self.BG2, self.BG3 = t["BG"], t["BG2"], t["BG3"]
        self.ACCENT, self.ACCENT2 = t["ACCENT"], t["ACCENT2"]
        self.GREEN, self.RED, self.YELLOW = t["GREEN"], t["RED"], t["YELLOW"]
        self.TEXT, self.TEXTDIM = t["TEXT"], t["TEXTDIM"]
        self.SHIELD_BLUE = t["ACCENT"]
        self.setStyleSheet(_build_theme_stylesheet(name))
        _save_theme(name)
        self._set_feedback(f"Theme: {name}")

    def _on_theme_changed(self, name):
        self._apply_theme(name)

    def _build_settings_tab(self):
        tab = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        grp_theme = QtWidgets.QGroupBox("Theme")
        grp_theme_lay = QtWidgets.QFormLayout(grp_theme)
        self._theme_combo = QtWidgets.QComboBox()
        self._theme_combo.addItems(THEMES.keys())
        self._theme_combo.setCurrentText(self._current_theme)
        self._theme_combo.currentTextChanged.connect(self._on_theme_changed)
        grp_theme_lay.addRow("Interface Theme:", self._theme_combo)
        layout.addWidget(grp_theme)

        grp_info = QtWidgets.QGroupBox("System")
        info_lay = QtWidgets.QFormLayout(grp_info)
        info_lay.addRow("Python:", QtWidgets.QLabel(sys.version.split()[0]))
        info_lay.addRow("Qt:", QtWidgets.QLabel(QtCore.QT_VERSION_STR))
        info_lay.addRow("Platform:", QtWidgets.QLabel(sys.platform))
        layout.addWidget(grp_info)

        layout.addStretch()
        save_btn = QtWidgets.QPushButton("Save All Configs")
        save_btn.setObjectName("accent")
        save_btn.clicked.connect(self._save_all_configs)
        layout.addWidget(save_btn)
        self.tabs.addTab(tab, "Settings")

    def _save_all_configs(self):
        saved = []
        try:
            bot.save_streamerbot_config()
            saved.append("StreamerBot")
        except Exception:
            pass
        for attr_name, func_name in [
            ("MUSIC_CONFIG", "save_music_config"),
            ("VIDEO_CONFIG", "save_video_config"),
            ("PERMISSIONS_CONFIG", "save_permissions_config"),
            ("SCHEDULER_CONFIG", "save_scheduler_config"),
            ("OBS_CONFIG", "save_obs_config"),
            ("CUSTOM_COMMANDS", "save_custom_commands"),
        ]:
            try:
                func = getattr(bot, func_name, None)
                if func:
                    func()
                    saved.append(attr_name)
            except Exception:
                pass
        try:
            bot.save_appearance_config()
            saved.append("Appearance")
        except Exception:
            pass
        try:
            bot.save_os_voting_config()
            saved.append("OS_Voting")
        except Exception:
            pass
        try:
            bot.save_user_mgmt()
            saved.append("User_Mgmt")
        except Exception:
            pass
        self._set_feedback(f"Saved: {', '.join(saved)}")

    # ============================= System Tray =============================
    def _setup_qt_tray(self):
        if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            return
        self._tray_icon = QtWidgets.QSystemTrayIcon(self)
        icon = QtGui.QIcon()
        pixmap = QtGui.QPixmap(64, 64)
        pixmap.fill(QtGui.QColor(0, 0, 0, 0))
        p = QtGui.QPainter(pixmap)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        p.setBrush(QtGui.QColor(self.ACCENT))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(4, 4, 56, 56, 12, 12)
        p.setPen(QtGui.QColor("#ffffff"))
        font = p.font()
        font.setPixelSize(28)
        font.setBold(True)
        p.setFont(font)
        p.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "UB")
        p.end()
        icon.addPixmap(pixmap)
        self._tray_icon.setIcon(icon)
        self._tray_icon.setToolTip("UltraBot Control Panel")
        menu = QtWidgets.QMenu()
        show_action = menu.addAction("Show Window")
        show_action.triggered.connect(self._restore_from_tray)
        menu.addSeparator()
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self._force_quit)
        self._tray_icon.setContextMenu(menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.DoubleClick:
            self._restore_from_tray()

    def _restore_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _force_quit(self):
        bot.bot_stop_event.set()
        try:
            bot.stop_realpc_bot()
        except Exception:
            pass
        if self._tray_icon:
            self._tray_icon.hide()
        os._exit(0)

    # ============================= TPM Check =============================
    def _check_tpm_before_start(self, vmx_path):
        has_tpm, has_encryption = _detect_tpm_and_encryption(vmx_path)
        if not has_tpm:
            self._vm_encryption_password = ""
            return True
        if not has_encryption:
            self._vm_encryption_password = ""
            QtWidgets.QMessageBox.warning(
                self, "TPM Detected, No Encryption",
                "VM has vTPM enabled but encryption is not configured.\n"
                "The VM may not start correctly.")
            return True
        for attempt in range(5):
            password, ok = QtWidgets.QInputDialog.getText(
                self, "Encryption Password",
                f"VM requires encryption password (attempt {attempt + 1}/5):",
                QtWidgets.QLineEdit.EchoMode.Password)
            if not ok:
                self._vm_encryption_password = ""
                return False
            if _validate_encryption_password(vmx_path, password):
                self._vm_encryption_password = password
                return True
            QtWidgets.QMessageBox.warning(
                self, "Invalid Password",
                f"Wrong password. {4 - attempt} attempts remaining.")
        self._vm_encryption_password = ""
        return False

    # ============================= Auto-start =============================
    def _auto_start_bot(self):
        if self._auto_start and not self._bot_running:
            vmx = bot.VMX_PATH if hasattr(bot, "VMX_PATH") else ""
            if vmx:
                if not self._check_tpm_before_start(vmx):
                    return
            self._start_bot()

    # ============================= Close handling =============================
    def closeEvent(self, event):
        if self._bot_running:
            answer = QtWidgets.QMessageBox.question(
                self, "Close", "Minimize to system tray instead of closing?",
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No
                | QtWidgets.QMessageBox.StandardButton.Cancel,
                QtWidgets.QMessageBox.StandardButton.Yes)
            if answer == QtWidgets.QMessageBox.StandardButton.Yes:
                event.ignore()
                self.hide()
                if self._tray_icon:
                    self._tray_icon.showMessage(
                        "UltraBot",
                        "Bot is still running. Right-click the tray icon to exit.",
                        QtWidgets.QSystemTrayIcon.MessageIcon.Information, 2000)
                return
            elif answer == QtWidgets.QMessageBox.StandardButton.No:
                bot.bot_stop_event.set()
                try:
                    bot.stop_realpc_bot()
                except Exception:
                    pass
                if self._tray_icon:
                    self._tray_icon.hide()
                event.accept()
                os._exit(0)
                return
            else:
                event.ignore()
                return
        else:
            if self._tray_icon:
                self._tray_icon.hide()
            event.accept()

    def show_welcome_guide(self):
        return None


def _force_windows_11_dpi():
    try:
        os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
        if hasattr(QtWidgets.QApplication, "setHighDpiScaleFactorRoundingPolicy"):
            QtWidgets.QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except Exception:
        pass


def main():
    _force_windows_11_dpi()
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("UltraBot Control Panel")
    app.setApplicationDisplayName("UltraBot Control Panel")
    app.setStyle("Fusion")

    if bot is None:
        QtWidgets.QMessageBox.critical(
            None,
            "Backend unavailable",
            "The Qt frontend requires bot.py beside this file.\n\n"
            f"Import error: {_BOT_IMPORT_ERROR}",
        )
        return 1

    splash = GlassSplashScreen()
    splash.show()

    window = [None]

    def _finish_splash():
        try:
            w = UltraBotGUIQt(auto_start=True)
            window[0] = w
            w.show()
            # Activate the backend's existing continuous auto-update and local
            # file-edit hot-reload watchdogs for the PyQt frontend as well.
            # They are started once, after the GUI exists, so update dialogs and
            # relaunch state can use the current application context safely.
            running_names = {t.name for t in threading.enumerate()}
            if "autoupdate_watcher" not in running_names and hasattr(bot, "_autoupdate_watcher"):
                threading.Thread(target=bot._autoupdate_watcher, daemon=True,
                                 name="autoupdate_watcher").start()
            if "file_edit_watchdog" not in running_names and hasattr(bot, "_file_edit_watchdog"):
                threading.Thread(target=bot._file_edit_watchdog, daemon=True,
                                 name="file_edit_watchdog").start()
        except Exception as exc:
            splash.close()
            QtWidgets.QMessageBox.critical(
                None,
                "YouTubeChatUsesVM-Windows-VMware failed to start",
                f"The interface could not be created:\n\n{exc}\n\n"
                "Check the console or log for the full traceback.",
            )
            traceback.print_exc()
            raise SystemExit(1)
        splash.close()

    splash.set_on_done(_finish_splash)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())