
import random
import time
import socket
import threading
import pickle

import pygame
from pygame.locals import *

import scoreboard as scoreboard
from scoreboard import player_new

pygame.font.init()
pygame.init()


screen_size = pygame.display.get_desktop_sizes()
screen = pygame.display.set_mode((screen_size[0]), flags=pygame.SCALED, vsync=1)
clock = pygame.time.Clock()
dt = 0


win_threshold = 2

EVT_SHOW_STATUS = pygame.USEREVENT + 10
EVT_TO_SINGLEPLAYER = pygame.USEREVENT + 11

def net_role():
    role, _ = multiplayer_properties.get()
    return role

def is_net_client():
    if not is_multiplayer:
        return False
    role, _ = multiplayer_properties.get()
    return role == "client"

def is_net_host():
    return net_role() == "host"

client_input = {"bat2_y": 0.0, "pause_toggle": False}

net_state = {"paused": False, "winner": None, "winner_until": 1.0}

win_overlay = {"winner": None, "until": 1.0, "saved": False}

interrupt = False

is_multiplayer = False

class bat:
    def __init__(self, color, Is_left, screen_width, screen_height, width = 20, height = 200):
        self.color = color
        self.width = width
        self.height = height
        self.Is_left = Is_left
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.bat_x = self.screen_width - self.width

        if self.Is_left:
            self.position = pygame.Vector2(0, self.screen_height / 2)
        else:
            self.position = pygame.Vector2(self.screen_width - self.width, self.screen_height / 2)

    @property
    def rect(self):
        return pygame.Rect(self.position.x, self.position.y, self.width, self.height)

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)
    
    def move(self, value):
        self.position.y += value * dt
        if self.position.y < 0:
            self.position.y = 0
        elif self.position.y > self.screen_height - self.height:
            self.position.y = self.screen_height - self.height

    def check_collision(self, location):
        return self.rect.collidepoint(location)
    
    def get_position(self):
        return self.position.y
    
    def set_position(self, y):
        self.position.y = y
    

bat1 = bat("white", True, screen.get_width(), screen.get_height())
bat2 = bat("white", False, screen.get_width(), screen.get_height())



class ball:
    def __init__(self, color, max_speed, screen_width, screen_height, radius = 10, speed_multiplication = 1.5):
        self.max_Speed = max_speed
        self.radius = radius
        self.speed_multiplication = speed_multiplication
        self.color = color

        self.screen_width = screen_width
        self.screen_height = screen_height

        self.position = pygame.Vector2(self.screen_width / 2, self.screen_height / 2)
        self.direction = pygame.Vector2(random.randrange(-5, 5, 2) * 2, random.randrange(-5, 5, 2) * 2)
    
    def reset(self, to_left):
        self.position = pygame.Vector2(self.screen_width / 2, self.screen_height / 2)

        def non_zero_x(low, high, step):
            x = 0
            while x == 0:
                x = random.randrange(low, high, step)
            return x

        if to_left is True:
            self.direction = pygame.Vector2(non_zero_x(-8, -2, 2), random.randrange(-5, 5, 2))
        elif to_left == "random":
            self.direction = pygame.Vector2(non_zero_x(-5, 5, 2) * 2, random.randrange(-5, 5, 2) * 2)
        else:
            self.direction = pygame.Vector2(non_zero_x(2, 8, 2), random.randrange(-5, 5, 2))

    def move(self):
        self.position += self.direction

    def bounce_vertical(self):
        self.direction.y *= -1

    def bounce_horizontal(self):
        self.direction.x *= -1
        if abs(self.direction.x) < self.max_Speed:
            self.direction *= self.speed_multiplication
    
    def check_collision(self):
        if self.position.y < self.radius or self.position.y > self.screen_height - self.radius + 5:
            self.bounce_vertical()

    def check_bat_collision(self, *bats):
        for bat in bats:
            if bat.check_collision(self.position):
                self.bounce_horizontal()
                break
    
    def draw(self, surface):
        pygame.draw.circle(surface, self.color, self.position, self.radius)

    def is_out_left(self):
        return self.position.x < -25 + self.radius

    def is_out_right(self):
        return self.position.x > self.screen_width + 25 - self.radius
    
    def get_position(self):
        return self.position
    
    def get_direction(self):
        return self.direction
    
    def set_position(self, pos):
        self.position = pos

    def set_direction(self, direction):
        self.direction = direction
    
    def set_max_speed(self, value):
        speed = [10.0, 15.0, 20.0, 25.0]
        self.max_Speed = speed[value]

game_ball = ball("white", 15.0, screen.get_width(), screen.get_height())


def draw_win_overlay(side):
    text = "Win!"
    overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    font = pygame.font.SysFont("sans", 80, True, False)
    msg = font.render(text, True, "white")
    screen.blit(overlay, (0, 0))
    if side == "left":
        screen.blit(msg, (screen.get_width() / 4 - msg.get_width() / 2, screen.get_height() / 2 - msg.get_height() / 2))
    else:
        screen.blit(msg, (screen.get_width() * 3 / 4 - msg.get_width() / 2, screen.get_height() / 2 - msg.get_height() / 2))


