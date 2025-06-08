import sys
import json
import requests
import urllib3
import time
import asyncio
from threading import Thread
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QLabel, QPushButton, QCheckBox, QComboBox,
                             QScrollArea, QGridLayout, QFrame, QMessageBox, QLineEdit,
                             QTextEdit, QTabWidget, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QObject
from PyQt5.QtGui import QPixmap, QFont, QPalette, QColor, QIcon
from lcu_driver import Connector
import os
import time
from GUI import LeagueAssistantApp,load_cached_data,resource_path
# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)




def main():
    app = QApplication(sys.argv) 
    if not LeagueAssistantApp.is_league_running():
        print("League of Legends client is not running. Please start the client first.")
        QMessageBox.critical(None, "League Not Running", "League of Legends client is not running.\nStart the game first.")
        return

    
    # Load cached champion data immediately for faster startup
    cached_data = load_cached_data()
    app.setWindowIcon(QIcon(resource_path("pngegg.ico")))
    
    window = LeagueAssistantApp()
    
    if cached_data:
        window.champion_select_widget.update_champions_data(cached_data)
        window.status_label.setText(f"Ready - Loaded {len(cached_data)} champions (cached)")
    
    window.show()
    sys.exit(app.exec_())
if __name__ == "__main__":
    main()