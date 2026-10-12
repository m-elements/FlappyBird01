import pygame
import random
import sys
import math
import struct
import io

pygame.init()

# Safe Audio Mixer Initialization
AUDIO_ENABLED = True
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=1024)
except Exception:
    AUDIO_ENABLED = False

# Fallback Sound class agar audio hardware fail ho jaye to game crash na ho
class DummySound:
    def play(self): pass

# --- CRASH-FREE IN-MEMORY WAV SOUND GENERATOR ---
def create_sound(freq_start, freq_end, duration, volume=0.25):
    if not AUDIO_ENABLED:
        return DummySound()
    try:
        sample_rate = 44100
        n_samples = int(sample_rate * duration)
        samples = bytearray()
        
        for i in range(n_samples):
            t = i / sample_rate
            freq = freq_start + (freq_end - freq_start) * (i / n_samples)
            
            # Retro 8-bit square wave synthesis
            val = 1.0 if math.sin(2 * math.pi * freq * t) > 0 else -1.0
            
            # Smooth fade-out to remove clicks
            envelope = 1.0 - (i / n_samples)
            sample_val = max(-32767, min(32767, int(val * envelope * volume * 32767)))
            samples.extend(struct.pack('<h', sample_val))
            
        # In-memory WAV Header file construction
        buf = io.BytesIO()
        data_size = len(samples)
        buf.write(b'RIFF')
        buf.write(struct.pack('<I', 36 + data_size))
        buf.write(b'WAVEfmt ')
        buf.write(struct.pack('<I', 16))
        buf.write(struct.pack('<H', 1))       # PCM format
        buf.write(struct.pack('<H', 1))       # Mono channel
        buf.write(struct.pack('<I', sample_rate))
        buf.write(struct.pack('<I', sample_rate * 2))
        buf.write(struct.pack('<H', 2))
        buf.write(struct.pack('<H', 16))
        buf.write(b'data')
        buf.write(struct.pack('<I', data_size))
        buf.write(samples)
        buf.seek(0)
        
        return pygame.mixer.Sound(buf)
    except Exception:
        return DummySound()

# Sound Effects Initialization
sound_jump = create_sound(450, 850, 0.08, volume=0.25)
sound_score = create_sound(700, 1100, 0.12, volume=0.2)
sound_hit = create_sound(200, 50, 0.25, volume=0.35)

# Screen setup
info = pygame.display.Info()
WIDTH = info.current_w
HEIGHT = info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Flappy Bird - Manu Pro Edition')
clock = pygame.time.Clock()

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SKY_BLUE = (135, 206, 235) 
PIPE_GREEN = (46, 204, 113)
PIPE_BORDER = (39, 174, 96)
GROUND_COLOR = (222, 184, 135)
GROUND_STRIPE = (205, 170, 125)
MOUNTAIN_COLOR_1 = (119, 136, 153)
MOUNTAIN_COLOR_2 = (176, 196, 222)
MANU_COLOR = (220, 20, 60) 

# Game Variables
game_state = 'READY' 
gravity = HEIGHT * 0.00075
bird_movement = 0
score = 0
high_score = 0
screen_shake = 0
mountain_scroll = 0
ground_scroll = 0

# Fonts
game_font = pygame.font.Font(None, int(HEIGHT * 0.05))
button_font = pygame.font.Font(None, int(HEIGHT * 0.04))
title_font = pygame.font.Font(None, int(HEIGHT * 0.08))

