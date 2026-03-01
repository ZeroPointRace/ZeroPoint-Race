import socket

PORT_UDP = 20777
PORT_WEB = 8088 
HEADER_SIZE = 29

# Bővített F1 24/25 pálya adatbázis
F1_TRACKS = {
    0: "Melbourne", 1: "Paul Ricard", 2: "Sanghaj", 3: "Szahír",
    4: "Barcelona", 5: "Monaco", 6: "Montreal", 7: "Silverstone",
    8: "Hockenheim", 9: "Hungaroring", 10: "Spa", 11: "Monza",
    12: "Szingapúr", 13: "Suzuka", 14: "Abu Dhabi", 15: "Austin", 16: "Interlagos",
    17: "Spielberg", 18: "Szocsi", 19: "Mexikóváros", 20: "Baku",
    21: "Imola", 22: "Zandvoort", 26: "Zandvoort", 27: "Imola",
    29: "Dzsidda", 30: "Miami", 31: "Las Vegas", 32: "Katár"
}

WEATHER_TYPES = {
    0: ("Tiszta ég", "☀️"), 1: ("Enyhén felhős", "🌤️"), 2: ("Borult", "☁️"), 
    3: ("Gyenge eső", "🌦️"), 4: ("Szakadó eső", "🌧️"), 5: ("Vihar", "⛈️")
}

TYRE_COLORS = { "S": "#ef4444", "M": "#f59e0b", "H": "#f8fafc", "I": "#22c55e", "W": "#3b82f6", "Ismeretlen": "#64748b" }

def get_local_ip() -> str:
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except: pass
    if not ips: return "127.0.0.1"
    preferred = [ip for ip in ips if ip.startswith("192.168.")]
    return preferred[0] if preferred else list(ips)[0]