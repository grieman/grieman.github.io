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
import shutil
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

def club_comp_accuracy_statements(club_histories, comp):
    output_list = []
    comp_matches = club_histories[(club_histories.Home == 1) & (club_histories.Competition == comp) & (~club_histories.Point_Diff.isna())]
    if len(comp_matches) > 0:
        num_teams = pd.concat([comp_matches.Opponent, comp_matches.Club]).nunique()
        recent_comp_matches = comp_matches.tail(int(np.ceil(num_teams/2)))

        correct_preds = sum((comp_matches.Point_Diff * comp_matches.Predicted_Spread) > 0)
        avg_error = np.mean(abs(comp_matches.Predicted_Spread - comp_matches.Point_Diff))
        recent_correct_preds = sum((recent_comp_matches.Point_Diff * recent_comp_matches.Predicted_Spread) > 0)
        recent_avg_error = np.mean(abs(recent_comp_matches.Predicted_Spread - recent_comp_matches.Point_Diff))

        output_list.append(f"Competition Accuracy: {correct_preds} of {comp_matches.shape[0]} ({np.round((correct_preds / comp_matches.shape[0]) * 100,2)}%)")
        output_list.append(f"Competition Error: {np.round(avg_error,2)} points per match")
        output_list.append(f"Last Round Accuracy: {recent_correct_preds} of {recent_comp_matches.shape[0]} ({np.round((recent_correct_preds / recent_comp_matches.shape[0]) * 100,2)}%)")
        output_list.append(f"Last Round Error: {np.round(recent_avg_error,2)} points per match")
    
    return output_list

def get_team_colors(home_team_name, away_team_name):
    # team colors
    if (home_team_name in set(team_colors.Team)) & (away_team_name in set(team_colors.Team)):
        home_color1 = team_colors[team_colors.Team == home_team_name].Primary.iloc[0]
        home_color2 = team_colors[team_colors.Team == home_team_name].Secondary.iloc[0]
        away_color1 = team_colors[team_colors.Team == away_team_name].Primary.iloc[0]
        away_color2 = team_colors[team_colors.Team == away_team_name].Secondary.iloc[0]
    else:
        print("NEED TEAM COLORS")
        home_color1 = 'black'
        home_color2 = 'black'
        away_color1 = 'white'
        away_color2 = 'white'
        
    return home_color1, home_color2, away_color1, away_color2

def fill_matches(directory_df, md_file):
    dir_df = directory_df.sort_values('dates')
    dir_int = dir_df[dir_df.levels == 'International']
    dir_pro = dir_df[(dir_df.levels == 'Pro1')|(dir_df.levels == 'Pro0')]
    dir_dom = dir_df[dir_df.levels == 'Domestic']
    if dir_int.shape[0] > 0:
        md_file.new_header(level = 1, title = 'International Matches')
        for comp in sorted(dir_int.comps.unique()):
            md_file.new_header(level = 2, title = comp[:-5])
            accuracy_lines = club_comp_accuracy_statements(club_histories, comp)
            for line in accuracy_lines:
                md_file.new_paragraph(line)
                
            for _, row in dir_int[dir_int.comps == comp].iterrows():
                md_file.new_paragraph(row[0])

    if dir_pro.shape[0] > 0:
        md_file.new_header(level = 1, title = 'Top Flight Leagues')
        for comp in sorted(dir_pro.comps.unique()):
            md_file.new_header(level = 2, title = comp[:-5])
            accuracy_lines = club_comp_accuracy_statements(club_histories, comp)
            for line in accuracy_lines:
                md_file.new_paragraph(line)
                
            for _, row in dir_pro[dir_pro.comps == comp].iterrows():
                md_file.new_paragraph(row[0])

    if dir_dom.shape[0] > 0:
        md_file.new_header(level = 1, title = 'Domestic Leagues')
        for comp in sorted(dir_dom.comps.unique()):
            md_file.new_header(level = 2, title = comp[:-5])
            accuracy_lines = club_comp_accuracy_statements(club_histories, comp)
            for line in accuracy_lines:
                md_file.new_paragraph(line)
                
            for _, row in dir_dom[dir_dom.comps == comp].iterrows():
                md_file.new_paragraph(row[0])