# Bird & Pipe Settings
bird_size = int(WIDTH * 0.07)
bird_rect = pygame.Rect(WIDTH // 4, HEIGHT // 2, bird_size, int(bird_size * 0.75))

pipe_width = int(WIDTH * 0.15)
pipe_gap = int(HEIGHT * 0.25)
pipe_list = []
SPAWNPIPE = pygame.USEREVENT
pygame.time.set_timer(SPAWNPIPE, 1400)

particles = []
clouds = [[random.randint(0, WIDTH), random.randint(int(HEIGHT*0.05), int(HEIGHT*0.4)), random.uniform(0.2, 0.6), random.uniform(0.8, 1.5)] for _ in range(5)]

button_w, button_h = int(WIDTH * 0.4), int(HEIGHT * 0.07)
restart_rect = pygame.Rect(WIDTH // 2 - button_w // 2, HEIGHT // 2 + 40, button_w, button_h)
pause_rect = pygame.Rect(WIDTH - int(WIDTH * 0.15), int(HEIGHT * 0.02), int(WIDTH * 0.1), int(WIDTH * 0.1))

# --- FUNCTIONS ---

def show_loading_screen():
    loading_font = pygame.font.Font(None, int(HEIGHT * 0.15)) 
    text_surf = loading_font.render("MANU", True, MANU_COLOR)
    text_rect = text_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    alpha_surf = pygame.Surface(text_rect.size, pygame.SRCALPHA)
    
    alpha, fade_dir, running = 0, 3, True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

        alpha += fade_dir
        if alpha >= 255:
            alpha = 255
            pygame.time.delay(800) 
            fade_dir = -4 
        elif alpha <= 0 and fade_dir < 0:
            running = False 

        screen.fill(BLACK)
        alpha_surf.fill((0, 0, 0, 0)) 
        alpha_surf.blit(text_surf, (0, 0))
        alpha_surf.set_alpha(alpha)
        screen.blit(alpha_surf, text_rect)
        pygame.display.update()
        clock.tick(60)

def draw_mountains(offset):
    base_y = HEIGHT - 60
    for i in range(-1, 3):
        start_x = i * WIDTH - (offset % WIDTH)
        pygame.draw.polygon(screen, MOUNTAIN_COLOR_1, [(start_x, base_y), (start_x + WIDTH//2, base_y - HEIGHT//3), (start_x + WIDTH, base_y)])
        pygame.draw.polygon(screen, MOUNTAIN_COLOR_2, [(start_x + WIDTH//4, base_y), (start_x + WIDTH//1.5, base_y - HEIGHT//4), (start_x + WIDTH*1.2, base_y)])

def draw_clouds():
    for cloud in clouds:
        x, y, speed, scale = cloud
        cloud[0] -= speed
        if cloud[0] < -WIDTH*0.2: 
            cloud[0] = WIDTH + 50
            cloud[1] = random.randint(int(HEIGHT*0.05), int(HEIGHT*0.4))
        
        pygame.draw.circle(screen, WHITE, (int(x), int(y)), int(30 * scale))
        pygame.draw.circle(screen, WHITE, (int(x + 25 * scale), int(y - 15 * scale)), int(35 * scale))
        pygame.draw.circle(screen, WHITE, (int(x + 50 * scale), int(y)), int(30 * scale))

def get_bird_surface(size):
    surf = pygame.Surface((int(size*1.6), size), pygame.SRCALPHA)
    body_rect = pygame.Rect(0, 0, size, int(size * 0.75))
    pygame.draw.ellipse(surf, (255, 215, 0), body_rect)
    pygame.draw.ellipse(surf, BLACK, body_rect, 2)
    
    wing_rect = pygame.Rect(int(size*0.1), int(size*0.3), int(size*0.4), int(size*0.25))
    pygame.draw.ellipse(surf, WHITE, wing_rect)
    pygame.draw.ellipse(surf, BLACK, wing_rect, 1)
    
    eye_x, eye_y, eye_r = int(size * 0.65), int(size * 0.2), int(size * 0.15)
    pygame.draw.circle(surf, WHITE, (eye_x, eye_y), eye_r)
    pygame.draw.circle(surf, BLACK, (eye_x + int(eye_r*0.4), eye_y), int(eye_r * 0.4))
    
    beak = [(int(size*0.9), int(size*0.35)), (int(size*1.3), int(size*0.45)), (int(size*0.9), int(size*0.6))]
    pygame.draw.polygon(surf, (255, 140, 0), beak)
    pygame.draw.polygon(surf, BLACK, beak, 1)
    return surf

def create_pipe(current_score):
    min_h, max_h = int(HEIGHT * 0.2), int(HEIGHT * 0.55)
    random_pipe_pos = random.randint(min_h, max_h)
    
    bottom_pipe = pygame.Rect(WIDTH, random_pipe_pos, pipe_width, HEIGHT - random_pipe_pos)
    top_pipe = pygame.Rect(WIDTH, 0, pipe_width, random_pipe_pos - pipe_gap)
    is_moving = current_score >= 10 and random.random() > 0.7 
    
    return {
        'bottom': bottom_pipe, 
        'top': top_pipe, 
        'moving': is_moving, 
        'base_y': random_pipe_pos, 
        'time': random.uniform(0, 10)
    }

def move_pipes(pipes, speed):
    for p in pipes:
        p['bottom'].x -= speed
        p['top'].x -= speed
        if p['moving']:
            p['time'] += 0.05
            oscillation = math.sin(p['time']) * (HEIGHT * 0.08)
            p['bottom'].y = p['base_y'] + oscillation
            p['top'].bottom = p['base_y'] - pipe_gap + oscillation
            p['bottom'].height = HEIGHT - p['bottom'].y
    return [p for p in pipes if p['bottom'].right > 0]

def draw_pipes(pipes):
    for p in pipes:
        for rect in [p['bottom'], p['top']]:
            pygame.draw.rect(screen, PIPE_GREEN, rect)
            pygame.draw.rect(screen, PIPE_BORDER, rect, 3)
            if rect.y == 0:
                pygame.draw.rect(screen, PIPE_GREEN, (rect.x - 5, rect.bottom - 30, pipe_width + 10, 30))
                pygame.draw.rect(screen, PIPE_BORDER, (rect.x - 5, rect.bottom - 30, pipe_width + 10, 30), 3)
            else:
                pygame.draw.rect(screen, PIPE_GREEN, (rect.x - 5, rect.y, pipe_width + 10, 30))
                pygame.draw.rect(screen, PIPE_BORDER, (rect.x - 5, rect.y, pipe_width + 10, 30), 3)

def check_collision(pipes):
    for p in pipes:
        if bird_rect.colliderect(p['bottom']) or bird_rect.colliderect(p['top']):
            return False
    if bird_rect.top <= -50 or bird_rect.bottom >= HEIGHT - 60:
        return False
    return True

def draw_animated_ground(offset):
    ground_y = HEIGHT - 60
    ground_rect = pygame.Rect(0, ground_y, WIDTH, 60)
    pygame.draw.rect(screen, GROUND_COLOR, ground_rect)
    
    stripe_width = 40
    for i in range(-1, (WIDTH // stripe_width) + 2):
        stripe_x = i * stripe_width - (offset % stripe_width)
        pygame.draw.polygon(screen, GROUND_STRIPE, [
            (stripe_x, ground_y), 
            (stripe_x + 20, ground_y), 
            (stripe_x - 10, HEIGHT), 
            (stripe_x - 30, HEIGHT)
        ])
    pygame.draw.line(screen, BLACK, (0, ground_y), (WIDTH, ground_y), 3)

def draw_pause_button():
    pygame.draw.rect(screen, WHITE, pause_rect, border_radius=10)
    pygame.draw.rect(screen, BLACK, pause_rect, 2, border_radius=10)
    pygame.draw.rect(screen, BLACK, (pause_rect.centerx - 10, pause_rect.centery - 12, 6, 24))
    pygame.draw.rect(screen, BLACK, (pause_rect.centerx + 4, pause_rect.centery - 12, 6, 24))

# --- MAIN RUN ---
show_loading_screen()
bird_surface_original = get_bird_surface(bird_size)

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit(); sys.exit()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if game_state == 'READY':
                game_state = 'PLAYING'
                bird_movement = -HEIGHT * 0.012
                sound_jump.play()

            elif game_state == 'PLAYING':
                if pause_rect.collidepoint(event.pos):
                    game_state = 'PAUSED'
                else:
                    bird_movement = -HEIGHT * 0.012
                    sound_jump.play()
                    for _ in range(6):
                        particles.append([bird_rect.centerx, bird_rect.bottom, random.randint(3, 7), random.uniform(-2, 2), random.uniform(2, 5)])
            
            elif game_state == 'PAUSED':
                game_state = 'PLAYING'
            
            elif game_state == 'GAMEOVER':
                if restart_rect.collidepoint(event.pos):
                    game_state = 'READY'
                    pipe_list.clear()
                    particles.clear()
                    bird_rect.center = (WIDTH // 4, HEIGHT // 2)
                    bird_movement = 0
                    score = 0
                    screen_shake = 0

        if event.type == SPAWNPIPE and game_state == 'PLAYING':
            pipe_list.append(create_pipe(int(score)))

    shake_x, shake_y = (random.randint(-10, 10), random.randint(-10, 10)) if screen_shake > 0 else (0, 0)
    if screen_shake > 0: screen_shake -= 1

    screen.fill(SKY_BLUE)
    draw_clouds()
    
    if game_state in ['PLAYING', 'READY']:
        mountain_scroll += int(WIDTH * 0.002)
    draw_mountains(mountain_scroll)

    current_speed = int(WIDTH * 0.012) + min(int(score * 0.2), 10)

    if game_state == 'PLAYING':
        bird_movement += gravity
        bird_rect.centery += int(bird_movement)
        
        angle = -bird_movement * 2.5
        angle = max(min(angle, 35), -80)
        rotated_bird = pygame.transform.rotozoom(bird_surface_original, angle, 1)
        
        for p in particles[:]:
            p[0] -= current_speed * 0.5; p[1] += p[4]; p[2] -= 0.2
            if p[2] <= 0: particles.remove(p)
            else: pygame.draw.circle(screen, WHITE, (int(p[0]) + shake_x, int(p[1]) + shake_y), int(p[2]))

        screen.blit(rotated_bird, rotated_bird.get_rect(center=(bird_rect.centerx + shake_x, bird_rect.centery + shake_y)))
        
        pipe_list = move_pipes(pipe_list, current_speed)
        draw_pipes(pipe_list)
        
        prev_score = int(score)
        score += 0.012
        if int(score) > prev_score:
            sound_score.play()

        if not check_collision(pipe_list):
            sound_hit.play()
            game_state = 'GAMEOVER'
            screen_shake = 15
            if score > high_score: high_score = score

    elif game_state in ['READY', 'PAUSED']:
        if game_state == 'READY':
            bird_rect.centery = HEIGHT//2 + math.sin(pygame.time.get_ticks() / 200) * 15
        screen.blit(bird_surface_original, bird_surface_original.get_rect(center=bird_rect.center))
        draw_pipes(pipe_list)

    elif game_state == 'GAMEOVER':
        rotated_bird = pygame.transform.rotozoom(bird_surface_original, -90, 1)
        screen.blit(rotated_bird, rotated_bird.get_rect(center=(bird_rect.centerx + shake_x, bird_rect.centery + shake_y)))
        draw_pipes(pipe_list)

    if game_state == 'PLAYING':
        draw_pause_button()
        score_txt = game_font.render(str(int(score)), True, WHITE)
        screen.blit(score_txt, score_txt.get_rect(center=(WIDTH // 2, int(HEIGHT * 0.1))))

    elif game_state == 'READY':
        title = title_font.render("TAP TO START", True, WHITE)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 3)))

    elif game_state == 'PAUSED':
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))
        pause_txt = title_font.render("PAUSED", True, WHITE)
        screen.blit(pause_txt, pause_txt.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

    elif game_state == 'GAMEOVER':
        score_surf = game_font.render(f'Score: {int(score)}', True, WHITE)
        high_surf = game_font.render(f'High Score: {int(high_score)}', True, (255, 215, 0))
        screen.blit(score_surf, score_surf.get_rect(center=(WIDTH // 2 + shake_x, int(HEIGHT * 0.3) + shake_y)))
        screen.blit(high_surf, high_surf.get_rect(center=(WIDTH // 2 + shake_x, int(HEIGHT * 0.4) + shake_y)))
        
        pygame.draw.rect(screen, (231, 76, 60), restart_rect.move(shake_x, shake_y), border_radius=15)
        pygame.draw.rect(screen, WHITE, restart_rect.move(shake_x, shake_y), 3, border_radius=15)
        btn_text = button_font.render('RESTART', True, WHITE)
        screen.blit(btn_text, btn_text.get_rect(center=restart_rect.move(shake_x, shake_y).center))

    if game_state in ['PLAYING', 'READY']:
        ground_scroll = (ground_scroll + current_speed) % 40 if 'current_speed' in locals() else (ground_scroll + int(WIDTH * 0.012)) % 40
    draw_animated_ground(ground_scroll)

    pygame.display.update()
    clock.tick(60)
