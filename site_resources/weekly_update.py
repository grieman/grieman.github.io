## IMPORTS
import sys
import yaml
with open('secrets.yml', 'r') as file:
    secrets = yaml.safe_load(file)
sys.path.append(secrets['elo_proj_path'])

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)


from player_club_classes import team_elo, Player, Club, Match, team_elo_minutes
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
from support_files.comp_levels import comp_level_dict, comp_match_dict
from tabulate import tabulate
import os
import glob
import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from plot_functions import *

## Need to ge the current home advantage? as 5 as of 8/5, 3 as of 11/8, 7 as of 12/31
# this should REALLY not be hard coded
home_advantage = 4
named_players = []

def elo_contribition(player_df, column):
    mult = np.where(player_df.Number <= 15, (7/8), 0.234)
    return player_df[column] * mult

def clean_leading_space(orig_name, new_name):
    ## quick and dirty remove empty leading lines
    TAG = b'HEADERSTART'
    tag_found = False
    with open(orig_name, 'rb') as in_file:
        with open(new_name, 'wb') as out_file:
            for line in in_file:
                if not tag_found:
                    if line.strip() == TAG:
                        tag_found = True
                else:
                    out_file.write(line)

def comp_accuracy_statements(matchlist, comp):
    output_list = []
    comp_matches = pd.DataFrame([x for x in match_list if (x['competition'] == comp) and ('point_diff' in x.keys())])
    if len(comp_matches) > 0:
        comp_matches = comp_matches.drop(['home_team','away_team','commentary_df'], axis =1)
        comp_matches = comp_matches[~comp_matches.point_diff.isna()]

        correct_preds = sum((comp_matches.point_diff * comp_matches.adv_spread) > 0)
        avg_error = np.mean(abs(comp_matches.adv_spread - comp_matches.point_diff))
        num_teams = pd.concat([comp_matches.home_team_name, comp_matches.away_team_name]).nunique()
        recent_comp_matches = comp_matches.tail(int(np.ceil(num_teams/2)))
        recent_correct_preds = sum((recent_comp_matches.point_diff * recent_comp_matches.adv_spread) > 0)
        recent_avg_error = np.mean(abs(recent_comp_matches.adv_spread - recent_comp_matches.point_diff))

        output_list.append(f"Competition Accuracy: {correct_preds} of {comp_matches.shape[0]} ({np.round((correct_preds / comp_matches.shape[0]) * 100,2)}%)")
        output_list.append(f"Competition Error: {np.round(avg_error,2)} points per match")
        output_list.append(f"Last Round Accuracy: {recent_correct_preds} of {recent_comp_matches.shape[0]} ({np.round((recent_correct_preds / recent_comp_matches.shape[0]) * 100,2)}%)")
        output_list.append(f"Last Round Error: {np.round(recent_avg_error,2)} points per match")
    
    return output_list

files = glob.glob('projections/*') + glob.glob('reviews/*') + glob.glob('_includes/plots/recap_predictions/*')# + glob.glob('playerfiles/*')
for f in files:
    os.remove(f)

team_colors = pd.DataFrame(team_color_dict).T
team_colors.columns = ['Primary', 'Secondary']
team_colors = team_colors.rename_axis('Team').reset_index()
# Replace empty colors with something GARISH to finish color map
team_colors['Primary'] = team_colors['Primary'].replace('','#EE3A8C')
team_colors['Secondary'] = team_colors['Secondary'].replace('','#8B4513')


from plotly.validators.scatter.marker import SymbolValidator
raw_symbols = SymbolValidator().values

simple_symbols = [i for i in raw_symbols if str(i).isalpha()]

with open('../Rugby_ELO/processed_data/playerbase.pickle', 'rb') as handle:
    playerbase = pickle.load(handle)
with open('../Rugby_ELO/processed_data/matchlist.pickle', 'rb') as handle:
    matchlist = pickle.load(handle)
with open('../Rugby_ELO/processed_data/teamlist.pickle', 'rb') as handle:
    teamlist = pickle.load(handle)
with open('../Rugby_ELO/processed_data/clubbase.pickle', 'rb') as handle:
    clubbase = pickle.load(handle)


## LOAD DATA
club_histories = pd.concat([x.return_history() for x in clubbase.values()])

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