def make_matchpage(
    file_name,
    folder,
    main_header, 
    match_date,
    club_prediction,
    club_victor,
    club_margin,
    perf_plot_path,
    spread_plot_path,
    resultbar_path,
    pred_text,
    n_pred_text,
    lineup_pred_text,
    n_lineup_pred_text,
    categories_list = ["review", "projection", "imputed"],
    player_table = None,
    score_path = None,
    prob_path = None,
    num_shifts = None
    ):

    md_file = MdUtils(file_name=f'temp//{file_name}')
    # yaml header
    md_file.new_line("HEADERSTART")
    md_file.new_line("---")
    md_file.new_line("layout: page")
    md_file.new_line(f'title: {main_header}')
    md_file.new_line(f'date: {match_date} 18:00:00 -0500')
    md_file.new_line("categories: match " + " ".join(categories_list))
    md_file.new_line("---")

    md_file.new_header(level = 1, title = main_header)
    md_file.new_header(level=1, title = "Club Level Predictions")
    md_file.new_paragraph(
        f"The first set of predictions treats a club as the smallest object, as the club develops its members, organizes a gameplan, and deploys its players as needed for each match. This club model has a prediction of {club_prediction}, which translates to predicting {club_victor} to win by {club_margin}."
        )
    md_file.new_paragraph(
        "Each club has a rating and a rating deviation (simiar to a Glicko system), and expected performances can be generated. This allows for simulated matches and spreads like the ones below."
        )

    md_file.new_header(level=2, title = "Projected Performances")
    md_file.new_paragraph(f'![Projected Performances]({perf_plot_path})')

    md_file.new_header(level=2, title = "Projected Spreads")
    md_file.new_paragraph(f'![Projected Spreads]({spread_plot_path})')

    md_file.new_header(level=2, title = "Projected Results")
    md_file.new_paragraph(f'![Projected Results]({resultbar_path})')


    ## Break, now player level
    md_file.new_header(level=1, title = "Player Level Predictions")
    md_file.new_paragraph(
        "Treating teams instead as an entity made up of the currently active players, I have ratings for each player in an altogether different system. These can be combined to form team ratings once teamsheets are announced, weighting starters a bit higher than the reserves. After the match is played, players can be weighted by their minutes on the field, allowing for an accurate measure of the team's composition. With these compiled team ratings, we can make predictions, measure inaccuracy, and update the individual player ratings."
        )

    if pred_text:
        md_file.new_header(level = 2, title = f'Prediction with Player Minutes: {pred_text}')
        md_file.new_paragraph(n_pred_text)

    ## Win probability plots
    if score_path:
        md_file.new_header(level = 2, title = 'Scores over Time')
        md_file.new_paragraph(f'![In Match Scores]({score_path})')

    if prob_path:
        md_file.new_header(level = 2, title = 'Win Probability over Time')
        md_file.new_paragraph(f'![In Match Predictions]({prob_path})')
    
    if num_shifts:
        md_file.new_paragraph(f"There were {int(num_shifts)} large changes in win probability in this match")

    if lineup_pred_text:
        if ("imputed" not in categories_list):
            md_file.new_header(level = 2, title = f'Prediction without Player Minutes: {lineup_pred_text}')
            md_file.new_paragraph(n_lineup_pred_text)
            md_file.new_paragraph()
    
    if "imputed" in categories_list:
        md_file.new_header(level = 2, title = f'Prediction with Imputed Lineups: {lineup_pred_text}')
        md_file.new_paragraph(n_lineup_pred_text)
        md_file.new_paragraph()

    if player_table:
        md_file.new_paragraph(player_table)
        md_file.new_paragraph()


    md_file.create_md_file()

    clean_leading_space(f'temp//{file_name}.md', f'{folder}//{file_name}.md')

# files = glob.glob('projections/*') + glob.glob('reviews/*') + glob.glob('_includes/plots/recap_predictions/*')# + glob.glob('playerfiles/*')
folders = ["projections", "reviews"]
for f in folders:
    shutil.rmtree(f)

if not os.path.exists('projections/plots'):
    os.makedirs('projections/plots', mode=0o777)

