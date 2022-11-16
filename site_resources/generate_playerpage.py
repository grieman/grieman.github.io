## IMPORTS
import sys
import yaml
with open('secrets.yml', 'r') as file:
    secrets = yaml.safe_load(file)
sys.path.append(secrets['elo_proj_path'])

from player_club_classes import team_elo, Player, Club, Match
import pandas as pd
import numpy as np
from mdutils.mdutils import MdUtils
from mdutils import Html
from support_files.team_colors import team_color_dict
from plot_functions import *
import os
import glob
import datetime
import pickle
from IPython.display import display
from tabulate import tabulate

pd.options.display.max_columns = None

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

def main(named_players):
    ## Load in + prep data
    team_colors = pd.DataFrame(team_color_dict).T
    team_colors.columns = ['Primary', 'Secondary']
    team_colors = team_colors.rename_axis('Team').reset_index()

    with open('../Rugby_ELO/processed_data/playerbase.pickle', 'rb') as handle:
        playerbase = pickle.load(handle)
    with open('../Rugby_ELO/processed_data/matchlist.pickle', 'rb') as handle:
        matchlist = pickle.load(handle)
    with open('../Rugby_ELO/processed_data/teamlist.pickle', 'rb') as handle:
        teamlist = pickle.load(handle)

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

    player_elo['week_num'] = player_elo['Date'].dt.isocalendar().week
    player_elo['month'] = player_elo['Date'].dt.month
    player_elo['year'] = player_elo['Date'].dt.year

    player_elo.loc[player_elo.Position == 'BR', 'Position'] = 'N8'

    starters = player_elo[player_elo.Position != 'R']
    starters = starters.dropna(subset=['Position'])

    starters = player_elo[player_elo.Position != 'R']
    starters = starters.dropna(subset=['Position'])
    last_date_of_months = player_elo.groupby(pd.Grouper(key="Date", freq='M')).Date.max()
    percentile_list = []

    for date in last_date_of_months:
        current_players = starters[starters.Date < date]
        current_players = current_players[current_players.Date >= date - datetime.timedelta(days=365)]
        current_players = current_players[current_players.groupby(['Full Name'])['Date'].transform(max) == current_players['Date']].copy()
        percentile_df = current_players.groupby('Position')['end_elo'].quantile([0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]).reset_index()
        percentile_df.columns = ['Position', 'Percentile', 'elo']
        percentile_df = percentile_df.pivot(index = 'Position', columns = 'Percentile')
        percentile_df.columns = ["Percentile_" + str(int(x*100)) for x in percentile_df.columns.droplevel()]
        percentile_df = percentile_df.reset_index()
        percentile_df['year'] = date.year
        percentile_df['month'] = date.month

        mean_df = current_players.groupby('Position')['end_elo'].mean().reset_index()
        mean_df.columns = ['Position', 'elo_mean']
        percentile_df = percentile_df.merge(mean_df)

        percentile_list.append(percentile_df)
        
    percentile_df = pd.concat(percentile_list)
    percentile_df['dates'] = pd.to_datetime(percentile_df['year'].astype(int).astype(str)  + percentile_df['month'].astype(int).astype(str).str.pad(2, fillchar = '0'), format='%Y%m')

    ## Data loaded
    for player in named_players:
        # Takeshi Hino
        playerid = player_elo[player_elo['Full Name'] == player].Unicode_ID.iloc[0]
        player_df = player_elo[player_elo.Unicode_ID == playerid].copy()
        player_df['opponent'] = np.where(player_df.Team == player_df['Home Team'], player_df['Away Team'], player_df['Home Team'])
        player_df['win'] = np.where(
            (player_df['Home Score'] > player_df['Away Score']) & (player_df.Team == player_df['Home Team']) | 
            (player_df['Home Score'] < player_df['Away Score']) & (player_df.Team == player_df['Away Team']), 1, 0)
        player_df.loc[player_df['Home Score'] == player_df['Away Score'], 'win'] = 0.5

        name = player_df.Full_Name.iloc[0]
        print(name)
        current_elo = player_df.end_elo.iloc[-1]
        try:
            current_percentile = player_df.merge(make_current_percentile(starters, player_df.Date.iloc[-1])).percentile[0]
        except:
            current_percentile = None
        
        positions = player_df[player_df.Position != 'R'].Position.value_counts(normalize=True).loc[lambda x : x > 0.1].keys().tolist()[0:2]
        #player_history_plot(player_df, percentile_df)
        by_team = player_df.groupby('Team').win.agg(['count', 'mean']).reset_index().sort_values('count', ascending=False)
        by_opponent = player_df.groupby('opponent').win.agg(['count', 'mean']).reset_index().sort_values('count', ascending=False).head()

        playerpage = MdUtils(file_name=f'temp//{name.replace(" ", "")}_page')

        # yaml header
        playerpage.new_line("HEADERSTART")
        playerpage.new_line("---")
        playerpage.new_line("layout: page")
        playerpage.new_line(f"title: {name}")
        playerpage.new_line(f"date: {datetime.datetime.now()}")
        playerpage.new_line("categories: player")
        playerpage.new_line("---")

        playerpage.new_header(level = 1, title = name)
        playerpage.new_header(level = 2, title = f"Positions: {', '.join([x for x in positions])}")
        if 'Pro' in player_df.comp_level.unique():
            playerpage.new_header(level = 2, title = f"Club: {player_df[player_df.comp_level.str.contains('Pro')].sort_values('Date').iloc[-1].Team}")
        if 'International' in player_df.comp_level.unique():
            playerpage.new_header(level = 2, title = f"Country: {player_df[player_df.comp_level == 'International'].sort_values('Date').iloc[-1].Team}")

        playerpage.new_header(level = 2, title = f"Current elo: {np.round(current_elo)}")
        playerpage.new_header(level = 2, title = f"Current Percentile: {current_percentile}")

        if list(player_df.Position.unique()) != ['R']:
            playerpage.new_header(level=1, title = "Elo History")
            plot_path = player_history_plot(player_df, percentile_df)
            playerpage.new_paragraph(f"![elo history]({plot_path})")



        playerpage.new_header(level=1, title = "Match History")
        team_info = player_df.groupby('Team').win.agg(['count', 'mean']).reset_index().sort_values('count', ascending=False)
        opponent_info = player_df.groupby('opponent').win.agg(['count', 'mean']).reset_index().sort_values('count', ascending=False)
        team_info.columns = ["Team", "Appearances", 'Win Rate']
        opponent_info.columns = ["Opponent", "Matches", 'Win Rate']
        team_table = tabulate(team_info, tablefmt="pipe", headers="keys", showindex=False)
        opponent_table = tabulate(opponent_info, tablefmt="pipe", headers="keys", showindex=False)
        playerpage.new_paragraph(team_table)
        playerpage.new_paragraph(opponent_table)

        playerpage.create_md_file()
        clean_leading_space(
            f'temp//{name.replace(" ", "")}_page.md', 
            f'playerfiles//{name.replace(" ", "")}_cleaned.md'
            )

if __name__ == "__main__":
    main(
        named_players=['Maro Itoje']
        )