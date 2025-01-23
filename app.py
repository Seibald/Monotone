from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, async_mode='eventlet')  # Utilisation de eventlet pour Windows

# Données pour les sessions
sessions = {}


# Route pour la page d'accueil
@app.route('/')
def index():
    return render_template('index.html', sessions=sessions)


# Route pour créer une session
@app.route('/create_session', methods=['POST'])
def create_session():
    session_name = request.form.get('session_name')
    if session_name and session_name not in sessions:
        sessions[session_name] = []
        return jsonify({'success': True, 'message': 'Session créée !'})
    return jsonify({'success': False, 'message': 'Session déjà existante ou invalide.'})


# Route pour rejoindre une session
@app.route('/join_session', methods=['POST'])
def join_session():
    session_name = request.form.get('session_name')
    if session_name in sessions and len(sessions[session_name]) < 2:
        player_name = request.form.get('player_name')
        sessions[session_name].append(player_name)
        return jsonify({'success': True, 'message': 'Session rejointe !'})
    return jsonify({'success': False, 'message': 'Impossible de rejoindre la session.'})


# Route pour la page de jeu
@app.route('/game/<session_name>')
def game(session_name):
    if session_name in sessions and len(sessions[session_name]) == 2:
        return render_template('game.html', session_name=session_name, players=sessions[session_name])
    return redirect(url_for('index'))


# WebSocket : Gérer les connexions
@socketio.on('connect')
def handle_connect():
    print('Un utilisateur est connecté.')


@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)
    emit('message', f"Un joueur a rejoint la session {room}", to=room)


@socketio.on('leave')
def on_leave(data):
    room = data['room']
    leave_room(room)
    emit('message', f"Un joueur a quitté la session {room}", to=room)


# Logique du jeu (Cartes, effets, et partie)
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
        target = input("Choisissez une cible pour OUBLI 2 (1 ou 2): ")
        if target == "1":
            player['blase_count'] = max(0, player['blase_count'] - 2)
        elif target == "2":
            opponent['blase_count'] = max(0, opponent['blase_count'] - 2)
    elif card == "BLAZ 2":
        target = input("Choisissez une cible pour BLAZ 2 (1 ou 2): ")
        if target == "1":
            player['blase_count'] += 2
        elif target == "2":
            opponent['blase_count'] += 2


# Effet des héros
def hero_effect(hero, player, opponent):
    if hero == "Héros 1":
        player['degats_de_reveil'] += player['blase_count']
        print(f"Effet de Héros 1 activé : Ajout de {player['blase_count']} à vos dégâts de réveil.")
    elif hero == "Héros 2":
        damage = max(0, 3 - player['blase_count'])
        opponent['pv'] -= damage
        print(f"Effet de Héros 2 activé : Retrait de {damage} PV à l'adversaire.")


# Fonction de démarrage du jeu
def start_game(session_name):
    # Initialiser les joueurs
    player1 = {
        "pv": 15,
        "degats_de_reveil": 0,
        "blase_count": 0,
        "hero": "Héros 1"
    }

    player2 = {
        "pv": 15,
        "degats_de_reveil": 0,
        "blase_count": 0,
        "hero": "Héros 2"
    }

    # Choisir le joueur 1
    starting_player = random.choice([1, 2])
    print(f"\nLe Joueur {starting_player} commence la partie !")

    return player1, player2


if __name__ == "__main__":
    socketio.run(app, debug=True)
