import json
import requests
import time
from threading import Thread
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QLabel, QPushButton, QCheckBox, QComboBox,
                             QScrollArea, QGridLayout, QFrame, QMessageBox, QLineEdit,
                             QTextEdit, QTabWidget, QSplitter, QStackedWidget, QSpacerItem,
                             QSizePolicy)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QObject, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPixmap, QFont, QPalette, QColor, QIcon, QPainter, QBrush, QLinearGradient
from lcu_driver import Connector
import os
import psutil
import threading
import time
from LCUConnector import LCUConnector
from ChampionDataFetcher import ChampionDataFetcher
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

CACHE_FILE = resource_path("champion_cache.json")
ICON_CACHE_DIR = resource_path("champion_icons")
PICKS_FILE = resource_path("picks.txt")
BANS_FILE = resource_path("bans.txt")
PICKS_BANS_FILE = resource_path("picks_bans.json")
ROLES = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "SUPPORT"]

def load_cached_data():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load cache: {e}")
    return None

def save_cached_data(data):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def download_icon(name, url):
    os.makedirs(ICON_CACHE_DIR, exist_ok=True)
    path = os.path.join(ICON_CACHE_DIR, f"{name}.png")
    if not os.path.exists(path):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                with open(path, "wb") as f:
                    f.write(response.content)
        except Exception as e:
            print(f"Failed to download icon for {name}: {e}")
    return path


class ModernCard(QFrame):
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("modernCard")
        self.title = title
        self.init_ui()
        
    def init_ui(self):
        self.setFrameStyle(QFrame.NoFrame)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        if self.title:
            title_label = QLabel(self.title)
            title_label.setObjectName("cardTitle")
            layout.addWidget(title_label)
            
        self.content_layout = layout
        self.setLayout(layout)
        
    def add_widget(self, widget):
        self.content_layout.addWidget(widget)


class StatusIndicator(QWidget):
    def __init__(self):
        super().__init__()
        self.connected = False
        self.setFixedSize(12, 12)
        
    def set_connected(self, connected):
        self.connected = connected
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        color = QColor("#10B981") if self.connected else QColor("#EF4444")
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 12, 12)


class ConnectionStatusWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        self.status_indicator = StatusIndicator()
        
        self.status_label = QLabel("League Client")
        self.status_label.setObjectName("statusLabel")
        
        self.connection_text = QLabel("Disconnected")
        self.connection_text.setObjectName("connectionText")
        
        layout.addWidget(self.status_indicator)
        layout.addWidget(self.status_label)
        layout.addWidget(self.connection_text)
        layout.addStretch()
        
        self.setLayout(layout)
        
    def update_status(self, connected):
        self.status_indicator.set_connected(connected)
        self.connection_text.setText("Connected" if connected else "Disconnected")
        self.connection_text.setProperty("connected", connected)
        self.connection_text.style().polish(self.connection_text)


class ModernToggle(QWidget):
    toggled = pyqtSignal(bool)
    
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.text = text
        self.checked = False
        self.setObjectName("modernToggleWidget")
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # Text label
        self.text_label = QLabel(self.text)
        self.text_label.setObjectName("toggleText")
        
        # Toggle switch
        self.toggle_switch = ToggleSwitch()
        self.toggle_switch.toggled.connect(self.on_toggle)
        
        layout.addWidget(self.text_label)
        layout.addStretch()
        layout.addWidget(self.toggle_switch)
        
        self.setLayout(layout)
        
    def on_toggle(self, checked):
        self.checked = checked
        self.toggled.emit(checked)
        
    def setChecked(self, checked):
        self.checked = checked
        self.toggle_switch.setChecked(checked)
        
    def isChecked(self):
        return self.checked