class name_input_screen:
    def __init__(self, screen, font, clock):
        self.screen = screen
        self.font = font
        self.clock = clock
        self.playernames = ["", ""]
    
    def input_name(self, player_number):
        if self.playernames[player_number] == "":
            
            names = scoreboard.scoreboard_new.get_names()

            active = True

            suggestion_text = None

            while active:
                self.screen.fill("black")

                name_text = self.font.render(f"Enter Player {player_number + 1} Name:", True, "white")
                input_text = self.font.render(self.playernames[player_number], True, "white")
                
                if not names == "Database created!":
                    matches = []
                    match = ""
                    if len(self.playernames[player_number]) >= 1:
                        for name in names:
                            if (name.lower()).startswith((self.playernames[player_number]).lower()):
                                matches.append(name)
                                if not match:
                                    match = name
                        
                    if match and match.lower() != (self.playernames[player_number].lower()):
                        input_length = len(self.playernames[player_number])
                        suggestion_text = self.font.render(match[input_length:], True, "grey")
                    else:
                        suggestion_text = None

                offset = (name_text.get_width() + input_text.get_width()) / 2
                self.screen.blit(name_text, (self.screen.get_width() / 2 - offset, self.screen.get_height() / 2 + 5))
                self.screen.blit(input_text, ((self.screen.get_width() / 2 + 330) - offset, self.screen.get_height() / 2 + 5))
                if suggestion_text:
                    self.screen.blit(suggestion_text, ((self.screen.get_width() / 2 + 330 + input_text.get_width()) - offset, self.screen.get_height() / 2 + 5))

                pygame.display.flip()

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()

                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_RETURN:
                            if self.playernames[player_number].strip().lower() == "bot":
                                warning_text = self.font.render("Name 'Bot' is not allowed!", True, "red")
                                self.screen.blit(warning_text, (self.screen.get_width() / 2 - warning_text.get_width() / 2,self.screen.get_height() / 2 + 50))
                                pygame.display.flip()
                                pygame.time.delay(1500)
                            elif self.playernames[1].strip().lower() == self.playernames[0].strip().lower():
                                warning_text = self.font.render("Same name not allowed twice!", True, "red")
                                self.screen.blit(warning_text, (self.screen.get_width() / 2 - warning_text.get_width() / 2,self.screen.get_height() / 2 + 50))
                                pygame.display.flip()
                                pygame.time.delay(1500)

                            else:
                                active = False
                        elif event.key == pygame.K_BACKSPACE:
                            self.playernames[player_number] = self.playernames[player_number][:-1]
                        elif event.key == pygame.K_TAB:
                            self.playernames[player_number] = match
                            active = False
                        else:
                            if len(self.playernames[player_number]) < 15:
                                self.playernames[player_number] += event.unicode

                self.clock.tick(30)

            return self.playernames[player_number]
        else:
            return self.playernames[player_number]
    
    def get_names(self):
        names = self.playernames[:]
        if pausemenu.is_bot_match() and not names[1]:
            names[1] = "Bot"
        return names
    
    def set_names(self, pos, name):
        self.playernames[pos] = name      

if __name__ == "__main__":
    font_names = pygame.font.SysFont("sans", 40, True, False)
    name_input = name_input_screen(screen, font_names, clock)

    player1 = name_input.input_name(0)


class scoreboard_ingame:
    def __init__(self, color, screen_width, win_threshold, name_input, score1 = 0, score2 = 0):
        self.color = color
        self.score1 = score1
        self.score2 = score2
        self.screen_width = screen_width
        self.win_threshold = win_threshold
        self.name_input = name_input
        self.game = "Pong"

        self.font_scoreboard = pygame.font.SysFont("sans", 40, True, False)
    def draw(self, surface):
        score = self.font_scoreboard.render(f"{self.score1}   {self.score2}", True, self.color)
        surface.blit(score, (self.screen_width / 2.068, 0))

    def get_score(self):
        return [self.score1, self.score2]

    def write_to_database(self, player_name, number_of_games, wins, record = 0):
        player = scoreboard.player_new(player_name, self.game, number_of_games, wins, record)
        playerstats = scoreboard.scoreboard_new.getStats(player)
        if isinstance(playerstats, dict):
            player.number_of_games = int(playerstats["number of games"]) + number_of_games
            player.wins = int(playerstats["wins"]) + wins
            scoreboard.scoreboard_new.save(player)
        else:
            print(playerstats)


    def update_score(self, score1, score2):
        self.score1 = score1
        self.score2 = score2
    
    def reset_score(self):
        self.score1 = 0
        self.score2 = 0
    
    def set_game(self, game):
        self.game = game

