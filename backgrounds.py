import pygame
import math
import random

def create_pixel_backgrounds():
    pygame.init()
    w, h = 250, 95
    sky_h = 85
    runway_h = 10

    # earth
    surf_earth = pygame.Surface((w, h))
    c_top = (15, 25, 50)
    c_mid = (35, 70, 115)
    c_low = (95, 145, 180)
    c_haz = (165, 195, 215)
    
    for y in range(sky_h):
        t = y / float(sky_h)
        if t < 0.5:
            f = t / 0.5
            r = int(c_top[0] * (1 - f) + c_mid[0] * f)
            g = int(c_top[1] * (1 - f) + c_mid[1] * f)
            b = int(c_top[2] * (1 - f) + c_mid[2] * f)
        elif t < 0.85:
            f = (t - 0.5) / 0.35
            r = int(c_mid[0] * (1 - f) + c_low[0] * f)
            g = int(c_mid[1] * (1 - f) + c_low[1] * f)
            b = int(c_mid[2] * (1 - f) + c_low[2] * f)
        else:
            f = (t - 0.85) / 0.15
            r = int(c_low[0] * (1 - f) + c_haz[0] * f)
            g = int(c_low[1] * (1 - f) + c_haz[1] * f)
            b = int(c_low[2] * (1 - f) + c_haz[2] * f)
        pygame.draw.line(surf_earth, (r, g, b), (0, y), (w, y))

    random.seed(42)
    m1_pts = [(0, sky_h)]
    for x in range(0, w + 10, 10):
        ny = sky_h - 18 - int(math.sin(x * 0.05) * 8 + math.sin(x * 0.12) * 4 + (x % 15))
        m1_pts.append((x, ny))
    m1_pts.append((w, sky_h))
    pygame.draw.polygon(surf_earth, (45, 65, 90), m1_pts)

    m2_pts = [(0, sky_h)]
    for x in range(0, w + 8, 8):
        ny = sky_h - 8 - int(math.sin(x * 0.08) * 5 + (x * 3 % 7))
        m2_pts.append((x, ny))
    m2_pts.append((w, sky_h))
    pygame.draw.polygon(surf_earth, (30, 50, 70), m2_pts)

    def draw_pixel_cloud(surf, cx, cy, sz):
        c_white = (240, 245, 255)
        c_shad = (160, 180, 205)
        for dx in range(-sz, sz + 1):
            for dy in range(-int(sz * 0.6), int(sz * 0.6) + 1):
                if (dx**2)/(sz**2) + (dy**2)/((sz * 0.6)**2) <= 1.0:
                    c = c_shad if dy > 0 else c_white
                    surf.set_at((cx + dx, cy + dy), c)

    draw_pixel_cloud(surf_earth, 40, 22, 18)
    draw_pixel_cloud(surf_earth, 55, 20, 14)
    draw_pixel_cloud(surf_earth, 130, 32, 22)
    draw_pixel_cloud(surf_earth, 150, 30, 16)
    draw_pixel_cloud(surf_earth, 175, 18, 14)

    pygame.draw.rect(surf_earth, (34, 52, 40), (0, sky_h, w, runway_h))
    pygame.draw.rect(surf_earth, (35, 40, 48), (0, sky_h + 2, w, runway_h - 2))
    for rx in range(0, w, 12):
        pygame.draw.line(surf_earth, (240, 240, 240), (rx, sky_h + 5), (rx + 6, sky_h + 5))
        surf_earth.set_at((rx, sky_h + 2), (220, 200, 50))

    out_earth = pygame.transform.scale(surf_earth, (1000, 380))
    pygame.image.save(out_earth, "bg_earth.png")

    # mars
    surf_mars = pygame.Surface((w, h))
    c_m_top = (30, 12, 20)
    c_m_mid = (95, 38, 28)
    c_m_low = (165, 75, 42)
    c_m_haz = (215, 120, 68)

    for y in range(sky_h):
        t = y / float(sky_h)
        if t < 0.6:
            f = t / 0.6
            r = int(c_m_top[0] * (1 - f) + c_m_mid[0] * f)
            g = int(c_m_top[1] * (1 - f) + c_m_mid[1] * f)
            b = int(c_m_top[2] * (1 - f) + c_m_mid[2] * f)
        else:
            f = (t - 0.6) / 0.4
            r = int(c_m_mid[0] * (1 - f) + c_m_haz[0] * f)
            g = int(c_m_mid[1] * (1 - f) + c_m_haz[1] * f)
            b = int(c_m_mid[2] * (1 - f) + c_m_haz[2] * f)
        pygame.draw.line(surf_mars, (r, g, b), (0, y), (w, y))

    pygame.draw.circle(surf_mars, (190, 175, 165), (48, 18), 4)
    pygame.draw.rect(surf_mars, (140, 125, 115), (47, 18, 3, 3))
    surf_mars.set_at((65, 26), (210, 195, 185))
    surf_mars.set_at((66, 26), (170, 155, 145))

    mars_m1 = [(0, sky_h)]
    for x in range(0, w + 10, 10):
        ny = sky_h - 22 - int(math.sin(x * 0.04 + 1.2) * 12 + math.cos(x * 0.08) * 5)
        mars_m1.append((x, ny))
    mars_m1.append((w, sky_h))
    pygame.draw.polygon(surf_mars, (85, 32, 25), mars_m1)

    mars_m2 = [(0, sky_h)]
    for x in range(0, w + 8, 8):
        ny = sky_h - 10 - int(math.sin(x * 0.07) * 6 + (x * 5 % 9))
        mars_m2.append((x, ny))
    mars_m2.append((w, sky_h))
    pygame.draw.polygon(surf_mars, (125, 48, 32), mars_m2)

    for _ in range(12):
        wx = random.randint(10, w - 40)
        wy = random.randint(35, sky_h - 15)
        wl = random.randint(12, 35)
        pygame.draw.line(surf_mars, (180, 95, 55), (wx, wy), (wx + wl, wy), 1)

    pygame.draw.rect(surf_mars, (140, 52, 34), (0, sky_h, w, runway_h))
    pygame.draw.rect(surf_mars, (52, 45, 50), (0, sky_h + 2, w, runway_h - 2))
    for rx in range(0, w, 12):
        pygame.draw.line(surf_mars, (245, 140, 40), (rx, sky_h + 5), (rx + 6, sky_h + 5))
        surf_mars.set_at((rx, sky_h + 2), (255, 100, 30))

    out_mars = pygame.transform.scale(surf_mars, (1000, 380))
    pygame.image.save(out_mars, "bg_mars.png")

    # moon
    surf_moon = pygame.Surface((w, h))
    surf_moon.fill((6, 7, 12))

    random.seed(1337)
    for _ in range(90):
        sx = random.randint(0, w - 1)
        sy = random.randint(0, sky_h - 15)
        bri = random.choice([(255, 255, 255), (200, 220, 255), (150, 160, 200), (255, 240, 180)])
        surf_moon.set_at((sx, sy), bri)
        if random.random() < 0.08:
            surf_moon.set_at((sx + 1, sy), (100, 120, 180))
            surf_moon.set_at((sx - 1, sy), (100, 120, 180))
            surf_moon.set_at((sx, sy + 1), (100, 120, 180))
            surf_moon.set_at((sx, sy - 1), (100, 120, 180))

    ex, ey, er = 55, 24, 10
    pygame.draw.circle(surf_moon, (30, 95, 195), (ex, ey), er)
    pygame.draw.rect(surf_moon, (45, 145, 75), (ex - 5, ey - 6, 6, 5))
    pygame.draw.rect(surf_moon, (50, 155, 80), (ex - 2, ey - 2, 7, 6))
    pygame.draw.rect(surf_moon, (45, 140, 70), (ex - 7, ey + 2, 5, 4))
    pygame.draw.line(surf_moon, (230, 245, 255), (ex - 7, ey - 3), (ex + 6, ey - 4))
    pygame.draw.line(surf_moon, (230, 245, 255), (ex - 5, ey + 4), (ex + 4, ey + 3))
    pygame.draw.circle(surf_moon, (80, 160, 240), (ex, ey), er + 1, 1)

    moon_m1 = [(0, sky_h)]
    for x in range(0, w + 10, 10):
        ny = sky_h - 18 - int(abs(math.sin(x * 0.06)) * 14 + (x * 7 % 6))
        moon_m1.append((x, ny))
    moon_m1.append((w, sky_h))
    pygame.draw.polygon(surf_moon, (50, 54, 62), moon_m1)

    moon_m2 = [(0, sky_h)]
    for x in range(0, w + 8, 8):
        ny = sky_h - 9 - int(math.sin(x * 0.1) * 5 + (x * 3 % 5))
        moon_m2.append((x, ny))
    moon_m2.append((w, sky_h))
    pygame.draw.polygon(surf_moon, (75, 80, 90), moon_m2)

    pygame.draw.rect(surf_moon, (85, 90, 100), (0, sky_h, w, runway_h))
    pygame.draw.rect(surf_moon, (38, 42, 48), (0, sky_h + 2, w, runway_h - 2))
    for rx in range(0, w, 12):
        pygame.draw.line(surf_moon, (120, 220, 255), (rx, sky_h + 5), (rx + 6, sky_h + 5))
        surf_moon.set_at((rx, sky_h + 2), (255, 255, 255))

    out_moon = pygame.transform.scale(surf_moon, (1000, 380))
    pygame.image.save(out_moon, "bg_moon.png")

if __name__ == "__main__":
    create_pixel_backgrounds()
