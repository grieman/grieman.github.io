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
import pickle
from mdutils.mdutils import MdUtils
from mdutils import Html
from team_colors import team_color_dict
from tabulate import tabulate

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

## ~~~~~~~~~~~~~~~~~ RECENT MATCHES ~~~~~~~~~~~~~~~~~~~ ##


fut_dir_md = MdUtils(file_name=f'Current_Projections', title="Projections")
## Future Matches
future_games =[x for x in match_list if 'point_diff' not in x.keys()]
for future_game in future_games:

    home_team = pd.DataFrame(future_game['home_team'][:, [0,1, -1]], columns = ['Number', 'Name', 'elo'])
    away_team = pd.DataFrame(future_game['away_team'][:, [0,1, -1]], columns = ['Number', 'Name', 'elo'])
    home_team = home_team.sort_values('Number')
    away_team = away_team.sort_values('Number')
    home_table = tabulate(home_team, tablefmt="pipe", headers="keys", showindex=False)
    away_table = tabulate(away_team, tablefmt="pipe", headers="keys", showindex=False)
    double_table = f'<table><tr><th>Home Team </th><th>Away Team</th></tr><tr><td>\n\n{home_table}\n\n</td><td>\n\n{away_table}\n\n</td></tr> </table>'

    pretty_name = f'{future_game["away_team_name"]} at {future_game["home_team_name"]}'
    file_name = f'{future_game["date"].date().strftime("%Y-%m-%d")}-{future_game["home_team_name"].replace(" ", "")}-{future_game["away_team_name"].replace(" ", "")}'
    main_header = f'{future_game["away_team_name"]} ({round(future_game["lineup_away_elo"], 2)}) at {future_game["home_team_name"]} ({round(future_game["lineup_home_elo"], 2)})'
    fut_match_md = MdUtils(file_name=f'projections//{file_name}', title=main_header)

    favorite = future_game["home_team_name"] if future_game["lineup_spread"] > 0 else future_game["away_team_name"]
    pred_text = f'{favorite} by {round(abs(future_game["lineup_spread"]), 1)}'

    fut_match_md.new_header(level = 1, title = f'Prediction: {pred_text}')
    fut_match_md.new_paragraph(double_table)
    fut_match_md.create_md_file()

    fut_dir_md.new_paragraph(f'[{pretty_name}; {pred_text}](projections//{file_name})')

fut_dir_md.create_md_file()