## ~~~~~~~~~~~~~~~~~ RECENT MATCHES ~~~~~~~~~~~~~~~~~~~ ##
rec_dir_md = MdUtils(file_name=f'temp//Recent_Matches')
rec_dir_md.new_line("HEADERSTART")
rec_dir_md.new_line("---")
rec_dir_md.new_line("layout: article")
rec_dir_md.new_line(f'title: Recent Matches')
rec_dir_md.new_line("key: page-recents")
rec_dir_md.new_line("---")

match_dir_strings = []
match_comps = []
match_levels = []
match_dates = []

recent_games = [x for x in match_list if datetime.datetime.now() > x['date'] > datetime.datetime.now() - datetime.timedelta(days=10)]
recent_games = [x for x in recent_games if 'point_diff' in x.keys()]

for recent_game in recent_games:
    if 'away_score' in recent_game.keys():
        
        current_players = make_current_percentile(starters, recent_game['date'])
        pretty_name = f'{recent_game["away_team_name"]} at {recent_game["home_team_name"]}'
        file_name = f'{recent_game["date"].date().strftime("%Y-%m-%d")}-{recent_game["home_team_name"].replace(" ", "")}-{recent_game["away_team_name"].replace(" ", "")}'
        score_header = f'{recent_game["away_team_name"]} at {recent_game["home_team_name"]}; {recent_game["away_score"]}-{recent_game["home_score"]}'
        main_header = f'{recent_game["away_team_name"]} ({round(recent_game["away_elo"], 2)}) at {recent_game["home_team_name"]} ({round(recent_game["home_elo"], 2)}); {recent_game["away_score"]}-{recent_game["home_score"]}'
        print(pretty_name)

        # team colors
        if (recent_game["home_team_name"] in set(team_colors.Team)) & (recent_game["away_team_name"] in set(team_colors.Team)):
            home_color1 = team_colors[team_colors.Team == recent_game["home_team_name"]].Primary.iloc[0]
            home_color2 = team_colors[team_colors.Team == recent_game["home_team_name"]].Secondary.iloc[0]
            away_color1 = team_colors[team_colors.Team == recent_game["away_team_name"]].Primary.iloc[0]
            away_color2 = team_colors[team_colors.Team == recent_game["away_team_name"]].Secondary.iloc[0]
        else:
            print("NEED TEAM COLORS")
            home_color1 = 'black'
            home_color2 = 'black'
            away_color1 = 'white'
            away_color2 = 'white'

        ## Club Level Info
        '''club_level_match = club_histories[(club_histories.Club == recent_game['home_team_name']) & (club_histories.Date == recent_game['date'])]
        home_sims = np.random.normal(club_level_match.mu, club_level_match.sigma, size=1000)
        away_sims = np.random.normal(club_level_match.Opponent_mu, club_level_match.Opponent_sigma, size=1000)
        spreads = (home_sims - away_sims) / 20

        fig, ax = plt.subplots()
        sns.kdeplot(data=home_sims, ax=ax, color=home_color1, fill=True, label=f'{recent_game["home_team_name"]} Possible Performances')
        sns.kdeplot(data=away_sims, ax=ax, color=away_color1, fill=True, label=f'{recent_game["away_team_name"]} Possible Performances')
        ax.legend()
        sns.move_legend(ax, "lower center", bbox_to_anchor=(.5, 1), ncol=3, title=None, frameon=False)
        plt.tight_layout()
        #plt.show()

        spread_df = pd.DataFrame({'spread': np.round(spreads, 0).astype(int)})
        spread_df['result_numeric'] = ((np.sign(spread_df.spread) + 1) / 2)
        spread_df['result'] = spread_df['result_numeric'].map({1:f'{recent_game["home_team_name"]} Victory', 0:f'{recent_game["away_team_name"]} Victory', 0.5:'Tie'})
        spread_df = spread_df.sort_values('result_numeric')
        sns.displot(spread_df, x='spread', bins = np.sort(spread_df.spread.unique()), hue='result', palette=[away_color1, 'yellow', home_color1,])
        #plt.show()'''

        ## Match Lineups
        home_team = pd.DataFrame(recent_game['home_team'][:, [0,1,31,-3,-1]], columns = ['Number', 'Full_Name', 'Minutes', 'Unicode_ID', 'elo'])
        home_team = home_team.merge(current_players, on=['Full_Name', 'Unicode_ID'], how = 'left')
        home_team = home_team.drop(['Unicode_ID'], axis = 1)
        away_team = pd.DataFrame(recent_game['away_team'][:, [0,1,31,-3,-1]], columns = ['Number', 'Full_Name', 'Minutes', 'Unicode_ID', 'elo'])
        away_team = away_team.merge(current_players, on=['Full_Name', 'Unicode_ID'], how = 'left')
        away_team = away_team.drop(['Unicode_ID'], axis = 1)

        home_team.columns = ['Number', 'Home Player', 'Home Minutes', 'Home elo', 'Home Percentile']
        away_team.columns = ['Number', 'Away Player', 'Away Minutes', 'Away elo', 'Away Percentile']
        
        named_players.append(home_team['Home Player'])
        named_players.append(away_team['Away Player'])

        home_team['Home Player'] = [f"[{name}](..//playerfiles//{name.replace(' ', '')}_cleaned.md)" for name in home_team['Home Player']]
        away_team['Away Player'] = [f"[{name}](..//playerfiles//{name.replace(' ', '')}_cleaned.md)" for name in away_team['Away Player']]

        all_players = home_team.merge(away_team, on = 'Number', how= 'outer')
        all_players = all_players.sort_values('Number')
        all_players = all_players.apply(pd.to_numeric, errors='ignore').round({'Home elo':2, 'Away elo':2})
        all_players = all_players[['Away Minutes', 'Away Player', 'Away elo','Away Percentile', 'Number', 'Home Percentile', 'Home elo', 'Home Player', 'Home Minutes']]
        player_table = tabulate(all_players, tablefmt="pipe", headers="keys", showindex=False)

        rec_match_md = MdUtils(file_name=f'temp//{file_name}')

        # yaml header
        rec_match_md.new_line("HEADERSTART")
        rec_match_md.new_line("---")
        rec_match_md.new_line("layout: page")
        rec_match_md.new_line(f'title: {score_header}')
        rec_match_md.new_line(f'date: {recent_game["date"]} 18:00:00 -0500')
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

        rec_match_md.new_header(level = 1, title = main_header)
        rec_match_md.new_header(level = 1, title = f'Prediction: {pred_text}')
        rec_match_md.new_paragraph(n_pred_text)

        ## Win probability plots
        if isinstance(recent_game['commentary_df'], np.ndarray):
            try:
                match_events = real_time_preds.real_time_df(recent_game)
                '''sns.lineplot(x = 'Time', y = 'prediction', data = match_events)
                ax2 = plt.twinx()
                sns.lineplot(x = 'Time', y = 'Home Points', data=match_events, color=home_color1, ax=ax2)
                pred_plot = sns.lineplot(x = 'Time', y = 'Away Points', data=match_events, color=away_color1, ax=ax2)
                pred_plot.figure.savefig(f"reviews/recap_predictions_{file_name}.png")
                pred_plot.figure.clf()'''
                prob_path = prob_plot(match_events, file_name, home_color1, away_color1, home_color2, away_color2)
                plt.close()
                score_path = score_plot(match_events, file_name, recent_game, home_color1, away_color1, home_color2, away_color2)
                plt.close()

                rec_match_md.new_header(level = 2, title = 'Scores over Time')
                rec_match_md.new_paragraph(f'![In Match Scores]({score_path})')
                rec_match_md.new_header(level = 2, title = 'Win Probability over Time')
                rec_match_md.new_paragraph(f'![In Match Predictions]({prob_path})')
                 
            except:
                pass


        rec_match_md.new_header(level = 1, title = f'Pre-Match Prediction: {lineup_pred_text}')
        rec_match_md.new_paragraph(n_lineup_pred_text)
        #rec_match_md.new_header(level = 1, title = f'Projection using minutes played for each player: {pred_text}')
        #rec_match_md.new_paragraph(n_pred_text)
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

        match_dir_strings.append(f'[{recent_game["date"].date().strftime("%Y-%m-%d") + " " + main_header}](reviews//{file_name})')
        match_comps.append(recent_game['competition'])
        match_levels.append(recent_game['comp_level'])
        match_dates.append(recent_game["date"])

        #rec_dir_md.new_paragraph(f'[{score_header}](reviews//{file_name})')

        ## quick and dirty remove empty leading lines
        clean_leading_space(f'temp//{file_name}.md', f'reviews//{file_name}.md')

