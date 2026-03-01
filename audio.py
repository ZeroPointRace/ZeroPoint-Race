import threading
import queue
import asyncio
import tempfile
import os
import time
import logging
import edge_tts
import pygame

class AudioManager:
    def __init__(self):
        try: pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
        except: pygame.mixer.init()
        self.q = queue.Queue()
        threading.Thread(target=self._worker, daemon=True).start()

    def say(self, text, priority=False):
        if priority:
            with self.q.mutex: self.q.queue.clear()
            if pygame.mixer.music.get_busy(): pygame.mixer.music.stop()
        self.q.put(text)

    async def _generate_voice(self, text, filename):
        communicate = edge_tts.Communicate(text, "hu-HU-TamasNeural", rate="+10%")
        await communicate.save(filename)

    def _worker(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while True:
            text = self.q.get()
            try:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
                    fname = tf.name
                loop.run_until_complete(self._generate_voice(text, fname))
                if os.path.exists(fname):
                    pygame.mixer.music.load(fname)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy(): time.sleep(0.1)
                    pygame.mixer.music.unload()
                    time.sleep(0.2)
                    os.remove(fname)
            except Exception as e:
                logging.error(f"Hang hiba: {e}")
                if 'fname' in locals() and os.path.exists(fname):
                    try: os.remove(fname)
                    except: pass
            finally:
                self.q.task_done()