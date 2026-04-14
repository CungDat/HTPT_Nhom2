import socket, threading, json, os, time

HOST, PORT = '0.0.0.0', 5000
FILE_NAME, LOG_FILE = "shared_resource.txt", "history_log.txt"
clients_conn = {}
request_queue = []   # Hàng đợi các máy đang chờ
is_busy = False      # Trạng thái: Có ai đang sửa file không?

def write_log(message):
    now = time.time()
    timestamp = time.strftime('%H:%M:%S', time.localtime(now)) + f".{int(now*1000)%1000:03d}"
    log_entry = f"[{timestamp}] {message}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")
    print(f"\033[94m{log_entry}\033[0m")

def handle_client(conn, addr):
    global is_busy
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

                elif msg['type'] == 'REQUEST':
                    write_log(f"YÊU CẦU: Client {client_id} xin vào miền găng.")
                    if not is_busy:
                        # Cấp quyền ngay lập tức
                        is_busy = True
                        write_log(f"CẤP QUYỀN: Cho phép Client {client_id} vào.")
                        conn.sendall((json.dumps({'type': 'GRANT'}) + "\n").encode('utf-8'))
                    else:
                        # Tài nguyên bận, đưa vào hàng đợi, KHÔNG trả lời (chặn client)
                        request_queue.append(client_id)
                        write_log(f"HÀNG ĐỢI: Client {client_id} phải đợi (Hàng đợi: {request_queue})")

                elif msg['type'] == 'RELEASE':
                    write_log(f"GIẢI PHÓNG: Client {client_id} đã xong việc.")
                    if request_queue:
                        next_id = request_queue.pop(0)
                        is_busy = True # Chuyển quyền cho người tiếp theo
                        write_log(f"CẤP QUYỀN TIẾP: Cho phép Client {next_id} từ hàng đợi.")
                        clients_conn[next_id].sendall((json.dumps({'type': 'GRANT'}) + "\n").encode('utf-8'))
                    else:
                        is_busy = False

                elif msg['type'] == 'PULL_FILE':
                    content = ""
                    if os.path.exists(FILE_NAME):
                        with open(FILE_NAME, "r", encoding="utf-8") as f: content = f.read()
                    conn.sendall((json.dumps({'type': 'FILE_CONTENT', 'content': content}) + "\n").encode('utf-8'))

                elif msg['type'] == 'PUSH_FILE':
                    with open(FILE_NAME, "w", encoding="utf-8") as f: f.write(msg['content'])
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
    print(f"[*] SERVER ĐIỀU PHỐI (CENTRALIZED) ĐANG CHẠY TẠI {PORT}...")
    while True:
        c, a = server.accept()
        threading.Thread(target=handle_client, args=(c, a), daemon=True).start()