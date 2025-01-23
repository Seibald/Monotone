from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app)

# Définir les cartes et les effets
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

rooms = {}  # Dictionnaire pour stocker les informations des salles de jeu

# Effets des cartes
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
        target = session.get('target')
        if target == "self":
            player['blase_count'] = max(0, player['blase_count'] - 2)
        elif target == "opponent":
            opponent['blase_count'] = max(0, opponent['blase_count'] - 2)
    elif card == "BLAZ 2":
        target = session.get('target')
        if target == "self":
            player['blase_count'] += 2
        elif target == "opponent":
            opponent['blase_count'] += 2

# Effet des héros
def hero_effect(hero, player, opponent):
    if hero == "Héros 1":
        player['degats_de_reveil'] += player['blase_count']
    elif hero == "Héros 2":
        damage = max(0, 3 - player['blase_count'])
        opponent['pv'] -= damage

# Routes Flask
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/redeem_code', methods=['POST'])
def redeem_code():
    # Gestion du code pour débloquer un héros
    # Pour l'instant, on redirige simplement vers l'index
    return redirect(url_for('index'))

@app.route('/start', methods=['POST'])
def start():
    session['hero'] = request.form['hero']
    session['room'] = request.form['room']
    room = session['room']
    if room not in rooms:
        rooms[room] = {
            'players': [],
            'deck': [],
            'current_turn': 1,
            'last_card': None
        }
    if len(rooms[room]['players']) < 2:
        rooms[room]['players'].append({
            'pv': 15,
            'degats_de_reveil': 0,
            'blase_count': 0,
            'hero': request.form['hero'],
            'username': session['username']
        })
    return redirect(url_for('game'))

@app.route('/game')
def game():
    room = session['room']
    if len(rooms[room]['players']) < 2:
        return "En attente d'un autre joueur..."
    return render_template('game.html', room=room)

@app.route('/end')
def end():
    return render_template('end.html', winner=session.get('winner'))

# Gestion des événements Socket.IO
@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    emit('start_game', {'msg': f'Un joueur a rejoint la salle {room}'}, room=room)
    if len(rooms[room]['players']) == 2:
        start_game(room)

def start_game(room):
    deck = []
    for card, count in cards:
        deck.extend([card] * count)
    random.shuffle(deck)
    rooms[room]['deck'] = deck
    emit('start_game', {'msg': 'La partie commence !'}, room=room)

@socketio.on('play_card')
def on_play_card(data):
    room = data['room']
    card = data['card']
    target = data['target']

    session['target'] = target
    player = rooms[room]['players'][0]  # Joueur 1
    opponent = rooms[room]['players'][1]  # Joueur 2

    if card == "eveillez":
        opponent['pv'] -= player['degats_de_reveil']
        player['degats_de_reveil'] = 0
        apply_card_effect(rooms[room]['last_card'], player, opponent)
    elif card == "blasez":
        player['blase_count'] += 1
        hero_effect(player['hero'], player, opponent)

    if opponent['pv'] <= 0:
        session['winner'] = player['hero']
        emit('end_game', {'winner': player['hero']}, room=room)
    else:
        emit('update_game', {'player': player, 'opponent': opponent}, room=room)

if __name__ == '__main__':
    socketio.run(app, debug=True)