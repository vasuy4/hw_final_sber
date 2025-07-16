from flask import Flask, request, jsonify
import random
from collections import deque

class GameServer:
    def __init__(self):
        self.app = Flask(__name__)
        self.state = "room"  # room, tunnel
        self.find_id = 4  # Ищем выход из комнаты
        self.history_direction = []  # История последних направлений
        self.activated_guide = False  # Активирован ли сфинкс
        self.wait = 0
        self.last_position = None  # Последняя позиция персонажа
        self.entrance_exit = None  # Позиция выхода, через который вошли в комнату
        self.visited_exits = set()  # Множество посещенных выходов
        self.room_entry_steps = 0  # Количество шагов в текущей комнате
        
        self.app.add_url_rule('/inputs', view_func=self.handle_inputs, methods=['POST'])
        self.app.add_url_rule('/tasks', view_func=self.handle_tasks, methods=['POST'])
        self.app.add_url_rule('/tasks/last', view_func=self.handle_last_task, methods=['PATCH'])
        self.app.add_url_rule('/notifications', view_func=self.handle_notifications, methods=['POST'])
    
    def find_position(self, view, target_id):
        """Находит позицию объекта на карте"""
        for i, row in enumerate(view):
            for j, cell in enumerate(row):
                if cell == target_id:
                    return (i, j)
        return None

    def find_all_positions(self, view, target_id):
        """Находит все позиции объекта на карте"""
        positions = []
        for i, row in enumerate(view):
            for j, cell in enumerate(row):
                if cell == target_id:
                    positions.append((i, j))
        return positions

    def get_back_direction(self):
        """Возвращает направление, противоположное последнему движению"""
        if not self.history_direction:
            return None
            
        last_move = self.history_direction[-1]
        opposite_map = {
            "Left": "Right",
            "Right": "Left",
            "Up": "Down",
            "Down": "Up"
        }
        return opposite_map.get(last_move)

    def get_valid_directions(self, view, player_pos):
        """Возвращает доступные направления движения"""
        directions = []
        moves = [
            ("Left", 0, -1),
            ("Right", 0, 1),
            ("Up", -1, 0),
            ("Down", 1, 0)
        ]
        
        for name, di, dj in moves:
            ni, nj = player_pos[0] + di, player_pos[1] + dj
            if 0 <= ni < len(view) and 0 <= nj < len(view[0]):
                if view[ni][nj] in {1, 2, 4, 5}:
                    directions.append(name)
                    
        return directions

    def find_path_to_any(self, view, start, targets):
        """Поиск кратчайшего пути к любой цели из списка"""
        if not start or not targets:
            return None
            
        rows = len(view)
        cols = len(view[0])
        visited = [[False] * cols for _ in range(rows)]
        queue = deque()
        queue.append((start, []))  # (position, path)
        
        moves = [
            ("Left", 0, -1),
            ("Right", 0, 1),
            ("Up", -1, 0),
            ("Down", 1, 0)
        ]
        
        while queue:
            (i, j), path = queue.popleft()
            
            if (i, j) in targets:
                return path[0] if path else None
                
            if visited[i][j]:
                continue
                
            visited[i][j] = True
            
            for name, di, dj in moves:
                ni, nj = i + di, j + dj
                if (0 <= ni < rows and 0 <= nj < cols and 
                    not visited[ni][nj] and 
                    view[ni][nj] in {1, 2, 4, 5}):
                    queue.append(((ni, nj), path + [name]))
                    
        return None

    def decide_direction_room(self, view, player_pos):
        """Определяет направление движения в комнате с учетом истории выходов"""
        # Приоритет 1: проводник (5)
        if not self.activated_guide:
            guide_pos = self.find_position(view, 5)
            if guide_pos:
                if player_pos == guide_pos:
                    self.activated_guide = True
                else:
                    direction = self.find_path_to_any(view, player_pos, [guide_pos])
                    if direction:
                        return direction

        if self.activated_guide:
            exit_pos = self.find_position(view, 2)
            if exit_pos:
                direction = self.find_path_to_any(view, player_pos, [exit_pos])
                if direction:
                    return direction

        if self.room_entry_steps < 10:
            valid_dirs = self.get_valid_directions(view, player_pos)
            if valid_dirs:
                return random.choice(valid_dirs)
            return random.choice(["Up", "Down", "Left", "Right"])

        tunnel_exits = self.find_all_positions(view, 4)
        
        valid_exits = [exit for exit in tunnel_exits if exit != self.entrance_exit]
        
        if not valid_exits:
            valid_exits = tunnel_exits
        
        fresh_exits = [exit for exit in valid_exits if exit not in self.visited_exits]
        
        targets = fresh_exits if fresh_exits else valid_exits
        
        if targets:
            direction = self.find_path_to_any(view, player_pos, targets)
            if direction:
                return direction
                
        valid_dirs = self.get_valid_directions(view, player_pos)
        if valid_dirs:
            return random.choice(valid_dirs)
            
        return random.choice(["Up", "Down", "Left", "Right"])

    def decide_direction_tunnel(self, view, player_pos):
        """Определяет направление движения в туннеле"""
        back_dir = self.get_back_direction()
        valid_dirs = self.get_valid_directions(view, player_pos)
        
        if back_dir and back_dir in valid_dirs:
            valid_dirs.remove(back_dir)
        
        if valid_dirs:
            return random.choice(valid_dirs)
            
        return back_dir or random.choice(["Up", "Down", "Left", "Right"])

    def handle_inputs(self):
        data = request.json
        
        if not data or 'view' not in data or not isinstance(data['view'], list):
            return jsonify({"action": "None"}), 400
            
        view = data['view']
        if not all(isinstance(row, list) for row in view) or not all(all(isinstance(cell, int) for cell in row) for row in view):
            return jsonify({"action": "None"}), 400

        player_pos = self.find_position(view, 3)
        if not player_pos:
            return jsonify({"action": random.choice(["Up", "Down", "Left", "Right"])}), 200
        
        if len(self.history_direction) > 0 and self.wait <= 0:
            di_map = {"Left": (0, -1), "Right": (0, 1), "Up": (-1, 0), "Down": (1, 0)}
            di, dj = di_map[self.history_direction[-1]]
            old_i, old_j = player_pos[0] - di, player_pos[1] - dj
            
            if 0 <= old_i < len(view) and 0 <= old_j < len(view[0]):
                if view[old_i][old_j] == 4 and self.state == "tunnel":
                    self.state = "room"
                    
                    self.entrance_exit = (old_i, old_j)
                    self.visited_exits.add((old_i, old_j))
                    self.room_entry_steps = 0
        
        self.wait -= 1
        
        if self.state == "room":
            self.room_entry_steps += 1
            direction = self.decide_direction_room(view, player_pos)
        else:
            direction = self.decide_direction_tunnel(view, player_pos)

        di_map = {"Left": (0, -1), "Right": (0, 1), "Up": (-1, 0), "Down": (1, 0)}
        di, dj = di_map[direction]
        new_i, new_j = player_pos[0] + di, player_pos[1] + dj

        if 0 <= new_i < len(view) and 0 <= new_j < len(view[0]):
            if view[new_i][new_j] == 4:
                if self.state == "room":
                    self.state = "tunnel"
                    self.wait = 2
                    
                    self.entrance_exit = None
        
        self.history_direction.append(direction)
        if len(self.history_direction) > 10:
            self.history_direction.pop(0)
            
        self.last_position = player_pos

        return jsonify({"action": direction}), 200

    def handle_tasks(self):
        data = request.json
        
        if not data or 'type' not in data or 'task' not in data:
            return "", 400
        
        self.activated_guide = True
        self.find_id = 2 
        answer = "Да"

        return jsonify({"answer": answer}), 200

    def handle_last_task(self):
        data = request.json
        
        if not data or 'result' not in data or data['result'] not in ["Ok", "TryAgain", "Fail"]:
            return "", 400

        return "", 200

    def handle_notifications(self):
        data = request.json
        
        if not data or 'type' not in data or 'desc' not in data:
            return "", 400
            
        self.state = "room"
        self.activated_guide = False
        self.find_id = 4
        self.history_direction = []
        self.wait = 0
        self.last_position = None
        self.entrance_exit = None
        self.visited_exits = set()
        self.room_entry_steps = 0
        return "", 200

    def run(self, host='0.0.0.0', port=8080):
        self.app.run(host=host, port=port, debug=True)

if __name__ == '__main__':
    server = GameServer()
    server.run()
