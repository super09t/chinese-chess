import pygame
import os
import sys
import threading
import time
import paramiko
import socket
import re

# Kích thước bàn cờ
CELL_SIZE = 60
BOARD_WIDTH = 9 * CELL_SIZE
BOARD_HEIGHT = 10 * CELL_SIZE
INFO_PANEL_HEIGHT = 150
WINDOW_WIDTH = BOARD_WIDTH
WINDOW_HEIGHT = BOARD_HEIGHT + INFO_PANEL_HEIGHT

# Màu sắc
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
BROWN = (165, 42, 42)
LIGHT_BROWN = (222, 184, 135)
HIGHLIGHT_COLOR = (0, 255, 0, 128)  # Màu xanh lá cây với độ trong suốt
LAST_MOVE_COLOR = (255, 255, 0)  # Màu vàng cho nước đi gần nhất

# Thông tin kết nối Raspberry Pi
PI_HOST = "192.168.100.88"
PI_PORT = 22
PI_USERNAME = "nsd"
PI_PASSWORD = "1"
ELEPHANTEYE_DIR = "/home/nsd/eleeye/eleeye"
ELEPHANTEYE_EXEC = "eleeye"

# Danh sách font hỗ trợ Unicode
UNICODE_FONTS = [
    "Arial Unicode MS",
    "DejaVu Sans",
    "FreeSans",
    "Noto Sans",
    "Segoe UI",
    "Microsoft Sans Serif",
    None  # Fallback to default
]

# Hàm khởi tạo font hỗ trợ Unicode
def get_unicode_font(size, bold=False):
    # Thử từng font trong danh sách cho đến khi tìm được font khả dụng
    for font_name in UNICODE_FONTS:
        try:
            if font_name:
                return pygame.font.SysFont(font_name, size, bold)
            else:
                # Sử dụng font mặc định của pygame nếu không có font nào khác
                return pygame.font.Font(pygame.font.get_default_font(), size)
        except:
            continue
    
    # Nếu không tìm được font nào, sử dụng font mặc định
    return pygame.font.Font(pygame.font.get_default_font(), size)