if not os.path.exists('reviews/plots'):
    os.makedirs('reviews/plots', mode=0o777)

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
#club_histories = club_histories[(~club_histories.Outcome.isna())]

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
        print(pretty_name)

        # team colors
        home_color1, home_color2, away_color1, away_color2 = get_team_colors(recent_game["home_team_name"], recent_game["away_team_name"])

        ## Generate Club Level Info
        club_level_match = club_histories[(club_histories.Club == recent_game['home_team_name']) & (club_histories.Opponent == recent_game['away_team_name']) & (club_histories.Date == recent_game['date'])].iloc[0]
        home_sims = np.random.normal(club_level_match['mu'], club_level_match['sigma'], size=2000)
        away_sims = np.random.normal(club_level_match.Opponent_mu, club_level_match.Opponent_sigma, size=2000)

        ## Match Lineups + player_table
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

        favorite = recent_game["home_team_name"] if recent_game["spread"] > 0 else recent_game["away_team_name"]
        lineup_favorite = recent_game["home_team_name"] if recent_game["lineup_spread"] + home_advantage > 0 else recent_game["away_team_name"]
        n_lineup_favorite = recent_game["home_team_name"] if recent_game["lineup_spread"] > 0 else recent_game["away_team_name"]
        favorite = recent_game["home_team_name"] if recent_game["spread"] + home_advantage > 0 else recent_game["away_team_name"]
        n_favorite = recent_game["home_team_name"] if recent_game["spread"] > 0 else recent_game["away_team_name"]


        file_name = f'{recent_game["date"].date().strftime("%Y-%m-%d")}-{recent_game["home_team_name"].replace(" ", "")}-{recent_game["away_team_name"].replace(" ", "")}'
        main_header = f'{recent_game["away_team_name"]} at {recent_game["home_team_name"]}; {recent_game["away_score"]}-{recent_game["home_score"]}'
        match_date = recent_game["date"]
        club_prediction = np.round(club_level_match['Prediction'], 3)
        club_victor = club_level_match['Club'] if club_prediction >= 0.5 else club_level_match['Opponent']
        club_margin = np.round(club_level_match['Predicted_Spread'], 1) if club_prediction >= 0.5 else np.round(club_level_match['Predicted_Spread'], 1) * -1
        perf_plot_path, spread_plot_path, resultbar_path = glicko_club_plots(
            home_sims, away_sims, recent_game['home_team_name'], 
            recent_game['away_team_name'], "reviews/", file_name, home_color1, 
            away_color1, home_color2, away_color2, recent_game['point_diff']
            )
        pred_text = f'{favorite} by {round(abs(recent_game["spread"] + home_advantage ), 1)}'
        n_pred_text = f'{n_favorite} by {round(abs(recent_game["spread"]), 1)} on a neutral field'
        lineup_pred_text = f'{lineup_favorite} by {round(abs(recent_game["lineup_spread"] + home_advantage), 1)}'
        n_lineup_pred_text = f'{n_lineup_favorite} by {round(abs(recent_game["lineup_spread"]), 1)} on a neutral pitch'
        ## Win probability plots
        prob_path = None
        score_path = None
        num_shifts = None
        if isinstance(recent_game['commentary_df'], np.ndarray):
            try:
                match_events = real_time_preds.real_time_df(recent_game)
                num_shifts = sum(abs(match_events.prediction.diff()) > 0.025)
                prob_path = prob_plot(match_events, file_name, home_color1, away_color1, home_color2, away_color2)
                plt.close()
                score_path = score_plot(match_events, file_name, recent_game, home_color1, away_color1, home_color2, away_color2)
                plt.close()                 
            except:
                pass

        make_matchpage(
            file_name,
            "reviews",
            main_header, 
            match_date,
            club_prediction,
            club_victor,
            club_margin,
            perf_plot_path,
            spread_plot_path,
            resultbar_path,
            pred_text,
            n_pred_text,
            lineup_pred_text,
            n_lineup_pred_text,
            categories_list = ["review"],
            player_table = player_table,
            score_path = score_path,
            prob_path = prob_path,
            num_shifts = num_shifts
        )

        match_dir_strings.append(f'[{recent_game["date"].date().strftime("%Y-%m-%d") + " " + main_header}](reviews//{file_name})')
        match_comps.append(recent_game['competition'])
        match_levels.append(recent_game['comp_level'])
        match_dates.append(match_date)



