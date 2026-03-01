import time
import logging
from aiohttp import web

from config import PORT_WEB, get_local_ip
from models import GameState
from audio import AudioManager
from telemetry import TelemetryListener
from strategy import RaceEngineer
from web import WebServer

logging.basicConfig(filename='f1_engineer_liga.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    print(f"[{time.strftime('%H:%M:%S')}] Rendszer indul... Kérlek várj.")
    print(f"[{time.strftime('%H:%M:%S')}] A Dashboard hamarosan elérhető lesz a böngésződben!")
    
    # Központi állapot inicializálása
    state = GameState()
    
    # Modulok példányosítása és összekötése
    audio = AudioManager()
    telemetry = TelemetryListener(state)
    engineer = RaceEngineer(state, audio)
    server = WebServer(state, audio, engineer)
    
    print(f"\n=======================================================")
    print(f" SIKERES INDÍTÁS (MODULARIZÁLT VERZIÓ)! ")
    print(f" Nyisd meg a böngésződet a PC-n, mobilon vagy tableten:")
    print(f" CÍM: http://{get_local_ip()}:{PORT_WEB}")
    print(f"=======================================================\n")
    
    # Webszerver indítása (ez blokkolja a főszálat)
    web.run_app(server.app, host='0.0.0.0', port=PORT_WEB, print=None)