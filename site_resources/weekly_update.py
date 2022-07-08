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
    match_list.append({key:val for key, val in vars(match).items() if key not in ['home_team', 'away_team']})

match_df = pd.DataFrame(match_list)
match_df['week_num'] = match_df['date'].dt.isocalendar().week
match_df['month'] = match_df['date'].dt.month
match_df['year'] = match_df['date'].dt.year

## ~~~~~~~~~~~~~~~~~ RECENT MATCHES ~~~~~~~~~~~~~~~~~~~ ##


fut_dir_md = MdUtils(file_name=f'Current_Projections', title="Projections")
## Future Matches
future_games = match_df[match_df.point_diff.isna()]
for _, future_game in future_games.iterrows():
    pretty_name = f'{future_game["away_team_name"]} at {future_game["home_team_name"]}'
    file_name = f'{future_game["date"].date().strftime("%Y-%m-%d")}-{future_game["home_team_name"].replace(" ", "")}-{future_game["away_team_name"].replace(" ", "")}'
    main_header = f'{future_game["away_team_name"]} ({round(future_game["lineup_away_elo"], 2)}) at {future_game["home_team_name"]} ({round(future_game["lineup_home_elo"], 2)})'
    favorite = future_game["home_team_name"] if future_game["lineup_spread"] > 0 else future_game["away_team_name"]
    pred_text = f'Prediction: {favorite} by {round(abs(future_game["lineup_spread"]), 1)}'

    fut_match_md = MdUtils(file_name=f'_posts//projections//{file_name}', title=main_header)
    fut_match_md.new_header(level = 1, title = pred_text)
    fut_match_md.create_md_file()

    fut_dir_md.new_paragraph(f'[{pretty_name}](_posts//projections//{file_name})')

fut_dir_md.create_md_file()

