from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, emit
import uuid

app = Flask(__name__)
socketio = SocketIO(app)

sessions = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_session', methods=['POST'])
def create_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = {'players': []}
    return redirect(url_for('session', session_id=session_id))

@app.route('/session/<session_id>')
def session(session_id):
    if session_id not in sessions:
        return redirect(url_for('index'))
    return render_template('session.html', session_id=session_id)

@socketio.on('join')
def on_join(data):
    session_id = data['session']
    username = data['username']
    join_room(session_id)
    if len(sessions[session_id]['players']) < 2:
        sessions[session_id]['players'].append(username)
    emit('update', sessions[session_id], room=session_id)

@socketio.on('move')
def on_move(data):
    session_id = data['session']
    emit('move', data, room=session_id)

if __name__ == '__main__':
    socketio.run(app, debug=True)