if __name__ == "__main__":
    scoreboard_instance = scoreboard_ingame("white", screen.get_width(), win_threshold, name_input)

class pause_menu:
    def __init__(self, botmatch, surface, screen_width, screen_height):
        self.paused = False
        self.font_pausemenu = pygame.font.SysFont("sans", 80, True, False)
        self.font_scoreboard = pygame.font.SysFont("sans", 36, True, False)
        self.screen_width = screen_width 
        self.screen_height = screen_height
        self.surface = surface
        self.botmatch = botmatch
        self.show_difficulty = False
        self.bot_button = pygame.Rect(0, 0, 0, 0)
        self.twoplayer_button = pygame.Rect(0, 0, 0, 0)
        self.difficulty_button1 = pygame.Rect(0, 0, 0, 0)
        self.difficulty_button2 = pygame.Rect(0, 0, 0, 0)
        self.difficulty_button3 = pygame.Rect(0, 0, 0, 0)
        self.difficulty_button4 = pygame.Rect(0, 0, 0, 0)
        self.online_multiplayer_button = pygame.Rect(0, 0, 0, 0)
        self._clock = pygame.time.Clock()

    def _hover_fill(self, rect):

        hover_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        hover_surf.fill((255, 255, 255, 50))
        self.surface.blit(hover_surf, rect.topleft)

    def render(self, paused):
        screen.fill("black")
        self.paused = paused
        mouse_pos = pygame.mouse.get_pos()

        bot_rect    = pygame.Rect(self.screen_width/2 - 350, self.screen_height/2, 200, 100)
        two_rect    = pygame.Rect(self.screen_width/2 - 100, self.screen_height/2, 200, 100)
        online_rect = pygame.Rect(self.screen_width/2 + 155, self.screen_height/2, 200, 100)
        r1 = pygame.Rect(screen.get_width()/2 - 365, screen.get_height()/1.5 - 20, 160, 60)
        r2 = pygame.Rect(screen.get_width()/2 - 185, screen.get_height()/1.5 - 20, 160, 60)
        r3 = pygame.Rect(screen.get_width()/2 - 5, screen.get_height()/1.5 - 20, 160, 60)
        r4 = pygame.Rect(screen.get_width()/2 +   175, screen.get_height()/1.5 - 20, 200, 60)
        over = [r1.collidepoint(mouse_pos), r2.collidepoint(mouse_pos), r3.collidepoint(mouse_pos), r4.collidepoint(mouse_pos)]

        self.bot_button = bot_rect
        self.twoplayer_button = two_rect
        self.online_multiplayer_button = online_rect

        over_bot    = bot_rect.collidepoint(mouse_pos)
        over_two    = two_rect.collidepoint(mouse_pos)
        over_online = online_rect.collidepoint(mouse_pos)

        try:
            if over_bot or over_two or over_online or over[0] or over[1] or over[2] or over[3]:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
            else:
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        except Exception:
            pass

        bot_border = 8 if self.botmatch else 4
        two_border = 4 if self.botmatch else 8
        online_border = 4

        pygame.draw.rect(self.surface, "white", bot_rect, bot_border, 15)
        pygame.draw.rect(self.surface, "white", two_rect, two_border, 15)
        pygame.draw.rect(self.surface, "white", online_rect, online_border, 15)

        if over_bot: self._hover_fill(bot_rect)
        if over_two: self._hover_fill(two_rect)
        if over_online: self._hover_fill(online_rect)

        Pause_text = self.font_pausemenu.render("Paused", True, "White")
        Botmatch_text1 = self.font_scoreboard.render("Play against", True, "White")
        Twoplayer_text1 = self.font_scoreboard.render("Play against", True, "White")
        Botmatch_text2 = self.font_scoreboard.render("Bot", True, "White")
        Twoplayer_text2 = self.font_scoreboard.render("other Player", True, "White")
        online_multiplayer_text1 = self.font_scoreboard.render("online", True, "White")
        online_multiplayer_text2 = self.font_scoreboard.render("Multiplayer", True, "White")

        screen.blit(Pause_text, (screen.get_width() / 2 - (Pause_text.get_width() /2), screen.get_height() / 2.8))
        screen.blit(Botmatch_text1, (screen.get_width() /2 - 336, screen.get_height() /2 + 6))
        screen.blit(Twoplayer_text1, (screen.get_width() / 2 - 86, screen.get_height() / 2 + 6))
        screen.blit(Botmatch_text2, (screen.get_width() /2 - 280, screen.get_height() /2 + 6 + Botmatch_text2.get_height()))
        screen.blit(Twoplayer_text2, (screen.get_width() / 2 - 86, screen.get_height() / 2 + 6 + Twoplayer_text2.get_height()))
        screen.blit(online_multiplayer_text1, (screen.get_width() / 2 + 214, screen.get_height() / 2 + 6))
        screen.blit(online_multiplayer_text2, (screen.get_width() / 2 + 180, screen.get_height() / 2 + 6 + Twoplayer_text2.get_height()))

        if self.show_difficulty:
            self.render_difficulty_buttons()

        pygame.display.flip()

    def render_difficulty_buttons(self):
        r1 = pygame.Rect(screen.get_width()/2 - 365, screen.get_height()/1.5 - 20, 160, 60)
        r2 = pygame.Rect(screen.get_width()/2 - 185, screen.get_height()/1.5 - 20, 160, 60)
        r3 = pygame.Rect(screen.get_width()/2 - 5, screen.get_height()/1.5 - 20, 160, 60)
        r4 = pygame.Rect(screen.get_width()/2 +   175, screen.get_height()/1.5 - 20, 200, 60)

        self.difficulty_button1, self.difficulty_button2 = r1, r2
        self.difficulty_button3, self.difficulty_button4 = r3, r4

        mouse_pos = pygame.mouse.get_pos()
        over = [r1.collidepoint(mouse_pos), r2.collidepoint(mouse_pos), r3.collidepoint(mouse_pos), r4.collidepoint(mouse_pos)]

        pygame.draw.rect(screen, "white", r1, 4, 15)
        pygame.draw.rect(screen, "white", r2, 4, 15)
        pygame.draw.rect(screen, "white", r3, 4, 15)
        pygame.draw.rect(screen, "white", r4, 4, 15)

        if over[0]: self._hover_fill(r1)
        if over[1]: self._hover_fill(r2)
        if over[2]: self._hover_fill(r3)
        if over[3]: self._hover_fill(r4)

        # try:
        #     if over[0] or over[1] or over[2] or over[3]:
        #         pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
        #     else:
        #         pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
        # except Exception:
        #     pass

        easy_text        = self.font_scoreboard.render("Easy", True, "White")
        medium_text      = self.font_scoreboard.render("Medium", True, "White")
        hard_text        = self.font_scoreboard.render("Hard", True, "White")
        unbeatable_text  = self.font_scoreboard.render("Unbeatable", True, "White")

        screen.blit(easy_text,       (r1.x + 45, r1.y + 8))
        screen.blit(medium_text,     (r2.x + 25, r2.y + 8))
        screen.blit(hard_text,       (r3.x + 45, r3.y + 8))
        screen.blit(unbeatable_text, (r4.x + 20, r4.y + 8))

    def button_logic(self):
        while self.paused:
            self.render(self.paused)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.paused = False

                if event.type == pygame.KEYDOWN:
                    if event.key == K_ESCAPE:
                        self.paused = False

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.bot_button.collidepoint(pygame.mouse.get_pos()):
                        self.botmatch = True
                        self.show_difficulty = True
                        scoreboard_instance.set_game("Pong")

                    elif self.twoplayer_button.collidepoint(pygame.mouse.get_pos()):
                        self.botmatch = False
                        self.show_difficulty = False
                        self.paused = False 
                        if name_input.playernames[1] == "Bot":
                            name_input.playernames[1] = ""
                        name_input.input_name(1)
                        game_ball.reset("random")
                        scoreboard_instance.set_game("Pong")

                    elif self.online_multiplayer_button.collidepoint(pygame.mouse.get_pos()):
                        self.botmatch = False
                        self.show_difficulty = False

                        global interrupt, is_multiplayer
                        interrupt = True
                        is_multiplayer = True
                        render_connection_info("Looking for server")
                        threading.Thread(target=network_discovery.look_for_server, daemon=True).start()
                        game_ball.reset("random")
                        scoreboard_instance.set_game("Pong Multiplayer")
                        self.paused = False

                    if self.difficulty_button1.collidepoint(pygame.mouse.get_pos()):
                        game_bot.change_difficulty(0)
                    elif self.difficulty_button2.collidepoint(pygame.mouse.get_pos()):
                        game_bot.change_difficulty(1)
                    elif self.difficulty_button3.collidepoint(pygame.mouse.get_pos()):
                        game_bot.change_difficulty(2)
                    elif self.difficulty_button4.collidepoint(pygame.mouse.get_pos()):
                        game_bot.change_difficulty(3)

            self._clock.tick(60)

    def is_bot_match(self):
        return self.botmatch

    def is_paused(self):
        return self.paused

    def set_paused(self, paused):
        self.paused = paused

        