class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.checked = False
        self.setFixedSize(50, 24)
        self.setObjectName("toggleSwitch")
        
        # Animation for smooth toggle
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        
    def setChecked(self, checked):
        if self.checked != checked:
            self.checked = checked
            self.update()
            
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.checked = not self.checked
            self.toggled.emit(self.checked)
            self.update()
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background track
        track_color = QColor("#3B82F6" if self.checked else "#475569")
        painter.setBrush(QBrush(track_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 50, 24, 12, 12)
        
        # Toggle thumb
        thumb_x = 26 if self.checked else 2
        thumb_color = QColor("#FFFFFF")
        painter.setBrush(QBrush(thumb_color))
        painter.drawEllipse(thumb_x, 2, 20, 20)


class ModernComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("modernCombo")


class AutomationControlWidget(QWidget):
    auto_accept_changed = pyqtSignal(bool)
    auto_select_changed = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # Auto Accept Card
        accept_card = ModernCard("Queue Accept")
        
        self.auto_accept_toggle = ModernToggle("Auto Accept Queue")
        self.auto_accept_toggle.toggled.connect(self.on_auto_accept_changed)
        accept_card.add_widget(self.auto_accept_toggle)
        
        # Auto Select Card
        select_card = ModernCard("Champion Selection")
        
        self.auto_select_toggle = ModernToggle("Auto Pick/Ban Champions")
        self.auto_select_toggle.toggled.connect(self.on_auto_select_changed)
        select_card.add_widget(self.auto_select_toggle)
        
        layout.addWidget(accept_card)
        layout.addWidget(select_card)
        layout.addStretch()
        
        self.setLayout(layout)
        
    def on_auto_accept_changed(self, enabled):
        self.auto_accept_changed.emit(enabled)
        
    def on_auto_select_changed(self, enabled):
        self.auto_select_changed.emit(enabled)


class NotificationsWidget(QWidget):
    notifications_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        notifications_card = ModernCard("Notifications")
        
        self.enable_notifications_toggle = ModernToggle("Enable WhatsApp Notifications")
        self.enable_notifications_toggle.toggled.connect(self.save_settings)
        notifications_card.add_widget(self.enable_notifications_toggle)
        
        layout.addWidget(notifications_card)
        self.setLayout(layout)

    def load_settings(self):
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    config = json.load(f)
                    whatsapp_config = config.get("whatsapp_notifications", {})
                    self.enable_notifications_toggle.setChecked(whatsapp_config.get("enabled", False))
            else:
                self.enable_notifications_toggle.setChecked(False)
        except Exception as e:
            print(f"Error loading notification settings: {e}")

    def save_settings(self):
        config = {}
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    config = json.load(f)
        except Exception as e:
            print(f"Error reading config file: {e}")

        whatsapp_config = config.get("whatsapp_notifications", {})
        whatsapp_config["enabled"] = self.enable_notifications_toggle.isChecked()
        config["whatsapp_notifications"] = whatsapp_config

        try:
            with open("config.json", "w") as f:
                json.dump(config, f, indent=4)
            if "whatsapp_notifications" in config:
                self.notifications_updated.emit(config["whatsapp_notifications"])
        except Exception as e:
            print(f"Error saving notification settings: {e}")


class ChampionItem(QWidget):
    def __init__(self, champion_name, icon_path=None, index=1):
        super().__init__()
        self.champion_name = champion_name
        self.icon_path = icon_path
        self.index = index
        
        
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)
        
        # Index number
        index_label = QLabel(f"{self.index}")
        index_label.setObjectName("championIndex")
        index_label.setFixedSize(20, 20)
        index_label.setAlignment(Qt.AlignCenter)
        
        # Champion icon
        icon_label = QLabel()
        if self.icon_path and os.path.exists(self.icon_path):
            pixmap = QPixmap(self.icon_path).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(pixmap)
        else:
            # Placeholder icon
            icon_label.setFixedSize(32, 32)
            icon_label.setStyleSheet("background: rgba(148, 163, 184, 0.3); border-radius: 16px;")
        
        # Champion name
        name_label = QLabel(self.champion_name)
        name_label.setObjectName("championName")
        
        layout.addWidget(index_label)
        layout.addWidget(icon_label)
        layout.addWidget(name_label)
        layout.addStretch()
        
        self.setLayout(layout)


