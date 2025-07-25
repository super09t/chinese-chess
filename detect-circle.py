import cv2
import numpy as np
import os

def detect_chess_pieces(image_path, output_dir=None, reference_points=None):
    """
    Phát hiện quân cờ (hình tròn) trong ảnh bàn cờ và lưu kết quả
    Đồng thời xác định vị trí của quân cờ trên bàn cờ dựa vào các điểm tham chiếu
    
    Args:
        image_path: Đường dẫn đến ảnh cần phân tích
        output_dir: Thư mục để lưu ảnh kết quả, mặc định là cùng thư mục với ảnh đầu vào
        reference_points: Các điểm tham chiếu để xác định bàn cờ, format: [(x1,y1,pos1), (x2,y2,pos2),...]
    """
    # Kiểm tra file ảnh tồn tại
    if not os.path.exists(image_path):
        print(f"Không tìm thấy file ảnh: {image_path}")
        return
    
    # Đọc ảnh
    image = cv2.imread(image_path)
    if image is None:
        print(f"Không thể đọc ảnh: {image_path}")
        return
    
    # Tạo bản sao để vẽ kết quả
    output_image = image.copy()
    
    # Chuyển sang ảnh xám
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Tăng cường ảnh để dễ dàng phát hiện hình tròn
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Áp dụng Canny edge detection để tìm cạnh
    edges = cv2.Canny(blurred, 50, 150)
    
    # Lưu ảnh cạnh để kiểm tra
    edge_path = os.path.join(os.path.dirname(image_path), "edges.png")
    cv2.imwrite(edge_path, edges)
    
    # Phát hiện hình tròn với các tham số được tinh chỉnh
    # Ước tính kích thước quân cờ dựa trên kích thước ảnh
    height, width = image.shape[:2]
    
    # Xử lý các điểm tham chiếu
    if reference_points is None or len(reference_points) < 4:
        print("Không đủ điểm tham chiếu, sử dụng ước tính mặc định")
        min_dim = min(height, width)
        board_size = min_dim
        board_x = (width - board_size) // 2
        board_y = (height - board_size) // 2
        cell_size = board_size / 9  # Bàn cờ 9x9
        
        # Tạo lưới mặc định
        grid_points = {}
        for row in range(10):  # 0-9
            for col in range(9):  # a-i
                pos = chr(97 + col) + str(row)
                x = int(board_x + col * cell_size)
                y = int(board_y + row * cell_size)
                grid_points[pos] = (x, y)
    else:
        # Tạo một từ điển ánh xạ vị trí (a0, b1, ...) đến tọa độ (x, y)
        position_map = {}
        for x, y, pos in reference_points:
            position_map[pos] = (x, y)
        
        # Tìm các điểm góc
        if 'a0' in position_map and 'i0' in position_map and 'a9' in position_map:
            top_left = position_map['a0']
            top_right = position_map['i0']
            bottom_left = position_map['a9']
            
            # Tính toán kích thước ô cờ
            board_width = top_right[0] - top_left[0]
            board_height = bottom_left[1] - top_left[1]
            
            cell_width = board_width / 8  # 9 cột (a-i) = 8 khoảng
            cell_height = board_height / 9  # 10 hàng (0-9) = 9 khoảng
            
            print(f"Kích thước bàn cờ: {board_width}x{board_height} pixel")
            print(f"Kích thước ô cờ: chiều ngang: {cell_width:.1f}, chiều dọc: {cell_height:.1f}")
            
            # Tạo lưới điểm dựa trên các điểm tham chiếu
            grid_points = {}
            
            # Tạo lưới dựa trên nội suy tuyến tính từ các điểm tham chiếu
            for row in range(10):  # 0-9
                for col in range(9):  # a-i
                    pos = chr(97 + col) + str(row)
                    
                    # Nếu đã có điểm tham chiếu, sử dụng trực tiếp
                    if pos in position_map:
                        grid_points[pos] = position_map[pos]
                    else:
                        # Nội suy tuyến tính
                        x = top_left[0] + col * cell_width
                        y = top_left[1] + row * cell_height
                        grid_points[pos] = (int(x), int(y))
        else:
            print("Không tìm thấy đủ điểm góc, sử dụng ước tính mặc định")
            min_dim = min(height, width)
            board_size = min_dim
            board_x = (width - board_size) // 2
            board_y = (height - board_size) // 2
            cell_size = board_size / 9
            
            # Tạo lưới mặc định
            grid_points = {}
            for row in range(10):  # 0-9
                for col in range(9):  # a-i
                    pos = chr(97 + col) + str(row)
                    x = int(board_x + col * cell_size)
                    y = int(board_y + row * cell_size)
                    grid_points[pos] = (x, y)
    
    # Tính toán kích thước quân cờ dựa trên kích thước ô
    # Sử dụng khoảng cách giữa các điểm lưới liền kề
    cell_sizes = []
    for row in range(9):  # 0-8
        for col in range(8):  # a-h
            pos1 = chr(97 + col) + str(row)
            pos2 = chr(97 + col + 1) + str(row)  # Điểm bên phải
            pos3 = chr(97 + col) + str(row + 1)  # Điểm bên dưới
            
            if pos1 in grid_points and pos2 in grid_points:
                x1, y1 = grid_points[pos1]
                x2, y2 = grid_points[pos2]
                dist = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                cell_sizes.append(dist)
            
            if pos1 in grid_points and pos3 in grid_points:
                x1, y1 = grid_points[pos1]
                x3, y3 = grid_points[pos3]
                dist = np.sqrt((x3 - x1)**2 + (y3 - y1)**2)
                cell_sizes.append(dist)
    
    # Tính kích thước ô trung bình
    avg_cell_size = np.mean(cell_sizes) if cell_sizes else 50
    
    # Ước tính kích thước quân cờ
    min_radius = int(avg_cell_size * 0.3)  # Bán kính tối thiểu
    max_radius = int(avg_cell_size * 0.5)  # Bán kính tối đa
    
    print(f"Kích thước ảnh: {width}x{height}")
    print(f"Kích thước ô trung bình: {avg_cell_size:.1f} pixel")
    print(f"Tìm kiếm quân cờ với bán kính từ {min_radius} đến {max_radius} pixel")
    
    # Tạo ảnh bàn cờ với lưới
    board_image = output_image.copy()
    
    # Vẽ lưới bàn cờ
    for row in range(10):  # 0-9
        for col in range(9):  # a-i
            pos = chr(97 + col) + str(row)
            if pos in grid_points:
                x, y = grid_points[pos]
                
                # Vẽ điểm lưới
                cv2.circle(board_image, (x, y), 3, (0, 255, 0), -1)
                
                # Hiển thị tên vị trí
                cv2.putText(board_image, pos, (x - 10, y + 15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
    
    # Vẽ các đường nối giữa các điểm lưới
    for row in range(10):  # 0-9
        for col in range(8):  # a-h (chỉ đến h vì i là cột cuối)
            pos1 = chr(97 + col) + str(row)
            pos2 = chr(97 + col + 1) + str(row)
            
            if pos1 in grid_points and pos2 in grid_points:
                pt1 = grid_points[pos1]
                pt2 = grid_points[pos2]
                cv2.line(board_image, pt1, pt2, (0, 255, 0), 1)
    
    for row in range(9):  # 0-8 (chỉ đến 8 vì 9 là hàng cuối)
        for col in range(9):  # a-i
            pos1 = chr(97 + col) + str(row)
            pos2 = chr(97 + col) + str(row + 1)
            
            if pos1 in grid_points and pos2 in grid_points:
                pt1 = grid_points[pos1]
                pt2 = grid_points[pos2]
                cv2.line(board_image, pt1, pt2, (0, 255, 0), 1)
    
    # Đánh dấu các điểm tham chiếu
    if reference_points:
        for x, y, pos in reference_points:
            cv2.circle(board_image, (x, y), 5, (0, 0, 255), -1)
            cv2.putText(board_image, pos, (x + 10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    # Lưu ảnh bàn cờ với lưới
    grid_path = os.path.join(os.path.dirname(image_path), "chess_grid.png")
    cv2.imwrite(grid_path, board_image)
    print(f"Đã lưu ảnh lưới bàn cờ tại: {grid_path}")
    
    # Phát hiện hình tròn
    circles = cv2.HoughCircles(
        blurred, 
        cv2.HOUGH_GRADIENT, 
        dp=1,
        minDist=int(avg_cell_size * 0.8),
        param1=50,
        param2=30,
        minRadius=min_radius, 
        maxRadius=max_radius
    )
    
    # Nếu không tìm thấy đủ quân cờ, thử lại với tham số khác
    if circles is None or len(circles[0]) < 10:
        print("Thử lại với tham số khác...")
        circles = cv2.HoughCircles(
            blurred, 
            cv2.HOUGH_GRADIENT, 
            dp=1, 
            minDist=int(avg_cell_size * 0.7),
            param1=50, 
            param2=25,
            minRadius=min_radius - 5, 
            maxRadius=max_radius + 5
        )
    
    # Lọc các hình tròn phát hiện được
    if circles is not None:
        circles = np.uint16(np.around(circles))
        print(f"Tìm thấy {len(circles[0])} hình tròn tiềm năng")
        
        # Lọc các hình tròn dựa trên độ tương phản
        filtered_circles = []
        
        for circle in circles[0]:
            x, y, r = circle
            
            # Đảm bảo hình tròn nằm trong ảnh
            if x - r < 0 or y - r < 0 or x + r >= width or y + r >= height:
                continue
            
            # Cắt vùng hình tròn
            mask = np.zeros_like(gray)
            cv2.circle(mask, (x, y), r, 255, -1)
            
            # Tính độ tương phản giữa bên trong và bên ngoài hình tròn
            inner_mean = cv2.mean(gray, mask=mask)[0]
            
            # Tạo vùng đệm xung quanh
            outer_mask = np.zeros_like(gray)
            cv2.circle(outer_mask, (x, y), r + 5, 255, 5)
            outer_mean = cv2.mean(gray, mask=outer_mask)[0]
            
            # Tính độ tương phản
            contrast = abs(inner_mean - outer_mean)
            
            # Chỉ giữ lại các hình tròn có độ tương phản cao
            if contrast > 20:
                filtered_circles.append((x, y, r, contrast))
        
        print(f"Sau khi lọc: {len(filtered_circles)} quân cờ")
        
        # Sắp xếp theo độ tương phản giảm dần
        filtered_circles.sort(key=lambda x: x[3], reverse=True)
        
        # Giới hạn số lượng quân cờ
        max_pieces = min(32, len(filtered_circles))
        chess_pieces = filtered_circles[:max_pieces]
        
        # Tạo file để lưu tọa độ
        coords_file = os.path.join(os.path.dirname(image_path), "chess_pieces_coordinates.txt")
        with open(coords_file, 'w', encoding='utf-8') as f:
            f.write("Tọa độ các quân cờ đã phát hiện:\n")
            f.write("STT, x, y, radius, color, position\n")
            
            # Vẽ các quân cờ và lưu tọa độ
            for i, (x, y, r, _) in enumerate(chess_pieces):
                # Cắt vùng quân cờ
                piece_region = image[y-r:y+r, x-r:x+r]
                
                if piece_region.size == 0:
                    continue
                
                # Xác định màu quân cờ
                hsv = cv2.cvtColor(piece_region, cv2.COLOR_BGR2HSV)
                
                # Tính độ sáng trung bình
                brightness = np.mean(hsv[:,:,2])
                
                # Phân loại quân cờ đen/trắng dựa trên độ sáng
                if brightness < 100:
                    color = "black"
                    circle_color = (0, 0, 255)  # Đỏ cho quân đen
                else:
                    color = "white"
                    circle_color = (255, 0, 0)  # Xanh dương cho quân trắng
                
                # Vẽ viền hình tròn
                cv2.circle(output_image, (x, y), r, circle_color, 2)
                
                # Vẽ tâm hình tròn
                cv2.circle(output_image, (x, y), 2, (0, 255, 0), 3)
                
                # Xác định vị trí trên bàn cờ bằng cách tìm ô gần nhất
                min_distance = float('inf')
                closest_position = None
                
                # Tìm ô gần nhất với quân cờ
                for pos, (grid_x, grid_y) in grid_points.items():
                    # Tính khoảng cách từ quân cờ đến điểm lưới
                    distance = np.sqrt((x - grid_x)**2 + (y - grid_y)**2)
                    
                    # Cập nhật nếu tìm thấy ô gần hơn
                    if distance < min_distance:
                        min_distance = distance
                        closest_position = pos
                
                # Xác định vị trí dựa trên ô gần nhất
                chess_position = closest_position
                
                # Hiển thị số thứ tự
                cv2.putText(output_image, str(i+1), (x - 10, y - r - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                
                # Hiển thị tọa độ (x,y)
                coord_text = f"({x},{y})"
                cv2.putText(output_image, coord_text, (x - r, y + r + 15), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
                
                # Hiển thị vị trí trên bàn cờ
                cv2.putText(output_image, chess_position, (x + 5, y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                
                # Ghi tọa độ vào file
                f.write(f"{i+1}, {x}, {y}, {r}, {color}, {chess_position}\n")
        
        print(f"Đã lưu tọa độ quân cờ vào: {coords_file}")
    else:
        print("Không tìm thấy quân cờ nào trong ảnh")
    
    # Xác định thư mục đầu ra
    if output_dir is None:
        output_dir = os.path.dirname(image_path)
    
    # Tạo thư mục đầu ra nếu chưa tồn tại
    os.makedirs(output_dir, exist_ok=True)
    
    # Lưu ảnh kết quả
    output_path = os.path.join(output_dir, "detected_chess_pieces.png")
    cv2.imwrite(output_path, output_image)
    print(f"Đã lưu ảnh kết quả tại: {output_path}")
    
    return output_path, coords_file

if __name__ == "__main__":
    # Đường dẫn đến ảnh cần phân tích
    image_path = r"C:\Users\duong.ns\Desktop\chess\board_1753175979.png"
    
    # Các điểm tham chiếu để xác định bàn cờ
    # Format: [(x, y, position), ...]
    reference_points = [
        (30, 28, 'a0'),    # Góc trên bên trái
        (518, 28, 'i0'),   # Góc trên bên phải
        (30, 578, 'a9'),   # Góc dưới bên trái
        (276, 578, 'e9'),  # Điểm tham chiếu bổ sung
        (92, 28, 'b0'),    # Điểm tham chiếu bổ sung
        (152, 28, 'c0'),   # Điểm tham chiếu bổ sung
        (214, 28, 'd0'),   # Điểm tham chiếu bổ sung
        (336, 28, 'f0'),   # Điểm tham chiếu bổ sung
        (396, 28, 'g0'),   # Điểm tham chiếu bổ sung
        (458, 28, 'h0'),   # Điểm tham chiếu bổ sung
        (30, 210, 'a3'),   # Điểm tham chiếu bổ sung
        (92, 150, 'b2'),   # Điểm tham chiếu bổ sung
        (152, 272, 'c4'),  # Điểm tham chiếu bổ sung
        (30, 394, 'a6'),   # Điểm tham chiếu bổ sung
        (92, 458, 'b7'),   # Điểm tham chiếu bổ sung
        (152, 394, 'c6')   # Điểm tham chiếu bổ sung
    ]
    
    # Phát hiện quân cờ
    output_path, coords_file = detect_chess_pieces(image_path, reference_points=reference_points)
    
    print("\nHoàn thành phát hiện quân cờ!")
    print(f"Ảnh kết quả: {output_path}")
    print(f"File tọa độ: {coords_file}")
