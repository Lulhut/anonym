from flask import Flask, render_template, request
from flask_limiter import Limiter
from flask_socketio import SocketIO, emit
from flask_cors import CORS


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

def get_user_ip():
    forwarded_for = request.headers.get('X-Forwarded-For', None)
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote_addr

limiter = Limiter(get_user_ip, app=app)

socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
@limiter.limit("10 per second")
def home():
    return render_template('home.html')


# ===================== WEBSOCKET EVENTS ===================== #

connected_users = {}  # user_id -> socket_id (sid)
public_keys = {}
queue = []

@socketio.on("connect")
def on_connect(data):
    sid = request.sid
    if not data or "public_key" not in data:
        return
    key = data["public_key"]
    public_keys[sid] = key
    if not len(queue) == 0:
        other_sid = queue.pop(0)
        connected_users[sid] = other_sid
        emit("connected", {"public_key": public_keys[other_sid]}, to=sid)
        connected_users[other_sid] = sid
        emit("connected", {"public_key": key}, to=other_sid)
    else:
        queue.append(sid)
    print("Client connected:", sid)

@socketio.on("chat")
def register_user(data):
    sid = request.sid
    if sid in queue:
        return
    message = data["message"]
    other_sid = connected_users.get(sid)
    if other_sid:
        emit("chat", {"message": message}, to=other_sid)
    print(f"User hat jetzt SID {sid}")

@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    print("Client disconnected:", sid)
    if sid in connected_users:
        other_sid = connected_users[sid]
        emit("partner_disconnected", to=other_sid)
        del connected_users[other_sid]
        del connected_users[sid]
    elif sid in queue:
        queue.remove(sid)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=9295)
