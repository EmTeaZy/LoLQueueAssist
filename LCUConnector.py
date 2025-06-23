import requests
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
import json

PICKS_BANS_FILE = "picks_bans.json"
ROLES = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]

class LCUConnector(QObject):
    """Handles League Client connection and automation"""
    status_changed = pyqtSignal(bool)
    game_event = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.connector = Connector()
        self.summoner_id = None
        self.champions_map = {}
        self.picks_bans = {role: {"picks": [], "bans": []} for role in ROLES}
        self.current_role = "TOP"
        self.pick_number = 0
        self.ban_number = 0
        self.auto_accept_enabled = False
        self.auto_select_enabled = False
        self.pick_in_progress = False
        
        # State variables
        self.am_i_assigned = False
        self.am_i_banning = False
        self.am_i_picking = False
        self.in_game = False
        self.phase = ''
        self.action_id = None
        
        # Load picks and bans on initialization
        self.load_picks_and_bans()
        self.setup_connector()
    
    def load_picks_and_bans(self):
        """Load picks and bans from files"""
        try:
            if os.path.exists(PICKS_BANS_FILE):
                with open(PICKS_BANS_FILE, "r", encoding="utf-8") as f:
                    self.picks_bans = json.load(f)
            else:
                for role in ROLES:
                    self.picks_bans[role]["picks"] = []
                    self.picks_bans[role]["bans"] = []
            self.game_event.emit(f"Loaded picks and bans from {PICKS_BANS_FILE}")
        except Exception as e:
            self.game_event.emit(f"Error loading picks/bans: {str(e)}")
            self.picks_bans = {role: {"picks": [], "bans": []} for role in ROLES}
    
    def save_picks_and_bans(self):
        try:
            with open(PICKS_BANS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.picks_bans, f, ensure_ascii=False, indent=2)
            self.game_event.emit(f"Saved picks and bans to {PICKS_BANS_FILE}")
        except Exception as e:
            self.game_event.emit(f"Error saving picks/bans: {str(e)}")
    
    def setup_connector(self):
        """Setup LCU connector events"""
        @self.connector.ready
        async def connect(connection):
            try:
                temp_champions_map = {}
                summoner = await connection.request('get', '/lol-summoner/v1/current-summoner')
                summoner_to_json = await summoner.json()
                self.summoner_id = summoner_to_json['summonerId']
                
                champion_list = await connection.request('get', f'/lol-champions/v1/inventories/{self.summoner_id}/champions-minimal')
                champion_list_to_json = await champion_list.json()
                
                for i in range(len(champion_list_to_json)):
                    temp_champions_map.update({champion_list_to_json[i]['name']: champion_list_to_json[i]['id']})
                
                self.champions_map = temp_champions_map
                self.status_changed.emit(True)
                self.game_event.emit('LCU API is ready to be used.')
                
                # Reload picks and bans to ensure they're current
                self.load_picks_and_bans()
                
            except Exception as e:
                self.game_event.emit(f'Error connecting to LCU: {str(e)}')
                self.status_changed.emit(False)

        @self.connector.ws.register('/lol-matchmaking/v1/ready-check', event_types=('UPDATE',))
        async def ready_check_changed(connection, event):
            if self.auto_accept_enabled and event.data['state'] == 'InProgress' and event.data['playerResponse'] == 'None':
                await connection.request('post', '/lol-matchmaking/v1/ready-check/accept', data={})
                self.game_event.emit('Auto-accepted queue!')

        @self.connector.ws.register('/lol-champ-select/v1/session', event_types=('CREATE', 'UPDATE',))
        async def champ_select_changed(connection, event):
            
            have_i_prepicked = False
            lobby_phase = event.data['timer']['phase']
            print(f"Lobby phase: {lobby_phase}, Current phase: {self.phase}")
            
            local_player_cell_id = event.data['localPlayerCellId']
            assigned_role = None
            for teammate in event.data['myTeam']:
                if teammate['cellId'] == local_player_cell_id:
                    assigned_role = teammate.get('assignedPosition', 'TOP').upper()
                    break
            if assigned_role not in ROLES:
                assigned_role = 'TOP'
            self.current_role = assigned_role
            picks = self.picks_bans.get(assigned_role, {}).get('picks', [])
            bans = self.picks_bans.get(assigned_role, {}).get('bans', [])
            self.picks = picks.copy()
            self.bans = bans.copy()
            
            if lobby_phase not in ['PLANNING', 'BAN_PICK', 'FINALIZATION'] or not event.data.get("actions"):
                self.pick_number = 0
                self.ban_number = 0
                self.pick_in_progress = False
                self.ban_in_progress = False
                self.am_i_picking = False
                self.am_i_banning = False
                self.am_i_assigned = False
                self.in_game = False
                self.phase = ''
                self.action_id = None
                self.game_event.emit("Champ Select exited (cancelled/quit) — state reset.")
                return  
            # Check if assigned to position
            for teammate in event.data['myTeam']:
                if teammate['cellId'] == local_player_cell_id:
                    self.am_i_assigned = True
            
            # Check current action
            for action in event.data['actions']:
                for actionArr in action:
                    if actionArr['actorCellId'] == local_player_cell_id and actionArr['isInProgress'] == True:
                        self.phase = actionArr['type']
                        self.action_id = actionArr['id']
                        if self.phase == 'ban':
                            self.am_i_banning = actionArr['isInProgress']
                        if self.phase == 'pick':
                            self.am_i_picking = actionArr['isInProgress']
            
            if not self.auto_select_enabled:
                return
            
            
            # Auto ban
            if self.phase == 'ban' and lobby_phase == 'BAN_PICK' and self.am_i_banning and self.bans:
                try:
                    if self.ban_number < len(self.bans):
                        champion_name = self.bans[self.ban_number]
                        if champion_name in self.champions_map:
                            await connection.request('patch', '/lol-champ-select/v1/session/actions/%d' % self.action_id,
                                                   data={"championId": self.champions_map[champion_name], "completed": True})
                            self.game_event.emit(f'Auto-banned: {champion_name}')
                            self.ban_number += 1
                            self.am_i_banning = False
                except Exception as e:
                    self.game_event.emit(f'Failed to ban {champion_name}: {str(e)}')
                    self.ban_number += 1
                    if self.ban_number >= len(self.bans):
                        self.ban_number = 0
            
            # Auto pick
            if self.phase == 'pick' and lobby_phase == 'BAN_PICK' and self.am_i_picking and self.picks and not self.pick_in_progress:
                self.pick_in_progress = True  # start pick session
                try:
                    picked = False
                    for i in range(self.pick_number, len(self.picks)):
                        champion_name = self.picks[i]
                        try:
                            if champion_name in self.champions_map:
                                champion_id = self.champions_map[champion_name]
                                response = await connection.request(
                                    'patch',
                                    f'/lol-champ-select/v1/session/actions/{self.action_id}',
                                    data={"championId": champion_id, "completed": True}
                                )

                                # Check if the response was successful
                                if response.status == 204:
                                    self.game_event.emit(f'Auto-picked: {champion_name}')
                                    self.pick_number = i + 1
                                    self.am_i_picking = False
                                    picked = True
                                    break  
                                else:
                                    self.game_event.emit(f"Pick failed for {champion_name}, trying next...")

                        except Exception as e:
                            self.game_event.emit(f'Failed to pick {champion_name}: {str(e)}')
                        
                        await asyncio.sleep(1.5)  

                    if not picked:
                        self.game_event.emit("No valid champions could be picked from the list.")
                        self.pick_number = 0  

                except Exception as e:
                    self.game_event.emit(f'Error during picking phase: {str(e)}')
                finally:
                    self.pick_in_progress = False
            
            # Pre-pick (hover)
            if lobby_phase == 'PLANNING' and not have_i_prepicked and self.picks:
                try:
                    first_pick = self.picks[0] if self.picks else 'Teemo'
                    if first_pick in self.champions_map:
                        await connection.request('patch', '/lol-champ-select/v1/session/actions/%d' % self.action_id,
                                               data={"championId": self.champions_map[first_pick], "completed": False})
                        self.game_event.emit(f'Pre-picked: {first_pick}')
                        have_i_prepicked = True
                except Exception as e:
                    self.game_event.emit(f'Failed to pre-pick: {str(e)}')
            
            # Game detection
            if lobby_phase == 'FINALIZATION' and not self.in_game:
                try:
                    request_game_data = requests.get('https://127.0.0.1:2999/liveclientdata/allgamedata', verify=False)
                    game_data = request_game_data.json()['gameData']['gameTime']
                    if game_data > 0:
                        self.game_event.emit("Game started!")
                        self.in_game = True
                except Exception:
                    pass

        @self.connector.close
        async def disconnect(_):
            self.status_changed.emit(False)
            self.game_event.emit('The client has been closed!')
            
            # Reset only game state variables, NOT picks and bans
            self.am_i_assigned = False
            self.am_i_picking = False
            self.am_i_banning = False
            self.in_game = False
            self.phase = ''
            self.action_id = None
            
            # Reset counters but keep picks and bans persistent
            self.pick_number = 0
            self.ban_number = 0
            
            # Log that picks and bans are preserved
            self.game_event.emit(f'Picks and bans preserved: {len(self.picks)} picks, {len(self.bans)} bans')
            
    def start_connector(self):
        """Start the LCU connector in a separate thread"""
        def run_connector():
            try:
                self.connector.start()
            except Exception as e:
                self.game_event.emit(f'Failed to start connector: {str(e)}')
                self.status_changed.emit(False)
        
        thread = Thread(target=run_connector, daemon=True)
        thread.start()
    
    def update_picks_and_bans(self, picks_bans_dict, _=None):
        """Update the picks and bans lists"""
        self.picks_bans = picks_bans_dict.copy()
        self.save_picks_and_bans()
        self.pick_number = 0
        self.ban_number = 0
        self.game_event.emit(f'Updated picks and bans for all roles.')
    
    def set_auto_accept(self, enabled):
        """Enable/disable auto accept"""
        self.auto_accept_enabled = enabled
        status = "enabled" if enabled else "disabled"
        self.game_event.emit(f'Auto-accept {status}')
    
    def set_auto_select(self, enabled):
        """Enable/disable auto select"""
        self.auto_select_enabled = enabled
        status = "enabled" if enabled else "disabled"
        self.game_event.emit(f'Auto-select {status}')