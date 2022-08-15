## IMPORTS
import sys
import yaml
with open('secrets.yml', 'r') as file:
    secrets = yaml.safe_load(file)
sys.path.append(secrets['elo_proj_path'])

from player_club_classes import team_elo, Player, Club, Match
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly
import pickle
from mdutils.mdutils import MdUtils
from mdutils import Html
from support_files.team_colors import team_color_dict
from tabulate import tabulate
import os
import glob
import datetime

## Need to ge the current home advantage? as 5 as of 8/5
home_advantage = 5

def percentile(group):
    sz = group.size-1
    ranks = group.rank(method='max')
    return 100.0*(ranks-1)/sz

def elo_contribition(player_df, column):
    mult = np.where(player_df.Number <= 15, (7/8), 0.234)
    return player_df[column] * mult

def projection_contribution_plot(df, path):
    pos_plotlist = []
    for _, row in df.iterrows():
        pos_plot = go.Bar(
            name=row.Number,
            x = ['Home Team', 'Away Team'],
            y = [row['home contributions'], row['away contributions']],
            customdata = [row['Home Player'], row['Away Player']],
            hovertemplate = 
                "<b>%{customdata}</b>: " + 
                "%{y}"
        )
        pos_plotlist.append(pos_plot)

    fig = go.Figure(data=pos_plotlist)
    fig.update_layout(barmode='stack')
    fig.write_html(path)

def review_contribution_plot(df, path):
    pos_plotlist = []
    for _, row in df.iterrows():
        pos_plot = go.Bar(
            name=row.Number,
            x = ['Home Projected', 'Home Actual', 'Away Projected', 'Away Actual'],
            y = [row['home contributions'], row['home minute_elos'], row['away contributions'], row['away minute_elos']],
            customdata = [row['Home Player'], row['Home Player'], row['Away Player'], row['Away Player']],
            hovertemplate = 
                "<b>%{customdata}</b>: " + 
                "%{y}"
        )
        pos_plotlist.append(pos_plot)

    fig = go.Figure(data=pos_plotlist)
    fig.update_layout(barmode='stack')
    fig.write_html(path)

files = glob.glob('projections/*')
for f in files:
    os.remove(f)

files = glob.glob('reviews/*')
for f in files:
    os.remove(f)

files = glob.glob('temp/*')
for f in files:
    os.remove(f)

team_colors = pd.DataFrame(team_color_dict).T
team_colors.columns = ['Primary', 'Secondary']
team_colors = team_colors.rename_axis('Team').reset_index()

from plotly.validators.scatter.marker import SymbolValidator
raw_symbols = SymbolValidator().values

simple_symbols = [i for i in raw_symbols if str(i).isalpha()]

with open('../Rugby_ELO/processed_data/playerbase.pickle', 'rb') as handle:
    playerbase = pickle.load(handle)
with open('../Rugby_ELO/processed_data/matchlist.pickle', 'rb') as handle:
    matchlist = pickle.load(handle)
with open('../Rugby_ELO/processed_data/teamlist.pickle', 'rb') as handle:
    teamlist = pickle.load(handle)


## LOAD DATA
match_list = []
for _, match in matchlist.items():
    match_list.append({key:val for key, val in vars(match).items()})

player_elo_list = []
for player_name, player in playerbase.items():
    player_elo = pd.DataFrame(player.elo_list, columns = [
        'Number', 'Full_Name', 'Team', 'Player', 'Position', 'Tries',
        'Try Assists', 'Conversion Goals', 'Penalty Goals',
        'Drop Goals Converted', 'Points', 'Passes', 'Runs', 'Meters Run',
        'Clean Breaks', 'Defenders Beaten', 'Offload', 'Turnovers Conceded',
        'Tackles', 'Missed Tackles', 'Lineouts Won', 'Penalties Conceded',
        'Yellow Cards', 'Red Cards', 'espn_id_num', 'Competition', 'Date',
        'Home Team', 'Home Score', 'Away Team', 'Away Score', 'Minutes',
        'Position_Number', 'gameid', 'Unicode_ID', 'comp_level', 'start_elo', 'end_elo'
       ])
    player_elo['Full Name'] = player_name[0]
    player_elo['Unicode_ID'] = player_name[1]
    player_elo_list.append(player_elo)

