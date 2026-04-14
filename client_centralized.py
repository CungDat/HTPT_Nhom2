import socket, threading, json, time, os, platform, subprocess

class CentralizedClient:
    def __init__(self, client_id, host, port):
        self.id, self.host, self.port = client_id, host, port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.grant_event = threading.Event()
        self.file_ready = threading.Event()
        self.file_content = ""

    def listen(self):
        buf = ""
        while True:
            try:
                data = self.sock.recv(4096).decode('utf-8')
                if not data: break
                buf += data
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    msg = json.loads(line)
                    if msg['type'] == 'GRANT': self.grant_event.set()
                    elif msg['type'] == 'FILE_CONTENT':
                        self.file_content = msg['content']
                        self.file_ready.set()
            except: break

    def start(self):
        self.sock.connect((self.host, self.port))
        self.sock.sendall((json.dumps({'type': 'INIT', 'client_id': self.id}) + '\n').encode('utf-8'))
        threading.Thread(target=self.listen, daemon=True).start()
        
        while True:
            input("\n>> Nhấn ENTER để xin vào miền găng...")
            self.grant_event.clear()
            self.sock.sendall((json.dumps({'type': 'REQUEST', 'sender': self.id}) + '\n').encode('utf-8'))
            
            print("[!] Đang đợi điều phối viên cấp quyền...")
            self.grant_event.wait() # Bị chặn ở đây nếu Server chưa cho phép
            
            print("\033[92m[★★★] ĐÃ VÀO MIỀN GĂNG!\033[0m")
            self.file_ready.clear()
            self.sock.sendall((json.dumps({'type': 'PULL_FILE', 'sender': self.id}) + '\n').encode('utf-8'))
            self.file_ready.wait()

            with open("local_edit.txt", "w", encoding="utf-8") as f: f.write(self.file_content)
            try:
                if platform.system() == 'Windows': os.startfile('local_edit.txt')
                else: subprocess.call(['open' if platform.system()=='Darwin' else 'xdg-open', 'local_edit.txt'])
            except: pass

            input("Sửa xong, LƯU và ĐÓNG Notepad rồi nhấn ENTER tại đây...")
            with open("local_edit.txt", "r", encoding="utf-8") as f: content = f.read()
            self.sock.sendall((json.dumps({'type': 'PUSH_FILE', 'sender': self.id, 'content': content}) + '\n').encode('utf-8'))
            self.sock.sendall((json.dumps({'type': 'RELEASE', 'sender': self.id}) + '\n').encode('utf-8'))

if __name__ == "__main__":
    cid = int(input("ID (1-3): "))
    ip = "26.253.119.99"
    CentralizedClient(cid, ip, 5000).start()