import json
import os
import time
import asyncio
from aiohttp import web
from models import GameState
from audio import AudioManager
from strategy import RaceEngineer
from config import get_local_ip, TYRE_COLORS, WEATHER_TYPES

class WebServer:
    def __init__(self, state: GameState, audio: AudioManager, engineer: RaceEngineer):
        self.state = state
        self.audio = audio
        self.engineer = engineer
        self.websockets = set()
        self.app = web.Application()
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/ws', self.handle_websocket)
        self.app.on_startup.append(self.start_background_tasks)

    async def handle_index(self, request):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        index_path = os.path.join(base_dir, 'index.html')
        if not os.path.exists(index_path):
            index_path = os.path.join(os.getcwd(), 'index.html')
        if os.path.exists(index_path):
            return web.FileResponse(index_path)
        else:
            return web.Response(text="<h1>HIBA: index.html nem található!</h1>", content_type='text/html', charset='utf-8')

    async def handle_websocket(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.websockets.add(ws)
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data.get("action") == "test_radio":
                        self.audio.say("Rádió teszt. A rendszer üzemkész.", priority=True)
        finally:
            self.websockets.remove(ws)
        return ws

    def _build_ui_payload(self) -> dict:
        st = self.state
        is_conn = time.time() - st.last_packet_time < 2
        
        act = sorted([d for d in st.drivers.values() if d.position > 0], key=lambda x: x.position)
        lb = []
        midx = next((i for i, d in enumerate(act) if d.is_me), -1)
        if midx != -1:
            disp = act[max(0, midx-3):min(len(act), midx+4)]
            my_d = st.drivers[st.my_car_idx]
            for d in disp:
                lb.append({
                    "pos": d.position, "car": "TE" if d.is_me else f"V{d.car_idx}",
                    "is_me": d.is_me,
                    "delta": f"{d.delta_to_ahead:.1f}s" if d.position > 1 else "Leader",
                    "delta_color": "text-amber-400" if d.is_me else ("text-red-400" if d.position < my_d.position else "text-green-400"),
                    "tyre": d.tyre_compound, "tyre_color": TYRE_COLORS.get(d.tyre_compound, "#fff"),
                    "age": d.tyre_age, "pits": d.pit_stops, "pen": f"{d.penalties}s" if d.penalties > 0 else "-"
                })

        grid = []
        tot = st.total_laps if st.total_laps > 0 else 1
        ltime = st.last_lap_time_ms / 1000.0
        if ltime < 30: ltime = 90.0
        
        for lap in range(1, tot + 1):
            l_ahead = lap - st.lap_number
            w_type = 0
            
            if l_ahead < 0: 
                pic, tcol, rp = WEATHER_TYPES[0][1], TYRE_COLORS["Ismeretlen"], 0
                w_type = 0
            elif not st.forecasts:
                cw = st.current_weather
                tcol = TYRE_COLORS["W"] if cw >= 4 else TYRE_COLORS["I"] if cw == 3 else TYRE_COLORS["M"]
                rp = 100 if cw == 5 else 80 if cw == 4 else 40 if cw == 3 else 10 if cw == 2 else 0
                pic = WEATHER_TYPES.get(cw, ("?", "☀️"))[1]
                w_type = cw
            else:
                m_ahead = (l_ahead * ltime) / 60.0
                points = [(0, st.current_weather, int(st.rain_intensity*100))]
                for f in st.forecasts:
                    points.append((f.time_offset, f.weather_type, f.rain_percentage))
                
                closest = min(points, key=lambda p: abs(p[0] - m_ahead))
                
                cw = closest[1]
                rp = closest[2]
                w_type = cw
                
                tcol = TYRE_COLORS["W"] if cw >= 4 else TYRE_COLORS["I"] if (cw == 3 or rp > 40) else TYRE_COLORS["M"]
                pic = WEATHER_TYPES.get(cw, ("?", "☀️"))[1]
            
            p_col = "#6366f1" if rp > 70 else "#3b82f6" if rp > 30 else "#60a5fa" if rp > 0 else "#334155"
            bg = f"rgba({int(tcol[1:3], 16)}, {int(tcol[3:5], 16)}, {int(tcol[5:7], 16)}, 0.2)" if lap == st.lap_number else "transparent"
            
            grid.append({
                "lap": lap, "icon": pic, "w_type": w_type, "progress": rp, "progress_color": p_col, "bg_color": bg,
                "text_color": "text-white" if lap == st.lap_number else "text-slate-400" if lap < st.lap_number else "text-slate-200",
                "is_current": lap == st.lap_number
            })

        fc_info = "Játékból kapott előrejelzés: NINCS (Pillanatnyi adatok)" if not st.forecasts else f"Játékból kapott előrejelzés: {', '.join([str(f.time_offset) for f in st.forecasts])} perces adatok"

        return {
            "ip_address": get_local_ip(),
            "track_name": st.track_name,
            "lap_info": f"Kör: {st.lap_number} / {st.total_laps}",
            "is_connected": is_conn,
            "connection_status": f"F1 Kapcsolat OK ({st.packet_count} csomag)" if is_conn else "Várakozás a játékra...",
            "forecast_info": fc_info,
            "leaderboard": lb,
            "strategy_grid": grid,
            "error_msg": st.error_msg,
            "car_health": { "wing": st.fw_damage, "wear": st.max_tyre_wear, "temp_state": st.tyre_temp_state }
        }

    async def broadcast_loop(self):
        while True:
            await asyncio.sleep(0.5)
            self.engineer.update()  # <-- Itt hívjuk meg a mérnöki logikát!
            if self.websockets:
                msg = json.dumps(self._build_ui_payload())
                for ws in list(self.websockets):
                    try: await ws.send_str(msg)
                    except: pass

    async def start_background_tasks(self, app):
        app['broadcaster'] = asyncio.create_task(self.broadcast_loop())