from flask import Flask, render_template, request
import random

app = Flask(__name__)

# Game plan generation function
def generate_game_plan(minutes, sub_time, game_type, players_data):
    # Determine the number of players on the field based on the game type
    if game_type == "5_a_side":
        num_players_on_field = 5
    elif game_type == "7_a_side":
        num_players_on_field = 7
    elif game_type == "11_a_side":
        num_players_on_field = 11

    # Calculate the number of segments based on game duration and substitution time
    num_segments = minutes // sub_time

    # Track playtime and substitutions for all players
    playtime_tracker = {player['name']: 0 for player in players_data}
    substitution_tracker = {player['name']: 0 for player in players_data}

    # Initialize the game plan for each segment
    game_plan = []

    # Split players into active and substitutes at the start
    active_players = players_data[:num_players_on_field]  # Players on the field
    substitute_players = players_data[num_players_on_field:]  # Players who start as substitutes

    permanent_goalkeeper = None  # Store the permanent goalkeeper

    # Function to prioritize players with fewer preferred positions
    def prioritize_by_preference_count(players, position):
        return sorted(
            [player for player in players if position in player['positions']],
            key=lambda p: len(p['positions'])
        )

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

        # Step 1: Assign the goalkeeper (fixed)
        if permanent_goalkeeper is None:
            # Assign the first available player with "goal" preference as the permanent goalkeeper
            for player in active_players:
                if 'goal' in player['positions']:
                    permanent_goalkeeper = player['name']
                    break
            if permanent_goalkeeper is None:  # If no preference, assign the first available player
                permanent_goalkeeper = active_players[0]['name']

        segment_plan['positions']['goal'] = permanent_goalkeeper
        assigned_players = {permanent_goalkeeper}
        playtime_tracker[permanent_goalkeeper] += sub_time

        # Step 2: Prioritize players with 1 preference for defense, midfield, and forward
        # Defense
        defense_needed = 2  # Ensure 2 defenders
        preferred_defenders = prioritize_by_preference_count(active_players, 'defense')
        for player in preferred_defenders[:defense_needed]:
            if player['name'] not in assigned_players:
                segment_plan['positions']['defense'].append(player['name'])
                assigned_players.add(player['name'])
                playtime_tracker[player['name']] += sub_time

        # Midfield
        mid_needed = (num_players_on_field - 1 - len(segment_plan['positions']['defense'])) // 2
        preferred_midfielders = prioritize_by_preference_count(active_players, 'mid')
        for player in preferred_midfielders[:mid_needed]:
            if player['name'] not in assigned_players:
                segment_plan['positions']['mid'].append(player['name'])
                assigned_players.add(player['name'])
                playtime_tracker[player['name']] += sub_time

        # Forward
        forward_needed = num_players_on_field - 1 - len(segment_plan['positions']['defense']) - len(segment_plan['positions']['mid'])
        preferred_forwards = prioritize_by_preference_count(active_players, 'forward')
        for player in preferred_forwards[:forward_needed]:
            if player['name'] not in assigned_players:
                segment_plan['positions']['forward'].append(player['name'])
                assigned_players.add(player['name'])
                playtime_tracker[player['name']] += sub_time

        # Step 3: Fill remaining positions with players who have multiple preferences
        unassigned_players = [p for p in active_players if p['name'] not in assigned_players]

        # Fill remaining defense positions
        defense_needed = 2 - len(segment_plan['positions']['defense'])
        if defense_needed > 0:
            for player in unassigned_players:
                if defense_needed > 0:
                    segment_plan['positions']['defense'].append(player['name'])
                    assigned_players.add(player['name'])
                    playtime_tracker[player['name']] += sub_time
                    defense_needed -= 1

        # Fill remaining midfield positions
        mid_needed = (num_players_on_field - 1 - len(segment_plan['positions']['defense'])) // 2 - len(segment_plan['positions']['mid'])
        if mid_needed > 0:
            for player in unassigned_players:
                if mid_needed > 0:
                    segment_plan['positions']['mid'].append(player['name'])
                    assigned_players.add(player['name'])
                    playtime_tracker[player['name']] += sub_time
                    mid_needed -= 1

        # Fill remaining forward positions
        forward_needed = (num_players_on_field - 1) - len(segment_plan['positions']['defense']) - len(segment_plan['positions']['mid']) - len(segment_plan['positions']['forward'])
        if forward_needed > 0:
            for player in unassigned_players:
                if forward_needed > 0:
                    segment_plan['positions']['forward'].append(player['name'])
                    assigned_players.add(player['name'])
                    playtime_tracker[player['name']] += sub_time
                    forward_needed -= 1

        # Step 4: Add substitutes for the segment
        for player in substitute_players:
            if player['name'] != permanent_goalkeeper:  # Skip the goalkeeper for substitutions
                segment_plan['subs'].append(player['name'])
                substitution_tracker[player['name']] += 1

        # Step 5: Rotate players for the next segment (goalkeeper stays fixed)
        swap_count = min(len(substitute_players), len(active_players) - 1)  # Don't swap the goalkeeper
        if swap_count > 0:
            active_players_except_goalkeeper = [p for p in active_players if p['name'] != permanent_goalkeeper]
            active_players, substitute_players = (
                active_players_except_goalkeeper[swap_count:] + substitute_players[:swap_count] + [p for p in active_players if p['name'] == permanent_goalkeeper],
                substitute_players[swap_count:] + active_players_except_goalkeeper[:swap_count],
            )

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

