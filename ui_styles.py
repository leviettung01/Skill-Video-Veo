"""
ui_styles.py -- Centralized QSS Stylesheets & Color Constants
================================================================
Tach rieng toan bo phan stylesheet/mau sac ra khoi grok_video_tool.py
de de dang chinh sua giao dien ma khong anh huong den logic.

Usage:
    from ui_styles import APP_STYLESHEET, C, style_btn
"""


class C:
    """Color constants."""
    PRIMARY        = "#7c3aed"
    PRIMARY_DARK   = "#6d28d9"
    PRIMARY_LIGHT  = "#a78bfa"
    PRIMARY_BG     = "#ede9fe"
    ACCENT_BLUE    = "#0ea5e9"
    ACCENT_TEAL    = "#06b6d4"
    ACCENT_GREEN   = "#16a34a"
    ACCENT_RED     = "#ef4444"
    ACCENT_AMBER   = "#f59e0b"
    BG             = "#ffffff"
    BG_SOFT        = "#f8fafc"
    BG_MUTED       = "#f1f5f9"
    BORDER         = "#e2e8f0"
    BORDER_FOCUS   = "#a78bfa"
    TEXT_MAIN      = "#0f172a"
    TEXT_BODY      = "#1e293b"
    TEXT_MUTED     = "#64748b"
    TEXT_LIGHT     = "#94a3b8"
    STATUS_WAIT    = ("#64748b", "#f1f5f9")
    STATUS_GEN     = ("#d97706", "#fef3c7")
    STATUS_IMG     = ("#0284c7", "#e0f2fe")
    STATUS_DONE    = ("#16a34a", "#dcfce7")
    STATUS_ERROR   = ("#dc2626", "#fee2e2")
    SIDEBAR_BG     = "#f8fafc"
    SIDEBAR_BORDER = "#e2e8f0"
    SIDEBAR_HOVER  = "#ede9fe"
    SIDEBAR_ACTIVE = "#7c3aed"


APP_STYLESHEET = """
QMainWindow { background-color: #ffffff; }
QWidget { font-family: "Segoe UI", sans-serif; color: #1e293b; }
QFrame#sidebar { background-color: #f8fafc; border-right: 1px solid #e2e8f0; }
QFrame#card { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; }
QFrame#card:hover { border-color: #a78bfa; }
QLineEdit, QTextEdit {
    background-color: #ffffff; border: 1px solid #e2e8f0;
    border-radius: 6px; padding: 6px; color: #0f172a;
}
QLineEdit:focus, QTextEdit:focus { border: 1px solid #a78bfa; }
QComboBox {
    background-color: #ffffff; border: 1px solid #e2e8f0;
    border-radius: 6px; padding: 6px; padding-right: 24px; color: #0f172a;
}
QComboBox::drop-down {
    subcontrol-origin: padding; subcontrol-position: top right;
    width: 20px; border-left-width: 0px;
    border-top-right-radius: 6px; border-bottom-right-radius: 6px;
}
QComboBox::down-arrow {
    image: none; border-top: 5px solid #64748b;
    border-left: 4px solid transparent; border-right: 4px solid transparent;
    width: 0; height: 0; margin-right: 8px;
}
QComboBox QAbstractItemView, QComboBox QListView {
    background-color: #ffffff; border: 1px solid #e2e8f0;
    border-radius: 6px; selection-background-color: #ede9fe;
    selection-color: #7c3aed; outline: none;
}
QScrollBar:vertical {
    border: none; background: #f1f5f9; width: 8px; border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #e2e8f0; border-radius: 4px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #94a3b8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar:horizontal {
    border: none; background: #f1f5f9; height: 8px; border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #e2e8f0; border-radius: 4px; min-width: 30px;
}
QPushButton#accent_btn {
    background-color: #7c3aed; color: white; border: none;
    border-radius: 8px; padding: 8px 18px; font-weight: bold; font-size: 13px;
}
QPushButton#accent_btn:hover { background-color: #6d28d9; }
QPushButton#accent_btn:disabled { background-color: #94a3b8; }
QPushButton#normal_btn {
    background-color: #f1f5f9; color: #64748b;
    border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 14px;
}
QPushButton#normal_btn:hover { background-color: #e2e8f0; }
QPushButton#danger_btn {
    background-color: #ef4444; color: white; border: none;
    border-radius: 6px; padding: 6px 12px; font-weight: bold;
}
QPushButton#danger_btn:hover { background-color: #dc2626; }
QPushButton#nav_btn {
    background-color: transparent; color: #64748b; border: none;
    border-radius: 8px; padding: 10px 14px; text-align: left; font-size: 13px;
}
QPushButton#nav_btn:hover { background-color: #ede9fe; color: #7c3aed; }
QPushButton#nav_btn_active {
    background-color: #ede9fe; color: #7c3aed; border: none;
    border-radius: 8px; padding: 10px 14px; text-align: left;
    font-size: 13px; font-weight: bold;
}
QProgressBar {
    border: none; border-radius: 5px; background: #f1f5f9;
    height: 6px; text-align: center;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7c3aed, stop:1 #0ea5e9);
    border-radius: 5px;
}
QTabWidget::pane {
    border: 1px solid #e2e8f0; border-radius: 8px; background: #ffffff;
}
QTabBar::tab {
    background: #f1f5f9; border: 1px solid #e2e8f0; border-bottom: none;
    padding: 6px 16px; border-top-left-radius: 6px; border-top-right-radius: 6px;
    color: #64748b;
}
QTabBar::tab:selected { background: #ffffff; color: #7c3aed; font-weight: bold; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 2px solid #e2e8f0; border-radius: 4px; background: #ffffff;
}
QCheckBox::indicator:checked { background-color: #7c3aed; border-color: #7c3aed; }
QToolTip {
    background-color: #0f172a; color: white; border: none;
    border-radius: 4px; padding: 4px 8px; font-size: 11px;
}
QGroupBox {
    border: 1px solid #e2e8f0; border-radius: 8px; margin-top: 8px;
    padding: 10px; font-weight: bold; color: #7c3aed;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }
QFrame#sb_card { background-color: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 12px; }
QFrame#account_row { background-color: #f1f5f9; border-radius: 6px; padding: 4px; }
QFrame#section_card {
    background-color: #ffffff; border: 1px solid #e2e8f0;
    border-radius: 8px; margin-bottom: 8px;
}
"""


