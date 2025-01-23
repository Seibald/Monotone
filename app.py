from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app)

# Cartes disponibles
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

sessions = {}

# Effets des cartes
def apply_card_effect(card, player, opponent, target=None):
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
        if target == 'self':
            player['blase_count'] = max(0, player['blase_count'] - 2)
        else:
            opponent['blase_count'] = max(0, opponent['blase_count'] - 2)
    elif card == "BLAZ 2":
        if target == 'self':
            player['blase_count'] += 2
        else:
            opponent['blase_count'] += 2

# Effet des héros
def hero_effect(hero, player, opponent):
    if hero == "Héros 1":
        player['degats_de_reveil'] += player['blase_count']
    elif hero == "Héros 2":
        damage = max(0, 3 - player['blase_count'])
        opponent['pv'] -= damage

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('get_sessions')
def get_sessions():
    sessions_list = [
        {'name': room, 'players': len(sessions[room]['players'])}
        for room in sessions
    ]
    emit('update_sessions', {'sessions': sessions_list}, broadcast=True)

@socketio.on('create_game')
def create_game(data):
    room = data['room']
    if room in sessions:
        emit('error', {'message': 'Cette session existe déjà.'})
        return

    sessions[room] = {
        'players': [],
        'deck': [],
        'turn': 1,
        'current_player': None,
        'game_started': False
    }

    # Ajouter les cartes au deck
    for card, count in cards:
        sessions[room]['deck'].extend([card] * count)
    random.shuffle(sessions[room]['deck'])

    join_room(room)
    emit('game_created', {'message': f'Session {room} créée.'}, room=request.sid)
    emit('update_sessions', {'sessions': [
        {'name': room, 'players': len(sessions[room]['players'])}
        for room in sessions
    ]}, broadcast=True)


@socketio.on('join_game')
def join_game(data):
    room = data['room']
    if room not in sessions:
        emit('error', {'message': 'Session inexistante.'})
        return

    if len(sessions[room]['players']) >= 2:
        emit('error', {'message': 'Session pleine.'})
        return

    player = {
        'id': request.sid,
        'pv': 15,
        'degats_de_reveil': 0,
        'blase_count': 0,
        'hero': None
    }
    sessions[room]['players'].append(player)
    join_room(room)

    if len(sessions[room]['players']) == 2:
        emit('ready_to_start', {'message': 'Les deux joueurs sont prêts !'}, room=room)

@socketio.on('choose_hero')
def choose_hero(data):
    room = data['room']
    hero = data['hero']

    player = next(p for p in sessions[room]['players'] if p['id'] == request.sid)
    player['hero'] = hero

    if all(p['hero'] for p in sessions[room]['players']):
        emit('start_game', {'message': 'Début de la partie.'}, room=room)

@socketio.on('roll_dice')
def roll_dice(data):
    room = data['room']
    dice = random.randint(1, 6)
    emit('dice_result', {'player_id': request.sid, 'dice': dice}, room=room)

@socketio.on('play_card')
def play_card(data):
    room = data['room']
    action = data['action']
    target = data.get('target', None)

    session = sessions[room]
    player = session['players'][session['current_player']]
    opponent = session['players'][1 - session['current_player']]

    # Piocher une carte
    if not session['deck']:
        emit('game_over', {'winner': 'Egalité (pioche épuisée)'}, room=room)
        return

    card = session['deck'].pop()
    if action == 'eveillez':
        opponent['pv'] -= player['degats_de_reveil']
        player['degats_de_reveil'] = 0
        apply_card_effect(card, player, opponent, target)
    elif action == 'blasez':
        player['blase_count'] += 1
        hero_effect(player['hero'], player, opponent)

    # Vérifier si la partie est terminée
    if opponent['pv'] <= 0:
        emit('game_over', {'winner': f'Joueur {1 if session["current_player"] == 0 else 2}'}, room=room)
        return

    # Passer au joueur suivant
    session['current_player'] = 1 - session['current_player']
    emit('update_game', {'player': player, 'opponent': opponent, 'card': card}, room=room)

if __name__ == '__main__':
    socketio.run(app, debug=True)
