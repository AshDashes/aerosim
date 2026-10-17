import pygame
import asyncio
import math
import os
import random
from settings import settings
from physics import physics
from brain import neural_network, crossover
from weather import get_live_density

COLOR_BG = (15, 15, 17)
COLOR_PANEL = (31, 41, 58)
COLOR_UI = (56, 76, 107)
COLOR_ACCENT = (184, 80, 36)
COLOR_TEXT = (235, 180, 155)
COLOR_WHITE = (255, 255, 255)

def make_sounds():
    import wave
    import struct
    def save_wav(name, data):
        with wave.open(name, "w") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(22050)
            for v in data:
                val_clamped = max(-1.0, min(1.0, v))
                f.writeframes(struct.pack("<h", int(val_clamped * 32767)))

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

class agent:
    def __init__(self, brain=None):
        self.physics = physics()
        self.brain = brain if brain is not None else neural_network()
        self.fitness = 0.0
        self.is_dead = False
        self.throttle = 0.0
        self.pitch = 0.0
    
class app:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            pass

        if not os.path.exists("alarm.wav"):
            try:
                make_sounds()
            except Exception:
                pass
        
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
        self.turbulences = [0.0, 2.0, 5.0]
        self.noises = [0.0, 0.05, 0.10]
        self.weather_locations = ["Standard", "CYYZ", "KORD", "EGLL"]
        
        try:
            self.font_title = pygame.font.SysFont("Arial", 40, True)
            self.font_ui = pygame.font.SysFont("Arial", 20, True)
            self.font_gauge = pygame.font.SysFont("Arial", 12, True)
        except Exception:
            self.font_title = pygame.font.Font(None, 40)
            self.font_ui = pygame.font.Font(None, 24)
            self.font_gauge = pygame.font.Font(None, 16)

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

        class DummyChannel:
            def play(self, *a, **k): pass
            def stop(self): pass
            def set_volume(self, *a): pass
            def get_busy(self): return False

        try:
            self.sound_engine = pygame.mixer.Sound("engine.wav")
            self.sound_alarm = pygame.mixer.Sound("alarm.wav")
            self.sound_crash = pygame.mixer.Sound("crash.wav")
            self.sound_click = pygame.mixer.Sound("click.wav")
            self.channel_engine = pygame.mixer.Channel(0)
            self.channel_alarm = pygame.mixer.Channel(1)
        except Exception:
            self.sound_engine = DummyChannel()
            self.sound_alarm = DummyChannel()
            self.sound_crash = DummyChannel()
            self.sound_click = DummyChannel()
            self.channel_engine = DummyChannel()
            self.channel_alarm = DummyChannel()
        self.crash_triggered = False

        self.population = []
        self.generation = 1
        self.best_fitness = 0.0
        self.train_timer = 0
        self.best_live_agent = None
        self.weather_loading = False

    async def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)
            await asyncio.sleep(0)
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
                    if event.key == pygame.K_f:
                        self.sound_click.play()
                        idx = self.flaps_options.index(self.sim_flaps)
                        self.sim_flaps = self.flaps_options[(idx + 1) % len(self.flaps_options)]
                    elif event.key == pygame.K_g:
                        self.sound_click.play()
                        self.sim_gear = not self.sim_gear
                    elif event.key == pygame.K_r:
                        self.reset_sim()
                    elif event.key == pygame.K_m or event.key == pygame.K_ESCAPE:
                        self.sound_click.play()
                        self.state = "MENU"
                        self.channel_engine.stop()
                        self.channel_alarm.stop()
                elif self.state == "TRAINING":
                    if event.key == pygame.K_r or event.key == pygame.K_m:
                        self.state = "MENU"
                        self.channel_engine.stop()
                elif self.state == "STARTUP":
                    if event.key == pygame.K_m or event.key == pygame.K_ESCAPE:
                        self.state = "MENU"

    def handle_click(self, pos):
        mx, my = pos
        if self.state == "MENU":
            if 400 <= mx <= 600 and 110 <= my <= 160:
                self.sound_click.play()
                self.state = "STARTUP"
                self.physics.reset(self.settings)
            elif 400 <= mx <= 600 and 175 <= my <= 225:
                self.sound_click.play()
                self.start_training()
            elif 400 <= mx <= 600 and 240 <= my <= 290:
                self.sound_click.play()
                idx = self.planets.index(self.settings.planet)
                self.settings.planet = self.planets[(idx + 1) % len(self.planets)]
            elif 400 <= mx <= 600 and 305 <= my <= 355:
                self.sound_click.play()
                idx = self.winds.index(self.settings.wind_speed)
                self.settings.wind_speed = self.winds[(idx + 1) % len(self.winds)]
            elif 400 <= mx <= 600 and 370 <= my <= 420:
                self.sound_click.play()
                idx = self.turbulences.index(self.settings.turbulence)
                self.settings.turbulence = self.turbulences[(idx + 1) % len(self.turbulences)]
            elif 400 <= mx <= 600 and 435 <= my <= 485:
                self.sound_click.play()
                idx = self.noises.index(self.settings.sensor_noise)
                self.settings.sensor_noise = self.noises[(idx + 1) % len(self.noises)]
            elif 400 <= mx <= 600 and 500 <= my <= 550:
                if not self.weather_loading:
                    self.sound_click.play()
                    idx = self.weather_locations.index(self.settings.weather_location)
                    loc = self.weather_locations[(idx + 1) % len(self.weather_locations)]
                    self.settings.weather_location = loc
                    if loc == "Standard":
                        self.settings.air_density = 1.225
                    else:
                        try:
                            import threading
                            t = threading.Thread(target=self.load_weather_thread, args=(loc,))
                            t.start()
                        except Exception:
                            self.load_weather_thread(loc)
            elif 400 <= mx <= 600 and 565 <= my <= 615:
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

    def start_training(self):
        self.state = "TRAINING"
        self.generation = 1
        self.best_fitness = 0.0
        self.train_timer = 0

        self.population = [agent() for _ in range(15)]
        for a in self.population:
            a.physics.reset(self.settings)

        self.best_live_agent = self.population[0]

        self.channel_engine.play(self.sound_engine, -1)
        self.channel_engine.set_volume(0.2)

    def evolve_population(self):
        self.population.sort(key=lambda a: a.fitness, reverse=True)
        gen_best = self.population[0]

        if gen_best.fitness > self.best_fitness:
            self.best_fitness = gen_best.fitness

        self.generation += 1
        self.train_timer = 0

        pool = self.population[:4]
        new_pop = []

        new_pop.append(agent(brain=gen_best.brain.clone()))

        while len(new_pop) < 15:
            p1 = random.choice(pool)
            p2 = random.choice(pool)
            child_brain = crossover(p1.brain, p2.brain)
            child_brain.mutate(0.1)
            new_pop.append(agent(brain=child_brain))

        self.population = new_pop
        for a in self.population:
            a.physics.reset(self.settings)

        self.best_live_agent = self.population[0]

    def load_weather_thread(self, loc):
        self.weather_loading = True
        density = get_live_density(loc)
        self.settings.air_density = density
        self.weather_loading = False

    def update(self):
        if self.state == "STARTUP" and self.switch_ignition == "START" and not self.engine_started:
            if self.switch_battery and self.switch_alternator and self.switch_fuel_pump:
                if pygame.time.get_ticks() - self.crank_time > 1500:
                    self.engine_started = True
                    self.switch_ignition = "BOTH"
        elif self.state == "SIM":
            keys = pygame.key.get_pressed()
            if keys[pygame.K_UP]:
                self.sim_throttle = min(self.sim_throttle + 0.8, 100.0)
            if keys[pygame.K_DOWN]:
                self.sim_throttle = max(self.sim_throttle - 0.8, 0.0)
            if keys[pygame.K_RIGHT]:
                self.sim_pitch = min(self.sim_pitch + 0.2, 20.0)
            if keys[pygame.K_LEFT]:
                self.sim_pitch = max(self.sim_pitch - 0.2, -10.0)

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
        elif self.state == "TRAINING":
            self.train_timer += 1
            all_dead = True
            max_live_fitness = -999999.0
            self.best_live_agent = None

            for a in self.population:
                if not a.is_dead:
                    all_dead = False
                    v_total = math.sqrt(a.physics.vx**2 + a.physics.vy**2)
                    
                    noise_v = 1.0
                    noise_alt = 1.0
                    if self.settings.sensor_noise > 0.0:
                        noise_v += random.uniform(-self.settings.sensor_noise, self.settings.sensor_noise)
                        noise_alt += random.uniform(-self.settings.sensor_noise, self.settings.sensor_noise)

                    inputs = [
                        (v_total * noise_v) / 50.0,
                        (a.physics.y * noise_alt) / 300.0,
                        a.pitch / 20.0,
                        a.physics.vy / 15.0,
                        (1000.0 - a.physics.x) / 1000.0
                    ]
                    outputs = a.brain.feedforward(inputs)
                    a.pitch = outputs[0] * 20.0
                    a.throttle = (outputs[1] + 1.0) / 2.0 * 100.0
                    
                    a.physics.update(0.05, a.throttle / 100.0, a.pitch, "Takeoff(15°)", True)
                    
                    dist_bonus = a.physics.vx * 0.05
                    alt_error = abs(a.physics.y - 150.0)
                    alt_bonus = max(0.0, 5.0 - alt_error * 0.05)
                    a.fitness += dist_bonus + alt_bonus

                    if "CRASH" in a.physics.status.upper() or a.physics.y < -10.0:
                        a.is_dead = True
                    if a.physics.x > 1500.0:
                        a.is_dead = True

                    if a.fitness > max_live_fitness:
                        max_live_fitness = a.fitness
                        self.best_live_agent = a

            if self.best_live_agent:
                vol = 0.2 + (self.best_live_agent.throttle / 100.0) * 0.4
                self.channel_engine.set_volume(vol)
                if "STALL" in self.best_live_agent.physics.status.upper():
                    if not self.channel_alarm.get_busy():
                        self.channel_alarm.play(self.sound_alarm)
                else:
                    self.channel_alarm.stop()

            if all_dead or self.train_timer >= 1500:
                self.evolve_population()

    def draw(self):
        self.screen.fill(COLOR_BG)
        if self.state == "MENU":
            self.draw_menu()
        elif self.state == "STARTUP":
            self.draw_startup()
        elif self.state == "SIM":
            self.draw_sim()
        elif self.state == "TRAINING":
            self.draw_training()
        pygame.display.flip()

    def draw_menu(self):
        title = self.font_title.render("AeroSim - Flight Dynamics Lab", True, COLOR_TEXT)
        self.screen.blit(title, (1000/2 - title.get_width()/2, 50))
        self.draw_btn("Manual Flight", 400, 110, 200, 50, COLOR_UI)
        self.draw_btn("Train AI Autopilot", 400, 175, 200, 50, COLOR_ACCENT)
        self.draw_btn(f"Planet: {self.settings.planet}", 400, 240, 200, 50, COLOR_PANEL)
        self.draw_btn(f"Wind: {int(self.settings.wind_speed)} kt", 400, 305, 200, 50, COLOR_PANEL)
        self.draw_btn(f"Turbulence: {self.settings.turbulence} m/s", 400, 370, 200, 50, COLOR_PANEL)
        self.draw_btn(f"Sensor Noise: {int(self.settings.sensor_noise * 100)}%", 400, 435, 200, 50, COLOR_PANEL)
        if self.weather_loading:
            weather_text = f"Weather: {self.settings.weather_location} [LOADING...]"
        else:
            weather_text = f"Weather: {self.settings.weather_location} ({self.settings.air_density:.3f})"
        self.draw_btn(weather_text, 400, 500, 200, 50, COLOR_PANEL)
        self.draw_btn("Exit", 400, 565, 200, 50, COLOR_ACCENT)

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
        self.screen.blit(status_txt, (460, 20))
        controls_txt = self.font_ui.render(
            f"Throttle: {int(self.sim_throttle)}% | Pitch: {int(self.sim_pitch)}° | Flaps: {self.sim_flaps} | Gear: {'DOWN' if self.sim_gear else 'UP'}",
            True, COLOR_TEXT
        )
        self.screen.blit(controls_txt, (460, 50))
        nav_txt = self.font_gauge.render("Press 'M' to Return to Menu | 'R' to Reset Runway", True, COLOR_WHITE)
        self.screen.blit(nav_txt, (460, 80))

        v_total = math.sqrt(self.physics.vx**2 + self.physics.vy**2)
        self.draw_dial("AIRSPEED", 110, 100, 48, v_total * 1.944, 160)
        self.draw_attitude_gyro(240, 100, 48, self.sim_pitch)
        self.draw_dial("ALTITUDE", 370, 100, 48, self.physics.y * 3.281, 3000)

        self.draw_turn_coordinator(110, 220, 48)
        self.draw_forces(240, 220)
        vy_ftmin = self.physics.vy * 196.85
        self.draw_vsi_dial("V. SPEED", 370, 220, 48, vy_ftmin, 2000)

        self.draw_energy_hud(750, 95)

        ground_y = 660
        pygame.draw.rect(self.screen, (27, 42, 74), (0, 320, 1000, 340))
        pygame.draw.rect(self.screen, (45, 58, 75), (0, ground_y, 1000, 40))
        pygame.draw.ellipse(self.screen, COLOR_PANEL, (100, 360, 120, 40))
        pygame.draw.ellipse(self.screen, COLOR_PANEL, (450, 400, 180, 50))
        pygame.draw.ellipse(self.screen, COLOR_PANEL, (750, 350, 140, 45))
        for r_x in range(0, 1000, 50):
            pygame.draw.line(self.screen, COLOR_WHITE, (r_x, ground_y + 15), (r_x + 25, ground_y + 15), 2)

        self.draw_environment_hud()

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
            flight_path_angle = math.atan2(self.physics.vy, self.physics.vx + self.physics.wind_speed) if v_total > 0.1 else 0.0
            cos_f, sin_f = math.cos(flight_path_angle), math.sin(flight_path_angle)
            
            def rotate_sprite(x, y):
                rx = x * cos_f - y * sin_f
                ry = x * sin_f + y * cos_f
                return int(curr_px + rx), int(curr_py - ry)

            f_s = rotate_sprite(-10, 0)
            f_e = rotate_sprite(10, 0)
            w_t = rotate_sprite(0, 8)
            w_b = rotate_sprite(0, -8)
            t_b = rotate_sprite(-8, 0)
            t_t = rotate_sprite(-10, 4)
            pygame.draw.line(self.screen, COLOR_WHITE, f_s, f_e, 3)
            pygame.draw.line(self.screen, COLOR_ACCENT, w_t, w_b, 2)
            pygame.draw.line(self.screen, COLOR_ACCENT, t_b, t_t, 2)

    def draw_training(self):
        pygame.draw.rect(self.screen, COLOR_PANEL, (0, 0, 1000, 320))
        
        pygame.draw.rect(self.screen, COLOR_BG, (750, 95, 220, 150), border_radius=5)
        pygame.draw.rect(self.screen, COLOR_UI, (750, 95, 220, 150), 2, border_radius=5)
        
        gen_lbl = self.font_ui.render(f"Gen: {self.generation}", True, COLOR_TEXT)
        best_lbl = self.font_gauge.render(f"Best Fitness: {self.best_fitness:.1f}", True, COLOR_WHITE)
        time_lbl = self.font_gauge.render(f"Time: {self.train_timer/60:.1f}s / 25s", True, COLOR_TEXT)
        alive_lbl = self.font_ui.render(f"Alive: {len([a for a in self.population if not a.is_dead])} / 15", True, COLOR_ACCENT)
        reset_lbl = self.font_gauge.render("Press 'R' to Exit Training", True, COLOR_WHITE)

        self.screen.blit(gen_lbl, (760, 110))
        self.screen.blit(best_lbl, (760, 140))
        self.screen.blit(time_lbl, (760, 160))
        self.screen.blit(alive_lbl, (760, 185))
        self.screen.blit(reset_lbl, (760, 215))

        leader = self.best_live_agent
        if leader:
            v_total = math.sqrt(leader.physics.vx**2 + leader.physics.vy**2)
            self.draw_dial("AIRSPEED", 110, 100, 48, v_total * 1.944, 160)
            self.draw_attitude_gyro(240, 100, 48, leader.pitch)
            self.draw_dial("ALTITUDE", 370, 100, 48, leader.physics.y * 3.281, 3000)

            self.draw_turn_coordinator(110, 220, 48)
            self.draw_forces_for_agent(240, 220, leader)
            vy_ftmin = leader.physics.vy * 196.85
            self.draw_vsi_dial("V. SPEED", 370, 220, 48, vy_ftmin, 2000)
            
            status_txt = self.font_ui.render(f"Leader: {leader.physics.status}", True, COLOR_TEXT)
            self.screen.blit(status_txt, (460, 20))
            controls_txt = self.font_ui.render(
                f"T: {int(leader.throttle)}% | P: {int(leader.pitch)}° | Fit: {leader.fitness:.1f}",
                True, COLOR_TEXT
            )
            self.screen.blit(controls_txt, (460, 50))
        else:
            self.draw_dial("AIRSPEED", 110, 100, 48, 0, 160)
            self.draw_dial("ALTITUDE", 370, 100, 48, 0, 3000)
            self.draw_vsi_dial("V. SPEED", 370, 220, 48, 0, 2000)

        ground_y = 660
        pygame.draw.rect(self.screen, (27, 42, 74), (0, 320, 1000, 340))
        pygame.draw.rect(self.screen, (45, 58, 75), (0, ground_y, 1000, 40))
        for r_x in range(0, 1000, 50):
            pygame.draw.line(self.screen, COLOR_WHITE, (r_x, ground_y + 15), (r_x + 25, ground_y + 15), 2)

        self.draw_environment_hud()

        for a in self.population:
            hx = a.physics.history_x
            hy = a.physics.history_y
            if len(hx) >= 2:
                max_x = max([max(agent.physics.history_x) for agent in self.population])
                max_y = max([max(agent.physics.history_y) for agent in self.population])
                max_x = max(max_x, 500.0)
                max_y = max(max_y, 100.0)
                
                points = []
                for x, y in zip(hx, hy):
                    px = (x / max_x) * 960 + 20
                    py = ground_y - (y / max_y) * 280
                    points.append((int(px), int(py)))
                
                is_leader = (a == leader)
                line_color = COLOR_WHITE if is_leader else COLOR_UI
                line_width = 3 if is_leader else 1
                pygame.draw.lines(self.screen, line_color, False, points, line_width)

                if not a.is_dead:
                    curr_px, curr_py = points[-1]
                    v_total = math.sqrt(a.physics.vx**2 + a.physics.vy**2)
                    flight_path_angle = math.atan2(a.physics.vy, a.physics.vx + self.settings.wind_speed) if v_total > 0.1 else 0.0
                    cos_f, sin_f = math.cos(flight_path_angle), math.sin(flight_path_angle)
                    
                    def rotate_sprite(x, y):
                        rx = x * cos_f - y * sin_f
                        ry = x * sin_f + y * cos_f
                        return int(curr_px + rx), int(curr_py - ry)

                    f_s = rotate_sprite(-10, 0)
                    f_e = rotate_sprite(10, 0)
                    w_t = rotate_sprite(0, 8)
                    w_b = rotate_sprite(0, -8)
                    t_b = rotate_sprite(-8, 0)
                    t_t = rotate_sprite(-10, 4)
                    
                    sprite_color = COLOR_ACCENT if is_leader else COLOR_WHITE
                    pygame.draw.line(self.screen, sprite_color, f_s, f_e, 3)
                    pygame.draw.line(self.screen, COLOR_UI, w_t, w_b, 2)
                    pygame.draw.line(self.screen, COLOR_UI, t_b, t_t, 2)

    def draw_dial(self, label, cx, cy, r, val, max_val):
        pygame.draw.circle(self.screen, COLOR_BG, (cx, cy), r)
        pygame.draw.circle(self.screen, COLOR_TEXT, (cx, cy), r, 2)
        txt = self.font_gauge.render(label, True, COLOR_TEXT)
        self.screen.blit(txt, (cx - txt.get_width()/2, cy - r - 13))
        val_txt = self.font_gauge.render(f"{int(val)}", True, COLOR_WHITE)
        self.screen.blit(val_txt, (cx - val_txt.get_width()/2, cy + 20))
        angle = math.radians(-90 + (val / max_val) * 360)
        nx = cx + (r - 10) * math.cos(angle)
        ny = cy + (r - 10) * math.sin(angle)
        pygame.draw.line(self.screen, COLOR_ACCENT, (cx, cy), (int(nx), int(ny)), 2)
        pygame.draw.circle(self.screen, COLOR_WHITE, (cx, cy), 3)

    def draw_vsi_dial(self, label, cx, cy, r, val, max_val):
        pygame.draw.circle(self.screen, COLOR_BG, (cx, cy), r)
        pygame.draw.circle(self.screen, COLOR_TEXT, (cx, cy), r, 2)
        txt = self.font_gauge.render(label, True, COLOR_TEXT)
        self.screen.blit(txt, (cx - txt.get_width()/2, cy - r - 13))
        val_txt = self.font_gauge.render(f"{int(val)}", True, COLOR_WHITE)
        self.screen.blit(val_txt, (cx - val_txt.get_width()/2, cy + 20))
        ratio = max(-1.0, min(1.0, val / max_val))
        angle = math.radians(-90 + ratio * 90)
        nx = cx + (r - 10) * math.cos(angle)
        ny = cy + (r - 10) * math.sin(angle)
        pygame.draw.line(self.screen, COLOR_ACCENT, (cx, cy), (int(nx), int(ny)), 2)
        pygame.draw.circle(self.screen, COLOR_WHITE, (cx, cy), 3)

    def draw_attitude_gyro(self, cx, cy, r, pitch_val):
        pygame.draw.circle(self.screen, COLOR_BG, (cx, cy), r)
        pitch_offset = int((pitch_val / 20.0) * (r - 5))
        pygame.draw.circle(self.screen, COLOR_UI, (cx, cy), r)
        pygame.draw.rect(self.screen, COLOR_ACCENT, (cx - r, cy + pitch_offset, r * 2, r - pitch_offset + 5))
        pygame.draw.line(self.screen, COLOR_WHITE, (cx - r + 3, cy + pitch_offset), (cx + r - 3, cy + pitch_offset), 2)
        pygame.draw.circle(self.screen, COLOR_TEXT, (cx, cy), r, 2)
        pygame.draw.line(self.screen, COLOR_WHITE, (cx - 12, cy), (cx - 4, cy), 2)
        pygame.draw.line(self.screen, COLOR_WHITE, (cx + 4, cy), (cx + 12, cy), 2)
        pygame.draw.circle(self.screen, COLOR_WHITE, (cx, cy), 2)
        txt = self.font_gauge.render("ATTITUDE", True, COLOR_TEXT)
        self.screen.blit(txt, (cx - txt.get_width()/2, cy - r - 13))

    def draw_turn_coordinator(self, cx, cy, r):
        pygame.draw.circle(self.screen, COLOR_BG, (cx, cy), r)
        pygame.draw.circle(self.screen, COLOR_TEXT, (cx, cy), r, 2)
        txt = self.font_gauge.render("TURN COORD", True, COLOR_TEXT)
        self.screen.blit(txt, (cx - txt.get_width()/2, cy - r - 13))
        
        roll_angle = math.radians(max(-30.0, min(30.0, self.physics.vy * 5.0)))
        cos_tc, sin_tc = math.cos(roll_angle), math.sin(roll_angle)
        def rotate_tc(x, y):
            return int(cx + (x * cos_tc - y * sin_tc)), int(cy + (x * sin_tc + y * cos_tc))
        pygame.draw.line(self.screen, COLOR_WHITE, rotate_tc(-15, 0), rotate_tc(15, 0), 3)
        pygame.draw.line(self.screen, COLOR_UI, rotate_tc(0, -8), rotate_tc(0, 8), 2)
        
        ball_x = cx + int(max(-15.0, min(15.0, self.physics.wind_speed * 1.5)))
        pygame.draw.rect(self.screen, COLOR_PANEL, (cx - 20, cy + 18, 40, 10), border_radius=3)
        pygame.draw.circle(self.screen, COLOR_ACCENT, (ball_x, cy + 23), 4)

    def draw_energy_hud(self, x, y):
        pygame.draw.rect(self.screen, COLOR_BG, (x - 10, y - 10, 220, 150), border_radius=5)
        pygame.draw.rect(self.screen, COLOR_UI, (x - 10, y - 10, 220, 150), 2, border_radius=5)
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
        
        pygame.draw.circle(self.screen, COLOR_BG, (cx, cy), 48)
        pygame.draw.circle(self.screen, COLOR_TEXT, (cx, cy), 48, 2)
        txt = self.font_gauge.render("FORCES", True, COLOR_TEXT)
        self.screen.blit(txt, (cx - txt.get_width()/2, cy - 48 - 13))
        pitch_rad = math.radians(p_val)
        cos_p, sin_p = math.cos(pitch_rad), math.sin(pitch_rad)
        def rotate(x, y):
            rx = x * cos_p - y * sin_p
            ry = x * sin_p + y * cos_p
            return cx + rx, cy - ry
        f_start = rotate(-20, 0)
        f_end = rotate(20, 0)
        pygame.draw.line(self.screen, COLOR_WHITE, (int(f_start[0]), int(f_start[1])), (int(f_end[0]), int(f_end[1])), 4)
        w_top = rotate(0, 15)
        w_bot = rotate(0, -15)
        pygame.draw.line(self.screen, COLOR_UI, (int(w_top[0]), int(w_top[1])), (int(w_bot[0]), int(w_bot[1])), 2)
        pygame.draw.circle(self.screen, COLOR_WHITE, (cx, cy), 2)
        s = 0.003
        forces = [
            (tx * s, -ty * s, (46, 204, 113), "T", 12, 0),     
            (-dx * s, -dy * s, COLOR_ACCENT, "D", -12, 0),    
            (lx * s, -ly * s, (52, 152, 219), "L", 0, -8),     
            (0, weight * s, (231, 76, 60), "W", 0, 8)       
        ]
        for fx, fy, color, label, off_x, off_y in forces:
            length = math.sqrt(fx**2 + fy**2)
            if length > 42.0:
                fx = (fx / length) * 42.0
                fy = (fy / length) * 42.0
            end_x, end_y = cx + fx, cy + fy
            pygame.draw.line(self.screen, color, (cx, cy), (int(end_x), int(end_y)), 2)
            lbl = self.font_gauge.render(label, True, color)
            self.screen.blit(lbl, (int(end_x + off_x - lbl.get_width()/2), int(end_y + off_y - lbl.get_height()/2)))

    def draw_forces_for_agent(self, cx, cy, ag):
        t_val = ag.throttle / 100.0
        p_val = ag.pitch
        tx, ty, lx, ly, dx, dy, weight, _, _ = ag.physics.phy_calc(t_val, p_val, "Takeoff(15°)", True)
        
        pygame.draw.circle(self.screen, COLOR_BG, (cx, cy), 48)
        pygame.draw.circle(self.screen, COLOR_TEXT, (cx, cy), 48, 2)
        txt = self.font_gauge.render("FORCES", True, COLOR_TEXT)
        self.screen.blit(txt, (cx - txt.get_width()/2, cy - 48 - 13))
        pitch_rad = math.radians(p_val)
        cos_p, sin_p = math.cos(pitch_rad), math.sin(pitch_rad)
        def rotate(x, y):
            rx = x * cos_p - y * sin_p
            ry = x * sin_p + y * cos_p
            return cx + rx, cy - ry
        f_start = rotate(-20, 0)
        f_end = rotate(20, 0)
        pygame.draw.line(self.screen, COLOR_WHITE, (int(f_start[0]), int(f_start[1])), (int(f_end[0]), int(f_end[1])), 4)
        w_top = rotate(0, 15)
        w_bot = rotate(0, -15)
        pygame.draw.line(self.screen, COLOR_UI, (int(w_top[0]), int(w_top[1])), (int(w_bot[0]), int(w_bot[1])), 2)
        pygame.draw.circle(self.screen, COLOR_WHITE, (cx, cy), 2)
        s = 0.003
        forces = [
            (tx * s, -ty * s, (46, 204, 113), "T", 12, 0),     
            (-dx * s, -dy * s, COLOR_ACCENT, "D", -12, 0),    
            (lx * s, -ly * s, (52, 152, 219), "L", 0, -8),     
            (0, weight * s, (231, 76, 60), "W", 0, 8)       
        ]
        for fx, fy, color, label, off_x, off_y in forces:
            length = math.sqrt(fx**2 + fy**2)
            if length > 42.0:
                fx = (fx / length) * 42.0
                fy = (fy / length) * 42.0
            end_x, end_y = cx + fx, cy + fy
            pygame.draw.line(self.screen, color, (cx, cy), (int(end_x), int(end_y)), 2)
            lbl = self.font_gauge.render(label, True, color)
            self.screen.blit(lbl, (int(end_x + off_x - lbl.get_width()/2), int(end_y + off_y - lbl.get_height()/2)))

    def draw_environment_hud(self):
        pygame.draw.rect(self.screen, COLOR_PANEL, (830, 340, 150, 120), border_radius=5)
        pygame.draw.rect(self.screen, COLOR_UI, (830, 340, 150, 120), 2, border_radius=5)
        
        lbl_title = self.font_gauge.render("ENVIRONMENT", True, COLOR_TEXT)
        lbl_planet = self.font_gauge.render(f"Planet: {self.settings.planet}", True, COLOR_WHITE)
        lbl_weather = self.font_gauge.render(f"Weather: {self.settings.weather_location}", True, COLOR_WHITE)
        lbl_density = self.font_gauge.render(f"Density: {self.settings.air_density:.3f}", True, COLOR_WHITE)
        
        self.screen.blit(lbl_title, (840, 350))
        self.screen.blit(lbl_planet, (840, 370))
        self.screen.blit(lbl_weather, (840, 390))
        self.screen.blit(lbl_density, (840, 410))
        
        wind_kt = int(self.settings.wind_speed)
        turb_ms = self.settings.turbulence
        
        if wind_kt > 0 or turb_ms > 0:
            wind_str = f"Wind: {wind_kt}kt"
            if turb_ms > 0:
                wind_str += f" | T: {int(turb_ms)}"
            lbl_wind = self.font_gauge.render(wind_str, True, COLOR_ACCENT)
            self.screen.blit(lbl_wind, (840, 430))
            
            if wind_kt > 0:
                pygame.draw.line(self.screen, COLOR_ACCENT, (960, 436), (935, 436), 2)
                pygame.draw.polygon(self.screen, COLOR_ACCENT, [(935, 436), (940, 432), (940, 440)])
        else:
            lbl_wind = self.font_gauge.render("Wind: Calm", True, COLOR_WHITE)
            self.screen.blit(lbl_wind, (840, 430))

async def main():
    game = app()
    await game.run()

try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = None

if loop and loop.is_running():
    asyncio.create_task(main())
else:
    asyncio.run(main())