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
import support_files.real_time_preds as real_time_preds
from tabulate import tabulate
import os
import glob
import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from plot_functions import *


## Need to ge the current home advantage? as 5 as of 8/5
home_advantage = 5

def percentile(group):
    sz = group.size-1
    ranks = group.rank(method='max')
    return 100.0*(ranks-1)/sz

def make_current_percentile(starters, match_date):
    current_players = starters[starters.Date < match_date]
    current_players = current_players[current_players.Date >= match_date - datetime.timedelta(days=365)]
    current_players = current_players[current_players.groupby(['Full Name'])['Date'].transform(max) == current_players['Date']].copy()
    current_players['percentile'] = np.floor(current_players.groupby('Position')['end_elo'].apply(percentile))
    current_players = current_players[['Full_Name', 'Unicode_ID', 'percentile']]
    return current_players

def elo_contribition(player_df, column):
    mult = np.where(player_df.Number <= 15, (7/8), 0.234)
    return player_df[column] * mult

def clean_leading_space(orig_name, new_name):
    ## quick and dirty remove empty leading lines
    TAG = 'HEADERSTART'
    tag_found = False
    with open(orig_name) as in_file:
        with open(new_name, 'w') as out_file:
            for line in in_file:
                if not tag_found:
                    if line.strip() == TAG:
                        tag_found = True
                else:
                    out_file.write(line)

files = glob.glob('projections/*') + glob.glob('reviews/*') + glob.glob('_includes/plots/recap_predictions/*')
for f in files:
    os.remove(f)

'''files = glob.glob('reviews/*')
for f in files:
    os.remove(f)'''


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

'''current_players = starters[starters.groupby(['Full Name'])['Date'].transform(max) == starters['Date']].copy()
current_players['percentile'] = np.floor(current_players.groupby('Position')['end_elo'].apply(percentile))
current_players = current_players[['Full_Name', 'Unicode_ID', 'percentile']]'''

## ~~~~~~~~~~~~~~~~~ RECENT MATCHES ~~~~~~~~~~~~~~~~~~~ ##
rec_dir_md = MdUtils(file_name=f'temp//Recent_Matches')
rec_dir_md.new_line("HEADERSTART")
rec_dir_md.new_line("---")
rec_dir_md.new_line("layout: article")
rec_dir_md.new_line(f"title: Recent Matches")
rec_dir_md.new_line("key: page-recents")
rec_dir_md.new_line("---")

match_dir_strings = []
match_comps = []
match_levels = []

recent_games = [x for x in match_list if datetime.datetime.now() > x['date'] > datetime.datetime.now() - datetime.timedelta(days=60)]
for recent_game in recent_games:
    
    current_players = make_current_percentile(starters, recent_game['date'])
    pretty_name = f'{recent_game["away_team_name"]} at {recent_game["home_team_name"]}'
    file_name = f'{recent_game["date"].date().strftime("%Y-%m-%d")}-{recent_game["home_team_name"].replace(" ", "")}-{recent_game["away_team_name"].replace(" ", "")}'
    score_header = f'{recent_game["away_team_name"]} at {recent_game["home_team_name"]}; {recent_game["away_score"]}-{recent_game["home_score"]}'
    main_header = f'{recent_game["away_team_name"]} ({round(recent_game["away_elo"], 2)}) at {recent_game["home_team_name"]} ({round(recent_game["home_elo"], 2)})'
    print(pretty_name)

    # team colors
    home_color1 = team_colors[team_colors.Team == recent_game["home_team_name"]].Primary.iloc[0]
    home_color2 = team_colors[team_colors.Team == recent_game["home_team_name"]].Secondary.iloc[0]
    away_color1 = team_colors[team_colors.Team == recent_game["away_team_name"]].Primary.iloc[0]
    away_color2 = team_colors[team_colors.Team == recent_game["away_team_name"]].Secondary.iloc[0]

    ## Match Lineups
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

    rec_match_md = MdUtils(file_name=f'temp//{file_name}')

    # yaml header
    rec_match_md.new_line("HEADERSTART")
    rec_match_md.new_line("---")
    rec_match_md.new_line("layout: page")
    rec_match_md.new_line(f"title: {score_header}")
    rec_match_md.new_line(f"date: {recent_game['date']} 18:00:00 -0500")
    rec_match_md.new_line("categories: match review")
    rec_match_md.new_line("---")

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

    ## Win probability plots
    if isinstance(recent_game['commentary_df'], np.ndarray):
        match_events = real_time_preds.real_time_df(recent_game)
        '''sns.lineplot(x = 'Time', y = 'prediction', data = match_events)
        ax2 = plt.twinx()
        sns.lineplot(x = 'Time', y = 'Home Points', data=match_events, color=home_color1, ax=ax2)
        pred_plot = sns.lineplot(x = 'Time', y = 'Away Points', data=match_events, color=away_color1, ax=ax2)
        pred_plot.figure.savefig(f"reviews/recap_predictions_{file_name}.png")
        pred_plot.figure.clf()'''
        prob_path = prob_plot(match_events, file_name)
        score_path = score_plot(match_events, file_name, recent_game, home_color1, away_color1, home_color2, away_color2)

        rec_match_md.new_paragraph(f"![In Match Predictions]({prob_path})")
        rec_match_md.new_paragraph(f"![In Match Scores]({score_path})")


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

    match_dir_strings.append(f'[{score_header}](reviews//{file_name})')
    match_comps.append(recent_game['competition'])
    match_levels.append(recent_game['comp_level'])

    #rec_dir_md.new_paragraph(f'[{score_header}](reviews//{file_name})')

    ## quick and dirty remove empty leading lines
    clean_leading_space(f'temp//{file_name}.md', f'reviews//{file_name}.md')

