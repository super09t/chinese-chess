import tkinter as tk
import pyautogui
import numpy as np
import cv2
import time
import threading
import queue
from PIL import Image, ImageTk

class ScreenCaptureApp:
    def __init__(self):
        # Khởi tạo biến cho vùng chọn
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0
        self.selecting = False
        self.selected = False
        self.capture_running = False
        self.capture_thread = None
        self.capture_delay = 0.5  # Thời gian giữa các lần chụp (giây)
        
        # Queue để giao tiếp giữa các thread
        self.frame_queue = queue.Queue(maxsize=1)
        
        # Lấy kích thước màn hình
        self.screen_width, self.screen_height = pyautogui.size()
        
        # Tạo cửa sổ chính
        self.root = tk.Tk()
        self.root.title("Chon vung ban co")
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-alpha', 0.3)  # Làm mờ màn hình
        self.root.attributes('-topmost', True)
        
        # Canvas để vẽ vùng chọn
        self.canvas = tk.Canvas(self.root, cursor="cross", 
                               width=self.screen_width, 
                               height=self.screen_height)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Chụp màn hình làm nền
        self.update_background()
        
        # Thêm sự kiện chuột
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        
        # Thêm phím tắt
        self.root.bind("<Escape>", self.on_escape)
        
        # Hướng dẫn
        self.instruction = self.canvas.create_text(
            self.screen_width // 2, 30, 
            text="Keo chuot de chon vung ban co. Nhan ESC de huy.",
            fill="red", font=("Arial", 16, "bold"))
        
        # Cửa sổ hiển thị ảnh đã chụp
        self.preview_window = None
        self.preview_label = None
        
        # Thông tin vùng chọn
        self.info_text = self.canvas.create_text(
            10, 10, anchor="nw",
            text="", fill="black", font=("Arial", 12))
    
    def update_background(self):
        # Chụp màn hình
        screenshot = pyautogui.screenshot()
        self.background_image = ImageTk.PhotoImage(screenshot)
        
        # Hiển thị ảnh nền
        self.canvas.create_image(0, 0, image=self.background_image, anchor=tk.NW)
    
    def on_press(self, event):
        # Bắt đầu chọn vùng
        self.selecting = True
        self.start_x = event.x
        self.start_y = event.y
        
        # Tạo hình chữ nhật cho vùng chọn
        self.selection_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="red", width=2)
    
    def on_drag(self, event):
        if self.selecting:
            # Cập nhật vùng chọn khi kéo chuột
            self.end_x = event.x
            self.end_y = event.y
            
            # Cập nhật hình chữ nhật
            self.canvas.coords(self.selection_rect, 
                              self.start_x, self.start_y, 
                              self.end_x, self.end_y)
            
            # Cập nhật thông tin kích thước
            width = abs(self.end_x - self.start_x)
            height = abs(self.end_y - self.start_y)
            self.canvas.itemconfig(
                self.info_text, 
                text=f"Kich thuoc: {width}x{height} px")
    
    def on_release(self, event):
        if self.selecting:
            self.selecting = False
            self.selected = True
            
            # Chuẩn hóa tọa độ (đảm bảo start < end)
            if self.start_x > self.end_x:
                self.start_x, self.end_x = self.end_x, self.start_x
            if self.start_y > self.end_y:
                self.start_y, self.end_y = self.end_y, self.start_y
            
            # Tính toán kích thước vùng chọn
            width = self.end_x - self.start_x
            height = self.end_y - self.start_y
            
            # Hiển thị thông tin và nút bắt đầu
            self.canvas.delete(self.instruction)
            self.instruction = self.canvas.create_text(
                self.screen_width // 2, 30, 
                text=f"Vung da chon: ({self.start_x}, {self.start_y}) - Kich thuoc: {width}x{height}",
                fill="green", font=("Arial", 16, "bold"))
            
            # Tạo nút bắt đầu chụp
            self.start_button = tk.Button(
                self.root, text="Bat dau chup", 
                command=self.start_capture,
                font=("Arial", 12), bg="green", fg="white")
            self.start_button_window = self.canvas.create_window(
                self.screen_width // 2, 70, 
                window=self.start_button)
            
            # Tạo nút hủy
            self.cancel_button = tk.Button(
                self.root, text="Huy", 
                command=self.on_escape,
                font=("Arial", 12), bg="red", fg="white")
            self.cancel_button_window = self.canvas.create_window(
                self.screen_width // 2 + 100, 70, 
                window=self.cancel_button)
    
    def on_escape(self, event=None):
        # Hủy chọn vùng và thoát
        if self.capture_running:
            self.capture_running = False
            if self.capture_thread:
                self.capture_thread.join(timeout=1.0)
        
        if self.preview_window:
            self.preview_window.destroy()
        
        self.root.destroy()
    
    def start_capture(self):
        # Bắt đầu chụp ảnh liên tục
        if self.selected:
            # Lưu thông tin vùng chọn
            self.save_coordinates()
            
            # Đóng cửa sổ chọn vùng
            self.root.destroy()
            
            # Tạo cửa sổ xem trước
            self.create_preview_window()
            
            # Bắt đầu luồng chụp ảnh
            self.capture_running = True
            self.capture_thread = threading.Thread(target=self.capture_loop)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            
            # Bắt đầu cập nhật giao diện
            self.update_preview()
    
    def create_preview_window(self):
        # Tạo cửa sổ xem trước
        self.preview_window = tk.Tk()
        self.preview_window.title("Ban co dang chup")
        self.preview_window.attributes('-topmost', True)
        
        # Tạo label hiển thị ảnh
        self.preview_label = tk.Label(self.preview_window)
        self.preview_label.pack(padx=10, pady=10)
        
        # Tạo khung điều khiển
        control_frame = tk.Frame(self.preview_window)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Nhãn tốc độ chụp
        tk.Label(control_frame, text="Toc do chup (giay):").pack(side=tk.LEFT, padx=5)
        
        # Thanh trượt điều chỉnh tốc độ
        self.speed_scale = tk.Scale(
            control_frame, from_=0.1, to=2.0, 
            resolution=0.1, orient=tk.HORIZONTAL,
            command=self.update_capture_speed)
        self.speed_scale.set(self.capture_delay)
        self.speed_scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Nút dừng
        self.stop_button = tk.Button(
            control_frame, text="Dung chup", 
            command=self.stop_capture,
            bg="red", fg="white")
        self.stop_button.pack(side=tk.RIGHT, padx=5)
        
        # Xử lý sự kiện đóng cửa sổ
        self.preview_window.protocol("WM_DELETE_WINDOW", self.stop_capture)
        
        # Chụp ảnh đầu tiên để hiển thị ngay
        screenshot = pyautogui.screenshot(region=(
            self.start_x, self.start_y, 
            self.end_x - self.start_x, 
            self.end_y - self.start_y))
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Hiển thị ảnh đầu tiên
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        img_tk = ImageTk.PhotoImage(image=img)
        self.preview_label.config(image=img_tk)
        self.preview_label.image = img_tk
    
    def update_capture_speed(self, value):
        # Cập nhật tốc độ chụp
        self.capture_delay = float(value)
    
    def stop_capture(self):
        # Dừng chụp ảnh
        self.capture_running = False
        if self.capture_thread:
            self.capture_thread.join(timeout=1.0)
        
        if self.preview_window:
            self.preview_window.destroy()
    
    def update_preview(self):
        """Cập nhật giao diện từ main thread"""
        if not self.capture_running or not self.preview_window:
            return
            
        try:
            # Lấy frame mới nhất từ queue (nếu có)
            if not self.frame_queue.empty():
                frame = self.frame_queue.get(block=False)
                
                # Hiển thị ảnh trong cửa sổ xem trước
                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(img)
                img_tk = ImageTk.PhotoImage(image=img)
                
                # Cập nhật label
                self.preview_label.config(image=img_tk)
                self.preview_label.image = img_tk  # Giữ tham chiếu
        except Exception as e:
            print(f"Loi khi cap nhat preview: {e}")
        
        # Lập lịch cập nhật tiếp theo
        if self.preview_window:
            self.preview_window.after(100, self.update_preview)
    
    def capture_loop(self):
        # Vòng lặp chụp ảnh liên tục
        last_frame = None
        
        while self.capture_running:
            try:
                # Chụp vùng đã chọn
                screenshot = pyautogui.screenshot(region=(
                    self.start_x, self.start_y, 
                    self.end_x - self.start_x, 
                    self.end_y - self.start_y))
                
                # Chuyển đổi sang định dạng OpenCV
                frame = np.array(screenshot)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Lưu frame hiện tại
                cv2.imwrite("current_board.png", frame)
                
                # Đưa frame vào queue để hiển thị
                if not self.frame_queue.full():
                    self.frame_queue.put(frame, block=False)
                
                # So sánh với frame trước đó (nếu cần)
                if last_frame is not None:
                    # Tính toán sự khác biệt
                    diff = cv2.absdiff(frame, last_frame)
                    gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                    _, thresh = cv2.threshold(gray_diff, 30, 255, cv2.THRESH_BINARY)
                    
                    # Nếu có sự thay đổi đáng kể
                    if np.sum(thresh) > 100000:  # Ngưỡng thay đổi
                        # Lưu ảnh với timestamp
                        timestamp = int(time.time())
                        cv2.imwrite(f"C:/Users/duong.ns/Desktop/chess/board_{timestamp}.png", frame)
                        print(f"Phat hien thay doi - Da luu anh: board_{timestamp}.png")
                
                # Cập nhật frame trước đó
                last_frame = frame
                
                # Chờ đến lần chụp tiếp theo
                time.sleep(self.capture_delay)
                
            except Exception as e:
                print(f"Loi khi chup anh: {e}")
                time.sleep(1)  # Chờ một chút nếu có lỗi
    
    def save_coordinates(self):
        # Lưu tọa độ và kích thước vùng chọn
        width = self.end_x - self.start_x
        height = self.end_y - self.start_y
        
        print(f"Tọa độ và kích thước đã lưu:")
        print(f"X: {self.start_x}, Y: {self.start_y}, Width: {width}, Height: {height}")
        
        # Tạo file Python với thông tin tọa độ - sử dụng UTF-8
        with open('C:/Users/duong.ns/Desktop/chess/board_coordinates.py', 'w', encoding='utf-8') as f:
            f.write(f"# Toa do va kich thuoc ban co\n")
            f.write(f"BOARD_X = {self.start_x}\n")
            f.write(f"BOARD_Y = {self.start_y}\n")
            f.write(f"BOARD_WIDTH = {width}\n")
            f.write(f"BOARD_HEIGHT = {height}\n")
        
        print("Đã lưu vào file 'board_coordinates.py'")

if __name__ == "__main__":
    app = ScreenCaptureApp()
    app.root.mainloop()
