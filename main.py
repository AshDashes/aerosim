import pygame
import math
import os
import wave
import struct
import random
from settings import settings
from physics import physics

COLOR_BG = (15, 15, 17)
COLOR_PANEL = (31, 41, 58)
COLOR_UI = (56, 76, 107)
COLOR_ACCENT = (184, 80, 36)
COLOR_TEXT = (235, 180, 155)
COLOR_WHITE = (255, 255, 255)

def make_sounds():
    def save_wav(name, data):
        with wave.open(name, "w") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(22050)
            for v in data:
                f.writeframes(struct.pack("<h", int(v * 32767)))

    beep_data = [math.sin(2 * math.pi * 1000 * i / 22050) for i in range(int(22050 * 0.15))]
    save_wav("alarm.wav", beep_data)

    engine_data = []
    pulse_len = 630
    for i in range(int(22050 * 1.0)):
        k = i % pulse_len
        t_pulse = k / 22050.0
        pop = math.exp(-180.0 * t_pulse) * (math.sin(2 * math.pi * 70 * t_pulse) + 0.3 * random.uniform(-1.0, 1.0))
        hum = 0.2 * math.sin(2 * math.pi * 35 * i / 22050)
        engine_data.append(0.6 * pop + hum)
    save_wav("engine.wav", engine_data)

    crash_data = []
    for i in range(int(22050 * 1.5)):
        decay = math.exp(-3.0 * i / 22050)
        val = random.uniform(-0.5, 0.5) * decay
        crash_data.append(val)
    save_wav("crash.wav", crash_data)

    click_data = []
    for i in range(int(22050 * 0.03)):
        decay = math.exp(-800.0 * (i / 22050.0))
        val = decay * (math.sin(2 * math.pi * 1200 * (i / 22050.0)) + 0.4 * random.uniform(-1.0, 1.0))
        click_data.append(val)
    save_wav("click.wav", click_data)