pausemenu = pause_menu(True, screen, screen.get_width(), screen.get_height())


import random
import time

class bot(bat): 
    def __init__(self, color, is_left, screen_width, screen_height, width=20, height=200, max_speed=3, ball_radius=10): 
        super().__init__(color, is_left, screen_width, screen_height, width, height) 
        self.max_speed = max_speed 
        self.ball_radius = ball_radius 
        self.ball_pos = None 
        self.ball_direction = None
        self.iterations = 0
        self.previous_y = None

        self.last_adjust_time = time.time()
        self.adjust_interval = random.uniform(1, 5)
        self.current_target_y = None

        self.reflex_threshold = screen_width * 0.25
        self.difficulty = 0

    def predict_ball(self):
        x, y = self.ball_pos.x, self.ball_pos.y
        dx, dy = self.ball_direction.x, self.ball_direction.y
 
        if dx <= 0: 
            return self.ball_pos.y 
    
        while True:
            x += dx
            y += dy

            if y < self.ball_radius or y > self.screen_height - self.ball_radius: 
                dy *= -1 
                
            if x >= self.bat_x - self.ball_radius:
                if self.previous_y == y:
                    if self.iterations < 30:
                        self.iterations += 1
                    else:
                        self.iterations = 0
                        self.previous_y = y
                        return y
                else:
                    self.previous_y = y
                    return y
    
    def move(self, ball_pos, ball_direction): 
        self.ball_pos = ball_pos 
        self.ball_direction = ball_direction 
        predicted_y = self.predict_ball() 

        now = time.time()
        distance_to_bot = abs(self.bat_x - ball_pos.x)

        if distance_to_bot < self.reflex_threshold:
            self.current_target_y = predicted_y - self.height / 2
        else:
            if self.current_target_y is None or (now - self.last_adjust_time > self.adjust_interval):
                micro_offset = random.randint(-15, 15)
                self.current_target_y = (predicted_y + micro_offset) - self.height / 2
                self.last_adjust_time = now
                self.adjust_interval = random.uniform(1, 5)

        distance = self.current_target_y - self.position.y

        if abs(distance) > self.max_speed:
            self.position.y += self.max_speed if distance > 0 else -self.max_speed 
        else: 
            self.position.y = self.current_target_y

        self.position.y = max(0, min(self.position.y, self.screen_height - self.height)) 

    def change_difficulty(self, difficulty): 
        speed = [6, 10, 20, 45] 
        self.max_speed = speed[difficulty]
        game_ball.set_max_speed(difficulty)

        thresholds = [
            self.screen_width * 0.15,
            self.screen_width * 0.35,
            self.screen_width * 0.6,
            self.screen_width * 1.0,
        ]
        self.reflex_threshold = thresholds[difficulty]
        self.difficulty = difficulty


