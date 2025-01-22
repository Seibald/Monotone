# -*- coding: utf-8 -*-
from flask import Flask, render_template, session, request, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, emit
import random

app = Flask(__name__)
app.secret_key = "votre_clé_secrète"  # Nécessaire pour utiliser des sessions
socketio = SocketIO(app)

# Définition des cartes et des effets
cards = [
    ("CHARGE 1", 5),
    ("CHARGE 2", 3),
    ("CHARGE 3", 1),
    ("PV 2", 3),
    ("BOOST 1", 4),
    ("BOOST 2", 2),
    ("OUBLI 2", 4),
    ("BLAZ 2", 3)
]

# Joueurs et parties
games = {}


def apply_card_effect(card, player, opponent):
    if card.startswith("CHARGE"):
        charge_value = int(card.split()[1])
        opponent['pv'] -= charge_value
    elif card.startswith("PV"):
        pv_value = int(card.split()[1])
        player['pv'] += pv_value
    elif card.startswith("BOOST"):
        boost_value = int(card.split()[1])
        player['degats_de_reveil'] += boost_value
    elif card == "OUBLI 2":
        pass
    elif card == "BLAZ 2":
        pass


def hero_effect(hero, player, opponent):
    if hero == "Héros 1":
        player['degats_de_reveil'] += player['blase_count']
    elif hero == "Héros 2":
        damage = max(0, 3 - player['blase_count'])
        opponent['pv'] -= damage


@app.route('/')
def index():
    return render_template("index.html")

@app.route('/redeem_code', methods=['POST'])
def redeem_code():
    code = request.form.get('code')
    valid_codes = {
        "CODE123": "Héros 3",
        "CODE456": "Héros 4"
    }
    if code in valid_codes:
        session['heroes'] = session.get('heroes', [])
        session['heroes'].append(valid_codes[code])
        return redirect(url_for('index'))
    else:
        return "Code invalide.", 400

@app.route('/start', methods=['POST'])
def start():
    room = request.form.get('room')
    hero = request.form.get('hero')
    if room not in games:
        games[room] = {
            'deck': create_deck(),
            'players': {
                'player1': {"pv": 15, "degats_de_reveil": 0, "blase_count": 0, "hero": hero},
                'player2': None
            },
            'turn': 1,
            'current_player': 'player1'
        }
    session['room'] = room
    return redirect(url_for('game'))


def create_deck():
    deck = []
    for card, count in cards:
        deck.extend([card] * count)
    random.shuffle(deck)
    return deck


@app.route('/game')
def game():
    room = session.get('room')
    if not room or room not in games:
        return redirect(url_for('index'))
    return render_template("game.html", room=room)


@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    if games[room]['players']['player2'] is None:
        games[room]['players']['player2'] = {"pv": 15, "degats_de_reveil": 0, "blase_count": 0, "hero": data['hero']}
        emit('start_game', games[room], room=room)


@socketio.on('play_card')
def on_play_card(data):
    room = data['room']
    game = games[room]
    current_player_key = game['current_player']
    opponent_key = 'player1' if current_player_key == 'player2' else 'player2'
    current_player = game['players'][current_player_key]
    opponent = game['players'][opponent_key]

    card = data['card']
    if card in ["OUBLI 2", "BLAZ 2"]:
        target = data['target']
        if target == 'self':
            apply_card_effect(card, current_player, current_player)
        else:
            apply_card_effect(card, current_player, opponent)
    else:
        apply_card_effect(card, current_player, opponent)

    game['current_player'] = opponent_key
    game['turn'] += 1
    emit('update_game', game, room=room)


if __name__ == '__main__':
    socketio.run(app, debug=True)