dir_df = pd.DataFrame({'links':match_dir_strings, 'comps':match_comps, 'levels':match_levels, 'dates':match_dates})
## Add a summary of accuracy for each competition?
dir_df = dir_df.sort_values('dates')
dir_int = dir_df[dir_df.levels == 'International']
dir_pro = dir_df[(dir_df.levels == 'Pro1')|(dir_df.levels == 'Pro0')]
dir_dom = dir_df[dir_df.levels == 'Domestic']
if dir_int.shape[0] > 0:
    rec_dir_md.new_header(level = 1, title = 'International Matches')
    for comp in sorted(dir_int.comps.unique()):
        rec_dir_md.new_header(level = 2, title = comp[:-5])
        accuracy_lines = comp_accuracy_statements(matchlist, comp)
        for line in accuracy_lines:
            rec_dir_md.new_paragraph(line)
        for _, row in dir_int[dir_int.comps == comp].iterrows():
            rec_dir_md.new_paragraph(row[0])

if dir_pro.shape[0] > 0:
    rec_dir_md.new_header(level = 1, title = 'Professional Leagues')
    for comp in sorted(dir_pro.comps.unique()):
        rec_dir_md.new_header(level = 2, title = comp[:-5])
        accuracy_lines = comp_accuracy_statements(matchlist, comp)
        for line in accuracy_lines:
            rec_dir_md.new_paragraph(line)
        for _, row in dir_pro[dir_pro.comps == comp].iterrows():
            rec_dir_md.new_paragraph(row[0])