class Piece:
    def __init__(self, piece_type, is_red, x, y):
        self.piece_type = piece_type
        self.is_red = is_red
        self.x = x
        self.y = y
        self.selected = False
        self.last_moved = False  # Đánh dấu nước đi gần nhất
        
        # Tải hình ảnh quân cờ
        self.image = self.load_image()
    
    def load_image(self):
        color = "r" if self.is_red else "b"
        piece_images = {
            "vua": f"C:/Users/duong.ns/Desktop/chess/images/{color}k.png",  # Tướng/Vua
            "si": f"C:/Users/duong.ns/Desktop/chess/images/{color}a.png",  # Sĩ
            "tuong": f"C:/Users/duong.ns/Desktop/chess/images/{color}e.png",  # Tượng
            "xe": f"C:/Users/duong.ns/Desktop/chess/images/{color}r.png",  # Xe
            "ma": f"C:/Users/duong.ns/Desktop/chess/images/{color}h.png",  # Mã
            "phao": f"C:/Users/duong.ns/Desktop/chess/images/{color}c.png",  # Pháo
            "tot": f"C:/Users/duong.ns/Desktop/chess/images/{color}p.png",  # Tốt/Binh
        }
        
        image_path = piece_images.get(self.piece_type.lower())
        if image_path and os.path.exists(image_path):
            # Tải hình ảnh
            original_image = pygame.image.load(image_path)
            
            # Điều chỉnh kích thước hình ảnh để vừa với ô cờ
            target_size = int(CELL_SIZE * 0.8)  # 80% kích thước ô cờ
            scaled_image = pygame.transform.smoothscale(original_image, (target_size, target_size))
            
            return scaled_image
        else:
            # Tạo hình ảnh mặc định nếu không tìm thấy file
            surface = pygame.Surface((CELL_SIZE - 10, CELL_SIZE - 10), pygame.SRCALPHA)
            pygame.draw.circle(surface, RED if self.is_red else BLACK, 
                            (surface.get_width() // 2, surface.get_height() // 2), 
                            surface.get_width() // 2)
            font = get_unicode_font(20, True)
            text = font.render(self.piece_type, True, WHITE)
            text_rect = text.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2))
            surface.blit(text, text_rect)
            return surface
    
    def draw(self, surface):
        # Tính toán vị trí trên màn hình
        screen_x = self.x * CELL_SIZE + CELL_SIZE // 2
        screen_y = (9 - self.y) * CELL_SIZE + CELL_SIZE // 2
        
        # Vẽ viền ngoài cho nước đi gần nhất
        if self.last_moved:
            pygame.draw.circle(surface, LAST_MOVE_COLOR, (screen_x, screen_y), CELL_SIZE // 2)
        
        # Vẽ hình tròn nền
        if self.selected:
            pygame.draw.circle(surface, GREEN, (screen_x, screen_y), CELL_SIZE // 2 - 2)
        
        # Vẽ quân cờ
        if self.image:
            image_rect = self.image.get_rect(center=(screen_x, screen_y))
            surface.blit(self.image, image_rect)
        else:
            # Vẽ hình tròn nếu không có hình ảnh
            color = RED if self.is_red else BLACK
            pygame.draw.circle(surface, color, (screen_x, screen_y), CELL_SIZE // 2 - 5)
            
            # Vẽ chữ
            font = get_unicode_font(20, True)
            text = font.render(self.piece_type, True, WHITE)
            text_rect = text.get_rect(center=(screen_x, screen_y))
            surface.blit(text, text_rect)
        
        # Vẽ viền cho nước đi gần nhất
        if self.last_moved:
            pygame.draw.circle(surface, LAST_MOVE_COLOR, (screen_x, screen_y), CELL_SIZE // 2, 3)

class ElephantEyeEngine:
    def __init__(self):
        self.ssh = None
        self.sftp = None
        self.connected = False
        self.last_evaluation = 0
        self.last_depth = 0
        self.last_nodes = 0
        self.last_time = 0
        self.player_is_red = True
    
    def start(self):
        try:
            # Khởi tạo kết nối SSH
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(PI_HOST, PI_PORT, PI_USERNAME, PI_PASSWORD)
            
            # Tạo SFTP
            self.sftp = self.ssh.open_sftp()
            
            # Kiểm tra phiên bản ElephantEye
            stdin, stdout, stderr = self.ssh.exec_command(
                f"cd {ELEPHANTEYE_DIR} && (echo 'ucci'; sleep 1; echo 'quit') | ./{ELEPHANTEYE_EXEC}"
            )
            
            try:
                stdout.channel.settimeout(5)
                ucci_response = stdout.read().decode('utf-8')
                for line in ucci_response.split('\n'):
                    if line.startswith("id version"):
                        print(f"ElephantEye {line.split()[2]}")
                        break
            except socket.timeout:
                print("Timeout khi đọc phản hồi từ lệnh ucci")
            
            self.connected = True
            return True
        
        except Exception as e:
            print(f"Lỗi khi kết nối với Raspberry Pi: {e}")
            return False
    
    def get_best_move(self, moves, callback):
        if not self.connected:
            callback(None, 0, 0, 0, 0)
            return
        
        def worker():
            try:
                # Chuẩn bị FEN chuỗi ban đầu
                fen_start = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
                
                # Chuẩn bị chuỗi nước đi
                moves_str = ' '.join(moves) if moves else ""
                
                # Tạo script để tương tác với ElephantEye
                depth = 8  # Độ sâu tìm kiếm
                wait_time = 2  # Thời gian đợi (giây)
                
                script_content = f"""#!/bin/bash
cd {ELEPHANTEYE_DIR}
(
echo "ucci"
sleep 0.5
echo "setoption name Hash value 256"
echo "setoption name Pruning value true"
echo "setoption name Knowledge value 3"
echo "setoption name Ponder value true"
echo "position fen {fen_start}{' moves ' + moves_str if moves_str else ''}"
sleep 0.5
echo "go depth {depth}"
sleep {wait_time}
echo "quit"
) | ./{ELEPHANTEYE_EXEC} > /tmp/chess_output.txt 2>/tmp/chess_error.txt
"""
                
                # Lưu script vào file trên Raspberry Pi
                with self.sftp.file('/tmp/chess_script.sh', 'w') as f:
                    f.write(script_content)
                
                # Đặt quyền thực thi cho script
                self.ssh.exec_command("chmod +x /tmp/chess_script.sh")
                
                # Chạy script
                stdin, stdout, stderr = self.ssh.exec_command("/tmp/chess_script.sh")
                
                # Đợi script hoàn thành
                exit_status = stdout.channel.recv_exit_status()
                
                # Đọc kết quả
                stdin, stdout, stderr = self.ssh.exec_command("cat /tmp/chess_output.txt")
                response = stdout.read().decode('utf-8')
                
                # Phân tích kết quả
                analysis = self.analyze_response(response)
                
                # Lưu thông tin đánh giá
                self.last_evaluation = analysis['score'] if analysis['score'] is not None else 0
                self.last_depth = analysis['depth'] if analysis['depth'] is not None else 0
                self.last_nodes = analysis['nodes'] if analysis['nodes'] is not None else 0
                self.last_time = analysis['time'] if analysis['time'] is not None else 0
                
                # Gọi callback với kết quả
                callback(analysis['bestmove'], self.last_evaluation, self.last_depth, self.last_nodes, self.last_time)
                
                # Dọn dẹp file tạm
                self.ssh.exec_command("rm -f /tmp/chess_script.sh /tmp/chess_output.txt /tmp/chess_error.txt")
            
            except Exception as e:
                print(f"Lỗi khi lấy nước đi tốt nhất: {e}")
                callback(None, 0, 0, 0, 0)
        
        # Chạy trong một luồng riêng biệt
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
    
    def analyze_response(self, response):
        max_depth = 0
        final_score = None
        final_nodes = None
        final_time = None
        best_move = None
        
        # Tìm thông tin về độ sâu, điểm số và số nút
        depth_pattern = re.compile(r'info depth (\d+) score (-?\d+)')
        nodes_time_pattern = re.compile(r'info time (\d+) nodes (\d+)')
        bestmove_pattern = re.compile(r'bestmove ([a-i]\d[a-i]\d)')
        
        for line in response.split('\n'):
            depth_match = depth_pattern.match(line)
            if depth_match:
                depth = int(depth_match.group(1))
                score = int(depth_match.group(2))
                if depth > max_depth:
                    max_depth = depth
                    final_score = score
            
            nodes_time_match = nodes_time_pattern.match(line)
            if nodes_time_match:
                time_ms = int(nodes_time_match.group(1))
                nodes = int(nodes_time_match.group(2))
                final_time = time_ms / 1000  # Chuyển đổi sang giây
                final_nodes = nodes
            
            bestmove_match = bestmove_pattern.match(line)
            if bestmove_match:
                best_move = bestmove_match.group(1)
        
        return {
            'depth': max_depth,
            'score': final_score,
            'nodes': final_nodes,
            'time': final_time,
            'bestmove': best_move
        }
    
    def interpret_score(self, score):
        if score is None:
            return "Không có đánh giá"
        
        abs_score = abs(score)
        
        # Xác định bên nào đang có lợi thế
        if self.player_is_red:
            # Người chơi là quân đỏ
            if score < 0:
                side = "Bạn"
            else:
                side = "Đối thủ"
        else:
            # Người chơi là quân đen
            if score > 0:
                side = "Bạn"
            else:
                side = "Đối thủ"
        
        if abs_score == 0:
            return "Cân bằng (0)"
        elif abs_score < 30:
            return f"{side} có lợi thế rất nhỏ ({abs_score})"
        elif abs_score < 100:
            return f"{side} có lợi thế nhỏ ({abs_score})"
        elif abs_score < 200:
            return f"{side} có lợi thế quân tốt ({abs_score})"
        elif abs_score < 500:
            return f"{side} có lợi thế đáng kể ({abs_score})"
        elif abs_score < 900:
            return f"{side} có lợi thế lớn ({abs_score})"
        elif abs_score < 10000:
            return f"{side} có lợi thế thắng cuộc ({abs_score})"
        else:
            return f"{side} chiếu bí ({abs_score})"
    
    def set_player_color(self, is_red):
        self.player_is_red = is_red
    
    def stop(self):
        if self.sftp:
            self.sftp.close()
        
        if self.ssh:
            self.ssh.close()
        
        self.connected = False

class Board:
    def __init__(self):
        self.pieces = []
        self.selected_piece = None
        self.moves = []
        self.current_player_is_red = True  # Quân đỏ luôn đi trước
        self.evaluation = "Cân bằng (0)"
        self.depth = 0
        self.nodes = 0
        self.time = 0
        self.player_is_red = True  # Mặc định người chơi điều khiển quân đỏ
        self.engine = ElephantEyeEngine()
        self.engine_connected = False
        self.waiting_for_engine = False
        self.status_message = "Khởi động..."
        self.last_moved_piece = None  # Quân cờ di chuyển gần nhất
        self.last_move_from = None  # Vị trí xuất phát của nước đi gần nhất
        self.last_move_to = None  # Vị trí đích của nước đi gần nhất
        
        # Khởi tạo bàn cờ
        self.initialize_board()
        
        # Kết nối với ElephantEye
        self.connect_to_engine()
        
        # Nếu người chơi điều khiển quân đen, ElephantEye (quân đỏ) sẽ đi trước
        if not self.player_is_red:
            self.get_engine_move()
    
    def connect_to_engine(self):
        def worker():
            success = self.engine.start()
            self.engine_connected = success
            self.status_message = "Đã kết nối với ElephantEye" if success else "Không thể kết nối với ElephantEye"
        
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
    
    def initialize_board(self):
        # Xóa tất cả quân cờ
        self.pieces = []
        
        # Khởi tạo quân đỏ (phía dưới)
        # Xe
        self.pieces.append(Piece("Xe", True, 0, 0))
        self.pieces.append(Piece("Xe", True, 8, 0))
        # Mã
        self.pieces.append(Piece("Ma", True, 1, 0))
        self.pieces.append(Piece("Ma", True, 7, 0))
        # Tượng
        self.pieces.append(Piece("Tuong", True, 2, 0))
        self.pieces.append(Piece("Tuong", True, 6, 0))
        # Sĩ
        self.pieces.append(Piece("Si", True, 3, 0))
        self.pieces.append(Piece("Si", True, 5, 0))
        # Tướng
        self.pieces.append(Piece("Vua", True, 4, 0))
        # Pháo
        self.pieces.append(Piece("Phao", True, 1, 2))
        self.pieces.append(Piece("Phao", True, 7, 2))
        # Tốt
        self.pieces.append(Piece("Tot", True, 0, 3))
        self.pieces.append(Piece("Tot", True, 2, 3))
        self.pieces.append(Piece("Tot", True, 4, 3))
        self.pieces.append(Piece("Tot", True, 6, 3))
        self.pieces.append(Piece("Tot", True, 8, 3))
        
        # Khởi tạo quân đen (phía trên)
        # Xe
        self.pieces.append(Piece("Xe", False, 0, 9))
        self.pieces.append(Piece("Xe", False, 8, 9))
        # Mã
        self.pieces.append(Piece("Ma", False, 1, 9))
        self.pieces.append(Piece("Ma", False, 7, 9))
        # Tượng
        self.pieces.append(Piece("Tuong", False, 2, 9))
        self.pieces.append(Piece("Tuong", False, 6, 9))
        # Sĩ
        self.pieces.append(Piece("Si", False, 3, 9))
        self.pieces.append(Piece("Si", False, 5, 9))
        # Tướng
        self.pieces.append(Piece("Vua", False, 4, 9))
        # Pháo
        self.pieces.append(Piece("Phao", False, 1, 7))
        self.pieces.append(Piece("Phao", False, 7, 7))
        # Tốt
        self.pieces.append(Piece("Tot", False, 0, 6))
        self.pieces.append(Piece("Tot", False, 2, 6))
        self.pieces.append(Piece("Tot", False, 4, 6))
        self.pieces.append(Piece("Tot", False, 6, 6))
        self.pieces.append(Piece("Tot", False, 8, 6))
        
        # Đặt lại lượt đi
        self.current_player_is_red = True
        self.moves = []
        self.last_moved_piece = None
        self.last_move_from = None
        self.last_move_to = None
    
    def draw(self, surface):
        # Vẽ nền bàn cờ
        surface.fill(LIGHT_BROWN)
        
        # Vẽ lưới
        for i in range(10):
            # Vẽ đường ngang
            pygame.draw.line(surface, BLACK, 
                            (CELL_SIZE // 2, i * CELL_SIZE + CELL_SIZE // 2),
                            (BOARD_WIDTH - CELL_SIZE // 2, i * CELL_SIZE + CELL_SIZE // 2))
            
            # Vẽ đường dọc
            if i < 9:
                pygame.draw.line(surface, BLACK,
                                (i * CELL_SIZE + CELL_SIZE // 2, CELL_SIZE // 2),
                                (i * CELL_SIZE + CELL_SIZE // 2, BOARD_HEIGHT - CELL_SIZE // 2))
        
        # Vẽ cung điện
        # Cung điện dưới
        pygame.draw.line(surface, BLACK, 
                        (3 * CELL_SIZE + CELL_SIZE // 2, 0 * CELL_SIZE + CELL_SIZE // 2),
                        (5 * CELL_SIZE + CELL_SIZE // 2, 2 * CELL_SIZE + CELL_SIZE // 2))
        pygame.draw.line(surface, BLACK, 
                        (5 * CELL_SIZE + CELL_SIZE // 2, 0 * CELL_SIZE + CELL_SIZE // 2),
                        (3 * CELL_SIZE + CELL_SIZE // 2, 2 * CELL_SIZE + CELL_SIZE // 2))
        
        # Cung điện trên
        pygame.draw.line(surface, BLACK, 
                        (3 * CELL_SIZE + CELL_SIZE // 2, 9 * CELL_SIZE + CELL_SIZE // 2),
                        (5 * CELL_SIZE + CELL_SIZE // 2, 7 * CELL_SIZE + CELL_SIZE // 2))
        pygame.draw.line(surface, BLACK, 
                        (5 * CELL_SIZE + CELL_SIZE // 2, 9 * CELL_SIZE + CELL_SIZE // 2),
                        (3 * CELL_SIZE + CELL_SIZE // 2, 7 * CELL_SIZE + CELL_SIZE // 2))
        
        # Vẽ sông
        font = get_unicode_font(24, True)
        text1 = font.render("Sông", True, BLUE)
        text2 = font.render("Hà", True, BLUE)
        surface.blit(text1, (BOARD_WIDTH // 2 - text1.get_width() // 2, 4 * CELL_SIZE + 5))
        surface.blit(text2, (BOARD_WIDTH // 2 - text2.get_width() // 2, 5 * CELL_SIZE + 5))
        
        # Vẽ điểm đánh dấu nước đi gần nhất
        if self.last_move_from and self.last_move_to:
            # Vẽ điểm xuất phát
            from_x = self.last_move_from[0] * CELL_SIZE + CELL_SIZE // 2
            from_y = (9 - self.last_move_from[1]) * CELL_SIZE + CELL_SIZE // 2
            pygame.draw.circle(surface, LAST_MOVE_COLOR, (from_x, from_y), 5)
            
            # Vẽ điểm đích
            to_x = self.last_move_to[0] * CELL_SIZE + CELL_SIZE // 2
            to_y = (9 - self.last_move_to[1]) * CELL_SIZE + CELL_SIZE // 2
            
            # Vẽ đường nối giữa điểm xuất phát và điểm đích
            pygame.draw.line(surface, LAST_MOVE_COLOR, (from_x, from_y), (to_x, to_y), 2)
        
        # Vẽ các quân cờ
        for piece in self.pieces:
            piece.selected = (piece == self.selected_piece)
            piece.last_moved = (piece == self.last_moved_piece)
            piece.draw(surface)
        
        # Vẽ panel thông tin
        self.draw_info_panel(surface)
    
    def draw_info_panel(self, surface):
        # Vẽ nền cho panel thông tin
        pygame.draw.rect(surface, LIGHT_BROWN, (0, BOARD_HEIGHT, BOARD_WIDTH, INFO_PANEL_HEIGHT))
        pygame.draw.rect(surface, BLACK, (0, BOARD_HEIGHT, BOARD_WIDTH, INFO_PANEL_HEIGHT), 2)
        
        # Hiển thị lượt đi
        font = get_unicode_font(20, True)
        current_player = "Bạn" if (self.current_player_is_red and self.player_is_red) or (not self.current_player_is_red and not self.player_is_red) else "ElephantEye"
        turn_text = font.render(f"Lượt đi: {current_player} ({('Đỏ' if self.current_player_is_red else 'Đen')})", True, RED if self.current_player_is_red else BLACK)
        surface.blit(turn_text, (20, BOARD_HEIGHT + 15))
        
        # Hiển thị đánh giá
        eval_text = font.render(f"Đánh giá: {self.evaluation}", True, BLACK)
        surface.blit(eval_text, (20, BOARD_HEIGHT + 45))
        
        # Hiển thị độ sâu và số nút
        depth_str = str(self.depth) if self.depth is not None else "0"
        nodes_str = f"{self.nodes:,}" if self.nodes is not None else "0"
        time_str = f"{self.time:.1f}" if self.time is not None else "0.0"
        depth_nodes_text = font.render(f"Độ sâu: {depth_str} - Số nút: {nodes_str} - Thời gian: {time_str}s", True, BLACK)
        surface.blit(depth_nodes_text, (20, BOARD_HEIGHT + 75))
        
        # Hiển thị trạng thái
        status_text = font.render(f"Trạng thái: {self.status_message}", True, BLUE)
        surface.blit(status_text, (20, BOARD_HEIGHT + 105))
        
        # Hiển thị nước đi gần nhất
        if self.last_move_from and self.last_move_to:
            from_str = f"{chr(97 + self.last_move_from[0])}{self.last_move_from[1]}"
            to_str = f"{chr(97 + self.last_move_to[0])}{self.last_move_to[1]}"
            last_move_text = font.render(f"Nước đi gần nhất: {from_str}{to_str}", True, LAST_MOVE_COLOR)
            surface.blit(last_move_text, (BOARD_WIDTH - 220, BOARD_HEIGHT + 105))
    
    def get_piece_at(self, x, y):
        for piece in self.pieces:
            if piece.x == x and piece.y == y:
                return piece
        return None
    
    def select_piece(self, x, y):
        # Kiểm tra xem có đang đợi động cơ không
        if self.waiting_for_engine:
            return
        
        # Kiểm tra xem có phải lượt của người chơi không
        is_player_turn = (self.current_player_is_red and self.player_is_red) or (not self.current_player_is_red and not self.player_is_red)
        if not is_player_turn:
            self.status_message = "Không phải lượt của bạn"
            return
        
        # Lấy quân cờ tại vị trí được chọn
        piece = self.get_piece_at(x, y)
        
        # Nếu đã chọn một quân cờ trước đó
        if self.selected_piece:
            # Nếu chọn cùng một quân cờ, hủy chọn
            if self.selected_piece == piece:
                self.selected_piece = None
            # Nếu chọn một quân cờ khác cùng màu, chọn quân mới
            elif piece and piece.is_red == self.selected_piece.is_red:
                # Kiểm tra xem quân cờ có phải của người chơi không
                if (piece.is_red and self.player_is_red) or (not piece.is_red and not self.player_is_red):
                    self.selected_piece = piece
                else:
                    self.status_message = "Đó không phải là quân của bạn"
            # Nếu chọn một ô trống hoặc quân cờ đối phương, thử di chuyển
            else:
                # Thực hiện nước đi
                self.move_piece(self.selected_piece, x, y)
                self.selected_piece = None
        # Nếu chưa chọn quân cờ nào
        elif piece:
            # Chỉ cho phép chọn quân cờ của người chơi
            if (piece.is_red and self.player_is_red) or (not piece.is_red and not self.player_is_red):
                self.selected_piece = piece
            else:
                self.status_message = "Đó không phải là quân của bạn"
    
    def move_piece(self, piece, to_x, to_y):
        # Lưu vị trí cũ
        from_x, from_y = piece.x, piece.y
        
        # Kiểm tra quân ở vị trí đích
        target_piece = self.get_piece_at(to_x, to_y)
        if target_piece:
            # Không thể ăn quân cùng màu
            if target_piece.is_red == piece.is_red:
                return False
            # Ăn quân
            self.pieces.remove(target_piece)
        
        # Đánh dấu nước đi gần nhất
        # Đặt lại trạng thái đánh dấu cho tất cả quân cờ
        if self.last_moved_piece:
            self.last_moved_piece.last_moved = False
        
        # Lưu thông tin nước đi gần nhất
        self.last_moved_piece = piece
        self.last_move_from = (from_x, from_y)
        self.last_move_to = (to_x, to_y)
        
        # Di chuyển quân cờ
        piece.x, piece.y = to_x, to_y
        
        # Chuyển đổi sang định dạng UCCI
        move = chr(97 + from_x) + str(from_y) + chr(97 + to_x) + str(to_y)
        
        # Thêm nước đi vào lịch sử
        self.moves.append(move)
        
        # Đổi lượt
        self.current_player_is_red = not self.current_player_is_red
        
        # Nếu là lượt của máy, lấy nước đi từ ElephantEye
        is_engine_turn = (self.current_player_is_red and not self.player_is_red) or (not self.current_player_is_red and self.player_is_red)
        if is_engine_turn and self.engine_connected:
            self.get_engine_move()
        
        return True
    
    def get_engine_move(self):
        if not self.engine_connected:
            return
        
        self.waiting_for_engine = True
        self.status_message = "ElephantEye đang suy nghĩ..."
        
        # Lấy nước đi tốt nhất từ ElephantEye
        def on_move_received(move, evaluation, depth, nodes, time):
            if move:
                # Chuyển đổi từ định dạng UCCI sang tọa độ
                from_x = ord(move[0]) - 97
                from_y = int(move[1])
                to_x = ord(move[2]) - 97
                to_y = int(move[3])
                
                # Tìm quân cờ tại vị trí xuất phát
                piece = self.get_piece_at(from_x, from_y)
                if piece:
                    # Đặt lại trạng thái đánh dấu cho tất cả quân cờ
                    if self.last_moved_piece:
                        self.last_moved_piece.last_moved = False
                    
                    # Lưu thông tin nước đi gần nhất
                    self.last_moved_piece = piece
                    self.last_move_from = (from_x, from_y)
                    self.last_move_to = (to_x, to_y)
                    
                    # Di chuyển quân cờ
                    target_piece = self.get_piece_at(to_x, to_y)
                    if target_piece:
                        self.pieces.remove(target_piece)
                    
                    piece.x, piece.y = to_x, to_y
                    
                    # Thêm nước đi vào lịch sử
                    self.moves.append(move)
                    
                    # Cập nhật thông tin đánh giá
                    self.evaluation = self.engine.interpret_score(evaluation)
                    self.depth = depth
                    self.nodes = nodes
                    self.time = time
                    
                    # Đổi lượt
                    self.current_player_is_red = not self.current_player_is_red
                    
                    self.status_message = f"ElephantEye đã đi: {move}"
                else:
                    self.status_message = f"Lỗi: Không tìm thấy quân cờ tại {move[0]}{move[1]}"
            else:
                self.status_message = "ElephantEye không thể tìm được nước đi"
            
            self.waiting_for_engine = False
        
        # Gọi ElephantEye để lấy nước đi tốt nhất
        self.engine.get_best_move(self.moves, on_move_received)
    
    def handle_click(self, pos):
        # Chuyển đổi từ tọa độ chuột sang tọa độ bàn cờ
        x = pos[0] // CELL_SIZE
        y = 9 - (pos[1] // CELL_SIZE)
        
        # Chỉ xử lý click trong phạm vi bàn cờ
        if 0 <= x < 9 and 0 <= y < 10:
            self.select_piece(x, y)
    
    def reset_game(self):
        # Đóng kết nối với ElephantEye
        if self.engine_connected:
            self.engine.stop()
        
        # Khởi tạo lại bàn cờ
        self.initialize_board()
        
        # Kết nối lại với ElephantEye
        self.connect_to_engine()
        
        # Nếu người chơi điều khiển quân đen, ElephantEye (quân đỏ) sẽ đi trước
        if not self.player_is_red and self.engine_connected:
            self.get_engine_move()
    
    def set_player_color(self, is_red):
        self.player_is_red = is_red
        if self.engine_connected:
            self.engine.set_player_color(is_red)
        
        # Đặt lại bàn cờ
        self.initialize_board()
        
        # Nếu đổi sang quân đen và đang ở lượt đỏ, ElephantEye sẽ đi trước
        if not is_red and self.current_player_is_red and self.engine_connected:
            self.get_engine_move()

class ChessGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Cờ Tướng với ElephantEye")
        
        self.clock = pygame.time.Clock()
        self.board = Board()
        self.running = True
        
        # Tạo nút
        self.reset_button = pygame.Rect(WINDOW_WIDTH - 150, BOARD_HEIGHT + 20, 130, 40)
        self.switch_color_button = pygame.Rect(WINDOW_WIDTH - 150, BOARD_HEIGHT + 70, 130, 40)
    
    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    pos = pygame.mouse.get_pos()
                    
                    # Kiểm tra xem có nhấn vào nút nào không
                    if self.reset_button.collidepoint(pos):
                        self.board.reset_game()
                    elif self.switch_color_button.collidepoint(pos):
                        self.board.set_player_color(not self.board.player_is_red)
                    # Nếu không, xử lý click trên bàn cờ
                    elif pos[1] < BOARD_HEIGHT:
                        self.board.handle_click(pos)
            
            # Vẽ bàn cờ
            self.board.draw(self.screen)
            
            # Vẽ các nút
            pygame.draw.rect(self.screen, GREEN, self.reset_button)
            pygame.draw.rect(self.screen, BLUE, self.switch_color_button)
            
            font = get_unicode_font(20, True)
            reset_text = font.render("Chơi lại", True, BLACK)
            switch_text = font.render("Đổi bên", True, BLACK)
            
            self.screen.blit(reset_text, (self.reset_button.x + (self.reset_button.width - reset_text.get_width()) // 2, 
                                         self.reset_button.y + (self.reset_button.height - reset_text.get_height()) // 2))
            self.screen.blit(switch_text, (self.switch_color_button.x + (self.switch_color_button.width - switch_text.get_width()) // 2, 
                                          self.switch_color_button.y + (self.switch_color_button.height - switch_text.get_height()) // 2))
            
            pygame.display.flip()
            self.clock.tick(60)
        
        # Đóng kết nối với ElephantEye khi thoát
        if self.board.engine_connected:
            self.board.engine.stop()
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = ChessGame()
    game.run()
