import math
import random 

class physics:
    def __init__(self):
        self.mass = 1200.0
        self.wing_area = 16.0
        self.max_thrust = 5000.0
        self.g = 9.81
        self.wind_speed = 0.0
        self.fuel = 50.0
        self.ek = 0.0
        self.eg = 0.0
        self.work_done = 0.0
        self.reset()

    def reset(self, active_settings=None):
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.history_x = [0.0]
        self.history_y = [0.0]
        self.status = "On Runway"
        self.ek = 0.0
        self.eg = 0.0
        self.work_done = 0.0
        self.gust_x = 0.0
        self.gust_y = 0.0
        self.target_gust_x = 0.0
        self.target_gust_y = 0.0
        self.gust_timer = 0.0
    
        if active_settings:
            self.fuel = active_settings.fuel
            self.wind_speed = active_settings.wind_speed * 0.514
            self.turbulence = active_settings.turbulence
            self.rho_sea_level = active_settings.air_density

            if active_settings.planet == "Earth":
                self.g = 9.81

            elif active_settings.planet == "Mars":
                self.g = 3.71

            elif active_settings.planet == "Moon":
                self.g = 1.62
        else:
            self.g = 9.81
            self.wind_speed = 0.0
            self.fuel = 50.0
            self.turbulence = 0.0
            self.rho_sea_level = 1.225

    def phy_calc(self, throttle, pitch_deg, flaps, gear_down):
        if self.fuel > 0.0:
            thrust = throttle * self.max_thrust

        else:
            thrust = 0.0
            self.status = "Engine Off (No Fuel)"

        weight = self.mass * self.g
        v_air_x = self.vx + self.wind_speed + self.gust_x
        v_air_y = self.vy + self.gust_y
        v = math.sqrt(v_air_x**2 + v_air_y**2)

        if self.g == 9.81:
            rho = self.rho_sea_level * math.exp(-self.y / 8500.0)

        elif self.g == 3.71:
            rho = 0.02 * math.exp(-self.y / 11000.0)

        else:
            rho = 0.00001

        pitch_rad = math.radians(pitch_deg)
        flight_path_angle = math.atan2(v_air_y, v_air_x) if v > 0.1 else 0.0
        aoa_deg = math.degrees(pitch_rad - flight_path_angle)
        cl0 = 0.3

        if flaps == "Takeoff(15°)":
            cl0 = 0.45

        elif flaps == "Landing(30°)":
            cl0 = 0.6

        if aoa_deg > 15.0:
            cl = 0.1
            self.status = "Stall!"

        else:
            cl = cl0 + 0.1 * aoa_deg
            if self.y > 0 and not ("CRASH" in self.status.upper() or "LAND" in self.status.upper()):
                self.status = "Airborne"

        lift = 0.5 * rho * (v**2) * self.wing_area * cl
        cd0 = 0.03

        if gear_down:
            cd0 += 0.02
        if flaps != "Retracted":
            cd0 += 0.015

        cd = cd0 + 0.05 * (cl**2)
        drag = 0.5 * rho * (v**2) * self.wing_area * cd
        tx = thrust * math.cos(pitch_rad)
        ty = thrust * math.sin(pitch_rad)
        dx = drag * math.cos(flight_path_angle)
        dy = drag * math.sin(flight_path_angle)
        lx = -lift * math.sin(flight_path_angle)
        ly = lift * math.cos(flight_path_angle)

        return tx, ty, lx, ly, dx, dy, weight, thrust, v

    def update(self, dt, throttle, pitch_deg, flaps, gear_down):
        if self.turbulence > 0.0:
            self.gust_timer -= dt
            if self.gust_timer <= 0.0:
                self.target_gust_x = random.uniform(-self.turbulence, self.turbulence)
                self.target_gust_y = random.uniform(-self.turbulence * 0.7, self.turbulence * 0.7)
                self.gust_timer = random.uniform(0.8, 1.8)
            alpha = min(1.0, 3.0 * dt)
            self.gust_x += (self.target_gust_x - self.gust_x) * alpha
            self.gust_y += (self.target_gust_y - self.gust_y) * alpha
        else:
            self.gust_x = 0.0
            self.gust_y = 0.0

        tx, ty, lx, ly, dx, dy, weight, thrust_force, v_air = self.phy_calc(throttle, pitch_deg, flaps, gear_down)
        if self.fuel > 0.0:
            self.fuel -= throttle * 0.1 * dt

            if self.fuel < 0.0:
                self.fuel = 0.0

        if self.y <= 0:
            self.y = 0.0
            self.vy = 0.0

            if not ("CRASH" in self.status.upper() or "LAND" in self.status.upper()):
                normal_force = weight - ly
                friction = 0.02 * normal_force if normal_force > 0 else 0.0
                f_net_x = tx - dx - friction

                if ly > weight and self.vx > 30:
                    f_net_y = ly - weight
                    self.status = "Liftoff!"
                else:
                    f_net_y = 0.0
                    self.status = "On Runway"
            else:
                f_net_x = 0.0
                f_net_y = 0.0
        else:
            f_net_x = tx + lx - dx
            f_net_y = ty + ly - dy - weight

        ax = f_net_x / self.mass
        ay = f_net_y / self.mass

        self.vx += ax * dt
        self.vy += ay * dt

        if self.y == 0 and self.vx < 0:
            self.vx = 0.0

        self.x += self.vx * dt
        self.y += self.vy * dt

        if self.y < 0:
            self.y = 0.0

            if self.vy < -3.0:
                self.status = "Crashed!"
                self.vx = 0.0
                self.vy = 0.0

            else:
                self.status = "Landed!"
                self.vy = 0.0
                self.vx *= 0.5

        v_ground = math.sqrt(self.vx**2 + self.vy**2)
        self.ek = 0.5 * self.mass * (v_ground**2)
        self.eg = self.mass * self.g * self.y
        self.work_done += thrust_force * (v_ground * dt)

        self.history_x.append(self.x)
        self.history_y.append(self.y)