if dir_dom.shape[0] > 0:
    rec_dir_md.new_header(level = 1, title = 'Domestic Leagues')
    for comp in sorted(dir_dom.comps.unique()):
        rec_dir_md.new_header(level = 2, title = comp[:-5])
        accuracy_lines = comp_accuracy_statements(matchlist, comp)
        for line in accuracy_lines:
            rec_dir_md.new_paragraph(line)
        for _, row in dir_dom[dir_dom.comps == comp].iterrows():
            rec_dir_md.new_paragraph(row[0])

rec_dir_md.create_md_file()
clean_leading_space(f'temp//Recent_Matches.md', f'Recent_Matches.md')


## ~~~~~~~~~~~~~~~~~ FUTURE MATCHES ~~~~~~~~~~~~~~~~~~~ ##
fut_dir_md = MdUtils(file_name=f'temp//Current_Projections')
fut_dir_md.new_line("HEADERSTART")
fut_dir_md.new_line("---")
fut_dir_md.new_line("layout: article")
fut_dir_md.new_line(f'title: Current Projections')
fut_dir_md.new_line("key: page-projections")
fut_dir_md.new_line("---")

match_dir_strings = []
match_comps = []
match_levels = []
match_dates = []
future_names = []

current_players = make_current_percentile(starters, datetime.datetime.now())

print("FUTURE MATCHES")
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

    named_players.append(home_team['Home Player'])
    named_players.append(away_team['Away Player'])

    home_team['Home Player'] = [f"[{name}](..//playerfiles//{name.replace(' ', '')}_cleaned.md)" for name in home_team['Home Player']]
    away_team['Away Player'] = [f"[{name}](..//playerfiles//{name.replace(' ', '')}_cleaned.md)" for name in away_team['Away Player']]

    all_players = pd.merge(home_team, away_team, on = 'Number')
    all_players = all_players.sort_values('Number')
    all_players = all_players.apply(pd.to_numeric, errors='ignore').round({'Home elo':2, 'Away elo':2})
    all_players = all_players[['Away Player', 'Away elo','Away Percentile', 'Number', 'Home Percentile', 'Home elo', 'Home Player']]
    player_table = tabulate(all_players, tablefmt="pipe", headers="keys", showindex=False)

    pretty_name = f'{future_game["away_team_name"]} at {future_game["home_team_name"]}'
    file_name = f'{future_game["date"].date().strftime("%Y-%m-%d")}-{future_game["home_team_name"].replace(" ", "")}-{future_game["away_team_name"].replace(" ", "")}'
    main_header = f'{future_game["away_team_name"]} ({round(future_game["lineup_away_elo"], 2)}) at {future_game["home_team_name"]} ({round(future_game["lineup_home_elo"], 2)})'
    fut_match_md = MdUtils(file_name=f'temp//{file_name}')

    # yaml header
    fut_match_md.new_line("HEADERSTART")
    fut_match_md.new_line("---")
    fut_match_md.new_line("layout: page")
    fut_match_md.new_line(f'title: {pretty_name}')
    fut_match_md.new_line(f'date: {future_game["date"]} 18:00:00 -0500')
    fut_match_md.new_line("categories: match prediction")
    fut_match_md.new_line("---")

    print(pretty_name)

    favorite = future_game["home_team_name"] if future_game["lineup_spread"] + home_advantage > 0 else future_game["away_team_name"]
    pred_text = f'{favorite} by {round(abs(future_game["lineup_spread"] + home_advantage), 1)}'

    n_favorite = future_game["home_team_name"] if future_game["lineup_spread"] > 0 else future_game["away_team_name"]
    n_pred_text = f'{n_favorite} by {round(abs(future_game["lineup_spread"]), 1)} on a neutral pitch'

    fut_match_md.new_header(level = 1, title = main_header)
    fut_match_md.new_header(level = 1, title = f'Prediction: {pred_text}')
    fut_match_md.new_paragraph(n_pred_text)
    fut_match_md.new_paragraph(player_table)
    fut_match_md.new_paragraph()

    #fut_match_md.new_header(level = 1, title = 'Elo Contributions')

    all_players['home contributions'] = elo_contribition(all_players, 'Home elo')
    all_players['away contributions'] = elo_contribition(all_players, 'Away elo')
    #projection_contribution_plot(all_players, f"projections//{file_name}_contributions.html")
    #fut_match_md.new_paragraph(f"{{% include_relative {file_name}_contributions.html %}}")

    match_dir_strings.append(f'[{future_game["date"].date().strftime("%Y-%m-%d")} {main_header}](projections//{file_name})')
    #short_comp_name = future_game['competition'][:-5] if future_game['competition'][-4:].isnumeric() else future_game['competition']
    match_comps.append(future_game['competition'])
    match_levels.append(future_game['comp_level'])
    match_dates.append(future_game["date"])
    future_names.append(pretty_name)


    fut_match_md.create_md_file()

    #fut_dir_md.new_paragraph(f'[{pretty_name}; {pred_text}](projections//{file_name})')

    ## quick and dirty remove empty leading lines
    clean_leading_space(f'temp//{file_name}.md', f'projections//{file_name}.md')