class app:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        make_sounds()
        
        self.screen = pygame.display.set_mode((1000, 700))
        pygame.display.set_caption("AeroSim")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = "MENU"
        
        self.settings = settings()
        self.physics = physics()
        
        self.planets = ["Earth", "Mars", "Moon"]
        self.fuels = [10.0, 30.0, 50.0, 70.0]
        self.winds = [0.0, 10.0, 20.0, 30.0]
        
        self.font_title = pygame.font.SysFont("Arial", 40, True)
        self.font_ui = pygame.font.SysFont("Arial", 20, True)
        self.font_gauge = pygame.font.SysFont("Arial", 12, True)

        self.switch_battery = False
        self.switch_alternator = False
        self.switch_fuel_pump = False
        self.switch_ignition = "OFF"
        self.engine_started = False
        self.crank_time = 0.0

        self.sim_throttle = 0.0
        self.sim_pitch = 0.0
        self.sim_flaps = "Retracted"
        self.sim_gear = True
        self.flaps_options = ["Retracted", "Takeoff(15°)", "Landing(30°)"]

        self.sound_engine = pygame.mixer.Sound("engine.wav")
        self.sound_alarm = pygame.mixer.Sound("alarm.wav")
        self.sound_crash = pygame.mixer.Sound("crash.wav")
        self.sound_click = pygame.mixer.Sound("click.wav")
        self.channel_engine = pygame.mixer.Channel(0)
        self.channel_alarm = pygame.mixer.Channel(1)
        self.crash_triggered = False

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)
        pygame.quit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.handle_click(event.pos)
            elif event.type == pygame.KEYDOWN:
                if self.state == "SIM":
                    if event.key == pygame.K_UP:
                        self.sim_throttle = min(self.sim_throttle + 5.0, 100.0)
                    elif event.key == pygame.K_DOWN:
                        self.sim_throttle = max(self.sim_throttle - 5.0, 0.0)
                    elif event.key == pygame.K_RIGHT:
                        self.sim_pitch = min(self.sim_pitch + 1.0, 20.0)
                    elif event.key == pygame.K_LEFT:
                        self.sim_pitch = max(self.sim_pitch - 1.0, -10.0)
                    elif event.key == pygame.K_f:
                        self.sound_click.play()
                        idx = self.flaps_options.index(self.sim_flaps)
                        self.sim_flaps = self.flaps_options[(idx + 1) % len(self.flaps_options)]
                    elif event.key == pygame.K_g:
                        self.sound_click.play()
                        self.sim_gear = not self.sim_gear
                    elif event.key == pygame.K_r:
                        self.reset_sim()

    def handle_click(self, pos):
        mx, my = pos
        if self.state == "MENU":
            if 400 <= mx <= 600 and 200 <= my <= 250:
                self.sound_click.play()
                self.state = "STARTUP"
                self.physics.reset(self.settings)
            elif 400 <= mx <= 600 and 280 <= my <= 330:
                self.sound_click.play()
                idx = self.planets.index(self.settings.planet)
                self.settings.planet = self.planets[(idx + 1) % len(self.planets)]
            elif 400 <= mx <= 600 and 360 <= my <= 410:
                self.sound_click.play()
                idx = self.winds.index(self.settings.wind_speed)
                self.settings.wind_speed = self.winds[(idx + 1) % len(self.winds)]
            elif 400 <= mx <= 600 and 440 <= my <= 490:
                self.sound_click.play()
                idx = self.fuels.index(self.settings.fuel)
                self.settings.fuel = self.fuels[(idx + 1) % len(self.fuels)]
            elif 400 <= mx <= 600 and 520 <= my <= 570:
                self.sound_click.play()
                self.running = False
        elif self.state == "STARTUP":
            if 410 <= mx <= 540 and 200 <= my <= 280:
                self.sound_click.play()
                self.switch_battery = not self.switch_battery
            elif 560 <= mx <= 690 and 200 <= my <= 280:
                self.sound_click.play()
                self.switch_alternator = not self.switch_alternator
            elif 710 <= mx <= 840 and 200 <= my <= 280:
                self.sound_click.play()
                self.switch_fuel_pump = not self.switch_fuel_pump
            elif 525 <= mx <= 725 and 320 <= my <= 380:
                self.sound_click.play()
                if self.switch_ignition == "OFF":
                    self.switch_ignition = "BOTH"
                elif self.switch_ignition == "BOTH":
                    self.switch_ignition = "START"
                    self.crank_time = pygame.time.get_ticks()
                else:
                    self.switch_ignition = "OFF"
            elif self.engine_started and 400 <= mx <= 600 and 460 <= my <= 510:
                self.sound_click.play()
                self.state = "SIM"
                self.channel_engine.play(self.sound_engine, -1)
                self.channel_engine.set_volume(0.2)

    def update(self):
        if self.state == "STARTUP" and self.switch_ignition == "START" and not self.engine_started:
            if self.switch_battery and self.switch_alternator and self.switch_fuel_pump:
                if pygame.time.get_ticks() - self.crank_time > 1500:
                    self.engine_started = True
                    self.switch_ignition = "BOTH"
        elif self.state == "SIM":
            self.physics.update(0.05, self.sim_throttle / 100.0, self.sim_pitch, self.sim_flaps, self.sim_gear)
            if "CRASH" in self.physics.status.upper():
                self.sim_throttle = 0.0
                self.channel_engine.stop()
                self.channel_alarm.stop()
                if not self.crash_triggered:
                    self.sound_crash.play()
                    self.crash_triggered = True
            else:
                vol = 0.2 + (self.sim_throttle / 100.0) * 0.4
                self.channel_engine.set_volume(vol)
            if "STALL" in self.physics.status.upper():
                if not self.channel_alarm.get_busy():
                    self.channel_alarm.play(self.sound_alarm)
            else:
                self.channel_alarm.stop()

    def draw(self):
        self.screen.fill(COLOR_BG)
        if self.state == "MENU":
            self.draw_menu()
        elif self.state == "STARTUP":
            self.draw_startup()
        elif self.state == "SIM":
            self.draw_sim()
        pygame.display.flip()

    def draw_menu(self):
        title = self.font_title.render("AeroSim - Flight Dynamics Lab", True, COLOR_TEXT)
        self.screen.blit(title, (1000/2 - title.get_width()/2, 80))
        self.draw_btn("Start Pre-Flight", 400, 200, 200, 50, COLOR_UI)
        self.draw_btn(f"Planet: {self.settings.planet}", 400, 280, 200, 50, COLOR_PANEL)
        self.draw_btn(f"Wind: {int(self.settings.wind_speed)} kt", 400, 360, 200, 50, COLOR_PANEL)
        self.draw_btn(f"Fuel: {int(self.settings.fuel)} L", 400, 440, 200, 50, COLOR_PANEL)
        self.draw_btn("Exit", 400, 520, 200, 50, COLOR_ACCENT)

    def draw_btn(self, text, x, y, w, h, color):
        pygame.draw.rect(self.screen, color, (x, y, w, h), border_radius=5)
        txt = self.font_ui.render(text, True, COLOR_TEXT)
        self.screen.blit(txt, (x + w/2 - txt.get_width()/2, y + h/2 - txt.get_height()/2))

    def draw_startup(self):
        title = self.font_title.render("Pre-Flight Checklist", True, COLOR_TEXT)
        self.screen.blit(title, (1000/2 - title.get_width()/2, 50))
        checklist = [
            ("1. Battery Switch ON", self.switch_battery),
            ("2. Alternator Switch ON", self.switch_alternator),
            ("3. Fuel Pump Switch ON", self.switch_fuel_pump),
            ("4. Magnetos Key to BOTH", self.switch_ignition == "BOTH" or self.engine_started),
            ("5. Crank Starter (Click Key to START)", self.engine_started)
        ]
        y_offset = 180
        for text, completed in checklist:
            color = COLOR_TEXT if completed else COLOR_UI
            status_symbol = "[X]" if completed else "[ ]"
            txt = self.font_ui.render(f"{status_symbol} {text}", True, color)
            self.screen.blit(txt, (80, y_offset))
            y_offset += 50
        self.draw_switch("BATTERY", 410, 200, self.switch_battery)
        self.draw_switch("ALT", 560, 200, self.switch_alternator)
        self.draw_switch("FUEL PUMP", 710, 200, self.switch_fuel_pump)
        self.draw_btn(f"Ignition: {self.switch_ignition}", 525, 320, 200, 60, COLOR_UI)
        if self.engine_started:
            status_text = "ENGINE RUNNING"
            text_color = COLOR_TEXT
            self.draw_btn("Taxi to Runway", 400, 460, 200, 50, COLOR_ACCENT)
        else:
            status_text = "ENGINE COLD"
            text_color = COLOR_UI
        status_lbl = self.font_title.render(status_text, True, text_color)
        self.screen.blit(status_lbl, (1000/2 - status_lbl.get_width()/2, 560))

    def draw_switch(self, label, x, y, is_on):
        color = COLOR_ACCENT if is_on else COLOR_PANEL
        pygame.draw.rect(self.screen, color, (x, y, 130, 80), border_radius=5)
        txt = self.font_ui.render(label, True, COLOR_TEXT)
        self.screen.blit(txt, (x + 65 - txt.get_width()/2, y + 20))
        state_txt = "ON" if is_on else "OFF"
        txt_state = self.font_ui.render(state_txt, True, COLOR_WHITE)
        self.screen.blit(txt_state, (x + 65 - txt_state.get_width()/2, y + 45))

    def reset_sim(self):
        self.physics.reset(self.settings)
        self.sim_throttle = 0.0
        self.sim_pitch = 0.0
        self.sim_flaps = "Retracted"
        self.sim_gear = True
        self.crash_triggered = False
        self.channel_engine.stop()
        self.channel_alarm.stop()
        if self.engine_started:
            self.channel_engine.play(self.sound_engine, -1)
            self.channel_engine.set_volume(0.2)

    def draw_sim(self):
        pygame.draw.rect(self.screen, COLOR_PANEL, (0, 0, 1000, 320))
        status_txt = self.font_ui.render(f"Status: {self.physics.status}", True, COLOR_TEXT)
        self.screen.blit(status_txt, (30, 20))
        controls_txt = self.font_ui.render(
            f"Throttle: {int(self.sim_throttle)}% | Pitch: {int(self.sim_pitch)}° | Flaps: {self.sim_flaps} | Gear: {'DOWN' if self.sim_gear else 'UP'}",
            True, COLOR_TEXT
        )
        self.screen.blit(controls_txt, (30, 50))
        v_total = math.sqrt(self.physics.vx**2 + self.physics.vy**2)
        self.draw_dial("AIRSPEED", 100, 180, 55, v_total * 1.944, 160)
        self.draw_dial("ALTITUDE", 230, 180, 55, self.physics.y * 3.281, 3000)
        self.draw_attitude_gyro(360, 180, 55, self.sim_pitch)
        vy_ftmin = self.physics.vy * 196.85
        self.draw_vsi_dial("V. SPEED", 490, 180, 55, vy_ftmin, 2000)
        self.draw_energy_hud(760, 120)
        self.draw_forces(640, 180)
        ground_y = 660
        pygame.draw.rect(self.screen, (27, 42, 74), (0, 320, 1000, 340))
        pygame.draw.rect(self.screen, (45, 58, 75), (0, ground_y, 1000, 40))
        pygame.draw.ellipse(self.screen, COLOR_PANEL, (100, 360, 120, 40))
        pygame.draw.ellipse(self.screen, COLOR_PANEL, (450, 400, 180, 50))
        pygame.draw.ellipse(self.screen, COLOR_PANEL, (750, 350, 140, 45))
        for r_x in range(0, 1000, 50):
            pygame.draw.line(self.screen, COLOR_WHITE, (r_x, ground_y + 15), (r_x + 25, ground_y + 15), 2)
        hx = self.physics.history_x
        hy = self.physics.history_y
        if len(hx) >= 2:
            max_x = max(max(hx), 500.0)
            max_y = max(max(hy), 100.0)
            points = []
            for x, y in zip(hx, hy):
                px = (x / max_x) * 960 + 20
                py = ground_y - (y / max_y) * 280
                points.append((int(px), int(py)))
            pygame.draw.lines(self.screen, COLOR_TEXT, False, points, 3)
            curr_px, curr_py = points[-1]
            pygame.draw.polygon(self.screen, COLOR_ACCENT, [
                (curr_px + 10, curr_py),
                (curr_px - 8, curr_py - 5),
                (curr_px - 4, curr_py),
                (curr_px - 8, curr_py + 5)
            ])
            pygame.draw.polygon(self.screen, COLOR_WHITE, [
                (curr_px + 10, curr_py),
                (curr_px - 8, curr_py - 5),
                (curr_px - 4, curr_py),
                (curr_px - 8, curr_py + 5)
            ], 1)

    def draw_dial(self, label, cx, cy, r, val, max_val):
        pygame.draw.circle(self.screen, COLOR_BG, (cx, cy), r)
        pygame.draw.circle(self.screen, COLOR_TEXT, (cx, cy), r, 2)
        txt = self.font_gauge.render(label, True, COLOR_TEXT)
        self.screen.blit(txt, (cx - txt.get_width()/2, cy - r - 15))
        val_txt = self.font_gauge.render(f"{int(val)}", True, COLOR_WHITE)
        self.screen.blit(val_txt, (cx - val_txt.get_width()/2, cy + 25))
        angle = math.radians(-90 + (val / max_val) * 360)
        nx = cx + (r - 12) * math.cos(angle)
        ny = cy + (r - 12) * math.sin(angle)
        pygame.draw.line(self.screen, COLOR_ACCENT, (cx, cy), (int(nx), int(ny)), 3)
        pygame.draw.circle(self.screen, COLOR_WHITE, (cx, cy), 4)

    def draw_vsi_dial(self, label, cx, cy, r, val, max_val):
        pygame.draw.circle(self.screen, COLOR_BG, (cx, cy), r)
        pygame.draw.circle(self.screen, COLOR_TEXT, (cx, cy), r, 2)
        txt = self.font_gauge.render(label, True, COLOR_TEXT)
        self.screen.blit(txt, (cx - txt.get_width()/2, cy - r - 15))
        val_txt = self.font_gauge.render(f"{int(val)}", True, COLOR_WHITE)
        self.screen.blit(val_txt, (cx - val_txt.get_width()/2, cy + 25))
        ratio = max(-1.0, min(1.0, val / max_val))
        angle = math.radians(-90 + ratio * 90)
        nx = cx + (r - 12) * math.cos(angle)
        ny = cy + (r - 12) * math.sin(angle)
        pygame.draw.line(self.screen, COLOR_ACCENT, (cx, cy), (int(nx), int(ny)), 3)
        pygame.draw.circle(self.screen, COLOR_WHITE, (cx, cy), 4)

    def draw_attitude_gyro(self, cx, cy, r, pitch_val):
        pygame.draw.circle(self.screen, COLOR_BG, (cx, cy), r)
        pitch_offset = int((pitch_val / 20.0) * (r - 5))
        pygame.draw.circle(self.screen, COLOR_UI, (cx, cy), r)
        pygame.draw.rect(self.screen, COLOR_ACCENT, (cx - r, cy + pitch_offset, r * 2, r - pitch_offset + 5))
        pygame.draw.line(self.screen, COLOR_WHITE, (cx - r + 3, cy + pitch_offset), (cx + r - 3, cy + pitch_offset), 2)
        pygame.draw.circle(self.screen, COLOR_TEXT, (cx, cy), r, 2)
        pygame.draw.line(self.screen, COLOR_WHITE, (cx - 15, cy), (cx - 5, cy), 3)
        pygame.draw.line(self.screen, COLOR_WHITE, (cx + 5, cy), (cx + 15, cy), 3)
        pygame.draw.circle(self.screen, COLOR_WHITE, (cx, cy), 3)
        txt = self.font_gauge.render("ATTITUDE", True, COLOR_TEXT)
        self.screen.blit(txt, (cx - txt.get_width()/2, cy - r - 15))

    def draw_energy_hud(self, x, y):
        work_kj = self.physics.work_done / 1000.0
        ek_kj = self.physics.ek / 1000.0
        eg_kj = self.physics.eg / 1000.0
        total_energy = ek_kj + eg_kj
        lbl_w = self.font_gauge.render(f"Work: {work_kj:.1f} kJ", True, COLOR_TEXT)
        lbl_ek = self.font_gauge.render(f"Ek: {ek_kj:.1f} kJ", True, COLOR_TEXT)
        lbl_eg = self.font_gauge.render(f"Eg: {eg_kj:.1f} kJ", True, COLOR_TEXT)
        lbl_tot = self.font_gauge.render(f"Total E: {total_energy:.1f} kJ", True, COLOR_WHITE)
        lbl_fuel = self.font_ui.render(f"Fuel: {self.physics.fuel:.1f} L", True, COLOR_ACCENT)
        self.screen.blit(lbl_w, (x, y))
        self.screen.blit(lbl_ek, (x, y + 20))
        self.screen.blit(lbl_eg, (x, y + 40))
        self.screen.blit(lbl_tot, (x, y + 60))
        self.screen.blit(lbl_fuel, (x, y + 90))

    def draw_forces(self, cx, cy):
        t_val = self.sim_throttle / 100.0
        p_val = self.sim_pitch
        f_val = self.sim_flaps
        g_val = self.sim_gear
        tx, ty, lx, ly, dx, dy, weight, _, _ = self.physics.phy_calc(t_val, p_val, f_val, g_val)
        pitch_rad = math.radians(p_val)
        cos_p, sin_p = math.cos(pitch_rad), math.sin(pitch_rad)
        def rotate(x, y):
            rx = x * cos_p - y * sin_p
            ry = x * sin_p + y * cos_p
            return cx + rx, cy - ry
        f_start = rotate(-25, 0)
        f_end = rotate(25, 0)
        pygame.draw.line(self.screen, COLOR_WHITE, (int(f_start[0]), int(f_start[1])), (int(f_end[0]), int(f_end[1])), 4)
        w_top = rotate(0, 20)
        w_bot = rotate(0, -20)
        pygame.draw.line(self.screen, COLOR_UI, (int(w_top[0]), int(w_top[1])), (int(w_bot[0]), int(w_bot[1])), 3)
        pygame.draw.circle(self.screen, COLOR_WHITE, (cx, cy), 3)
        s = 0.005
        forces = [
            (tx * s, -ty * s, (46, 204, 113), "T", 15, 0),     
            (-dx * s, -dy * s, COLOR_ACCENT, "D", -15, 0),    
            (lx * s, -ly * s, (52, 152, 219), "L", 0, -10),     
            (0, weight * s, (231, 76, 60), "W", 0, 10)       
        ]
        for fx, fy, color, label, off_x, off_y in forces:
            end_x, end_y = cx + fx, cy + fy
            pygame.draw.line(self.screen, color, (cx, cy), (int(end_x), int(end_y)), 2)
            lbl = self.font_gauge.render(label, True, color)
            self.screen.blit(lbl, (int(end_x + off_x - lbl.get_width()/2), int(end_y + off_y - lbl.get_height()/2)))

if __name__ == "__main__":
    game = app()
    game.run()