game_bot = bot("blue", False, screen.get_width(), screen.get_height(), max_speed=8, ball_radius=10)


class properties:
    def __init__(self, role = None, player_num = None):
        self.role = role
        self.player_num = player_num

    def set(self, role = None, player_num = None):
        if role is not None:
            self.role = role

        if player_num is not None:
            self.player_num = player_num

    def get(self):
        return self.role, self.player_num

multiplayer_properties = properties()

class NetworkDiscovery:
    def __init__(self, broadcast_port=50000):
        self.broadcast_port = broadcast_port
        self.running = False

    def get_broadcast_address(self):
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        ip_parts = local_ip.split(".")
        ip_parts[-1] = "255"
        return ".".join(ip_parts)

    def look_for_server(self, attempts=5, timeout=0.5):
        self.running = True
        discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        discovery_socket.bind(("", self.broadcast_port))
        discovery_socket.settimeout(timeout)

        connected = False

        for i in range(attempts):
            if not self.running:
                break
            try:
                print("Looking for server", i + 1)
                render_connection_info("Looking for server" + ('.' * (i + 1)))
                data, addr = discovery_socket.recvfrom(1024)
                decoded = data.decode()

                if decoded.startswith("PONG_SERVER:"):
                    server_ip = addr[0]
                    server_port = int(decoded.split(":")[1])
                    print(f"Found server at {server_ip}:{server_port}")
                    render_connection_info("Server found")
                    game_client.connect(server_ip, server_port)
                    connected = True
                    break
            except socket.timeout:
                print("No server found, retrying...")

        discovery_socket.close()

        if not connected and self.running:
            print("No server found.")
            render_connection_info("No server found")
            pygame.time.delay(1000)
            game_server.start()

    def broadcast_server(self, tcp_port):
        self.running = True
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        broadcast_ip = self.get_broadcast_address()
        message = f"PONG_SERVER:{tcp_port}".encode()

        try:
            while self.running:
                broadcast_socket.sendto(message, (broadcast_ip, self.broadcast_port))
                time.sleep(1)
        except Exception as e:
            print("Broadcast server error:", e)
        finally:
            broadcast_socket.close()

    def stop_broadcast(self):
        self.running = False

network_discovery = NetworkDiscovery()

