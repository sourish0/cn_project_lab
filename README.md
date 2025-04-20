# Multiplayer Fighting Game Documentation

## Abstract
This document outlines the implementation and architecture of a multiplayer 2D fighting game built using Python’s Pygame library and UDP networking. The game allows two players to battle in real-time over a local network. The server manages the game state and synchronizes the actions of both players, while each client handles player input, rendering, and displaying the game.

---

## 1. Architecture Overview

The architecture of this multiplayer game is based on a simple client-server model using UDP (User Datagram Protocol) sockets for communication. The server maintains the game state and broadcasts updates to all connected clients. Each client is responsible for rendering the game, handling player input, and sending player state updates to the server.

### Components
1. **Server**: 
   - Manages game state, including player positions, health, and game logic.
   - Listens for player input and broadcasts game state updates to clients.

2. **Client**: 
   - Handles user input (movement, jumping, attacking).
   - Displays the game state (sprites, health bars, etc.).
   - Sends player state updates to the server and receives updates about the opponent's state.

---

## 2. Technologies Used

- **Python 3**: Programming language used for the game and networking.
- **Pygame**: A library for game development and rendering graphics.
- **UDP Sockets**: For low-latency real-time communication between the server and clients.
- **Pickle**: For serializing and deserializing data to be sent over the network.
- **Threading (Optional for future)**: Potential use for running separate threads for networking and rendering.

---

## 3. Implementation Steps

### 3.1 Step 1: Designing the Architecture
The system follows a client-server model, where:
- The **server** listens for incoming player data, manages the game state, and sends updates to clients.
- The **client** sends player data (e.g., position, movement, attacks) to the server and receives data about the opponent’s state (e.g., position, health, etc.).

### 3.2 Step 2: Server Code
The server listens on UDP port 9999 for incoming connections. It processes player states and determines the effects of attacks, movements, and other game actions. Here is the server code snippet:

```python
import socket
import pickle

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('0.0.0.0', 9999))
print("UDP server is running on port 9999...")

clients = []
player_states = {}
health = {0: 100, 1: 100}
restart_requests = set()
SPRITE_WIDTH = 60

while True:
    try:
        data, addr = server_socket.recvfrom(1024)

        if addr not in clients:
            clients.append(addr)
            player_idx = clients.index(addr)
            server_socket.sendto(pickle.dumps({"player_idx": player_idx}), addr)
            continue

        player_idx = clients.index(addr)
        state = pickle.loads(data)

        if isinstance(state, dict) and 'restart' in state:
            restart_requests.add(player_idx)
            if len(restart_requests) == 2:
                health = {0: 100, 1: 100}
                restart_requests.clear()
                print("Both players agreed to restart. Game reset.")
            continue

        player_states[player_idx] = state

        if len(clients) == 2:
            other_idx = 1 - player_idx
            other_state = player_states.get(other_idx)

            if state['is_attacking'] and other_state:
                dist = abs((state['x'] + SPRITE_WIDTH // 2) - (other_state['x'] + SPRITE_WIDTH // 2))
                if dist <= 10:
                    if other_state.get('is_guarding', False):
                        health[other_idx] -= 2  # Blocked hit
                    else:
                        health[other_idx] -= 5  # Normal hit
                    health[other_idx] = max(0, health[other_idx])

            response = {
                "x": other_state['x'],
                "y": other_state['y'],
                "is_jumping": other_state['is_jumping'],
                "is_attacking": other_state['is_attacking'],
                "is_guarding": other_state.get('is_guarding', False),
                "moving": other_state['moving'],
                "frame": other_state['frame'],
                "health": health[other_idx],
                "my_health": health[player_idx],
                "game_over": health[0] <= 0 or health[1] <= 0,
                "winner": 1 if health[1] <= 0 else (2 if health[0] <= 0 else 0)
            }
            server_socket.sendto(pickle.dumps(response), addr)

    except Exception as e:
        print("Error:", e)
```

### 3.3 Step 3: Client Code
The client connects to the server and sends player states, including movement, jumping, attacking, and guarding. It also receives the game state (opponent’s position, health, etc.) and renders the game accordingly. Here is the client code snippet:

```python
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
# Use attack sprite as guard pose
player1_guard = player1_attack


player1_index = 0
player1_surface = player1_walk[player1_index]
player1_rect = player1_surface.get_rect(midbottom=(100, 300))

player2_walk = [
    pygame.transform.flip(player1_walk[0], True, False),
    pygame.transform.flip(player1_walk[1], True, False)
]
player2_attack = pygame.transform.flip(player1_attack, True, False)
player2_jump = pygame.transform.flip(player1_jump, True, False)

player2_guard = player2_attack

player2_index = 0
player2_surface = player2_walk[player2_index]
player2_rect = player2_surface.get_rect(midbottom=(700, 300))

gravity = 1
jump_velocity = 0
is_jumping = False
is_attacking = False
is_guarding = False
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
    is_guarding = False

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

        if keys[pygame.K_DOWN]:
            is_guarding = True

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

        if is_guarding:
            player1_surface = player1_guard
        elif is_attacking:
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
            "is_guarding": is_guarding,
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

            if response["is_guarding"]:
                player2_surface = player2_guard
            elif response["is_jumping"]:
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
        msg = "Draw!" if winner == 0 else "You Win!" if winner - 1 == player_idx else "You Lose!"
        text = font.render(msg, True, (255, 255, 255))
        screen.blit(text, (300, 180))

    pygame.display.update()
    clock.tick(60)
```

### 3.4 Step 4: Multithreading
Currently, both client and server handle their tasks in a single thread. For future improvements, **multithreading** could be used to handle network communication and rendering separately.

### 3.5 Step 5: Synchronization and Smoothing
UDP is fast but unreliable, so occasional packet loss is expected. For smoother gameplay:
- Implement **interpolation** to predict missing frames based on player positions.
- Add more robust error handling and synchronization to minimize the impact of packet loss.

---

## 4. Conclusion

This multiplayer 2D fighting game demonstrates the use of Pygame and UDP networking to enable real-time gameplay over a local network. The game’s client-server architecture synchronizes player actions and health, making for a responsive multiplayer experience. The use of UDP ensures low-latency communication, which is essential for fast-paced gameplay.

---

## 5. Future Work

- **Matchmaking**: Implement matchmaking functionality using REST APIs (e.g., Flask or FastAPI) to allow players to find and join games.
- **Movement Smoothing**: Add interpolation techniques for smoother player movement.
- **User Interface**: Create a menu for hosting or joining games.
- **Internet Play**: Extend the game to support internet-wide multiplayer with NAT traversal.
