import pygame
import socket
import pickle
from sys import exit

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = ('192.168.29.227', 9999)  # 👈 Replace with your server's Wi-Fi IP
client_socket.setblocking(False)

pygame.init()
screen = pygame.display.set_mode((800, 400))
pygame.display.set_caption("Fighting Club")
clock = pygame.time.Clock()

sky_surface = pygame.image.load('Sky.png').convert()
ground_surface = pygame.image.load('ground.png').convert()

player1_walk = [
    pygame.image.load('Player/player_walk_1.png').convert_alpha(),
    pygame.image.load('Player/player_walk_2.png').convert_alpha()
]
player1_attack = pygame.image.load('Player/player_stand.png').convert_alpha()
player1_jump = pygame.image.load('Player/jump.png').convert_alpha()

player1_index = 0
player1_surface = player1_walk[player1_index]
player1_rect = player1_surface.get_rect(midbottom=(100, 300))

player2_walk = [
    pygame.transform.flip(player1_walk[0], True, False),
    pygame.transform.flip(player1_walk[1], True, False)
]
player2_attack = pygame.transform.flip(player1_attack, True, False)
player2_jump = pygame.transform.flip(player1_jump, True, False)
player2_index = 0
player2_surface = player2_walk[player2_index]
player2_rect = player2_surface.get_rect(midbottom=(700, 300))

gravity = 1
jump_velocity = 0
is_jumping = False
is_attacking = False
attack_timer = 0
ground_level = 300

player_health = 100
opponent_health = 100
game_over = False
winner = 0
font = pygame.font.SysFont(None, 48)

player_idx = None

while player_idx is None:
    try:
        client_socket.sendto(pickle.dumps({"init": True}), server_address)
        data, _ = client_socket.recvfrom(1024)
        response = pickle.loads(data)
        if 'player_idx' in response:
            player_idx = response['player_idx']
            print(f"Connected as Player {player_idx + 1}")
    except BlockingIOError:
        pass

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    keys = pygame.key.get_pressed()
    moving = False

    if not game_over:
        if keys[pygame.K_LEFT]:
            player1_rect.x -= 5
            moving = True
        elif keys[pygame.K_RIGHT]:
            player1_rect.x += 5
            moving = True

        if player1_rect.left < 0:
            player1_rect.left = 0
        if player1_rect.right > 800:
            player1_rect.right = 800

        if keys[pygame.K_UP] and not is_jumping:
            is_jumping = True
            jump_velocity = -15

        if is_jumping:
            player1_surface = player1_jump
            player1_rect.y += jump_velocity
            jump_velocity += gravity
            if player1_rect.bottom >= ground_level:
                player1_rect.bottom = ground_level
                is_jumping = False
                jump_velocity = 0

        if keys[pygame.K_SPACE] and not is_attacking:
            is_attacking = True
            attack_timer = 10

        if is_attacking:
            player1_surface = player1_attack
            attack_timer -= 1
            if attack_timer <= 0:
                is_attacking = False
        elif moving and not is_jumping:
            player1_index += 0.1
            if player1_index >= len(player1_walk):
                player1_index = 0
            player1_surface = player1_walk[int(player1_index)]
        elif not is_jumping:
            player1_surface = player1_walk[0]

        player1_state = {
            "x": player1_rect.x,
            "y": player1_rect.y,
            "is_jumping": is_jumping,
            "is_attacking": is_attacking,
            "moving": moving,
            "frame": player1_index
        }

        try:
            client_socket.sendto(pickle.dumps(player1_state), server_address)
        except Exception as e:
            print("Error sending data:", e)

        try:
            data, _ = client_socket.recvfrom(1024)
            response = pickle.loads(data)

            player2_rect.x = response['x']
            player2_rect.y = response['y']
            opponent_health = response['health']
            player_health = response['my_health']
            game_over = response['game_over']
            winner = response['winner']

            if response["is_jumping"]:
                player2_surface = player2_jump
            elif response["is_attacking"]:
                player2_surface = player2_attack
            elif response["moving"]:
                player2_index = response["frame"] % len(player2_walk)
                player2_surface = player2_walk[int(player2_index)]
            else:
                player2_surface = player2_walk[0]

        except BlockingIOError:
            pass

    screen.blit(sky_surface, (0, 0))
    screen.blit(ground_surface, (0, 300))
    screen.blit(player1_surface, player1_rect)
    screen.blit(player2_surface, player2_rect)

    pygame.draw.rect(screen, "red", (50, 30, 200, 20))
    pygame.draw.rect(screen, "green", (50, 30, 2 * player_health, 20))

    pygame.draw.rect(screen, "red", (550, 30, 200, 20))
    pygame.draw.rect(screen, "green", (550, 30, 2 * opponent_health, 20))

    if game_over:
        if winner == 0:
            msg = "Draw!"
        elif winner - 1 == player_idx:
            msg = "You Win!"
        else:
            msg = "You Lose!"
        text = font.render(msg, True, (255, 255, 255))
        screen.blit(text, (300, 180))

    pygame.display.update()
    clock.tick(60)
