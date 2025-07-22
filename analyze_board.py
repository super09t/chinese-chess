import cv2
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import os

def analyze_chess_board_intersections():
    # Đọc file tọa độ bàn cờ nếu có
    try:
        from board_coordinates import BOARD_X, BOARD_Y, BOARD_WIDTH, BOARD_HEIGHT
        print(f"Đã tìm thấy tọa độ bàn cờ: X={BOARD_X}, Y={BOARD_Y}, W={BOARD_WIDTH}, H={BOARD_HEIGHT}")
    except ImportError:
        print("Không tìm thấy file board_coordinates.py")
        return
    
    # Đọc ảnh bàn cờ hiện tại
    if os.path.exists("current_board.png"):
        img = cv2.imread("current_board.png")
    else:
        print("Không tìm thấy ảnh bàn cờ (current_board.png)")
        return
    
    if img is None:
        print("Không thể đọc ảnh bàn cờ")
        return
    
    # Kích thước ảnh
    height, width = img.shape[:2]
    print(f"Kích thước ảnh: {width}x{height}")
    
    # Số hàng và cột của bàn cờ tướng (9x10)
    ROWS, COLS = 10, 9
    
    # Tính khoảng cách giữa các đường
    cell_width = width / (COLS - 1)
    cell_height = height / (ROWS - 1)
    
    print(f"Khoảng cách giữa các đường ngang: {cell_height:.2f} pixel")
    print(f"Khoảng cách giữa các đường dọc: {cell_width:.2f} pixel")
    
    # Tạo bản sao để vẽ lên
    img_marked = img.copy()
    
    # Mảng lưu giá trị màu tại các giao điểm
    intersection_colors = []
    
    # Duyệt qua tất cả các giao điểm
    for row in range(ROWS):
        row_colors = []
        for col in range(COLS):
            # Tính tọa độ giao điểm
            x = int(col * cell_width)
            y = int(row * cell_height)
            
            # Đảm bảo tọa độ nằm trong ảnh
            x = min(max(x, 0), width - 1)
            y = min(max(y, 0), height - 1)
            
            # Lấy giá trị màu tại giao điểm (BGR)
            color = img[y, x]
            row_colors.append(color)
            
            # Vẽ điểm đánh dấu giao điểm
            cv2.circle(img_marked, (x, y), 3, (0, 0, 255), -1)
            
            # Hiển thị giá trị màu
            cv2.putText(img_marked, f"{color[2]},{color[1]},{color[0]}", 
                       (x + 5, y), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 255), 1)
        
        intersection_colors.append(row_colors)
    
    # Lưu ảnh đã đánh dấu
    cv2.imwrite("board_intersections.png", img_marked)
    print("Đã lưu ảnh với các giao điểm được đánh dấu: board_intersections.png")
    
    # Hiển thị bảng màu
    print("\nBảng màu tại các giao điểm (BGR):")
    print("=" * 80)
    print("Hàng/Cột", end="")
    for col in range(COLS):
        print(f"   Cột {col}   ", end="")
    print()
    print("-" * 80)
    
    for row in range(ROWS):
        print(f"Hàng {row}  ", end="")
        for col in range(COLS):
            color = intersection_colors[row][col]
            print(f"{color[0]:3d},{color[1]:3d},{color[2]:3d}", end=" ")
        print()
    
    # Tạo hình ảnh biểu diễn màu sắc
    color_grid = np.zeros((ROWS*30, COLS*30, 3), dtype=np.uint8)
    for row in range(ROWS):
        for col in range(COLS):
            color = intersection_colors[row][col]
            # Chuyển từ BGR sang RGB
            color_rgb = (color[2], color[1], color[0])
            # Tô màu ô
            color_grid[row*30:(row+1)*30, col*30:(col+1)*30] = color_rgb
    
    # Lưu bảng màu
    plt.figure(figsize=(10, 10))
    plt.imshow(color_grid)
    plt.title("Màu sắc tại các giao điểm")
    plt.xticks(np.arange(15, COLS*30, 30), range(COLS))
    plt.yticks(np.arange(15, ROWS*30, 30), range(ROWS))
    plt.grid(True)
    plt.savefig("intersection_colors.png")
    print("Đã lưu bảng màu: intersection_colors.png")

if __name__ == "__main__":
    analyze_chess_board_intersections()