def style_btn(bg: str, hover: str, text: str = "white",
              radius: int = 6, bold: bool = True, font_size: int = 12) -> str:
    weight = "bold" if bold else "normal"
    return (
        f"QPushButton {{ background-color: {bg}; color: {text}; border: none; "
        f"border-radius: {radius}px; padding: 6px 14px; font-weight: {weight}; "
        f"font-size: {font_size}px; }}"
        f"QPushButton:hover {{ background-color: {hover}; }}"
        f"QPushButton:disabled {{ background-color: #f1f5f9; color: #94a3b8; }}"
    )


def style_icon_btn(size: int = 28) -> str:
    return (
        f"QPushButton {{ background: transparent; border: none; "
        f"border-radius: {size // 2}px; padding: 2px; }}"
        f"QPushButton:hover {{ background: #f1f5f9; }}"
    )


def style_tag(bg: str, text_color: str) -> str:
    return (
        f"background: {bg}; color: {text_color}; "
        f"border-radius: 6px; padding: 2px 8px; "
        f"font-size: 10px; font-weight: bold;"
    )


def style_label_title(size: int = 14, color: str = "#0f172a", bold: bool = True) -> str:
    weight = "bold" if bold else "normal"
    return f"font-size: {size}px; font-weight: {weight}; color: {color};"


def style_label_sub(color: str = "#64748b", size: int = 11) -> str:
    return f"font-size: {size}px; color: {color};"


SB_STATUS_COLORS = {
    "waiting":    ("#64748b", "#f1f5f9"),
    "queued":     ("#64748b", "#f1f5f9"),
    "scripting":  ("#7c3aed", "#ede9fe"),
    "generating": ("#d97706", "#fef3c7"),
    "img_done":   ("#0284c7", "#e0f2fe"),
    "vid_gen":    ("#d97706", "#fef9c3"),
    "assembling": ("#0284c7", "#e0f2fe"),
    "done":       ("#16a34a", "#dcfce7"),
    "failed":     ("#dc2626", "#fee2e2"),
    "error":      ("#dc2626", "#fee2e2"),
}

SB_STATUS_LABELS = {
    "waiting":    "Cho",
    "queued":     "Hang cho",
    "scripting":  "Viet kich ban",
    "generating": "Dang xu ly",
    "img_done":   "Anh xong",
    "vid_gen":    "Dung video",
    "assembling": "Noi video",
    "done":       "Hoan thanh",
    "failed":     "Loi",
    "error":      "Loi",
}
