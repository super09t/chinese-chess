import cv2
import numpy as np
import mss
import time

# --- Tham số cấu hình ---
BOARD_ROWS = 10  # Cờ tướng: 10 hàng
BOARD_COLS = 9   # Cờ tướng: 9 cột
CIRCLE_DETECT_PARAM = dict(
    dp=1.2,           # Tỉ lệ nghịch giữa độ phân giải ảnh đầu vào và ảnh dùng để phát hiện (thường >1)
    minDist=20,       # Khoảng cách tối thiểu giữa các tâm hình tròn được phát hiện
    param1=25,        # Ngưỡng trên cho bộ phát hiện cạnh Canny (Edge)
    param2=25,        # Ngưỡng tích lũy để xác định một hình tròn (càng nhỏ càng dễ phát hiện nhiều hình tròn nhiễu)
    minRadius=20,     # Bán kính nhỏ nhất của hình tròn cần phát hiện (pixel)
    maxRadius=25      # Bán kính lớn nhất của hình tròn cần phát hiện (pixel)
)


def select_roi(image):
    print("Chọn vùng bàn cờ, nhấn ENTER để xác nhận, ESC để hủy.")
    roi = cv2.selectROI("Chọn vùng bàn cờ", image, False, False)
    cv2.destroyWindow("Chọn vùng bàn cờ")
    x, y, w, h = roi
    return x, y, w, h


def grab_screen(monitor):
    with mss.mss() as sct:
        img = np.array(sct.grab(monitor))
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img


def detect_circles(board_img):
    gray = cv2.cvtColor(board_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 5)
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=CIRCLE_DETECT_PARAM['dp'],
        minDist=CIRCLE_DETECT_PARAM['minDist'],
        param1=CIRCLE_DETECT_PARAM['param1'],
        param2=CIRCLE_DETECT_PARAM['param2'],
        minRadius=CIRCLE_DETECT_PARAM['minRadius'],
        maxRadius=CIRCLE_DETECT_PARAM['maxRadius']
    )
    if circles is not None:
        circles = np.uint16(np.around(circles[0]))
    else:
        circles = np.array([])
    return circles


def get_grid_points(w, h, rows=BOARD_ROWS, cols=BOARD_COLS):
    # Vùng viền mỗi cạnh là 1/18 chiều rộng bàn cờ
    margin_x = int(w / 18)
    margin_y = int(h / 18)
    usable_w = w - 2 * margin_x
    usable_h = h - 2 * margin_y
    points = []
    for i in range(rows):
        row = []
        for j in range(cols):
            x = int(margin_x + j * usable_w / (cols - 1))
            y = int(margin_y + i * usable_h / (rows - 1))
            row.append((x, y))
        points.append(row)
    return points


def board_state_from_circles(circles, grid_points, threshold=30):
    state = np.zeros((BOARD_ROWS, BOARD_COLS), dtype=int)
    if circles is None or len(circles) == 0:
        return state
    for i in range(BOARD_ROWS):
        for j in range(BOARD_COLS):
            gx, gy = grid_points[i][j]
            for c in circles:
                cx, cy, r = c
                if np.hypot(gx - cx, gy - cy) < threshold:
                    state[i, j] = 1
                    break
    return state


def find_move(prev, curr):
    # Tìm nước đi: vị trí từ 1->0 (rời đi), 0->1 (đến)
    move_from = None
    move_to = None
    for i in range(BOARD_ROWS):
        for j in range(BOARD_COLS):
            if prev[i, j] == 1 and curr[i, j] == 0:
                move_from = (i, j)
            if prev[i, j] == 0 and curr[i, j] == 1:
                move_to = (i, j)
    if move_from and move_to:
        # Chuyển sang ký hiệu cột (a-i) và hàng (0-9)
        col_map = 'abcdefghi'
        move_str = f"{col_map[move_from[1]]}{move_from[0]}{col_map[move_to[1]]}{move_to[0]}"
        return move_str
    return None


def main():
    print("Chương trình theo dõi bàn cờ tướng real-time. Nhấn 'q' để thoát.")
    # 1. Chụp màn hình ban đầu để chọn ROI
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # Toàn màn hình chính
        screen_img = np.array(sct.grab(monitor))
        screen_img = cv2.cvtColor(screen_img, cv2.COLOR_BGRA2BGR)
    x, y, w, h = select_roi(screen_img)
    monitor_roi = {"top": y, "left": x, "width": w, "height": h}

    # 2. Tính toán các điểm nút giao trên bàn cờ
    grid_points = get_grid_points(w, h)

    prev_state = np.zeros((BOARD_ROWS, BOARD_COLS), dtype=int)
    first = True

    while True:
        board_img = grab_screen(monitor_roi)
        circles = detect_circles(board_img)
        curr_state = board_state_from_circles(circles, grid_points)

        # Hiển thị trạng thái bàn cờ
        vis = board_img.copy()
        # Vẽ lưới
        for i in range(BOARD_ROWS):
            for j in range(BOARD_COLS):
                color = (0, 255, 0) if curr_state[i, j] == 1 else (200, 200, 200)
                cv2.circle(vis, grid_points[i][j], 8, color, 2)
        # Vẽ quân cờ phát hiện được
        if circles is not None and len(circles) > 0:
            for c in circles:
                cx, cy, r = c
                cv2.circle(vis, (cx, cy), r, (0, 0, 255), 2)
        cv2.imshow("Chess Board Tracking", vis)

        # So sánh và in nước đi
        if not first:
            move = find_move(prev_state, curr_state)
            if move:
                print("Nước đi:", move)
        else:
            first = False
        prev_state = curr_state.copy()

        key = cv2.waitKey(200)  # 200ms ~ 5fps
        if key == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main() 