dir_df = pd.DataFrame({'links':match_dir_strings, 'comps':match_comps, 'levels':match_levels, 'dates':match_dates})
## Add a summary of accuracy for each competition?
fill_matches(dir_df, rec_dir_md)
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

    pretty_name = f'{future_game["away_team_name"]} at {future_game["home_team_name"]}'
    print(pretty_name)

    home_color1, home_color2, away_color1, away_color2 = get_team_colors(future_game['home_team_name'], future_game['away_team_name'])

    # Club Level Info
    home_club = clubbase[future_game['home_team_name']]
    away_club = clubbase[future_game['away_team_name']]
    expectation, expectations, spreads, home_sims, away_sims = home_club.predict(away_club, home=True, n_sims=1000)
    club_spread = spreads.mean()
    club_header = f'{future_game["away_team_name"]} (~{round(away_sims.mean(), 2)}) at {future_game["home_team_name"]} (~{round(home_sims.mean(), 2)})'

    # Player Predictions
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


    lineup_favorite = future_game["home_team_name"] if future_game["lineup_spread"] + home_advantage > 0 else future_game["away_team_name"]
    n_lineup_favorite = future_game["home_team_name"] if future_game["lineup_spread"] > 0 else future_game["away_team_name"]


    file_name = f'{future_game["date"].date().strftime("%Y-%m-%d")}-{future_game["home_team_name"].replace(" ", "")}-{future_game["away_team_name"].replace(" ", "")}'
    main_header = f'{future_game["away_team_name"]} at {future_game["home_team_name"]}'
    match_date = future_game["date"]
    club_prediction = np.round(expectation, 3)
    club_victor = future_game['home_team_name'] if club_prediction >= 0.5 else future_game['away_team_name']
    club_margin = np.round(club_spread, 1) if club_prediction >= 0.5 else np.round(club_spread, 1) * -1
    perf_plot_path, spread_plot_path, resultbar_path = glicko_club_plots(
        home_sims, away_sims, future_game['home_team_name'], 
        future_game['away_team_name'], "projections/", file_name, home_color1, 
        away_color1, home_color2, away_color2
        )
    lineup_pred_text = f'{lineup_favorite} by {round(abs(future_game["lineup_spread"] + home_advantage ), 1)}'
    n_lineup_pred_text = f'{n_lineup_favorite} by {round(abs(future_game["lineup_spread"]), 1)} on a neutral field'

    make_matchpage(
        file_name,
        "projections",
        main_header, 
        match_date,
        club_prediction,
        club_victor,
        club_margin,
        perf_plot_path = perf_plot_path,
        spread_plot_path = spread_plot_path,
        resultbar_path = resultbar_path,
        pred_text = None,
        n_pred_text = None,
        lineup_pred_text = lineup_pred_text,
        n_lineup_pred_text = n_lineup_pred_text,
        categories_list = ["projection"],
        player_table = player_table,
        score_path = None,
        prob_path = None
    )

    match_dir_strings.append(f'[{future_game["date"].date().strftime("%Y-%m-%d")} {club_header}](projections//{file_name})')
    match_comps.append(future_game['competition'])
    match_levels.append(future_game['comp_level'])
    match_dates.append(future_game["date"])
    future_names.append(pretty_name)