player_elo = pd.concat(player_elo_list).reset_index(drop=True)
player_elo = pd.merge(player_elo, team_colors, on = 'Team', how = 'left')
player_elo['elo_change'] = player_elo.end_elo - player_elo.start_elo
player_elo.Date = pd.to_datetime(player_elo.Date)
starters = player_elo[player_elo.Position != 'R']
starters = starters.dropna(subset=['Position'])
current_players = starters[starters.groupby(['Full Name'])['Date'].transform(max) == starters['Date']]

current_players['percentile'] = np.floor(current_players.groupby('Position')['end_elo'].apply(percentile))
current_players = current_players[['Full_Name', 'Unicode_ID', 'percentile']]

## ~~~~~~~~~~~~~~~~~ RECENT MATCHES ~~~~~~~~~~~~~~~~~~~ ##
rec_dir_md = MdUtils(file_name=f'Recent_Matches', title="Recent Matches")
recent_games = [x for x in match_list if datetime.datetime.now() > x['date'] > datetime.datetime.now() - datetime.timedelta(days=10)]
for recent_game in recent_games:
    home_team = pd.DataFrame(recent_game['home_team'][:, [0,1,31,-3,-1]], columns = ['Number', 'Full_Name', 'Minutes', 'Unicode_ID', 'elo'])
    home_team = home_team.merge(current_players, on=['Full_Name', 'Unicode_ID'])
    home_team = home_team.drop(['Unicode_ID'], axis = 1)
    away_team = pd.DataFrame(recent_game['away_team'][:, [0,1,31,-3,-1]], columns = ['Number', 'Full_Name', 'Minutes', 'Unicode_ID', 'elo'])
    away_team = away_team.merge(current_players, on=['Full_Name', 'Unicode_ID'])
    away_team = away_team.drop(['Unicode_ID'], axis = 1)

    home_team.columns = ['Number', 'Home Player', 'Home Minutes', 'Home elo', 'Home Percentile']
    away_team.columns = ['Number', 'Away Player', 'Away Minutes', 'Away elo', 'Away Percentile']

    all_players = pd.merge(home_team, away_team)
    all_players = all_players.sort_values('Number')
    all_players = all_players.apply(pd.to_numeric, errors='ignore').round({'Home elo':2, 'Away elo':2})
    all_players = all_players[['Away Minutes', 'Away Player', 'Away elo','Away Percentile', 'Number', 'Home Percentile', 'Home elo', 'Home Player', 'Home Minutes']]
    player_table = tabulate(all_players, tablefmt="pipe", headers="keys", showindex=False)

    pretty_name = f'{recent_game["away_team_name"]} at {recent_game["home_team_name"]}'
    file_name = f'{recent_game["date"].date().strftime("%Y-%m-%d")}-{recent_game["home_team_name"].replace(" ", "")}-{recent_game["away_team_name"].replace(" ", "")}'
    score_header = f'{recent_game["away_team_name"]} at {recent_game["home_team_name"]}; {recent_game["away_score"]}-{recent_game["home_score"]}'
    main_header = f'{recent_game["away_team_name"]} ({round(recent_game["away_elo"], 2)}) at {recent_game["home_team_name"]} ({round(recent_game["home_elo"], 2)})'
    rec_match_md = MdUtils(file_name=f'temp//{file_name}')

    # yaml header
    rec_match_md.new_line("HEADERSTART")
    rec_match_md.new_line("---")
    rec_match_md.new_line("layout: page")
    rec_match_md.new_line(f"title: {score_header}")
    rec_match_md.new_line(f"date: {recent_game['date']} 18:00:00 -0500")
    rec_match_md.new_line("categories: match review")
    rec_match_md.new_line("---")

    print(pretty_name)

    favorite = recent_game["home_team_name"] if recent_game["spread"] > 0 else recent_game["away_team_name"]
    pred_text = f'{favorite} by {round(abs(recent_game["spread"]), 1)}'

    lineup_favorite = recent_game["home_team_name"] if recent_game["lineup_spread"] + home_advantage > 0 else recent_game["away_team_name"]
    lineup_pred_text = f'{favorite} by {round(abs(recent_game["lineup_spread"] + home_advantage), 1)}'

    n_lineup_favorite = recent_game["home_team_name"] if recent_game["lineup_spread"] > 0 else recent_game["away_team_name"]
    n_lineup_pred_text = f'{n_lineup_favorite} by {round(abs(recent_game["lineup_spread"]), 1)} on a neutral pitch'

    favorite = recent_game["home_team_name"] if recent_game["spread"] + home_advantage > 0 else recent_game["away_team_name"]
    pred_text = f'{favorite} by {round(abs(recent_game["spread"] + home_advantage ), 1)}'

    n_favorite = recent_game["home_team_name"] if recent_game["spread"] > 0 else recent_game["away_team_name"]
    n_pred_text = f'{n_favorite} by {round(abs(recent_game["spread"]), 1)} on a neutral field'

    rec_match_md.new_header(level = 1, title = f'Prediction: {pred_text}')
    rec_match_md.new_paragraph(n_pred_text)

    rec_match_md.new_header(level = 1, title = f'Pre-Match Prediction: {lineup_pred_text}')
    rec_match_md.new_paragraph(n_lineup_pred_text)
    rec_match_md.new_header(level = 1, title = f'Projection using minutes played for each player: {pred_text}')
    rec_match_md.new_paragraph(n_pred_text)
    rec_match_md.new_paragraph()
    rec_match_md.new_paragraph(player_table)
    rec_match_md.new_paragraph()

    #rec_match_md.new_header(level = 1, title = 'Elo Contributions')

    all_players['home contributions'] = elo_contribition(all_players, 'Home elo')
    all_players['away contributions'] = elo_contribition(all_players, 'Away elo')
    all_players['home minute_elos'] = all_players['Home elo'] * all_players['Home Minutes'] / max(all_players['Home Minutes'])
    all_players['away minute_elos'] = all_players['Away elo'] * all_players['Away Minutes'] / max(all_players['Home Minutes'])
    #review_contribution_plot(all_players, f"reviews//{file_name}_contributions.html")
    #rec_match_md.new_paragraph(f"{{% include_relative {file_name}_contributions.html %}}")

    rec_match_md.create_md_file()

    rec_dir_md.new_paragraph(f'[{score_header}](reviews//{file_name})')

    ## quick and dirty remove empty leading lines
    TAG = 'HEADERSTART'
    tag_found = False
    with open(f'temp//{file_name}.md') as in_file:
        with open(f'reviews//{file_name}.md', 'w') as out_file:
            for line in in_file:
                if not tag_found:
                    if line.strip() == TAG:
                        tag_found = True
                else:
                    out_file.write(line)

