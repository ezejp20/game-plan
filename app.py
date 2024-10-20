from flask import Flask, render_template, request
import random

app = Flask(__name__)

# Function to calculate substitution time
def calculate_sub_time(minutes, min_sub_time_input, num_players, num_goalkeepers):
    outfield_players = num_players - num_goalkeepers
    if not min_sub_time_input:
        ideal_sub_time = minutes // outfield_players
        return ideal_sub_time
    min_sub_time = int(min_sub_time_input)
    ideal_sub_time = minutes // outfield_players
    if min_sub_time < ideal_sub_time:
        return ideal_sub_time
    else:
        return min_sub_time

# Game plan generation function with goalie rotation
def generate_game_plan(minutes, sub_time, game_type, players_data):
    if game_type == "5_a_side":
        num_players_on_field = 5
    elif game_type == "7_a_side":
        num_players_on_field = 7
    elif game_type == "11_a_side":
        num_players_on_field = 11

    num_segments = minutes // sub_time

    playtime_tracker = {player['name']: 0 for player in players_data}
    substitution_tracker = {player['name']: 0 for player in players_data}

    game_plan = []

    # Split players into active and substitutes
    active_players = players_data[:num_players_on_field]
    substitute_players = players_data[num_players_on_field:]

    # Separate goalkeepers from the rest of the players for rotation
    goalkeepers = [player for player in players_data if 'goal' in player['positions']]
    goalie_rotation_index = 0

    # Function to prioritize players with fewer preferred positions and those who have sat out
    def prioritize_by_playtime(players, position, assigned_players):
        return sorted(
            [player for player in players if position in player['positions'] and player['name'] not in assigned_players],
            key=lambda p: (playtime_tracker[p['name']], len(p['positions']))
        )

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

        # Track assigned players for the current segment
        assigned_players = set()

        # Step 1: Rotate goalkeepers across segments
        if goalkeepers:
            current_goalkeeper = goalkeepers[goalie_rotation_index % len(goalkeepers)]['name']
            goalie_rotation_index += 1
        else:
            current_goalkeeper = active_players[0]['name']  # Fallback if no goalkeepers

        segment_plan['positions']['goal'] = current_goalkeeper
        assigned_players.add(current_goalkeeper)
        playtime_tracker[current_goalkeeper] += sub_time

        # Step 2: Prioritize players with less playtime for defense, midfield, and forward
        # Defense
        defense_needed = 2  # Ensure 2 defenders
        preferred_defenders = prioritize_by_playtime(active_players + substitute_players, 'defense', assigned_players)
        for player in preferred_defenders[:defense_needed]:
            if player['name'] not in assigned_players:
                segment_plan['positions']['defense'].append(player['name'])
                assigned_players.add(player['name'])
                playtime_tracker[player['name']] += sub_time

        # Midfield
        mid_needed = (num_players_on_field - 1 - len(segment_plan['positions']['defense'])) // 2
        preferred_midfielders = prioritize_by_playtime(active_players + substitute_players, 'mid', assigned_players)
        for player in preferred_midfielders[:mid_needed]:
            if player['name'] not in assigned_players:
                segment_plan['positions']['mid'].append(player['name'])
                assigned_players.add(player['name'])
                playtime_tracker[player['name']] += sub_time

        # Forward
        forward_needed = num_players_on_field - 1 - len(segment_plan['positions']['defense']) - len(segment_plan['positions']['mid'])
        preferred_forwards = prioritize_by_playtime(active_players + substitute_players, 'forward', assigned_players)
        for player in preferred_forwards[:forward_needed]:
            if player['name'] not in assigned_players:
                segment_plan['positions']['forward'].append(player['name'])
                assigned_players.add(player['name'])
                playtime_tracker[player['name']] += sub_time

        # Step 3: Handle substitutions
        players_not_assigned = [p for p in players_data if p['name'] not in assigned_players]
        
        # Ensure players not assigned are added to substitutes
        for player in players_not_assigned:
            if player['name'] not in assigned_players and player in active_players:
                active_players.remove(player)
                substitute_players.append(player)
            segment_plan['subs'].append(player['name'])
            substitution_tracker[player['name']] += 1

        # Add the segment plan to the overall game plan
        game_plan.append(segment_plan)

    return game_plan






# Route to display the form
@app.route('/')
def form():
    return render_template('form.html')

# Submit route
@app.route('/submit', methods=['POST'])
def submit():
    # Get form data
    minutes = int(request.form.get('minutes'))
    game_type = request.form.get('game_type')
    players = int(request.form.get('players'))

    # Get the minimum sub time, which could be blank
    min_sub_time_input = request.form.get('sub_time')

    # Calculate the actual substitution time using the new logic
    sub_time = calculate_sub_time(minutes, min_sub_time_input, players, num_goalkeepers=1)

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