print("FUTURE MATCHES - NO LINEUPS")
all_fut_matches = glob.glob(os.path.join("../Rugby_ELO/future_matches", "*.psv"))
## This needs cleaned up
# int(all_fut_matches[0].split("_")[-1].split(".")[0])
all_fut_matches = [x for x in all_fut_matches if int(x.split("_")[-1].split(".")[0]) > 2020]

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
        print(pretty_name)

        if (row['Home Team'] in clubbase.keys()) & (row['Away Team'] in clubbase.keys()):
            # team colors
            home_color1, home_color2, away_color1, away_color2 = get_team_colors(row['Home Team'], row['Away Team'])

            # Club Level Info
            home_club = clubbase[row['Home Team']]
            away_club = clubbase[row['Away Team']]
            expectation, expectations, spreads, home_sims, away_sims = home_club.predict(away_club, home=True, n_sims=1000)
            club_spread = spreads.mean()
            club_prediction = np.round(expectation, 3)
            club_victor = row['Home Team'] if club_prediction >= 0.5 else row['Away Team']
            club_margin = np.round(club_spread, 1) if club_prediction >= 0.5 else np.round(club_spread, 1) * -1
            club_header = f'{row["Away Team"]} (~{round(away_sims.mean(), 2)}) at {row["Home Team"]} (~{round(home_sims.mean(), 2)})'

            perf_plot, spread_plot, resultbar_plot = glicko_club_plots(
                home_sims, away_sims, row['Home Team'], 
                row['Away Team'], "projections/", file_name, home_color1, 
                away_color1, home_color2, away_color2
                )

            # Player Ranks
            ## Use current player elos, but historic team + minutes
            home_team = teamlist[row['Home Team']]
            away_team = teamlist[row['Away Team']]

            home_team_elos = [
                team_elo_minutes(matchlist[x['Match_Name']].home_team, playerbase) 
                if matchlist[x['Match_Name']].home_team_name == row['Home Team'] 
                else team_elo_minutes(matchlist[x['Match_Name']].away_team, playerbase)
                for x in home_team.history[-5:]
                ]
            away_team_elos = [
                team_elo_minutes(matchlist[x['Match_Name']].home_team, playerbase) 
                if matchlist[x['Match_Name']].home_team_name == row['Away Team'] 
                else team_elo_minutes(matchlist[x['Match_Name']].away_team, playerbase)
                for x in away_team.history[-5:]
                ]

            #home_team_elos = [x['elo'] for x in home_team.history[-5:]]
            #away_team_elos = [x['elo'] for x in away_team.history[-5:]]
            historic_weighting = [0.1, 0.15, 0.2, 0.25, 0.3]
            if len(home_team_elos) == 5:
                home_elo_avg = sum(np.multiply(home_team_elos, historic_weighting))
            else:
                home_elo_avg = np.mean(home_team_elos)

            if len(away_team_elos) == 5:
                away_elo_avg = sum(np.multiply(away_team_elos, historic_weighting))
            else:
                away_elo_avg = np.mean(away_team_elos)

            imputed_spread =  (home_elo_avg -  away_elo_avg) / 10 #GLOBAL_score_factor == 10, this should not be hard-coded
            main_header = f'{row["Away Team"]} (~{round(away_elo_avg, 2)}) at {row["Home Team"]} (~{round(home_elo_avg, 2)})'

            favorite = row["Home Team"] if imputed_spread + home_advantage > 0 else row["Away Team"]
            pred_text = f'{favorite} by {round(abs(imputed_spread + home_advantage), 1)}'

            n_favorite = row["Home Team"] if imputed_spread > 0 else row["Away Team"]
            n_pred_text = f'{n_favorite} by {round(abs(imputed_spread), 1)} on a neutral pitch'

            make_matchpage(
                file_name,
                "projections",
                pretty_name,
                match_date,
                club_prediction,
                club_victor,
                club_margin,
                perf_plot_path = perf_plot,
                spread_plot_path = spread_plot,
                resultbar_path =  resultbar_plot,
                pred_text = None,
                n_pred_text = None,
                lineup_pred_text = pred_text,
                n_lineup_pred_text = n_pred_text,
                categories_list = ["projection", "imputed"],
                player_table = None,
                score_path = None,
                prob_path = None
            )

            match_dir_strings.append(f'[{match_date} {club_header}](projections//{file_name})')
            match_comps.append(row['Competition'])
            match_levels.append(row['comp_level'])
            match_dates.append(match_date)
    
        else:
            match_dir_strings.append(f'{match_date} {pretty_name}')
            match_comps.append(row['Competition'])
            match_levels.append(row['comp_level'])
            match_dates.append(match_date)



dir_df = pd.DataFrame({'links':match_dir_strings, 'comps':match_comps, 'levels':match_levels, 'dates':match_dates})
fill_matches(dir_df, fut_dir_md)
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