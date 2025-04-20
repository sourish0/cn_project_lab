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
