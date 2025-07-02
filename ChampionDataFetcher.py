import json
import requests
from threading import Thread
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QLabel, QPushButton, QCheckBox, QComboBox,
                             QScrollArea, QGridLayout, QFrame, QMessageBox, QLineEdit,
                             QTextEdit, QTabWidget, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QObject
from PyQt5.QtGui import QPixmap, QFont, QPalette, QColor, QIcon
from lcu_driver import Connector
import os
import sys
import time


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

CACHE_FILE = resource_path("champion_cache.json")
ICON_CACHE_DIR = resource_path("champion_icons")



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
            else:
                print(f"Failed to download {name}: HTTP {response.status_code}")
        except Exception as e:
            print(f"Failed to download icon for {name}: {e}")
    return path


class ChampionDataFetcher(QThread):
    data_fetched = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def run(self):
        cached_data = load_cached_data()
        if cached_data:
            self.data_fetched.emit(cached_data)
        else:
            try:
                version_url = "https://ddragon.leagueoflegends.com/api/versions.json"
                response = requests.get(version_url, timeout=10)
                versions = response.json()
                latest_version = versions[0]

                base_url = "https://ddragon.leagueoflegends.com/cdn"
                champions_url = f"{base_url}/{latest_version}/data/en_US/champion.json"
                response = requests.get(champions_url, timeout=10)
                champion_data = response.json()

                champions = {}
                for champ_key, champ_data in champion_data['data'].items():
                    champ_name = champ_data['name']
                    image_url = f"{base_url}/{latest_version}/img/champion/{champ_data['image']['full']}"
                    champions[champ_name] = {
                        'id': champ_data['id'],
                        'key': champ_data['key'],
                        'name': champ_name,
                        'title': champ_data['title'],
                        'image_url': image_url
                    }

                    # Ensure icon is cached
                    download_icon(champ_name, image_url)

                save_cached_data(champions)
                self.data_fetched.emit(champions)

            except Exception as e:
                print(f"Error fetching data: {e}")
                self.error_occurred.emit(f"Failed to fetch and load champion data: {str(e)}")