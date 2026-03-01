import time
from models import GameState
from audio import AudioManager

class RaceEngineer:
    def __init__(self, state: GameState, audio: AudioManager):
        self.st = state
        self.audio = audio

    def update(self):
        st = self.st
        msgs = []
        
        # Rendszer ellenőrzés induláskor
        if time.time() - st.last_packet_time < 2:
            if not st.system_online_reported:
                msgs.append(f"Kapcsolat kész. Pálya: {st.track_name}.")
                st.system_online_reported = True
        
        if st.packet_count > 0:
            # 1. VERSENYESEMÉNYEK (PRIORITÁSOSAK)
            
            # Kék zászló - 5 másodpercenként ismétel, amíg kint van
            if st.trigger_blue_flag:
                if time.time() - st.last_blue_flag_time > 5:
                    self.audio.say("Kék zászló. Engedd el a gyorsabb autót.", priority=True)
                    st.last_blue_flag_time = time.time()
            
            # Safety Car / VSC állapotváltozás
            if st.safety_car_status != st.last_sc_status:
                if st.safety_car_status == 1: 
                    self.audio.say("Safety car a pályán. Tartsd a pozitív deltát.", priority=True)
                elif st.safety_car_status == 2: 
                    self.audio.say("Virtuális safety car elrendelve. Lassíts.", priority=True)
                else: 
                    self.audio.say("Zöld zászló, versenytempó.", priority=True)
                st.last_sc_status = st.safety_car_status

            # Normál események (mehetnek a listába)
            if st.trigger_warning:
                msgs.append(f"Figyelmeztetés: {st.last_warning_reason}.")
                st.trigger_warning = False
                
            if st.trigger_penalty:
                if st.last_penalty_type == 0:
                    msgs.append(f"Áthajtásos büntetést kaptál: {st.last_penalty_reason}. Három körön belül töltsd le!")
                elif st.last_penalty_type == 1:
                    msgs.append(f"Stop and go büntetést kaptál: {st.last_penalty_reason}. Három körön belül töltsd le!")
                elif st.last_penalty_time > 0:
                    msgs.append(f"{st.last_penalty_time} másodperces időbüntetés: {st.last_penalty_reason}.")
                else:
                    msgs.append(f"Büntetést kaptál: {st.last_penalty_reason}.")
                st.trigger_penalty = False

            # Áthajtásos emlékeztető a kör végén (3-as szektor)
            if st.pending_drive_through and st.current_sector == 2 and st.drive_through_reminder_lap != st.lap_number:
                msgs.append("Emlékeztető: Letöltendő áthajtásos büntetésed van. A kör végén gyere a boxba!")
                st.drive_through_reminder_lap = st.lap_number

            if st.trigger_fastest_lap:
                msgs.append("Leggyorsabb kör, lila szektorok.")
                st.trigger_fastest_lap = False

            # SC Delta figyelő (VSC/SC alatt)
            if st.safety_car_status in [1, 2]:
                if st.sc_delta < 0.0 and not st.sc_delta_reported:
                    msgs.append("Lassíts! Negatív a deltád, büntetést fogsz kapni!")
                    st.sc_delta_reported = True
                elif st.sc_delta > 0.2:
                    st.sc_delta_reported = False 

            # 2. SÉRÜLÉS ÉS KOPÁS
            if st.fw_damage >= 40 and not st.wing_damage_reported:
                msgs.append("Sérült az első szárny! Gyere a boxba cserélni!")
                st.wing_damage_reported = True
            elif st.fw_damage < 10: 
                st.wing_damage_reported = False 

            if st.rw_damage >= 20 and not st.rw_damage_reported:
                msgs.append("Sérült a hátsó szárny! Nehéz lesz az autó hátulja.")
                st.rw_damage_reported = True
            elif st.rw_damage < 10:
                st.rw_damage_reported = False

            # Defekt figyelés
            tyre_names = ["bal hátsó", "jobb hátsó", "bal első", "jobb első"]
            for i in range(4):
                if st.tyre_damage[i] >= 95:
                    st.puncture_counters[i] += 1
                    if st.puncture_counters[i] >= 3 and not st.puncture_reported[i]:
                        msgs.append(f"Defekt! Elment a {tyre_names[i]} gumi!")
                        st.puncture_reported[i] = True
                else:
                    st.puncture_counters[i] = 0
                    if st.tyre_damage[i] < 10: st.puncture_reported[i] = False

            # Kopás értesítések
            if st.max_tyre_wear >= 40.0 and not st.wear_40_reported:
                msgs.append("A gumik kopása elérte a 40 százalékot.")
                st.wear_40_reported = True
            if st.max_tyre_wear >= 60.0 and not st.wear_60_reported:
                msgs.append("Kritikus gumikopás, 60 százalék felett vagyunk!")
                st.wear_60_reported = True

            # GUMI HŐMÉRSÉKLET (Pálya vs Boxutca trükk)
            if st.pit_status == 0: # Csak kint a pályán figyelmeztet
                if st.tyre_temp_state != st.last_tyre_temp_state:
                    if st.tyre_temp_state == "cold":
                        msgs.append("Hidegek a gumik, alig van tapadás! Óvatosan a gázzal!")
                    elif st.tyre_temp_state == "hot":
                        msgs.append("Kritikusan forrók a gumik, azonnal hűtsd vissza őket!")
                    st.last_tyre_temp_state = st.tyre_temp_state
            else:
                # Amíg a boxban/garázsban vagy, "elfelejtjük" az állapotot, 
                # hogy kiérve a pályára rögtön érzékelje a váltást cold-ra.
                st.last_tyre_temp_state = "optimal"

            # 3. IDŐJÁRÁS ÉS STRATÉGIA
            if st.lap_number == 1 and not st.lap_1_weather_reported and st.lap_distance > 500:
                if st.forecasts:
                    t_max = st.total_laps * 1.5
                    has_rain = any(f.weather_type >= 3 or f.rain_percentage > 20 for f in st.forecasts)
                    if not has_rain: msgs.append("Jelentés: A futam végig száraz lesz.")
                    else: msgs.append("Jelentés: Eső várható a futam során, figyeljük a radart.")
                st.lap_1_weather_reported = True

            # Szektor 2 végi stratégiai jelentés
            if st.current_sector == 2 and not st.strategy_announced_this_lap and st.lap_number > 0:
                cur_rain = st.rain_intensity
                cur_tyre = st.current_tyre_compound
                
                # Egyszerűsített gumi-ajánló logika
                if cur_rain >= 0.60: st.ideal_tyre = "W"
                elif cur_rain >= 0.05: st.ideal_tyre = "I"
                else: st.ideal_tyre = "Slick"

                equipped_cat = "W" if cur_tyre == "W" else ("I" if cur_tyre == "I" else "Slick")
                
                if equipped_cat != st.ideal_tyre:
                    target_hu = "kék extrém" if st.ideal_tyre == "W" else ("zöld inter" if st.ideal_tyre == "I" else "száraz")
                    msgs.append(f"Taktikai javaslat: jöhetsz a boxba {target_hu} gumiért.")
                
                st.strategy_announced_this_lap = True
                
            if st.current_sector == 0: st.strategy_announced_this_lap = False

        # Összesített üzenetek bemondása (nem prioritásos tempóban)
        if msgs:
            final_speech = " ".join(msgs)
            self.audio.say(final_speech, priority=False)