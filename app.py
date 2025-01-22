from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room
import random

app = Flask(__name__)
app.secret_key = 'votre_cle_secrete'
socketio = SocketIO(app)

# Définir les cartes
deck = [
    *(['CHARGE 1'] * 5), *(['CHARGE 2'] * 3), ['CHARGE 3'],
    *(['PV 2'] * 3), *(['BOOST 1'] * 4), *(['BOOST 2'] * 2),
    *(['OUBLI 2'] * 4), *(['BLAZ 2'] * 3)
]

# Stocker les données des parties
games = {}

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_game():
    hero = request.form['hero']
    room = request.form['room']
    session['hero'] = hero
    session['room'] = room
    if room not in games:
        games[room] = {
            'player1': {'pv': 15, 'degats_de_reveil': 0, 'blase_count': 0},
            'player2': {'pv': 15, 'degats_de_reveil': 0, 'blase_count': 0},
            'deck': random.sample(deck, len(deck)),
            'turn': 1,
            'last_card': None
        }
    return render_template('game.html', room=room, turn=1, last_card=None)

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    emit('start_game', games[room], room=room)
    
@socketio.on('play_card')
def on_play_card(data):
    room = data['room']
    card_name = data['card']
    target = data['target']
    room_data = rooms[room]
    current_player = room_data["current_player"]
    opponent = "player2" if current_player == "player1" else "player1"
    card = next(card for card in cards if card["name"] == card_name)

    if card_name in ["OUBLI 2", "BLAZ 2"]:
        if target == "self":
            room_data[current_player]["blase_count"] = card["effect"](room_data[current_player], room_data[opponent])
        else:
            room_data[opponent]["blase_count"] = card["effect"](room_data[opponent], room_data[current_player])
    else:
        room_data[current_player]["degats_de_reveil"] = 0
        room_data[opponent]["pv"] = card["effect"](room_data[current_player], room_data[opponent])

    room_data["current_player"] = opponent
    room_data["turn"] += 1
    emit('update_game', room_data, room=room)


if __name__ == '__main__':
    socketio.run(app, debug=True)