#!/usr/bin/env python3
"""LED pixel face inspired by the supplied reference image.

Install: sudo pacman -S python-pygame
Run:     python led_face.py

Keys: Esc/Q quit, F fullscreen toggle, Space force a random expression.
"""
import math
import random
import sys
import pygame

W, H = 450, 300
FPS = 30
BLACK = (0, 0, 0)
CYAN = (83, 218, 255)
RED = (255, 48, 62)
AMBER = (255, 175, 65)
WHITE = (205, 247, 255)


def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


class Face:
    def __init__(self):
        self.mode = "idle"
        self.mode_until = 0
        self.next_event = random.uniform(2.0, 5.0)
        self.gaze = (0, 0)
        self.next_gaze = random.uniform(1.0, 3.0)
        self.blink = 0.0
        self.blinking = False
        self.color = CYAN
        self.color_from = CYAN
        self.color_to = CYAN
        self.color_start = 0.0
        self.color_duration = 0.25

    def set_color(self, color, now):
        self.color_from = self.color
        self.color_to = color
        self.color_start = now

    def expression(self, mode, now, duration=None):
        self.mode = mode
        self.mode_until = now + (duration if duration is not None else random.uniform(1.3, 2.8))
        self.set_color(RED if mode == "angry" else AMBER if mode == "surprised" else CYAN, now)

    def update(self, now, dt):
        t = min(1.0, (now - self.color_start) / max(0.001, self.color_duration))
        self.color = mix(self.color_from, self.color_to, t)

        if now >= self.next_gaze:
            self.gaze = random.choice([(-1, 0), (1, 0), (0, -1), (0, 1), (0, 0)])
            self.next_gaze = now + random.uniform(1.2, 3.5)

        if self.blinking:
            self.blink += dt * 8
            if self.blink >= 1:
                self.blink = 1
                self.blinking = False
                self._blink_opening = True
        elif getattr(self, "_blink_opening", False):
            self.blink -= dt * 8
            if self.blink <= 0:
                self.blink = 0
                self._blink_opening = False
                self.next_blink = now + random.uniform(2.0, 6.0)
        elif now >= getattr(self, "next_blink", 1.0):
            self.blinking = True
            self._blink_opening = False

        if now >= self.mode_until and self.mode != "idle":
            self.expression("idle", now, 0.4)
            self.next_event = now + random.uniform(3.0, 7.0)
        elif self.mode == "idle" and now >= self.next_event:
            mode = random.choices(
                ["angry", "squint", "surprised", "sleepy", "happy", "idle"],
                weights=[18, 22, 10, 16, 14, 20]
            )[0]
            if mode == "idle":
                self.next_event = now + random.uniform(2.0, 4.0)
            else:
                self.expression(mode, now)

    def pixel(self, glow, sharp, x, y, color, size=4):
        r = pygame.Rect(round(x-size/2), round(y-size/2), size, size)
        pygame.draw.rect(glow, (*color, 48), r.inflate(8, 8))
        pygame.draw.rect(glow, (*color, 75), r.inflate(4, 4))
        pygame.draw.rect(sharp, color, r)
        pygame.draw.rect(sharp, WHITE, r.inflate(-2, -2))

    def led_ring(self, glow, sharp, cx, cy, rx, ry, radius=68, thickness=10, phase=0):
        # LED matrix sampled on a regular grid; only cells near the ring are lit.
        step = 7
        for yy in range(-78, 79, step):
            for xx in range(-78, 79, step):
                d = math.sqrt((xx/rx)**2 + (yy/ry)**2)
                # Elliptical ring with a little pixelated edge.
                target = radius / 68
                if abs(d - target) < thickness / 68:
                    self.pixel(glow, sharp, cx+xx, cy+yy, self.color, 4)

    def draw_brow(self, glow, sharp, cx, cy, angry=False, left=True):
        for i in range(6):
            x = cx + (i-2.5)*6
            y = cy + (i*1.7 if angry and left else (5-i)*1.7 if angry else 0)
            self.pixel(glow, sharp, x, y, self.color, 4)

    def draw(self, screen, now):
        glow = pygame.Surface((W, H), pygame.SRCALPHA)
        sharp = pygame.Surface((W, H), pygame.SRCALPHA)

        squint = 0.42 if self.mode == "squint" else 0.68 if self.mode == "sleepy" else 1.0
        blink_scale = max(0.055, 1.0 - self.blink * 0.96)
        eye_ry = 68 * squint * blink_scale

        # Main hollow LED eyes, matching the reference's large matrix rings.
        for cx in (102, 348):
            self.led_ring(glow, sharp, cx, 150, 68, eye_ry, 68, 10)

        # Small brows / forehead LEDs.
        angry = self.mode == "angry"
        self.draw_brow(glow, sharp, 102, 43, angry, True)
        self.draw_brow(glow, sharp, 348, 43, angry, False)

        # Small pupils appear inside the rings and shift to look around.
        gx, gy = self.gaze
        if self.blink < 0.7:
            pupil_y = 150 + gy*12
            for cx in (102 + gx*17, 348 + gx*17):
                for dx, dy in [(-1,0),(0,0),(1,0),(0,-1),(0,1)]:
                    self.pixel(glow, sharp, cx+dx*6, pupil_y+dy*6, self.color, 4)

        # Tiny nose.
        for dx in (-1, 0, 1):
            self.pixel(glow, sharp, 225+dx*6, 202, self.color, 4)

        # Mouth built from LEDs; shape changes with expression.
        mouth = {
            "idle": [( -3,0),(-2,1),(-1,1),(0,1),(1,1),(2,1),(3,0)],
            "happy": [(-4,0),(-3,1),(-2,2),(-1,2),(0,2),(1,2),(2,2),(3,1),(4,0)],
            "angry": [(-4,2),(-3,1),(-2,0),(-1,0),(0,0),(1,0),(2,0),(3,1),(4,2)],
            "sad": [(-3,2),(-2,1),(-1,0),(0,0),(1,0),(2,1),(3,2)],
            "surprised": [(0,0),(0,1),(0,2),(-1,1),(1,1)],
            "sleepy": [(-3,0),(-2,0),(-1,0),(0,0),(1,0),(2,0),(3,0)],
            "squint": [(-3,0),(-2,1),(-1,1),(0,1),(1,1),(2,1),(3,0)],
        }.get(self.mode, [(-3,0),(-2,1),(-1,1),(0,1),(1,1),(2,1),(3,0)])

        mouth_scale = 1.5 if self.mode == "surprised" else 1.0
        for mx, my in mouth:
            self.pixel(glow, sharp, 225+mx*7*mouth_scale, 224+my*7*mouth_scale, self.color, 4)

        # Cheek/status LEDs at the sides, like the reference.
        for cx in (39, 411):
            for row in range(2):
                for col in range(4):
                    self.pixel(glow, sharp, cx+(col-1.5)*7, 248+row*22, self.color, 4)

        screen.fill(BLACK)
        screen.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        screen.blit(sharp, (0, 0))


def main():
    pygame.init()
    pygame.display.set_caption("LED Pixel Face")
    fullscreen = True
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    clock = pygame.time.Clock()
    face = Face()
    running = True
    while running:
        dt = min(clock.tick(FPS)/1000.0, 0.05)
        now = pygame.time.get_ticks()/1000.0
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif e.key == pygame.K_SPACE:
                    face.expression(random.choice(["angry","happy","surprised","sleepy","squint"]), now)
                elif e.key == pygame.K_f:
                    fullscreen = not fullscreen
                    screen = pygame.display.set_mode((0,0) if fullscreen else (900,600),
                        pygame.FULLSCREEN if fullscreen else 0)
        face.update(now, dt)
        logical = pygame.Surface((W,H))
        face.draw(logical, now)
        sw, sh = screen.get_size()
        scale = min(sw/W, sh/H)
        size = (max(1,int(W*scale)), max(1,int(H*scale)))
        # Nearest-neighbour scaling preserves the LED pixel look.
        scaled = pygame.transform.scale(logical, size)
        screen.fill(BLACK)
        screen.blit(scaled, ((sw-size[0])//2,(sh-size[1])//2))
        pygame.display.flip()
    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