rec_dir_md.create_md_file()

## ~~~~~~~~~~~~~~~~~ FUTURE MATCHES ~~~~~~~~~~~~~~~~~~~ ##
fut_dir_md = MdUtils(file_name=f'Current_Projections', title="Projections")
future_games =[x for x in match_list if 'point_diff' not in x.keys()]
for future_game in future_games:

    home_team = pd.DataFrame(future_game['home_team'][:, [0,1,-3, -1]], columns = ['Number', 'Full_Name', 'Unicode_ID', 'elo'])
    home_team = home_team.merge(current_players, on=['Full_Name', 'Unicode_ID'])
    home_team = home_team.drop(['Unicode_ID'], axis = 1)
    away_team = pd.DataFrame(future_game['away_team'][:, [0,1,-3, -1]], columns = ['Number', 'Full_Name', 'Unicode_ID', 'elo'])
    away_team = away_team.merge(current_players, on=['Full_Name', 'Unicode_ID'])
    away_team = away_team.drop(['Unicode_ID'], axis = 1)

    home_team.columns = ['Number', 'Home Player', 'Home elo', 'Home Percentile']
    away_team.columns = ['Number', 'Away Player', 'Away elo', 'Away Percentile']

    all_players = pd.merge(home_team, away_team)
    all_players = all_players.sort_values('Number')
    all_players = all_players.apply(pd.to_numeric, errors='ignore').round({'Home elo':2, 'Away elo':2})
    all_players = all_players[['Away Player', 'Away elo','Away Percentile', 'Number', 'Home Percentile', 'Home elo', 'Home Player']]
    player_table = tabulate(all_players, tablefmt="pipe", headers="keys", showindex=False)

    pretty_name = f'{future_game["away_team_name"]} at {future_game["home_team_name"]}'
    file_name = f'{future_game["date"].date().strftime("%Y-%m-%d")}-{future_game["home_team_name"].replace(" ", "")}-{future_game["away_team_name"].replace(" ", "")}'
    main_header = f'{future_game["away_team_name"]} ({round(future_game["lineup_away_elo"], 2)}) at {future_game["home_team_name"]} ({round(future_game["lineup_home_elo"], 2)})'
    fut_match_md = MdUtils(file_name=f'temp//{file_name}', title=main_header)

    # yaml header
    rec_match_md.new_line("HEADERSTART")
    fut_match_md.new_paragraph("---")
    fut_match_md.new_paragraph("layout: page")
    fut_match_md.new_paragraph(f"title: {pretty_name}")
    fut_match_md.new_paragraph(f"date: {x['date']} 18:00:00 -0500")
    fut_match_md.new_paragraph("categories: match prediction")
    fut_match_md.new_paragraph("---")

    print(pretty_name)

    favorite = future_game["home_team_name"] if future_game["lineup_spread"] + home_advantage > 0 else future_game["away_team_name"]
    pred_text = f'{favorite} by {round(abs(future_game["lineup_spread"] + home_advantage), 1)}'

    n_favorite = future_game["home_team_name"] if future_game["lineup_spread"] > 0 else future_game["away_team_name"]
    n_pred_text = f'{n_favorite} by {round(abs(future_game["lineup_spread"]), 1)} on a neutral pitch'

    fut_match_md.new_header(level = 1, title = f'Prediction: {pred_text}')
    fut_match_md.new_paragraph(n_pred_text)
    fut_match_md.new_paragraph(player_table)
    fut_match_md.new_paragraph()

    #fut_match_md.new_header(level = 1, title = 'Elo Contributions')

    all_players['home contributions'] = elo_contribition(all_players, 'Home elo')
    all_players['away contributions'] = elo_contribition(all_players, 'Away elo')
    #projection_contribution_plot(all_players, f"projections//{file_name}_contributions.html")
    #fut_match_md.new_paragraph(f"{{% include_relative {file_name}_contributions.html %}}")

    fut_match_md.create_md_file()

    fut_dir_md.new_paragraph(f'[{pretty_name}; {pred_text}](projections//{file_name})')

        ## quick and dirty remove empty leading lines
    TAG = 'HEADERSTART'
    tag_found = False
    with open(f'temp//{file_name}.md') as in_file:
        with open(f'projections//{file_name}.md', 'w') as out_file:
            for line in in_file:
                if not tag_found:
                    if line.strip() == TAG:
                        tag_found = True
                else:
                    out_file.write(line)

fut_dir_md.create_md_file()

