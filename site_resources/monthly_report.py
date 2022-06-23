## DATA LOAD
import sys
import yaml
with open('secrets.yml', 'r') as file:
    secrets = yaml.safe_load(file)
sys.path.append(secrets['elo_proj_path'])

from player_club_classes import team_elo, Player, Club, Match
from player_club_classes import GLOBAL_home_advantage, GLOBAL_score_factor, GLOBAL_k, GLOBAL_mov_score_add, GLOBAL_mov_score_mult, GLOBAL_mov_elo_mult, GLOBAL_mov_elo_add
import pandas as pd
import numpy as np
import pickle
from tabulate import tabulate

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

match_list = []
for _, match in matchlist.items():
    match_list.append({key:val for key, val in vars(match).items() if key not in ['home_team', 'away_team']})

match_df = pd.DataFrame(match_list)
match_df['week_num'] = match_df['date'].dt.isocalendar().week
match_df['month'] = match_df['date'].dt.month
match_df['year'] = match_df['date'].dt.year

player_elo_list = []
for player_name, player in playerbase.items():
    player_elo = player.elo_df
    player_elo['Full Name'] = player_name[0]
    player_elo['Unicode_ID'] = player_name[1]
    player_elo_list.append(player_elo)

player_elo = pd.concat(player_elo_list).reset_index(drop=True)
player_elo = pd.merge(player_elo, team_colors, on = 'Team', how = 'left')
player_elo['elo_change'] = player_elo.end_elo - player_elo.start_elo
player_elo['week_num'] = player_elo['Date'].dt.isocalendar().week
player_elo['month'] = player_elo['Date'].dt.month
player_elo['year'] = player_elo['Date'].dt.year


## REPORT DATA PREP
month = match_df[(match_df.year == 2022) & (match_df.month == 5)]
closest_games = month.sort_values('lineup_spread',  key=abs).head()
one_side_games = month.sort_values('lineup_spread',  key=abs, ascending=False).head()
closest_games = closest_games[['name', 'lineup_spread', 'spread', 'point_diff', 'home_score', 'away_score']].head()
one_side_games = one_side_games[['name', 'lineup_spread', 'spread', 'point_diff', 'home_score', 'away_score']].tail()
closest_games = closest_games.set_index('name')
one_side_games = one_side_games.set_index('name')


sorted_pred_accuracy = month.assign(tmp=month["point_diff"] - month["lineup_spread"]).sort_values(by="tmp", key=abs)#.drop(columns="tmp")
best_preds = sorted_pred_accuracy[['name', 'lineup_spread', 'spread', 'point_diff', 'home_score', 'away_score']].head()
worst_preds = sorted_pred_accuracy[['name', 'lineup_spread', 'spread', 'point_diff', 'home_score', 'away_score']].tail()
best_preds = best_preds.set_index('name')
worst_preds = worst_preds.set_index('name')

biggest_upsets = month[(month.lineup_spread * month.point_diff) < 0].assign(tmp=month["point_diff"] - month["lineup_spread"]).sort_values(by="tmp", key=abs, ascending=False).drop(columns="tmp").head()
biggest_covers = month[((month.lineup_spread * month.point_diff) > 0)].assign(tmp=month["point_diff"] - month["lineup_spread"]).sort_values(by="tmp", key=abs, ascending=False).drop(columns="tmp").head()
biggest_upsets = biggest_upsets[['name', 'lineup_spread', 'spread', 'point_diff', 'home_score', 'away_score']]
biggest_covers = biggest_covers[['name', 'lineup_spread', 'spread', 'point_diff', 'home_score', 'away_score']]
biggest_upsets = biggest_upsets.set_index('name')
biggest_covers = biggest_covers.set_index('name')

def elo_change(df):
    return df.iloc[-1].end_elo, df.iloc[0].start_elo, df.iloc[-1].end_elo - df.iloc[0].start_elo

player_month = player_elo[(player_elo.year == 2022) & (player_elo.month == 5)]
elo_changes = player_month.sort_values('Date').groupby(['Unicode_ID', 'Full Name', 'Team']).apply(elo_change).reset_index()
elo_changes[['end_elo', 'start_elo', 'elo_change']] = pd.DataFrame(elo_changes[0].tolist(), index=elo_changes.index)

## REPORT GENERATION
from mdutils.mdutils import MdUtils
from mdutils import Html

mdFile = MdUtils(file_name='_posts//2022-05-01-Report', title='Monthly Report - May 2022')

## ************ Summary Paragraph ************* ##
mdFile.new_header(level=1, title='Summary')  # style is set 'atx' format by default.

game_count_sentence = f"We had {month.shape[0]} rugby matches in May of 2022"
if month.shape[0] == 0:
    mdFile.new_paragraph(game_count_sentence + ". Check back next month.")
    mdFile.new_table_of_contents(table_title='Contents', depth=2)
    mdFile.create_md_file()
    quit()

comp_distribution = month.competition.value_counts().to_dict()
[str(x) + ' matches in ' + str(key) for key, x in comp_distribution.items()]
comp_breakdown = f''

mdFile.new_paragraph(f"We had {month.shape[0]} rugby matches in May of 2022.")
mdFile.new_paragraph()
## ************ Prediction Accuracy ************* ##
mdFile.new_header(level = 1, title = "Prediction Accuracy")

mdFile.new_header(level = 2, title = 'Best Predictions')
best_preds_md = tabulate(best_preds, tablefmt="pipe", headers="keys")
mdFile.new_paragraph(best_preds_md)
mdFile.new_paragraph()


mdFile.new_header(level = 2, title = 'Worst Predictions')
worst_preds_md = tabulate(worst_preds, tablefmt="pipe", headers="keys")
mdFile.new_paragraph(worst_preds_md)
mdFile.new_paragraph()

## ************ Prediction Accuracy ************* ##
mdFile.new_header(level = 1, title = "Games to Watch, Snoozes to Miss, Upsets, and Covers")

mdFile.new_header(level = 2, title = 'Closest Projections')
closest_games_md = tabulate(closest_games, tablefmt="pipe", headers="keys")
mdFile.new_paragraph(closest_games_md)
mdFile.new_paragraph()

mdFile.new_header(level = 2, title = 'Most One-Sided Projections')
one_side_games_md = tabulate(one_side_games, tablefmt="pipe", headers="keys")
mdFile.new_paragraph(one_side_games_md)
mdFile.new_paragraph()

mdFile.new_header(level = 2, title = 'Biggest Upsets')
biggest_upsets_md = tabulate(biggest_upsets, tablefmt="pipe", headers="keys")
mdFile.new_paragraph(biggest_upsets_md)
mdFile.new_paragraph()

mdFile.new_header(level = 2, title = 'Best Covers')
biggest_covers_md = tabulate(biggest_covers, tablefmt="pipe", headers="keys")
mdFile.new_paragraph(biggest_covers_md)
mdFile.new_paragraph()

mdFile.new_table_of_contents(table_title='Contents', depth=2)
mdFile.create_md_file()

'''
We had \a\ rugby matches in \current month\ of \current year\: \26\ matches 
in \Super Rugby Pacific\, .... and \7\ matches in the Gallagher Premiership.


Most Accurate Predictions
Worst Predictions

Projected Close Games
Projected Snoozes
Biggest Upsets
Best Covers

Biggest Risers
Biggest Fallers

Current Best
'''