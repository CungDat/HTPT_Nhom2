import socket, threading, json, time, os, platform, subprocess

class TokenRingNode:
    def __init__(self, client_id, total_nodes, send_raw):
        self.id = client_id
        self.total = total_nodes
        self.send_raw = send_raw
        
        # Trạng thái: RELEASED (Không cần), WANTED (Đang chờ thẻ), HELD (Đang trong miền găng)
        self.state = 'RELEASED'
        self.has_token = False
        
        # Công thức Vòng tròn (1->2, 2->3, 3->4, 4->1)
        self.next_id = (self.id % self.total) + 1
        
        self.file_content = ""
        self.file_ready = threading.Event()
        self.token_event = threading.Event()
        
        # Bật luồng chạy ngầm chuyên xử lý và chuyền Thẻ bài
        threading.Thread(target=self.token_runner, daemon=True).start()

    def log(self, content):
        self.send_raw({'type': 'LOG_EVENT', 'sender': self.id, 'content': content})

    def pass_token(self):
        self.has_token = False
        # Gửi thẻ bài (TOKEN) cho máy tiếp theo thông qua Server trung gian
        self.send_raw({'type': 'TOKEN', 'sender': self.id, 'target': self.next_id})

    def token_runner(self):
        """Luồng ngầm: Liên tục kiểm tra xem mình có đang giữ thẻ bài không"""
        while True:
            if self.has_token:
                if self.state == 'WANTED':
                    self.state = 'HELD'
                    self.token_event.set() # Đánh thức luồng chính đang bị kẹt
                    
                    # Ngủ đông ở đây chờ luồng chính sửa file xong (đổi state thành RELEASED)
                    while self.state == 'HELD':
                        time.sleep(0.1)
                
                if self.state == 'RELEASED':
                    time.sleep(0.5) # Dừng 0.5s để thẻ bài bay chậm lại, dễ quan sát log
                    self.pass_token()
            time.sleep(0.05)

    def request_access(self):
        self.state = 'WANTED'
        self.log(f"Client {self.id} đang WANTED, đợi Token")
        print(f"[...] Đang đợi Token quay tới...")
        
        self.token_event.clear()
        self.token_event.wait() # Code sẽ kẹt ở đây cho tới khi token_runner chộp được thẻ bài
        
        self.log(f"Client {self.id} đã HELD (Có Token)")
        print(f"[★★★] ĐÃ CHỘP ĐƯỢC TOKEN. ĐANG VÀO MIỀN GĂNG.")

    def release_access(self):
        self.state = 'RELEASED'
        self.log(f"Client {self.id} đã RELEASED. Chuyền Token.")
        print(f"[✓] Đã thoát Miền Găng. Chuyền Token cho Node {self.next_id}.")

    def handle_msg(self, msg):
        # Hàm này được gọi bởi luồng lắng nghe Socket
        if msg['type'] == 'TOKEN':
            self.has_token = True
        elif msg['type'] == 'FILE_CONTENT':
            self.file_content = msg['content']
            self.file_ready.set()

def main():
    print("=== HỆ THỐNG ĐỒNG BỘ TOKEN RING ===")
    my_id = int(input("Nhập ID (1, 2, 3, 4): "))
    total_nodes = 3
    host = "26.253.119.99"  # IP Server Radmin của nhóm bạn
    port = 5000
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
    except Exception as e:
        print(f"Không thể kết nối đến Server {host}:{port}. Lỗi: {e}")
        return

    def send_raw(data): 
        sock.sendall((json.dumps(data) + '\n').encode('utf-8'))
        
    node = TokenRingNode(my_id, total_nodes, send_raw)
    send_raw({'type': 'INIT', 'client_id': my_id})
    
    def listen():
        buf = ""
        while True:
            try:
                data = sock.recv(4096).decode('utf-8')
                if not data: break
                buf += data
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    node.handle_msg(json.loads(line))
            except: 
                print("\nMất kết nối tới Server.")
                break
    threading.Thread(target=listen, daemon=True).start()

    print(f"\n--- THIẾT LẬP: Mạng vòng truyền từ Node {my_id} ---> Node {node.next_id} ---")

    while True:
        cmd = input("\n>> Nhấn ENTER để xin sửa file, hoặc gõ 'START' để mồi Token: ")
        
        # BƯỚC KHỞI TẠO MẠNG
        if cmd.strip().upper() == 'START':
            if my_id == 1:
                node.has_token = True
                print("[!] Đã phát nổ mồi Token vào mạng vòng!")
            else:
                print("Chỉ Node 1 mới nên mồi Token để tránh hệ thống có 2 thẻ bài!")
            continue

        # BƯỚC XIN QUYỀN VÀ SỬA FILE
        node.request_access()
        
        node.file_ready.clear()
        send_raw({'type': 'PULL_FILE', 'sender': my_id})
        if not node.file_ready.wait(timeout=5):
            print("Lỗi: Không nhận được file từ Server!")
            node.release_access()
            continue
            
        with open("local_edit.txt", "w", encoding="utf-8") as f: 
            f.write(node.file_content)
        
        try:
            if platform.system() == 'Windows': os.startfile('local_edit.txt')
            else: subprocess.call(['open' if platform.system()=='Darwin' else 'xdg-open', 'local_edit.txt'])
        except: 
            print("Hãy tự mở local_edit.txt")

        input("Sửa xong, LƯU và ĐÓNG Notepad rồi nhấn ENTER tại đây...")
        with open("local_edit.txt", "r", encoding="utf-8") as f: 
            content = f.read()
            
        send_raw({'type': 'PUSH_FILE', 'sender': my_id, 'content': content})
        node.release_access()

if __name__ == "__main__":
    main()