class ChampionList(QWidget):
    def __init__(self, title, placeholder_text):
        super().__init__()
        self.title = title
        self.placeholder_text = placeholder_text
        self.selected_champions = []
        self.champion_icons = {}
        self.on_clear = None  # Callback for clear event
        self.init_ui()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Header
        header_layout = QHBoxLayout()
        title_label = QLabel(self.title)
        title_label.setObjectName("sectionTitle")
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("clearButton")
        self.clear_btn.clicked.connect(self.handle_clear)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.clear_btn)
        layout.addLayout(header_layout)
        
        # Combo box
        self.combo = ModernComboBox()
        self.combo.addItem(self.placeholder_text)
        layout.addWidget(self.combo)
        
        scroll_area = QScrollArea()
        scroll_area.setObjectName("championScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll_area.setMinimumHeight(200)  
        
        self.list_widget = QWidget()
       
        self.list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(5, 5, 5, 5)
        self.list_layout.setSpacing(8)
        
        # Placeholder label
        self.placeholder_label = QLabel(f"No {self.title.lower()} selected")
        self.placeholder_label.setObjectName("placeholderText")
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.list_layout.addWidget(self.placeholder_label)
        
        scroll_area.setWidget(self.list_widget)
        
        layout.addWidget(scroll_area, 1)  # stretch=1 makes it expand
        
        self.setLayout(layout)
        
    def handle_clear(self):
        if self.on_clear:
            self.on_clear()
        else:
            self.clear_list()

    def set_champion_icons(self, champion_icons):
        self.champion_icons = champion_icons
        self.update_display()
        
    def clear_list(self):
        self.selected_champions.clear()
        self.update_display()
        
    def update_display(self):
        # Clear existing items
        for i in reversed(range(self.list_layout.count())):
            child = self.list_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        if self.selected_champions:
            self.placeholder_label.hide()
            for i, champion in enumerate(self.selected_champions):
                icon_path = None
                if champion in self.champion_icons:
                    # Get the icon path from the champion icons
                    icon_path = os.path.join(ICON_CACHE_DIR, f"{champion}.png")
                
                champion_item = ChampionItem(champion, icon_path, i + 1)
                champion_item.setObjectName("championItem")
                self.list_layout.addWidget(champion_item)
            
            # Add stretch at the end
            self.list_layout.addStretch()
        else:
            self.placeholder_label.setText(f"No {self.title.lower()} selected")
            self.list_layout.addWidget(self.placeholder_label)
            self.placeholder_label.show()


class ChampionSelectWidget(QWidget):
    picks_bans_updated = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.champions_data = {}
        self.champion_icons = {}
        self.selected_role = "TOP"
        self.picks_bans = {role: {"picks": [], "bans": []} for role in ROLES}
        self.init_ui()
        QTimer.singleShot(0, self.load_saved_data)
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # Champion selection card
        card = ModernCard("Champion Selection")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(30)
        self.picks_widget = ChampionList("Priority Picks", "Select champion to pick...")
        self.picks_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.picks_widget.combo.currentTextChanged.connect(self.on_pick_selected)
        self.picks_widget.on_clear = self.on_clear_picks
        columns_layout.addWidget(self.picks_widget, 1)
        self.bans_widget = ChampionList("Priority Bans", "Select champion to ban...")
        self.bans_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.bans_widget.combo.currentTextChanged.connect(self.on_ban_selected)
        self.bans_widget.on_clear = self.on_clear_bans
        columns_layout.addWidget(self.bans_widget, 1)
        card.content_layout.addLayout(columns_layout, 1)
        layout.addWidget(card, 1)
        self.setLayout(layout)

    def on_role_changed(self, role):
        self.selected_role = role
        self.update_displays()
        self.save_last_role()

    def load_saved_data(self):
        try:
            if os.path.exists(PICKS_BANS_FILE):
                with open(PICKS_BANS_FILE, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                
                needs_saving = False
                if "UTILITY" in loaded_data and "SUPPORT" not in loaded_data:
                    loaded_data["SUPPORT"] = loaded_data.pop("UTILITY")
                    needs_saving = True
                
                self.picks_bans = loaded_data
                
                if needs_saving:
                    self.save_all_roles()
            else:
                # Migrate from old files if present
                picks, bans = [], []
                if os.path.exists("picks.txt"):
                    with open("picks.txt", "r", encoding="utf-8") as f:
                        picks = [line.strip() for line in f.readlines() if line.strip()]
                if os.path.exists("bans.txt"):
                    with open("bans.txt", "r", encoding="utf-8") as f:
                        bans = [line.strip() for line in f.readlines() if line.strip()]
                for role in ROLES:
                    self.picks_bans[role]["picks"] = picks.copy()
                    self.picks_bans[role]["bans"] = bans.copy()
                self.save_all_roles()
            self.update_displays()
            self.picks_bans_updated.emit(self.picks_bans)
        except Exception as e:
            print(f"Error loading saved data: {e}")

    def save_last_role(self):
        config = {}
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    config = json.load(f)
        except Exception as e:
            print(f"Error reading config file: {e}")

        config["last_selected_role"] = self.selected_role

        try:
            with open("config.json", "w") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Error saving last role: {e}")

    def save_all_roles(self):
        try:
            with open(PICKS_BANS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.picks_bans, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error writing to {PICKS_BANS_FILE}: {e}")

    def update_displays(self):
        picks = self.picks_bans[self.selected_role]["picks"]
        bans = self.picks_bans[self.selected_role]["bans"]
        self.picks_widget.selected_champions = picks.copy()
        self.bans_widget.selected_champions = bans.copy()
        self.picks_widget.update_display()
        self.bans_widget.update_display()

    def on_pick_selected(self, champion_name):
        if champion_name and not champion_name.startswith("Select champion"):
            picks = self.picks_bans[self.selected_role]["picks"]
            if champion_name not in picks:
                picks.append(champion_name)
                self.save_all_roles()
                self.update_displays()
                self.picks_bans_updated.emit(self.picks_bans)
            self.picks_widget.combo.setCurrentIndex(0)

    def on_ban_selected(self, champion_name):
        if champion_name and not champion_name.startswith("Select champion"):
            bans = self.picks_bans[self.selected_role]["bans"]
            if champion_name not in bans:
                bans.append(champion_name)
                self.save_all_roles()
                self.update_displays()
                self.picks_bans_updated.emit(self.picks_bans)
            self.bans_widget.combo.setCurrentIndex(0)

    def update_champions_data(self, champions_data):
        self.champions_data = champions_data
        self.download_champion_icons()
        self.populate_comboboxes()
        self.picks_widget.set_champion_icons(self.champion_icons)
        self.bans_widget.set_champion_icons(self.champion_icons)

    def download_champion_icons(self):
        for name, data in self.champions_data.items():
            path = download_icon(name, data['image_url'])
            if os.path.exists(path):
                pixmap = QPixmap(path).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.champion_icons[name] = pixmap
                
    def populate_comboboxes(self):
        champion_names = sorted(list(self.champions_data.keys()))
        
        self.picks_widget.combo.clear()
        self.picks_widget.combo.addItem("Select champion to pick...")
        for name in champion_names:
            icon_path = os.path.join(ICON_CACHE_DIR, f"{name}.png")
            if os.path.exists(icon_path):
                icon = QIcon(QPixmap(icon_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.picks_widget.combo.addItem(icon, name)
            else:
                self.picks_widget.combo.addItem(name)
        
        self.bans_widget.combo.clear()
        self.bans_widget.combo.addItem("Select champion to ban...")
        for name in champion_names:
            icon_path = os.path.join(ICON_CACHE_DIR, f"{name}.png")
            if os.path.exists(icon_path):
                icon = QIcon(QPixmap(icon_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.bans_widget.combo.addItem(icon, name)
            else:
                self.bans_widget.combo.addItem(name)

    def on_clear_picks(self):
        self.picks_bans[self.selected_role]["picks"] = []
        self.save_all_roles()
        self.update_displays()
        self.picks_bans_updated.emit(self.picks_bans)

    def on_clear_bans(self):
        self.picks_bans[self.selected_role]["bans"] = []
        self.save_all_roles()
        self.update_displays()
        self.picks_bans_updated.emit(self.picks_bans)


class InitializationManager(QObject):
    status_updated = pyqtSignal(str)
    initialization_finished = pyqtSignal()

    def __init__(self, lcu_connector, champion_fetcher):
        super().__init__()
        self.lcu_connector = lcu_connector
        self.champion_fetcher = champion_fetcher
        self.tasks_finished = threading.Event()

    def run(self):
        thread = Thread(target=self._run_all, daemon=True)
        thread.start()

    def _run_all(self):
        champion_thread = Thread(target=self._init_champions, daemon=True)
        notification_thread = Thread(target=self._init_notifications, daemon=True)

        champion_thread.start()
        notification_thread.start()

        champion_thread.join()
        notification_thread.join()

        self.initialization_finished.emit()

    def _init_champions(self):
        self.status_updated.emit("Initializing champions...")
        self.champion_fetcher.run()

    def _init_notifications(self):
        self.status_updated.emit("Initializing notification system...")
        self.lcu_connector.init_notification_system()


class LeagueAssistantApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.lcu_connector = LCUConnector()
        self.champion_fetcher = ChampionDataFetcher()
        self.init_ui()
        self.apply_modern_styles()
        self.setup_connections()
        self.start_initialization()
        
        
        # Start LCU connector
        self.lcu_connector.start_connector()
        
        # Monitor League client
        self.league_monitor_thread = threading.Thread(target=self.monitor_league_process, daemon=True)
        self.league_monitor_thread.start()

    def monitor_league_process(self):
        while True:
            if not self.is_league_running():
                print("League of Legends client closed. Exiting application...")
                QTimer.singleShot(0, self.close)
                break
            time.sleep(5)

    @staticmethod
    def is_league_running():
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == 'LeagueClientUx.exe':
                return True
        return False

    def init_ui(self):
        self.setWindowTitle("Queue Assist")
        self.setGeometry(100, 100, 900, 700)
        self.setMinimumSize(800, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(20)
        
        # Header with connection status
        header_layout = QHBoxLayout()
        
        # App title
        title_label = QLabel("League Queue Assist")
        title_label.setObjectName("appTitle")
        
        self.connection_widget = ConnectionStatusWidget()
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.connection_widget)
        
        main_layout.addLayout(header_layout)
        
        # Content area
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setSpacing(30)
        
        # Left sidebar - Automation controls
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(300)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        
        self.automation_widget = AutomationControlWidget()
        sidebar_layout.addWidget(self.automation_widget)

        self.notifications_widget = NotificationsWidget()
        sidebar_layout.addWidget(self.notifications_widget)
        sidebar_layout.addStretch()
        
        # Right main area - Champion selection tabs
        self.tabs = QTabWidget()
        self.tabs.setObjectName("roleTabs")
        self.champion_select_widgets = []

        for role in ROLES:
            champion_select_widget = ChampionSelectWidget()
            self.tabs.addTab(champion_select_widget, role)
            self.champion_select_widgets.append(champion_select_widget)
        
        content_layout.addWidget(sidebar)
        content_layout.addWidget(self.tabs, 1)
        
        main_layout.addWidget(content_widget)
        
        # Status bar
        self.status_label = QLabel("Initializing...")
        self.status_label.setObjectName("statusBar")
        main_layout.addWidget(self.status_label)
        
        central_widget.setLayout(main_layout)

    def apply_modern_styles(self):
        """Apply modern, minimal styling"""
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0F172A, stop:1 #1E293B);
                color: #F8FAFC;
            }
            
            QWidget {
                background: transparent;
                color: #F8FAFC;
                font-family: 'Century Gothic';
            }
            
            #appTitle {
                font-size: 28px;
                font-weight: 600;
                color: #F8FAFC;
                margin-bottom: 5px;
            }
            
            #statusLabel {
                font-size: 14px;
                font-weight: 500;
                color: #94A3B8;
            }
            
            #connectionText {
                font-size: 14px;
                font-weight: 500;
                color: #EF4444;
            }
            
            #connectionText[connected="true"] {
                color: #10B981;
            }
            
            #modernCard {
                background: rgba(30, 41, 59, 0.8);
                border: 1px solid rgba(148, 163, 184, 0.1);
                border-radius: 12px;
            }
            
            #cardTitle {
                font-size: 18px;
                font-weight: 600;
                color: #F8FAFC;
                margin-bottom: 10px;
            }
            
            #sectionTitle {
                font-size: 14px;
                font-weight: 600;
                color: #F8FAFC;
            }
            
            #modernToggleWidget {
                background: transparent;
                padding: 8px 0px;
            }
            
            #toggleText {
                font-size: 14px;
                color: #E2E8F0;
                font-weight: 500;
            }
            
            #toggleSwitch {
                background: transparent;
            }
            
            #championScrollArea {
                background: rgba(51, 65, 85, 0.5);
                border: 1px solid rgba(148, 163, 184, 0.1);
                border-radius: 8px;
            }
            
            #championScrollArea QScrollBar:vertical {
                background: rgba(71, 85, 105, 0.3);
                width: 8px;
                border-radius: 4px;
                margin: 2px;
            }
            
            #championScrollArea QScrollBar::handle:vertical {
                background: rgba(148, 163, 184, 0.5);
                border-radius: 4px;
                min-height: 20px;
            }
            
            #championScrollArea QScrollBar::handle:vertical:hover {
                background: rgba(148, 163, 184, 0.7);
            }
            
            #championItem {
                background: rgba(30, 41, 59, 0.6);
                border: 1px solid rgba(148, 163, 184, 0.1);
                border-radius: 6px;
                margin: 2px 0px;
            }
            
            #championItem:hover {
                background: rgba(30, 41, 59, 0.8);
                border-color: rgba(59, 130, 246, 0.3);
            }
            
            #championIndex {
                background: rgba(59, 130, 246, 0.8);
                color: white;
                border-radius: 10px;
                font-size: 11px;
                font-weight: 600;
            }
            
            #championName {
                font-size: 13px;
                color: #F8FAFC;
                font-weight: 500;
            }
            
            #placeholderText {
                color: #94A3B8;
                font-size: 13px;
                font-style: italic;
                padding: 20px;
            }
            
            #modernCombo {
                background: rgba(51, 65, 85, 0.8);
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 14px;
                color: #F8FAFC;
                min-height: 20px;
            }
            
            #modernCombo:hover {
                border-color: rgba(59, 130, 246, 0.5);
            }
            
            #modernCombo:focus {
                border-color: #3B82F6;
                outline: none;
            }
            
            #modernCombo::drop-down {
                border: none;
                width: 20px;
            }
            
            #modernCombo::down-arrow {
                image: none;
                border: 2px solid #94A3B8;
                border-top: none;
                border-right: none;
                width: 6px;
                height: 6px;
                
                margin-right: 8px;
            }
            
            #modernCombo QAbstractItemView {
                background: rgba(30, 41, 59, 0.95);
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 8px;
                selection-background-color: rgba(59, 130, 246, 0.3);
                color: #F8FAFC;
                padding: 4px;
            }
            
            #championsList {
                background: rgba(51, 65, 85, 0.5);
                border: 1px solid rgba(148, 163, 184, 0.1);
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                color: #E2E8F0;
                line-height: 1.4;
            }
            
            #clearButton {
                background: rgba(239, 68, 68, 0.1);
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 500;
                color: #F87171;
            }
            
            #clearButton:hover {
                background: rgba(239, 68, 68, 0.2);
                border-color: rgba(239, 68, 68, 0.5);
            }
            
            #clearButton:pressed {
                background: rgba(239, 68, 68, 0.3);
            }
            
            #sidebar {
                background: rgba(15, 23, 42, 0.6);
                border-radius: 12px;
                border: 1px solid rgba(148, 163, 184, 0.1);
                padding: 20px;
            }
            
            #statusBar {
                background: rgba(30, 41, 59, 0.6);
                border: 1px solid rgba(148, 163, 184, 0.1);
                border-radius: 8px;
                padding: 10px 15px;
                font-size: 13px;
                color: #94A3B8;
            }
           
           QTabWidget::pane {
               border: 1px solid rgba(148, 163, 184, 0.1);
               border-top: none;
               border-radius: 0 0 12px 12px;
               background: rgba(30, 41, 59, 0.8);
           }

           QTabBar::tab {
               background: transparent;
               border: 1px solid rgba(148, 163, 184, 0.1);
               border-bottom: none;
               padding: 10px 25px;
               font-size: 14px;
               font-weight: 600;
               color: #94A3B8;
               border-top-left-radius: 8px;
               border-top-right-radius: 8px;
               margin-right: 2px;
           }

           QTabBar::tab:hover {
               background: rgba(51, 65, 85, 0.5);
               color: #E2E8F0;
           }

           QTabBar::tab:selected {
               background: rgba(30, 41, 59, 0.8);
               border-color: rgba(148, 163, 184, 0.1);
               color: #F8FAFC;
           }
        """)
        
    def setup_connections(self):
        """Setup signal connections between components"""
        # LCU connector signals
        self.lcu_connector.status_changed.connect(self.connection_widget.update_status)
        
        # Automation control signals
        self.automation_widget.auto_accept_changed.connect(self.lcu_connector.set_auto_accept)
        self.automation_widget.auto_select_changed.connect(self.lcu_connector.set_auto_select)
        
        # Champion select signals
        for widget in self.champion_select_widgets:
            widget.picks_bans_updated.connect(self.lcu_connector.update_picks_and_bans)
        self.notifications_widget.notifications_updated.connect(self.lcu_connector.update_notifications_config)
        
        # Tab logic
        self.tabs.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index):
        champion_select_widget = self.tabs.widget(index)
        if champion_select_widget:
            role = self.tabs.tabText(index)
            champion_select_widget.on_role_changed(role)

    def start_initialization(self):
        self.init_manager = InitializationManager(self.lcu_connector, self.champion_fetcher)
        self.init_manager.status_updated.connect(self.status_label.setText)
        self.init_manager.initialization_finished.connect(self.on_initialization_finished)
        
        self.champion_fetcher.data_fetched.connect(self.on_champion_data_received)
        self.champion_fetcher.error_occurred.connect(self.on_champion_data_error)
        
        self.init_manager.run()

    def on_champion_data_received(self, champions_data):
        for widget in self.champion_select_widgets:
            widget.update_champions_data(champions_data)
        
        # Set initial role for the first tab
        if self.champion_select_widgets:
            self.on_tab_changed(self.tabs.currentIndex())
        
    def on_initialization_finished(self):
        self.status_label.setText("Ready")

    def on_champion_data_error(self, error_message):
        self.status_label.setText(f"Error: {error_message}")
        QMessageBox.warning(self, "Error", error_message)
        
    def closeEvent(self, event):
        """Handle application close"""
        try:
            self.lcu_connector.connector.stop()
        except:
            pass
        event.accept()


if __name__ == "__main__":
    app = QApplication([])
    app.setFont(QFont("Century Gothic"))
    window = LeagueAssistantApp()
    window.show()
    app.exec_()