print("FUTURE MATCHES - NO LINEUPS")
all_fut_matches = glob.glob(os.path.join("../Rugby_ELO/future_matches", "*.psv"))
fut_matches_df = pd.concat((pd.read_csv(f, sep="|") for f in all_fut_matches))
fut_matches_df = fut_matches_df.drop(["Unnamed: 0"], axis=1)
fut_matches_df.Date = pd.to_datetime(fut_matches_df.Date)
fut_matches_df = fut_matches_df[fut_matches_df.Date <= datetime.datetime.now() + datetime.timedelta(days=7)]
fut_matches_df = fut_matches_df[fut_matches_df.Date >= datetime.datetime.now() - datetime.timedelta(days=1)]

league_parts = fut_matches_df.loc[fut_matches_df.Competition.str.contains('_'), "Competition"].str.split('_').str[0]
year_parts = fut_matches_df.loc[fut_matches_df.Competition.str.contains('_'), "Competition"].str.split('_').str[1]
fut_matches_df.loc[fut_matches_df.Competition.str.contains('_'), "Competition"] = league_parts.replace(comp_match_dict) + " " + year_parts

fut_matches_df['comp_level'] = "Unknown"
for key, value in comp_level_dict.items():
    fut_matches_df.loc[fut_matches_df.Competition.str.contains(key), 'comp_level'] = value

#fut_matches_df['Competition'] = fut_matches_df['Competition'].str[:-5]