dir_df = pd.DataFrame({'links':match_dir_strings, 'comps':match_comps, 'levels':match_levels})
dir_int = dir_df[dir_df.levels == 'International']
dir_pro = dir_df[dir_df.levels == 'Pro']
dir_dom = dir_df[dir_df.levels == 'Domestic']
if dir_int.shape[0] > 0:
    rec_dir_md.new_header(level = 1, title = 'International Matches')
    for comp in sorted(dir_int.comps.unique()):
        rec_dir_md.new_header(level = 2, title = comp)
        for _, row in dir_int[dir_int.comps == comp].iterrows():
            rec_dir_md.new_paragraph(row[0])

if dir_pro.shape[0] > 0:
    rec_dir_md.new_header(level = 1, title = 'Professional Leagues')
    for comp in sorted(dir_pro.comps.unique()):
        rec_dir_md.new_header(level = 2, title = comp)
        for _, row in dir_pro[dir_pro.comps == comp].iterrows():
            rec_dir_md.new_paragraph(row[0])

if dir_dom.shape[0] > 0:
    rec_dir_md.new_header(level = 1, title = 'Domestic Leagues')
    for comp in sorted(dir_dom.comps.unique()):
        rec_dir_md.new_header(level = 2, title = comp)
        for _, row in dir_dom[dir_dom.comps == comp].iterrows():
            rec_dir_md.new_paragraph(row[0])

rec_dir_md.create_md_file()
clean_leading_space(f'temp//Recent_Matches.md', f'Recent_Matches.md')


## ~~~~~~~~~~~~~~~~~ FUTURE MATCHES ~~~~~~~~~~~~~~~~~~~ ##
fut_dir_md = MdUtils(file_name=f'temp//Current_Projections')
fut_dir_md.new_line("HEADERSTART")
fut_dir_md.new_line("---")
fut_dir_md.new_line("layout: article")
fut_dir_md.new_line(f"title: Current Projections")
fut_dir_md.new_line("key: page-projections")
fut_dir_md.new_line("---")

current_players = make_current_percentile(starters, datetime.datetime.now())

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
    fut_match_md.new_line("HEADERSTART")
    fut_match_md.new_paragraph("---")
    fut_match_md.new_paragraph("layout: page")
    fut_match_md.new_paragraph(f"title: {pretty_name}")
    fut_match_md.new_paragraph(f"date: {future_game['date']} 18:00:00 -0500")
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
    clean_leading_space(f'temp//{file_name}.md', f'projections//{file_name}.md')

fut_dir_md.create_md_file()
clean_leading_space(f'temp//Current_Projections.md', f'Current_Projections.md')


files = glob.glob('temp/*')
for f in files:
    os.remove(f)