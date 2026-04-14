import socket
import threading
import json
import time
import os
import platform
import subprocess

class RicartAgrawalaNode:
    def __init__(self, client_id, total, send_raw):
        self.id, self.total, self.send_raw = client_id, total, send_raw
        self.clock, self.state = 0, 'RELEASED'
        self.queue, self.ok_count = [], 0
        self.lock = threading.Lock()
        self.file_content = ""
        self.file_ready = threading.Event()

    def log_to_server(self, content):
        self.send_raw({'type': 'LOG_EVENT', 'sender': self.id, 'content': content, 'clock': self.clock})

    def request_access(self):
        with self.lock:
            self.state = 'WANTED'
            self.clock += 1
            self.ok_count = 0
            req_clock = self.clock
        
        self.log_to_server(f"Client {self.id} đang xin quyền")
        print(f"\n[!] Xin quyền vào Miền Găng (Clock: {req_clock})...")
        
        for i in range(1, self.total + 1):
            if i != self.id:
                self.send_raw({'type': 'REQUEST', 'sender': self.id, 'target': i, 'clock': req_clock})
        
        while self.ok_count < self.total - 1:
            time.sleep(0.1)
        
        with self.lock: self.state = 'HELD'
        self.log_to_server(f"Client {self.id} đã chiếm được Miền Găng")
        print(f"\033[92m[★★★] ĐÃ VÀO MIỀN GĂNG.\033[0m")

    def release_access(self):
        with self.lock:
            self.state = 'RELEASED'
            self.log_to_server(f"Client {self.id} đã RELEASED. Gửi OK cho các máy đợi: {self.queue}")
            for waiter in self.queue:
                self.send_raw({'type': 'OK', 'sender': self.id, 'target': waiter, 'clock': self.clock})
            self.queue.clear()
        print(f"[✓] Đã thoát Miền Găng và nhường quyền cho các máy khác.")

    def handle_msg(self, msg):
        with self.lock:
            self.clock = max(self.clock, msg.get('clock', 0)) + 1
            if msg['type'] == 'REQUEST':
                s, c = msg['sender'], msg['clock']
                # TÍNH NĂNG MỚI: Thông báo khi có người khác đang đợi mình
                if self.state == 'HELD':
                    print(f"\n\033[93m[!] THÔNG BÁO: Client {s} vừa nhấn Enter xin vào (đang đợi bạn xong)...\033[0m")
                    self.queue.append(s)
                elif self.state == 'WANTED' and (self.clock, self.id) < (c, s):
                    self.queue.append(s)
                else:
                    self.send_raw({'type': 'OK', 'sender': self.id, 'target': s, 'clock': self.clock})
            elif msg['type'] == 'OK':
                self.ok_count += 1
            elif msg['type'] == 'FILE_CONTENT':
                self.file_content = msg['content']
                self.file_ready.set()

def main():
    # NHỚ CHỈNH SỐ 3 HOẶC 4 TÙY THEO SỐ NGƯỜI TEST
    NUM_NODES = 3 
    
    my_id = int(input(f"Nhập ID của bạn (1-{NUM_NODES}): "))
    host = "26.253.119.99"
    port = 5000
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    
    def send_raw(data): sock.sendall((json.dumps(data) + '\n').encode('utf-8'))
    
    node = RicartAgrawalaNode(my_id, NUM_NODES, send_raw)
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
            except: break
    threading.Thread(target=listen, daemon=True).start()

    while True:
        input("\n>> Nhấn ENTER để xin quyền sửa file...")
        node.request_access()
        
        node.file_ready.clear()
        send_raw({'type': 'PULL_FILE', 'sender': my_id, 'clock': node.clock})
        if not node.file_ready.wait(timeout=5):
            print("Lỗi: Server không phản hồi nội dung file!")
            node.release_access()
            continue
        
        with open("local_edit.txt", "w", encoding="utf-8") as f:
            f.write(node.file_content)
        
        # TỰ ĐỘNG BẬT NOTEPAD
        try:
            if platform.system() == 'Windows':
                os.startfile('local_edit.txt')
            else:
                subprocess.call(['open' if platform.system() == 'Darwin' else 'xdg-open', 'local_edit.txt'])
        except:
            print("Vui lòng tự mở file local_edit.txt để sửa.")

        print(f"--- ĐANG TRONG MIỀN GĂNG ---")
        input("Sau khi sửa xong, LƯU và ĐÓNG Notepad rồi nhấn ENTER tại đây để kết thúc...")
        
        with open("local_edit.txt", "r", encoding="utf-8") as f:
            new_data = f.read()
        send_raw({'type': 'PUSH_FILE', 'sender': my_id, 'content': new_data, 'clock': node.clock})
        
        node.release_access()

if __name__ == "__main__":
    main()