class Client:
    def __init__(self):
        self.socket = None
        self.ip = None
        self.port = None
        self.paused = False
        self.server_closed = False

    def connect(self, ip, port):
        self.ip = ip
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            print(f"Connecting to server at {self.ip}:{self.port}...")
            self.socket.connect((self.ip, self.port))
            print("Connected to server!")
            render_connection_info("Connected to server")
            pygame.time.delay(1000)

            global interrupt
            interrupt = False
            multiplayer_properties.set("client", 2)
            self.interact()

        except ConnectionRefusedError:
            print("Connection failed. Make sure the server is running.")
            render_connection_info("Connection failed")

        except Exception as e:
            print(f"An error occurred: {e}")
            render_connection_info("Connection error")

        finally:
            self.disconnect()

    def interact(self):
        self.socket.settimeout(0.5)
        try:
            while self.socket:
                message = {
                    "bat2_y": client_input["bat2_y"],
                    "player_name_client": name_input.get_names()[0]
                }

                if client_input["pause_toggle"]:
                    message["pause_toggle"] = True
                client_input["pause_toggle"] = False

                try:
                    self.socket.send(pickle.dumps(message))
                except (BrokenPipeError, ConnectionResetError, OSError):
                    print("Lost connection while sending")
                    render_connection_info("Server closed the connection")
                    self.server_closed = True
                    break

                try:
                    response = self.socket.recv(4096)
                except socket.timeout:
                    continue

                if not response:
                    print("lost connection while receiving")
                    self.server_closed = True
                    self.disconnect()
                    break

                game_state = pickle.loads(response)

                bat1.set_position(game_state["bat1_y"])
                bat2.set_position(game_state["bat2_y"])
                game_ball.set_position(game_state["ball_pos"])
                game_ball.set_direction(game_state["ball_direction"])
                scoreboard_instance.update_score(game_state["score1"], game_state["score2"])
                name_input.set_names(0, game_state["player_name1"])
                name_input.set_names(1, game_state["player_name2"])

                net_state["paused"] = game_state.get("paused", False)

                if game_state.get("winner"):
                    net_state["winner"] = game_state["winner"]
                    net_state["winner_until"] = time.time() + 1.5
                else:
                    net_state["winner"] = None
                    net_state["winner_until"] = 0.0

                time.sleep(0.01)

        except Exception as e:
            print("Error in interactive_session:", e)
            render_connection_info("Server closed the connection")
            time.sleep(1000)
            self.server_closed = True

        finally:
            self.disconnect()

    def disconnect(self):
        if self.socket:
            try: self.socket.close()
            except: pass
            self.socket = None

        if self.server_closed:
            post_status_from_thread("Server was closed")
            reason = "server_closed"
        else:
            post_status_from_thread("Disconnected from server")
            reason = "manual_or_error"

        try:
            pygame.event.post(pygame.event.Event(EVT_TO_SINGLEPLAYER, {"by": "client", "reason": reason}))
        except Exception:
            pass

        self.server_closed = False



game_client = Client()

class Server:
    def __init__(self, host='0.0.0.0', port=12345, broadcast_port=50000):
        self.host = host
        self.port = port
        self.broadcast_port = broadcast_port

        self.broadcast_thread = None
        self.paused = False
        self.running = False

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.discovery = NetworkDiscovery(self.broadcast_port)

        self.broadcast_thread = threading.Thread(
            target=self.discovery.broadcast_server,
            args=(self.port,),
            daemon=True
        )
        self.broadcast_thread.start()

        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            render_connection_info("Started server")
            pygame.time.delay(1000)
            print(f"Server running on {self.host}:{self.port}")
            multiplayer_properties.set("host", 1)

            self.running = True

            while self.running:
                try:
                    print("\nWaiting for a connection...")
                    render_connection_info("Waiting for client connection")

                    client_socket, client_address = self.server_socket.accept()
                    if not self.running:
                        client_socket.close()
                        break

                    print(f"Connected to client: {client_address}")
                    render_connection_info("Connected to client")
                    pygame.time.delay(1000)

                    global interrupt
                    interrupt = False

                    self.handle_client(client_socket)

                except OSError as e:
                    if not self.running:
                        break
                    else:
                        print(f"Socket error: {e}")
                        break

        except KeyboardInterrupt:
            print("\nServer is shutting down...")
        finally:
            try:
                self.server_socket.close()
            except:
                pass
            print("Server closed")

    def stop(self):
        """Stop server gracefully."""
        self.running = False
        self.discovery.stop_broadcast()
        try:
            self.server_socket.close()
        except:
            pass
        if self.broadcast_thread and self.broadcast_thread.is_alive():
            self.broadcast_thread.join()

    def handle_client(self, client_socket):
        try:
            while self.running:
                data = client_socket.recv(1024)
                if not data:
                    break

                client_update = pickle.loads(data)

                if "bat2_y" in client_update:
                    bat2.set_position(client_update["bat2_y"])

                if "pause_toggle" in client_update and client_update["pause_toggle"]:
                    self.paused = not self.paused

                if "player_name_client" in client_update:
                    name_input.set_names(1, client_update["player_name_client"])

                winner = None
                if scoreboard_instance.get_score()[0] >= scoreboard_instance.win_threshold:
                    winner = "left"
                elif scoreboard_instance.get_score()[1] >= scoreboard_instance.win_threshold:
                    winner = "right"

                game_state = {
                    "bat1_y": bat1.get_position(),
                    "bat2_y": bat2.get_position(),
                    "ball_pos": game_ball.get_position(),
                    "ball_direction": game_ball.get_direction(),
                    "score1": scoreboard_instance.get_score()[0],
                    "score2": scoreboard_instance.get_score()[1],
                    "paused": self.paused,
                    "winner": win_overlay["winner"],
                    "player_name1": name_input.get_names()[1],
                    "player_name2": name_input.get_names()[0],
                }

                client_socket.send(pickle.dumps(game_state))

        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client_socket.close()
            print("Client connection closed")
            render_connection_info("Client disconnected")

            reset_multiplayer()
            pausemenu.set_paused(True)

