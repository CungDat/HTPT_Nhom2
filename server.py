import socket
import threading
import json
import os
import time

HOST = '0.0.0.0'
PORT = 5000
clients_conn = {} 
FILE_NAME = "shared_resource.txt"
LOG_FILE = "history_log.txt"

def write_log(message):
    """Ghi log kèm thời gian thực chi tiết đến mili giây"""
    now = time.time()
    mlsec = int(now * 1000) % 1000
    timestamp = time.strftime('%H:%M:%S', time.localtime(now)) + f".{mlsec:03d}"
    
    log_entry = f"[{timestamp}] {message}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")
    
    # In ra màn hình Server có màu xanh dương để dễ nhìn
    print(f"\033[94m{log_entry}\033[0m")

def handle_client(conn, addr):
    buffer = ""
    client_id = None
    try:
        while True:
            data = conn.recv(4096).decode('utf-8')
            if not data: break
            buffer += data
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                msg = json.loads(line)

                if msg['type'] == 'INIT':
                    client_id = msg['client_id']
                    clients_conn[client_id] = conn
                    write_log(f"HỆ THỐNG: Client {client_id} đã kết nối từ {addr}")
                
                elif msg['type'] == 'PULL_FILE':
                    content = ""
                    if os.path.exists(FILE_NAME):
                        with open(FILE_NAME, "r", encoding="utf-8") as f:
                            content = f.read()
                    reply = {'type': 'FILE_CONTENT', 'content': content}
                    conn.sendall((json.dumps(reply) + "\n").encode('utf-8'))
                    write_log(f"FILE: Client {client_id} đã lấy nội dung file.")

                elif msg['type'] == 'PUSH_FILE':
                    with open(FILE_NAME, "w", encoding="utf-8") as f:
                        f.write(msg['content'])
                    write_log(f"FILE: Client {client_id} đã cập nhật file mới (Clock: {msg['clock']})")

                elif msg['type'] == 'LOG_EVENT':
                    write_log(f"SỰ KIỆN: {msg['content']} (Clock: {msg['clock']})")

                elif 'target' in msg:
                    target = msg['target']
                    if target in clients_conn:
                        clients_conn[target].sendall((json.dumps(msg) + "\n").encode('utf-8'))
    except:
        pass
    finally:
        if client_id:
            write_log(f"HỆ THỐNG: Client {client_id} ngắt kết nối.")
            if client_id in clients_conn: del clients_conn[client_id]
        conn.close()

def start_server():
    if not os.path.exists(FILE_NAME): open(FILE_NAME, "w").close()
    if not os.path.exists(LOG_FILE): open(LOG_FILE, "w").close()
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(10)
    print(f"[*] SERVER ĐANG LẮNG NGHE TẠI PORT {PORT}...")
    write_log("HỆ THỐNG: Server bắt đầu hoạt động.")
    
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()