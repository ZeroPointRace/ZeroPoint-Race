import socket
import struct
import threading
import time
from models import GameState, WeatherForecast
from config import PORT_UDP, HEADER_SIZE, F1_TRACKS

class TelemetryListener:
    def __init__(self, state: GameState):
        self.state = state
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try: self.sock.bind(('0.0.0.0', PORT_UDP))
        except Exception as e: self.state.error_msg = f"Port bind hiba: {e}"
        self.sock.settimeout(1.0)
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            try:
                data, _ = self.sock.recvfrom(2048)
                if len(data) < HEADER_SIZE: continue 
                
                packet_format = struct.unpack_from('<H', data, 0)[0]
                if packet_format not in [2023, 2024, 2025]: continue
                
                packet_id = struct.unpack_from('<B', data, 6)[0]
                idx = struct.unpack_from('<B', data, 27)[0]
                self.state.my_car_idx = idx
                
                if packet_id == 1: # Session
                    if len(data) < 156: continue 
                    self.state.current_weather = struct.unpack_from('<B', data, 29)[0]
                    self.state.total_laps = struct.unpack_from('<B', data, 32)[0]
                    self.state.track_length = struct.unpack_from('<H', data, 33)[0]
                    cw = self.state.current_weather
                    self.state.rain_intensity = 0.3 if cw == 3 else 0.7 if cw == 4 else 1.0 if cw == 5 else 0.0
                    self.state.track_name = F1_TRACKS.get(struct.unpack_from('<b', data, 36)[0], "Ismeretlen pálya")
                    self.state.safety_car_status = struct.unpack_from('<B', data, 153)[0]
                    
                    num = struct.unpack_from('<B', data, 155)[0]
                    if 0 < num <= 56 and len(data) >= 156 + (num * 8):
                        new_f = []
                        for i in range(num):
                            off = 156 + (i * 8)
                            _, t_off, w_t, _, _, _, _, rain_p = struct.unpack_from('<BBBbbbbB', data, off)
                            if rain_p <= 100: new_f.append(WeatherForecast(t_off, w_t, rain_p))
                        self.state.forecasts = new_f
                    else: self.state.forecasts = []
                
                elif packet_id == 2: # Lap Data
                    item_size = (len(data) - HEADER_SIZE) // 22
                    if item_size < 35: continue
                    for i in range(22):
                        off = HEADER_SIZE + (i * item_size)
                        self.state.drivers[i].is_me = (i == idx)
                        if i == idx:
                            self.state.last_lap_time_ms = struct.unpack_from('<I', data, off + 0)[0]
                            self.state.lap_distance = struct.unpack_from('<f', data, off + 18)[0]
                            self.state.car_position = struct.unpack_from('<B', data, off + 30)[0]
                            self.state.lap_number = struct.unpack_from('<B', data, off + 31)[0]
                            self.state.pit_status = struct.unpack_from('<B', data, off + 32)[0] # 0: Pálya, 1: Pit Lane, 2: Garázs
                            self.state.current_sector = struct.unpack_from('<B', data, off + 34)[0]
                            
                            current_pits = struct.unpack_from('<B', data, off + 33)[0]
                            if current_pits > self.state.drivers[i].pit_stops:
                                self.state.pending_drive_through = False
                                
                        self.state.drivers[i].delta_to_ahead = struct.unpack_from('<H', data, off + 14)[0] / 1000.0
                        self.state.drivers[i].position = struct.unpack_from('<B', data, off + 30)[0]
                        self.state.drivers[i].pit_stops = struct.unpack_from('<B', data, off + 33)[0]
                        self.state.drivers[i].penalties = struct.unpack_from('<B', data, off + 36)[0]
                        
                        if i == idx and item_size >= 43:
                            self.state.sc_delta = struct.unpack_from('<f', data, off + 26)[0]
                
                elif packet_id == 3: # Event
                    if len(data) < HEADER_SIZE + 4: continue
                    event_code = data[HEADER_SIZE:HEADER_SIZE+4]
                    if event_code == b'PENA' and len(data) >= HEADER_SIZE + 7:
                        pen_type = struct.unpack_from('<B', data, HEADER_SIZE + 4)[0]
                        inf = struct.unpack_from('<B', data, HEADER_SIZE + 5)[0]
                        veh_idx = struct.unpack_from('<B', data, HEADER_SIZE + 6)[0]
                        p_time = struct.unpack_from('<B', data, HEADER_SIZE + 8)[0] if len(data) >= HEADER_SIZE + 9 else 0
                        
                        if veh_idx == idx:
                            if inf in [3, 4, 5, 6]: reason = "ütközés"
                            elif inf in [7, 8, 9, 10, 50, 51, 52, 53, 54]: reason = "pályaelhagyás"
                            elif inf == 11: reason = "kék zászló figyelmen kívül hagyása"
                            elif inf == 17: reason = "boxutca gyorshajtás"
                            else: reason = "szabálytalanság"
                            
                            if pen_type == 5:
                                self.state.last_warning_reason = reason
                                self.state.trigger_warning = True
                            else:
                                self.state.last_penalty_reason = reason
                                self.state.last_penalty_time = p_time
                                self.state.last_penalty_type = pen_type
                                self.state.trigger_penalty = True
                                if pen_type in [0, 1]:
                                    self.state.pending_drive_through = True
                    elif event_code == b'FTLP' and len(data) >= HEADER_SIZE + 5: 
                        if struct.unpack_from('<B', data, HEADER_SIZE + 4)[0] == idx:
                            self.state.trigger_fastest_lap = True

                elif packet_id == 6: # Car Telemetry
                    item_size = (len(data) - HEADER_SIZE) // 22
                    if item_size < 38: continue
                    for i in range(22):
                        off = HEADER_SIZE + (i * item_size)
                        if i == idx:
                            # 34-es offset = Belső maghőmérséklet (Carcass Temp)
                            temps = struct.unpack_from('<BBBB', data, off + 34)
                            avg_temp = sum(temps) / 4.0
                            
                            tc = self.state.current_tyre_compound
                            if tc in ["S", "M", "H", "Ismeretlen"]:
                                if avg_temp < 80: self.state.tyre_temp_state = "cold"
                                elif avg_temp <= 100: self.state.tyre_temp_state = "optimal"
                                elif avg_temp <= 105: self.state.tyre_temp_state = "warm"
                                else: self.state.tyre_temp_state = "hot"
                            elif tc == "I":
                                if avg_temp < 65: self.state.tyre_temp_state = "cold"
                                elif avg_temp <= 80: self.state.tyre_temp_state = "optimal"
                                elif avg_temp <= 90: self.state.tyre_temp_state = "warm"
                                else: self.state.tyre_temp_state = "hot"
                            elif tc == "W":
                                if avg_temp < 50: self.state.tyre_temp_state = "cold"
                                elif avg_temp <= 70: self.state.tyre_temp_state = "optimal"
                                elif avg_temp <= 80: self.state.tyre_temp_state = "warm"
                                else: self.state.tyre_temp_state = "hot"

                elif packet_id == 7: # Car Status
                    item_size = (len(data) - HEADER_SIZE) // 22
                    if item_size < 29: continue
                    for i in range(22):
                        off = HEADER_SIZE + (i * item_size)
                        v_tyre = struct.unpack_from('<B', data, off + 26)[0]
                        new_c = {16:"S", 17:"M", 18:"H", 7:"I", 8:"W"}.get(v_tyre, "Ismeretlen")
                        self.state.drivers[i].tyre_compound = new_c
                        self.state.drivers[i].tyre_age = struct.unpack_from('<B', data, off + 27)[0]
                        if i == idx:
                            self.state.current_tyre_compound = new_c
                            self.state.my_tyre_age = self.state.drivers[i].tyre_age
                            
                            flag_status = struct.unpack_from('<b', data, off + 28)[0]
                            self.state.trigger_blue_flag = (flag_status == 2)

                elif packet_id == 10: # Car Damage
                    item_size = (len(data) - HEADER_SIZE) // 22
                    if item_size < 30: continue
                    for i in range(22):
                        off = HEADER_SIZE + (i * item_size)
                        if i == idx:
                            rl, rr, fl, fr = struct.unpack_from('<ffff', data, off)
                            self.state.max_tyre_wear = max(rl, rr, fl, fr)
                            
                            rl_dam, rr_dam, fl_dam, fr_dam = struct.unpack_from('<BBBB', data, off + 16)
                            self.state.tyre_damage = [rl_dam, rr_dam, fl_dam, fr_dam]
                            
                            fl_wing = struct.unpack_from('<B', data, off + 24)[0]
                            fr_wing = struct.unpack_from('<B', data, off + 25)[0]
                            self.state.fw_damage = max(fl_wing, fr_wing)
                            
                            self.state.rw_damage = struct.unpack_from('<B', data, off + 26)[0]
                            floor_dam = struct.unpack_from('<B', data, off + 27)[0]
                            sidepod_dam = struct.unpack_from('<B', data, off + 29)[0]
                            self.state.side_damage = max(floor_dam, sidepod_dam)
                
                elif packet_id == 12: # Tyre Sets (Garázs Adat)
                    if len(data) >= 30:
                        car_idx = struct.unpack_from('<B', data, 29)[0]
                        if car_idx == idx:
                            self.state.fresh_tyres.clear()
                            for i in range(13):
                                off = 30 + (i * 10)
                                if len(data) >= off + 10:
                                    comp = struct.unpack_from('<B', data, off + 0)[0]
                                    wear = struct.unpack_from('<B', data, off + 2)[0]
                                    avail = struct.unpack_from('<B', data, off + 3)[0]
                                    fitted = struct.unpack_from('<B', data, off + 8)[0]
                                    
                                    if avail == 1 and fitted == 0 and wear < 15:
                                        comp_name = {16:"S", 17:"M", 18:"H"}.get(comp)
                                        if comp_name: 
                                            self.state.fresh_tyres.add(comp_name)

                self.state.last_packet_time = time.time()
                self.state.packet_count += 1
                self.state.error_msg = ""
            except socket.timeout: pass
            except Exception as e: self.state.error_msg = f"Olvasási hiba: {e}"