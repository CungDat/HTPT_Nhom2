import socket, threading, json, os, time

HOST, PORT = '0.0.0.0', 5000
FILE_NAME, LOG_FILE = "shared_resource.txt", "history_log.txt"
clients_conn = {}

def write_log(message):
    now = time.time()
    timestamp = time.strftime('%H:%M:%S', time.localtime(now)) + f".{int(now*1000)%1000:03d}"
    log_entry = f"[{timestamp}] {message}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")
    # In màu vàng cho các sự kiện TOKEN để Đạt dễ theo dõi
    if "TOKEN" in message:
        print(f"\033[93m{log_entry}\033[0m")
    else:
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
                client_id = msg.get('sender') or msg.get('client_id')

                if msg['type'] == 'INIT':
                    clients_conn[client_id] = conn
                    write_log(f"HỆ THỐNG: Client {client_id} đã kết nối.")

                elif msg['type'] == 'TOKEN':
                    target = msg['target']
                    write_log(f"CHUYỀN THẺ: Node {msg['sender']} ---> Node {target}")
                    if target in clients_conn:
                        clients_conn[target].sendall((json.dumps(msg) + "\n").encode('utf-8'))
                    else:
                        # Nếu máy tiếp theo chưa online, giữ Token lại hoặc báo lỗi
                        write_log(f"LỖI: Node {target} chưa online, Token bị kẹt tại Server!")

                elif msg['type'] == 'PULL_FILE':
                    content = ""
                    if os.path.exists(FILE_NAME):
                        with open(FILE_NAME, "r", encoding="utf-8") as f: content = f.read()
                    conn.sendall((json.dumps({'type': 'FILE_CONTENT', 'content': content}) + "\n").encode('utf-8'))

                elif msg['type'] == 'PUSH_FILE':
                    with open(FILE_NAME, "w", encoding="utf-8") as f: f.write(msg['content'])
                    write_log(f"FILE: Client {client_id} đã cập nhật file.")

                elif msg['type'] == 'LOG_EVENT':
                    write_log(f"CLIENT {client_id}: {msg['content']}")
    except: pass
    finally:
        if client_id in clients_conn: del clients_conn[client_id]
        conn.close()

if __name__ == "__main__":
    if not os.path.exists(FILE_NAME): open(FILE_NAME, "w").close()
    if not os.path.exists(LOG_FILE): open(LOG_FILE, "w").close()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(10)
    print(f"[*] SERVER TOKEN RING ĐANG CHẠY TẠI {PORT}...")
    while True:
        c, a = server.accept()
        threading.Thread(target=handle_client, args=(c, a), daemon=True).start()