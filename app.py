from flask import Flask, render_template, request
import random

app = Flask(__name__)

# Function to calculate substitution time
def calculate_sub_time(minutes, min_sub_time_input, num_players, num_goalkeepers):
    outfield_players = num_players - num_goalkeepers
    if not min_sub_time_input:
        # Calculate an optimal substitution time
        possible_segment_lengths = [i for i in range(1, minutes + 1) if minutes % i == 0]
        # Find the longest segment length that results in a reasonable number of rotations
        ideal_sub_time = max(possible_segment_lengths, key=lambda x: minutes // x if minutes // x <= outfield_players else 0)
        return ideal_sub_time

    min_sub_time = int(min_sub_time_input)
    ideal_sub_time = minutes // outfield_players

    # Return the greater of the user input and calculated ideal sub time
    return max(min_sub_time, ideal_sub_time)

# Game plan generation function with goalie rotation
def generate_game_plan(minutes, sub_time, game_type, players_data):
    # Determine number of players on the field based on game type
    if game_type == "5_a_side":
        num_players_on_field = 5
    elif game_type == "7_a_side":
        num_players_on_field = 7
    elif game_type == "11_a_side":
        num_players_on_field = 11

    # Calculate number of segments based on game duration and substitution time
    num_segments = minutes // sub_time
    playtime_tracker = {player['name']: 0 for player in players_data}
    substitution_tracker = {player['name']: 0 for player in players_data}
    goal_time_tracker = {player['name']: 0 for player in players_data}

    game_plan = []

    # Identify the dedicated goalkeeper and any flexible goalkeepers
    dedicated_goalkeeper = None
    flexible_goalkeepers = []
    non_goalkeepers = []

    for player in players_data:
        if 'goal' in player['positions'] and len(player['positions']) == 1:
            # Player only wants to play as goalkeeper
            dedicated_goalkeeper = player['name']
            break
        elif 'goal' in player['positions']:
            # Player can play as goalkeeper and other positions
            flexible_goalkeepers.append(player)
        else:
            # Player cannot play as goalkeeper
            non_goalkeepers.append(player)

    # Function to prioritize players with less playtime
    def prioritize_by_playtime(players, position, assigned_players):
        return sorted(
            [player for player in players if position in player['positions'] and player['name'] not in assigned_players],
            key=lambda p: (playtime_tracker[p['name']], len(p['positions']))
        )

    flexible_goalkeeper_index = 0

    for segment in range(num_segments):
        segment_end_time = (segment + 1) * sub_time
        segment_plan = {
            'time': f'{segment * sub_time} - {segment_end_time} mins',
            'positions': {
                'goal': None,
                'defense': [],
                'mid': [],
                'forward': []
            },
            'subs': []
        }

        assigned_players = set()

        # Step 1: Assign the goalkeeper
        if dedicated_goalkeeper:
            # Use the dedicated goalkeeper for the entire game
            segment_plan['positions']['goal'] = dedicated_goalkeeper
            assigned_players.add(dedicated_goalkeeper)
            playtime_tracker[dedicated_goalkeeper] += sub_time
            goal_time_tracker[dedicated_goalkeeper] += 1
        elif flexible_goalkeepers:
            # Rotate flexible goalkeepers if there is no dedicated one
            current_goalkeeper = flexible_goalkeepers[flexible_goalkeeper_index % len(flexible_goalkeepers)]['name']
            segment_plan['positions']['goal'] = current_goalkeeper
            assigned_players.add(current_goalkeeper)
            playtime_tracker[current_goalkeeper] += sub_time
            goal_time_tracker[current_goalkeeper] += 1
            flexible_goalkeeper_index += 1

        # Step 2: Prioritize players for defense, midfield, and forward based on playtime
        # Defense
        defense_needed = 2
        preferred_defenders = prioritize_by_playtime(players_data, 'defense', assigned_players)
        for player in preferred_defenders[:defense_needed]:
            if player['name'] not in assigned_players:
                segment_plan['positions']['defense'].append(player['name'])
                assigned_players.add(player['name'])
                playtime_tracker[player['name']] += sub_time

        # Midfield
        mid_needed = (num_players_on_field - 1 - len(segment_plan['positions']['defense'])) // 2
        preferred_midfielders = prioritize_by_playtime(players_data, 'mid', assigned_players)
        for player in preferred_midfielders[:mid_needed]:
            if player['name'] not in assigned_players:
                segment_plan['positions']['mid'].append(player['name'])
                assigned_players.add(player['name'])
                playtime_tracker[player['name']] += sub_time

        # Forward
        forward_needed = num_players_on_field - 1 - len(segment_plan['positions']['defense']) - len(segment_plan['positions']['mid'])
        preferred_forwards = prioritize_by_playtime(players_data, 'forward', assigned_players)
        for player in preferred_forwards[:forward_needed]:
            if player['name'] not in assigned_players:
                segment_plan['positions']['forward'].append(player['name'])
                assigned_players.add(player['name'])
                playtime_tracker[player['name']] += sub_time

        # Step 3: Assign remaining players to substitutes
        players_not_assigned = [p for p in players_data if p['name'] not in assigned_players]
        for player in players_not_assigned:
            segment_plan['subs'].append(player['name'])
            substitution_tracker[player['name']] += 1

        game_plan.append(segment_plan)

    # Generate summary of time spent in goal, on field, and as substitutes
        summary = {
        player['name']: {
            'goal_segments': goal_time_tracker[player['name']],
            'sub_segments': substitution_tracker[player['name']],
            'field_segments': num_segments - substitution_tracker[player['name']] - goal_time_tracker[player['name']],
            'mins_subbed': substitution_tracker[player['name']] * sub_time,
            'mins_subbed_goal': (substitution_tracker[player['name']] + goal_time_tracker[player['name']]) * sub_time
        } for player in players_data
    }

    return game_plan, summary











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
    sub_time = calculate_sub_time(minutes, min_sub_time_input, players, num_goalkeepers=1)

    # Process player data with defaults
    player_data = []
    for i in range(1, players + 1):
        name = request.form.get(f'player_name_{i}') or f'Player {i}'
        positions = request.form.getlist(f'positions_{i}')
        if not positions:
            positions = ['defense', 'mid', 'forward', 'goal']
        player_data.append({'name': name, 'positions': positions})

    # Generate game plan and summary
    game_plan, summary = generate_game_plan(minutes, sub_time, game_type, player_data)

    # Pass game_plan, summary, and sub_time to the template
    return render_template('game_plan.html', game_plan=game_plan, summary=summary, sub_time=sub_time)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

