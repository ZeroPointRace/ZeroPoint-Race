from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class WeatherForecast:
    time_offset: int 
    weather_type: int 
    rain_percentage: int

@dataclass
class DriverData:
    position: int = 0
    car_idx: int = 0
    is_me: bool = False
    delta_to_ahead: float = 0.0
    penalties: int = 0
    pit_stops: int = 0
    tyre_compound: str = "Ismeretlen"
    tyre_age: int = 0

@dataclass
class GameState:
    packet_count: int = 0
    last_packet_time: float = 0.0
    track_name: str = "Pálya keresése..."
    track_length: int = 0
    lap_distance: float = 0.0
    
    lap_number: int = 0
    total_laps: int = 1
    last_lap_time_ms: int = 0
    car_position: int = 0
    current_sector: int = 0
    pit_status: int = 0
    current_tyre_compound: str = "Ismeretlen"
    
    current_weather: int = 0
    rain_intensity: float = 0.0 
    forecasts: List[WeatherForecast] = field(default_factory=list)
    
    drivers: Dict[int, DriverData] = field(default_factory=lambda: {i: DriverData(car_idx=i) for i in range(22)})
    my_car_idx: int = 0
    
    # AUTÓ ÁLLAPOT VÁLTOZÓK
    fw_damage: int = 0
    rw_damage: int = 0
    side_damage: int = 0
    max_tyre_wear: float = 0.0
    my_tyre_age: int = 0
    tyre_damage: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    tyre_temp_state: str = "optimal"
    last_tyre_temp_state: str = "optimal"
    
    # AGRESSZÍV CSOMAG VÁLTOZÓK
    sc_delta: float = 0.0
    sc_delta_reported: bool = False
    ideal_tyre: str = "Slick"
    target_tyre: str = ""
    pit_call_count: int = 0
    puncture_counters: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    
    safety_car_status: int = 0
    last_sc_status: int = 0
    trigger_blue_flag: bool = False
    trigger_penalty: bool = False
    last_penalty_reason: str = ""
    last_penalty_time: int = 0
    last_penalty_type: int = 0
    pending_drive_through: bool = False
    drive_through_reminder_lap: int = -1
    trigger_warning: bool = False
    last_warning_reason: str = ""
    trigger_fastest_lap: bool = False
    
    strategy_announced_this_lap: bool = False
    lap_1_weather_reported: bool = False
    system_online_reported: bool = False
    
    # HANG RIASZTÁS FLAGEK
    wing_damage_reported: bool = False
    rw_damage_reported: bool = False
    side_damage_reported: bool = False
    wear_40_reported: bool = False
    wear_60_reported: bool = False
    wear_prediction_reported: bool = False
    puncture_reported: List[bool] = field(default_factory=lambda: [False, False, False, False])
    radar_rain_warning_issued: bool = False
    radar_dry_warning_issued: bool = False
    
    last_blue_flag_time: float = 0.0
    error_msg: str = ""