game_server = Server()

connection_status = ""
show_connection_overlay = False
overlay_display_until = 0.0

def render_connection_info(state):
    global connection_status, show_connection_overlay, interrupt
    connection_status = state
    show_connection_overlay = True
    interrupt = True

def post_status_from_thread(state):
    try:
        pygame.event.post(pygame.event.Event(EVT_SHOW_STATUS, {"text": state}))
    except Exception:
        print(state)


def reset_multiplayer():
    global client_input, net_state, win_overlay, interrupt


    if not is_net_host():
        multiplayer_properties.set(None, None)


    client_input = {"bat2_y": 0.0, "pause_toggle": False}
    net_state = {"paused": False, "winner": None, "winner_until": 1.0}
    win_overlay = {"winner": None, "until": 1.0, "saved": False}
    interrupt = False

    multiplayer_properties.set(None, None)

    if game_client.socket:
        try: game_client.socket.close()
        except: pass
        game_client.socket = None


def singleplayer_mode(type):
    global is_multiplayer, interrupt, client_input, net_state, win_overlay

    network_discovery.running = False
    interrupt = False

    multiplayer_properties.set(None, None)   
    is_multiplayer = False                   


    if game_client.socket:
        try:
            game_client.socket.close()
        except: pass
        game_client.socket = None

    if type == "server":
        try: game_server.stop()
        except: pass


    client_input = {"bat2_y": 0.0, "pause_toggle": False}
    net_state = {"paused": False, "winner": None, "winner_until": 1.0}
    win_overlay = {"winner": None, "until": 1.0, "saved": False}

    pausemenu.botmatch = True
    scoreboard_instance.set_game("Pong")
    name_input.set_names(1, "Bot")
    game_ball.reset("random")


def draw_pause_overlay(text="Paused"):
    overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 140))
    font = pygame.font.SysFont("sans", 80, True, False)
    msg = font.render(text, True, "white")
    screen.blit(overlay, (0, 0))
    screen.blit(msg, (screen.get_width()/2 - msg.get_width()/2,
                      screen.get_height()/2 - msg.get_height()/2))


