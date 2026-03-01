# ZeroPoint-Race
Intelligent F1 Race Engineer &amp; Telemetry Dashboard for F1 23/24/25.
🌟 Key Features
1. Interactive Voice Engineer (Edge-TTS)
•	Natural Speech: Uses edge-tts technology (hu-HU-TamasNeural) for human-like communication.
•	Priority Messaging: Critical info (blue flags, safety cars, penalties) instantly interrupts regular updates.
•	System Reports: Automatic connection check and track identification upon startup.
2. Real-Time Telemetry Processing
•	Multi-Game Support: Recognizes UDP packet formats for F1 23
•	Damage & Wear: Monitors front/rear wing damage, floor status, and tire wear percentages.
•	Thermal Management: Alerts if tires are too cold (below 80°C) or critically hot (above 105°C).
3. Strategy & Weather Radar
•	60-Minute Forecast: Extracts detailed weather forecast data directly from the game.
•	Auto Tire Recommendation: Suggests switching to Inter or Wet tires based on rain intensity (on a 0.05-0.60+ scale).
•	Penalty Reminder: If you receive a Drive-Through penalty, the engineer reminds you to pit at the end of the lap.
🛠️ Technology Stack
•	Backend: Python 3.10+, aiohttp (web server), pygame (audio playback).
•	Frontend: Vue.js 3, Tailwind CSS, Phosphor Icons.
•	Data Transfer: UDP (from game, port: 20777), WebSocket (to frontend).
________________________________________
🚀 Installation & Usage
For Developers (Using Python)
1.	Install Python: Ensure Python 3.10 or newer is installed and added to your PATH.
2.	Install Dependencies:
Bash
pip install edge-tts pygame aiohttp
3.	Run: Execute python main.py.
4.	Access: Open the IP address shown in the console (default port: 8088) in your browser.
For Users (Standalone Executable)
•	Download the latest ZeroPointRace.exe from the Releases section.
•	Run the file (no Python installation required).
In-Game Settings
•	Navigate to Settings -> Telemetry Settings.
•	UDP Telemetry: ON
•	UDP Port: 20777
•	UDP Format: 2023
UDP Broadcast: Set to OFF (Crucial for console-to-PC communication).
UDP IP Address: Enter the local IP address of your PC (the one shown in the ZeroPoint Race console, e.g., 192.168.1.15).
UDP Send Rate: 20Hz or 30Hz.
________________________________________
☕ Support
If you enjoy this project and want to support its development:
https://buymeacoffee.com/zeropointrace