for _, row in fut_matches_df.iterrows():
    match_date = row["Date"].date().strftime("%Y-%m-%d")
    pretty_name = f'{row["Away Team"]} at {row["Home Team"]}'
    file_name = f'{match_date}-{row["Home Team"].replace(" ", "")}-{row["Away Team"].replace(" ", "")}'

    if pretty_name not in future_names:
        home_club = teamlist[row['Home Team']]
        away_club = teamlist[row['Away Team']]

        ## Use current player elos, but historic team + minutes
        home_club_elos = [
            team_elo_minutes(matchlist[x['Match_Name']].home_team, playerbase) 
            if matchlist[x['Match_Name']].home_team_name == row['Home Team'] 
            else team_elo_minutes(matchlist[x['Match_Name']].away_team, playerbase)
            for x in home_club.history[-5:]
            ]
        away_club_elos = [
            team_elo_minutes(matchlist[x['Match_Name']].home_team, playerbase) 
            if matchlist[x['Match_Name']].home_team_name == row['Away Team'] 
            else team_elo_minutes(matchlist[x['Match_Name']].away_team, playerbase)
            for x in away_club.history[-5:]
            ]

        #home_club_elos = [x['elo'] for x in home_club.history[-5:]]
        #away_club_elos = [x['elo'] for x in away_club.history[-5:]]
        historic_weighting = [0.1, 0.15, 0.2, 0.25, 0.3]
        home_elo_avg = sum(np.multiply(home_club_elos, historic_weighting))
        away_elo_avg = sum(np.multiply(away_club_elos, historic_weighting))

        imputed_spread =  (home_elo_avg -  away_elo_avg) / 10 #GLOBAL_score_factor == 10, this should not be hard-coded

        main_header = f'{row["Away Team"]} (~{round(away_elo_avg, 2)}) at {row["Home Team"]} (~{round(home_elo_avg, 2)})'

        fut_match_md = MdUtils(file_name=f'temp//{file_name}')

        # yaml header
        fut_match_md.new_line("HEADERSTART")
        fut_match_md.new_line("---")
        fut_match_md.new_line("layout: page")
        fut_match_md.new_line(f'title: {pretty_name}')
        fut_match_md.new_line(f'date: {row["Date"]} 18:00:00 -0500')
        fut_match_md.new_line("categories: match prediction imputed")
        fut_match_md.new_line("---")

        print(pretty_name)

        favorite = row["Home Team"] if imputed_spread + home_advantage > 0 else row["Away Team"]
        pred_text = f'{favorite} by {round(abs(imputed_spread + home_advantage), 1)}'

        n_favorite = row["Home Team"] if imputed_spread > 0 else row["Away Team"]
        n_pred_text = f'{n_favorite} by {round(abs(imputed_spread), 1)} on a neutral pitch'

        fut_match_md.new_header(level = 1, title = main_header)
        fut_match_md.new_header(level = 1, title = f'Prediction: {pred_text}')
        fut_match_md.new_paragraph(n_pred_text)
        fut_match_md.new_paragraph()

        match_dir_strings.append(f'[{match_date} {main_header}](projections//{file_name})')
        match_comps.append(row['Competition'])
        match_levels.append(row['comp_level'])
        match_dates.append(match_date)

        fut_match_md.create_md_file()

        clean_leading_space(f'temp//{file_name}.md', f'projections//{file_name}.md')



dir_df = pd.DataFrame({'links':match_dir_strings, 'comps':match_comps, 'levels':match_levels, 'dates':match_dates})
dir_df = dir_df.sort_values('dates')
dir_int = dir_df[dir_df.levels == 'International']
dir_pro = dir_df[(dir_df.levels == 'Pro1')|(dir_df.levels == 'Pro0')]
dir_dom = dir_df[dir_df.levels == 'Domestic']
if dir_int.shape[0] > 0:
    fut_dir_md.new_header(level = 1, title = 'International Matches')
    for comp in sorted(dir_int.comps.unique()):
        fut_dir_md.new_header(level = 2, title = comp[:-5])
        accuracy_lines = comp_accuracy_statements(matchlist, comp)
        for line in accuracy_lines:
            fut_dir_md.new_paragraph(line)
            
        for _, row in dir_int[dir_int.comps == comp].iterrows():
            fut_dir_md.new_paragraph(row[0])

if dir_pro.shape[0] > 0:
    fut_dir_md.new_header(level = 1, title = 'Professional Leagues')
    for comp in sorted(dir_pro.comps.unique()):
        fut_dir_md.new_header(level = 2, title = comp[:-5])
        accuracy_lines = comp_accuracy_statements(matchlist, comp)
        for line in accuracy_lines:
            fut_dir_md.new_paragraph(line)
            
        for _, row in dir_pro[dir_pro.comps == comp].iterrows():
            fut_dir_md.new_paragraph(row[0])

if dir_dom.shape[0] > 0:
    fut_dir_md.new_header(level = 1, title = 'Domestic Leagues')
    for comp in sorted(dir_dom.comps.unique()):
        fut_dir_md.new_header(level = 2, title = comp[:-5])
        accuracy_lines = comp_accuracy_statements(matchlist, comp)
        for line in accuracy_lines:
            fut_dir_md.new_paragraph(line)
            
        for _, row in dir_dom[dir_dom.comps == comp].iterrows():
            fut_dir_md.new_paragraph(row[0])

fut_dir_md.create_md_file()
clean_leading_space(f'temp//Current_Projections.md', f'Current_Projections.md')


## run generate playerpage for all named players
import generate_playerpage
named_players = list(set(list(pd.concat(named_players))))
#with open(r'named_players.txt', 'w') as fp:
#    fp.write("\n".join(str(item) for item in named_players))

generate_playerpage.main(named_players, regenerate = False)


files = glob.glob('temp/*')
for f in files:
    os.remove(f)