if __name__ == "__main__":
    running = True
    while running:

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_x:
                    if is_net_host():
                        singleplayer_mode("server")
                    running = False

                if event.key == pygame.K_ESCAPE:
                    if is_net_host() and is_multiplayer:
                        game_server.paused = not game_server.paused
                    elif is_net_client() and is_multiplayer:
                        client_input["pause_toggle"] = True
                    elif not is_multiplayer:
                        pause_game()

            if event.type == EVT_SHOW_STATUS:
                render_connection_info(event.text)

            if event.type == EVT_TO_SINGLEPLAYER:
                if event.dict.get("reason") == "server_closed":
                    render_connection_info("Server was closed")

                singleplayer_mode("client")

                interrupt = False
                show_connection_overlay = False

        def pause_game():   
            pausemenu.render(True)
            pausemenu.button_logic()

        if is_net_host():
            paused_now = game_server.paused
        elif is_net_client():
            paused_now = net_state["paused"]
        else:
            paused_now = False

        if interrupt: 
            for event in pygame.event.get(): 
                if event.type == pygame.QUIT: 
                    running = False 

            screen.fill("black") 
            if show_connection_overlay:
                mouse_pos = pygame.mouse.get_pos()
                overlay = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA) 
                overlay.fill((0, 0, 0, 140)) 
                font = pygame.font.SysFont("sans", 50, True, False) 
                msg = font.render(connection_status or "Connecting...", True, "white") 
                screen.blit(overlay, (0, 0)) 
                screen.blit(msg, (screen.get_width()/2 - msg.get_width()/2, screen.get_height()/2 - msg.get_height()/2))

                return_text = font.render("return", True, "White")
                screen.blit(return_text, (screen.get_width() / 2 - return_text.get_width() + return_text.get_width() /2, screen.get_height() / 2 + 100 + 15))
                return_button = pygame.draw.rect(screen, "white", (screen.get_width() / 2 - return_text.get_width() + 20, screen.get_height() / 2 + 100, 200, 100), 4, 15)
                over_return = return_button.collidepoint(mouse_pos)
                try:
                    if over_return:
                        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
                    else:
                        pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                except Exception:
                    pass

                if over_return:
                    pausemenu._hover_fill(return_button)

                for event in pygame.event.get():
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if return_button.collidepoint(pygame.mouse.get_pos()):
                            if is_net_host():
                                singleplayer_mode("server")
                            else:
                                singleplayer_mode("client")

                pygame.display.flip() 
                dt = clock.tick(60) / 1000 
                continue

        screen.fill("black")
        center_line = pygame.draw.line(screen, "white",(screen.get_width() / 2, 0), (screen.get_width() / 2, screen.get_height()))

        player_names = name_input.get_names()
        if is_net_client() and not pausemenu.is_bot_match():
            name1 = font_names.render(player_names[1], True, "White")
            name2 = font_names.render(player_names[0], True, "White")
        else:
            name1 = font_names.render(player_names[0], True, "White")
            name2 = font_names.render(player_names[1], True, "White")

        screen.blit(name1, (20, 20))
        screen.blit(name2, (screen.get_width() - name2.get_width() - 20, 20))

        keys = pygame.key.get_pressed()

        if not is_net_client() and is_net_host():
            if keys[pygame.K_w]:
                bat1.move(-800)
            if keys[pygame.K_s]:
                bat1.move(800)

        if pausemenu.is_bot_match() and not is_net_client():
            game_bot.move(game_ball.get_position(), game_ball.get_direction())
        else:
            if is_net_client():
                move = 0
                if keys[pygame.K_w]:
                    move -= 800 * dt
                if keys[pygame.K_s]:
                    move += 800 * dt
                intended = bat2.get_position() + move
                intended = max(0, min(intended, screen.get_height() - bat2.height))
                client_input["bat2_y"] = intended
        
        if not pausemenu.is_bot_match() and not is_net_client() and not is_net_host():
            if keys[pygame.K_w]:
                bat1.move(-800)
            if keys[pygame.K_s]:
                bat1.move(800)
            if keys[pygame.K_UP]:
                bat2.move(-800)
            if keys[pygame.K_DOWN]:
                bat2.move(800)

        if pausemenu.is_bot_match() and not is_net_client() and not is_net_host():
            if keys[pygame.K_w]:
                bat1.move(-800)
            if keys[pygame.K_s]:
                bat1.move(800)


        if not paused_now:
            if is_net_client():
                pass
            else:
                game_ball.move()
                game_ball.check_collision()

                is_out_left = game_ball.is_out_left()
                is_out_right = game_ball.is_out_right()

                if is_out_left:
                    current_score = scoreboard_instance.get_score()
                    scoreboard_instance.update_score(current_score[0], current_score[1] + 1)
                    game_ball.reset(True)

                if is_out_right:
                    current_score = scoreboard_instance.get_score()
                    scoreboard_instance.update_score(current_score[0] + 1, current_score[1])
                    game_ball.reset(False)

                if win_overlay["winner"] is None:
                    s1, s2 = scoreboard_instance.get_score()
                    if s1 >= scoreboard_instance.win_threshold:
                        win_overlay.update({"winner": "left", "until": time.time() + 1.5, "saved": False})
                    elif s2 >= scoreboard_instance.win_threshold:
                        win_overlay.update({"winner": "right", "until": time.time() + 1.5, "saved": False})

                if pausemenu.is_bot_match():
                    game_ball.check_bat_collision(bat1, game_bot)
                else:
                    game_ball.check_bat_collision(bat1, bat2)

        game_ball.draw(screen)
        bat1.draw(screen)
        if pausemenu.is_bot_match() and not is_net_client():
            game_bot.draw(screen)
        else:
            bat2.draw(screen)

        scoreboard_instance.draw(screen)

        if (is_net_host() or is_multiplayer or pausemenu.is_bot_match()) and win_overlay["winner"]:
            draw_win_overlay(win_overlay["winner"])

            game_paused = True

            if time.time() >= win_overlay["until"]:
                if not win_overlay["saved"]:
                    names = name_input.get_names()

                    if win_overlay["winner"] == "left":
                        scoreboard_instance.write_to_database(names[0], 1, 1)
                        scoreboard_instance.write_to_database(names[1], 0, 1)
                    else:
                        scoreboard_instance.write_to_database(names[0], 0, 1)
                        scoreboard_instance.write_to_database(names[1], 1, 1)

                    win_overlay["saved"] = True
                scoreboard_instance.reset_score()
                game_ball.reset("random")
                win_overlay.update({"winner": None, "until": 0.0, "saved": False})
                game_paused = False

        if is_net_client() and net_state["winner"]:
            draw_win_overlay(net_state["winner"])
            client_paused = True

            if time.time() >= net_state["winner_until"]:
                net_state["winner"] = None
                net_state["winner_until"] = 0.0
                client_paused = False


        if paused_now:
            if is_net_host() or is_net_client():
                draw_pause_overlay(text="Paused")
            else:
                pausemenu.render(True)
                pausemenu.button_logic()

        pygame.display.flip()
        dt = clock.tick(60) / 1000

pygame.quit()

