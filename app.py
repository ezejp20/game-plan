from flask import Flask, render_template, request
import random

app = Flask(__name__)

# Function to calculate substitution time
def calculate_sub_time(minutes, min_sub_time_input, num_players, num_goalkeepers):
    outfield_players = num_players - num_goalkeepers
    if not min_sub_time_input:
        # Calculate a balanced sub time close to dividing playtime evenly among outfield players
        ideal_sub_time = round(minutes / outfield_players, 1)  # Allow half-minute precision
        return ideal_sub_time

    min_sub_time = int(min_sub_time_input)
    ideal_sub_time = minutes // outfield_players

    # Return the greater of the user input and calculated ideal sub time
    return max(min_sub_time, ideal_sub_time)

# Helper function to conditionally format time
def format_time(time_value):
    return f"{time_value:.1f}".rstrip('0').rstrip('.')  # Remove trailing zeros and decimal point if whole

# Game plan generation function with goalie rotation
def generate_game_plan(minutes, sub_time, game_type, players_data):
    # Determine number of players on the field based on game type
    if game_type == "5_a_side":
        num_players_on_field = 5
    elif game_type == "6_a_side":
        num_players_on_field = 6
    elif game_type == "7_a_side":
        num_players_on_field = 7
    elif game_type == "11_a_side":
        num_players_on_field = 11

    # Calculate number of segments based on game duration and substitution time
    num_segments = int(minutes / sub_time)  # Convert to integer for use in loop
    segment_duration = minutes / num_segments
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
            dedicated_goalkeeper = player['name']
            break
        elif 'goal' in player['positions']:
            flexible_goalkeepers.append(player)
        else:
            non_goalkeepers.append(player)

    def prioritize_by_playtime(players, position, assigned_players):
        return sorted(
            [player for player in players if position in player['positions'] and player['name'] not in assigned_players],
            key=lambda p: (playtime_tracker[p['name']], len(p['positions']))
        )

    flexible_goalkeeper_index = 0

    for segment in range(num_segments):
        segment_start_time = format_time(segment * segment_duration)
        segment_end_time = format_time((segment + 1) * segment_duration)
        segment_plan = {
            'time': f'{segment_start_time} - {segment_end_time} mins',
            'positions': {
                'goal': None,
                'defense': [],
                'mid': [],
                'forward': []
            },
            'subs': []
        }

        assigned_players = set()
        remaining_field_slots = num_players_on_field

        # Step 1: Assign the goalkeeper
        if dedicated_goalkeeper:
            segment_plan['positions']['goal'] = dedicated_goalkeeper
            assigned_players.add(dedicated_goalkeeper)
            goal_time_tracker[dedicated_goalkeeper] += 1
            remaining_field_slots -= 1
        elif flexible_goalkeepers:
            current_goalkeeper = flexible_goalkeepers[flexible_goalkeeper_index % len(flexible_goalkeepers)]['name']
            segment_plan['positions']['goal'] = current_goalkeeper
            assigned_players.add(current_goalkeeper)
            goal_time_tracker[current_goalkeeper] += 1
            flexible_goalkeeper_index += 1
            remaining_field_slots -= 1

        # Step 2: Assign players to other positions based on playtime, ensuring fair rotation
        for position in ["defense", "mid", "forward"]:
            # Determine required players for each position
            if position == "defense":
                needed = 1  # Allow flexibility here for single-player defense
            elif position == "mid":
                needed = (num_players_on_field - 1 - len(segment_plan['positions']['defense'])) // 2
            else:  # position == "forward"
                needed = num_players_on_field - 1 - len(segment_plan['positions']['defense']) - len(segment_plan['positions']['mid'])

            # Prioritize players with less playtime for each position
            preferred_players = prioritize_by_playtime(players_data, position, assigned_players)
            for player in preferred_players[:needed]:
                segment_plan['positions'][position].append(player['name'])
                assigned_players.add(player['name'])
                playtime_tracker[player['name']] += sub_time
                remaining_field_slots -= 1

        # NEW STEP: If any slots remain, rotate other players into available positions based on playtime
        if remaining_field_slots > 0:
            remaining_players = [p for p in players_data if p['name'] not in assigned_players]
            prioritized_remaining_players = sorted(remaining_players, key=lambda p: playtime_tracker[p['name']])

            for player in prioritized_remaining_players:
                if remaining_field_slots == 0:
                    break
                if 'defense' in player['positions'] and len(segment_plan['positions']['defense']) < 2:
                    segment_plan['positions']['defense'].append(player['name'])
                elif 'mid' in player['positions'] and len(segment_plan['positions']['mid']) < 3:
                    segment_plan['positions']['mid'].append(player['name'])
                elif 'forward' in player['positions'] and len(segment_plan['positions']['forward']) < 2:
                    segment_plan['positions']['forward'].append(player['name'])
                assigned_players.add(player['name'])
                playtime_tracker[player['name']] += sub_time
                remaining_field_slots -= 1

        # Step 4: Assign remaining players as substitutes if no field slots are left
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
            'mins_off': substitution_tracker[player['name']] * sub_time,
            'mins_subbed_goal': (substitution_tracker[player['name']] + goal_time_tracker[player['name']]) * sub_time
        } for player in players_data
    }

    return game_plan, summary

# Route to display the initial form
@app.route('/')
def form():
    return render_template('form.html')

# Route to submit the form and display the game plan
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

# Route to update the game plan after editing
@app.route('/update_game_plan', methods=['POST'])
def update_game_plan():
    # Extract the updated team sheet data from the form
    updated_data = request.form.to_dict()
    
    # Reconstruct `game_plan` based on the updated data
    # Parse the data to update players' names and positions based on `updated_data`
    # This could include parsing position changes and assigning them back to the `game_plan`

    # You may need to re-process or recalculate parts of the game plan based on the changes.
    
    # After updating, render the updated game plan
    return render_template('game_plan.html', game_plan=game_plan, summary=summary, sub_time=sub_time)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)











