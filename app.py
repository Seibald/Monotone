from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room, emit
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key'
socketio = SocketIO(app)

# Définition des cartes
cards = [
    {"name": "CHARGE 1", "effect": lambda hero, opponent: opponent["pv"] - 1, "count": 5},
    {"name": "CHARGE 2", "effect": lambda hero, opponent: opponent["pv"] - 2, "count": 3},
    {"name": "CHARGE 3", "effect": lambda hero, opponent: opponent["pv"] - 3, "count": 1},
    {"name": "PV 2", "effect": lambda hero, opponent: hero["pv"] + 2, "count": 3},
    {"name": "BOOST 1", "effect": lambda hero, _: hero["degats_de_reveil"] + 1, "count": 4},
    {"name": "BOOST 2", "effect": lambda hero, _: hero["degats_de_reveil"] + 2, "count": 2},
    {"name": "OUBLI 2", "effect": lambda hero, _: hero["blase_count"] - 2, "count": 4},
    {"name": "BLAZ 2", "effect": lambda hero, _: hero["blase_count"] + 2, "count": 3},
]

# Initialisation des héros
heroes = {
    "Héros 1": {"pv": 15, "degats_de_reveil": 0, "blase_count": 0,
                "effect": lambda hero: hero["degats_de_reveil"] + hero["blase_count"]},
    "Héros 2": {"pv": 15, "degats_de_reveil": 0, "blase_count": 0,
                "effect": lambda hero: hero["pv"] - (3 - hero["blase_count"])},
}

# Initialisation des salles de jeu
rooms = {}


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/redeem_code', methods=['POST'])
def redeem_code():
    code = request.form['code']
    # Logique pour débloquer un héros avec un code
    return redirect(url_for('index'))


@app.route('/start', methods=['POST'])
def start():
    hero = request.form['hero']
    room = request.form['room']
    session['hero'] = hero
    session['room'] = room
    if room not in rooms:
        rooms[room] = {
            "deck": [card for card in cards for _ in range(card["count"])],
            "player1": {"hero": hero, "pv": 15, "degats_de_reveil": 0, "blase_count": 0, "hand": []},
            "player2": {"hero": None, "pv": 15, "degats_de_reveil": 0, "blase_count": 0, "hand": []},
            "turn": 1,
            "current_player": "player1"
        }
        random.shuffle(rooms[room]["deck"])
    return redirect(url_for('game'))


@app.route('/game')
def game():
    room = session.get('room')
    if not room or room not in rooms:
        return redirect(url_for('index'))
    return render_template('game.html', room=room, turn=rooms[room]["turn"],
                           current_player_key=rooms[room]["current_player"],
                           player1=rooms[room]["player1"], player2=rooms[room]["player2"], last_card=None)


@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    if rooms[room]["player2"]["hero"] is None:
        rooms[room]["player2"]["hero"] = data['hero']
    emit('start_game', rooms[room], room=room)


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