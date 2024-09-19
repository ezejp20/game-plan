from flask import Flask, render_template, request
import random

app = Flask(__name__)

# Game plan generation function
def generate_game_plan(minutes, sub_time, game_type, players_data):
    # Determine the number of players based on the game type
    if game_type == "5_a_side":
        num_players_on_field = 5
    elif game_type == "7_a_side":
        num_players_on_field = 7
    elif game_type == "11_a_side":
        num_players_on_field = 11

    # Calculate the number of segments based on game duration and sub time
    num_segments = minutes // sub_time

    # Track playtime and substitutions for all players
    playtime_tracker = {player['name']: 0 for player in players_data}
    substitution_tracker = {player['name']: 0 for player in players_data}

    # Initialize the game plan for each segment
    game_plan = []

    # Loop over each time segment
    for segment in range(num_segments):
        segment_plan = {
            'time': f'{segment * sub_time} - {(segment + 1) * sub_time} mins',
            'positions': {
                'goal': None,
                'defense': [],
                'mid': [],
                'forward': []
            },
            'subs': []
        }

        # Sort players by least playtime to balance playtime and substitutions
        available_players = sorted(players_data, key=lambda p: playtime_tracker[p['name']])
        assigned_players = set()  # Track assigned players in this segment

        # Step 1: Assign the goalkeeper (prioritized)
        eligible_goalkeepers = [player for player in available_players if 'goal' in player['positions'] and player['name'] not in assigned_players]
        if eligible_goalkeepers:
            goalkeeper = eligible_goalkeepers[0]
            segment_plan['positions']['goal'] = goalkeeper['name']
            assigned_players.add(goalkeeper['name'])  # Mark player as assigned
            playtime_tracker[goalkeeper['name']] += sub_time
        else:
            # Assign someone to goal if no one prefers it
            goalkeeper = available_players[0]  # Automatically assign first available player
            segment_plan['positions']['goal'] = goalkeeper['name']
            assigned_players.add(goalkeeper['name'])
            playtime_tracker[goalkeeper['name']] += sub_time

        # Step 2: Assign defenders (prioritized)
        defense_players_needed = 2  # Ensure at least 2 defenders
        eligible_defenders = [player for player in available_players if 'defense' in player['positions'] and player['name'] not in assigned_players]

        while defense_players_needed > 0 and eligible_defenders:
            player = eligible_defenders.pop(0)
            segment_plan['positions']['defense'].append(player['name'])
            assigned_players.add(player['name'])  # Mark player as assigned
            playtime_tracker[player['name']] += sub_time
            defense_players_needed -= 1

        # If not enough defenders, assign others to defense
        while defense_players_needed > 0:
            player = next(p for p in available_players if p['name'] not in assigned_players)
            segment_plan['positions']['defense'].append(player['name'])
            assigned_players.add(player['name'])  # Mark player as assigned
            playtime_tracker[player['name']] += sub_time
            defense_players_needed -= 1

        # Step 3: Assign midfielders and forwards (based on preferences)
        remaining_players_needed = num_players_on_field - 1 - len(segment_plan['positions']['defense'])

        eligible_midfielders = [player for player in available_players if 'mid' in player['positions'] and player['name'] not in assigned_players]
        eligible_forwards = [player for player in available_players if 'forward' in player['positions'] and player['name'] not in assigned_players]

        # Alternate between midfield and forward, prioritizing preferences
        for i in range(remaining_players_needed):
            if i % 2 == 0 and eligible_midfielders:
                player = eligible_midfielders.pop(0)
                segment_plan['positions']['mid'].append(player['name'])
                assigned_players.add(player['name'])  # Mark player as assigned
            elif eligible_forwards:
                player = eligible_forwards.pop(0)
                segment_plan['positions']['forward'].append(player['name'])
                assigned_players.add(player['name'])  # Mark player as assigned
            else:
                # If no preferred players are left, assign others
                player = next(p for p in available_players if p['name'] not in assigned_players)
                if i % 2 == 0:
                    segment_plan['positions']['mid'].append(player['name'])
                else:
                    segment_plan['positions']['forward'].append(player['name'])
                assigned_players.add(player['name'])
                playtime_tracker[player['name']] += sub_time

        # Step 4: Add remaining players as substitutes (those not assigned)
        substitutes = [player for player in available_players if player['name'] not in assigned_players]
        for player in substitutes:
            segment_plan['subs'].append(player['name'])
            substitution_tracker[player['name']] += 1

        # Add the segment plan to the overall game plan
        game_plan.append(segment_plan)

    return game_plan












# Route to display the form
@app.route('/')
def form():
    return render_template('form.html')

# Route to handle form submission and display game plan
@app.route('/submit', methods=['POST'])
def submit():
    # Get form data
    minutes = int(request.form.get('minutes'))
    game_type = request.form.get('game_type')
    players = int(request.form.get('players'))
    sub_time = int(request.form.get('sub_time'))

    # Process player data with defaults
    player_data = []
    for i in range(1, players + 1):
        # Get the player name, defaulting to "Player 1", "Player 2", etc. if empty
        name = request.form.get(f'player_name_{i}') or f'Player {i}'

        # Get the player's selected positions
        positions = request.form.getlist(f'positions_{i}')

        # If no positions are selected, default to all positions
        if not positions:
            positions = ['defense', 'mid', 'forward', 'goal']

        # Append the player's data
        player_data.append({'name': name, 'positions': positions})

    # Generate game plan using the updated function
    game_plan = generate_game_plan(minutes, sub_time, game_type, player_data)

    # Render the game plan page with the generated plan
    return render_template('game_plan.html', game_plan=game_plan)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

