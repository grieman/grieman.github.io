## IMPORTS
import sys
import yaml
with open('secrets.yml', 'r') as file:
    secrets = yaml.safe_load(file)
sys.path.append(secrets['elo_proj_path'])

import pickle
from player_club_classes import team_elo, Player, Club, Match
import pandas as pd
import numpy as np
from mdutils.mdutils import MdUtils
from mdutils import Html
from tabulate import tabulate
from sklearn import metrics
from support_files.comp_funcs import sim_remaining
from support_files.team_colors import team_color_dict
from support_files.plot_functions import *

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

def main():

    md_file = MdUtils(file_name=f'temp//World_Cup_2023')
    # yaml header
    md_file.new_line("HEADERSTART")
    md_file.new_line("---")
    md_file.new_line("layout: page")
    md_file.new_line(f'title: World Cup 2023 Projections')
    md_file.new_line(f'date: ')
    md_file.new_line("categories: projection")
    md_file.new_line("---")

    poola = [
        'New Zealand',
        'France',
        'Italy',
        'Uruguay',
        'Namibia'
    ]
    poolb = [
        'South Africa',
        'Ireland',
        'Scotland',
        'Tonga',
        'Romania'
    ]
    poolc = [
        'Wales',
        'Australia',
        'Fiji',
        'Georgia',
        'Portugal'
    ]
    poold = [
        'England',
        'Japan',
        'Argentina',
        'Samoa',
        'Chile'
    ]

    team_colors = pd.DataFrame(team_color_dict).T
    team_colors.columns = ['Primary', 'Secondary']
    team_colors = team_colors.rename_axis('Team').reset_index()

    with open('../Rugby_ELO/processed_data/clubbase.pickle', 'rb') as handle:
        clubbase = pickle.load(handle)

    fut_matches_df = pd.read_csv("../Rugby_ELO/future_matches/worldcup_2023.psv", sep="|")
    fut_matches_df.Date = pd.to_datetime(fut_matches_df.Date)
    fut_matches_df['neutral'] = np.where(fut_matches_df['Home Team'] == 'France', 0, 1)

    conditions  = [
        fut_matches_df['Home Team'].isin(poola), 
        fut_matches_df['Home Team'].isin(poolb), 
        fut_matches_df['Home Team'].isin(poolc), 
        fut_matches_df['Home Team'].isin(poold)
        ]
    choices = ['PoolA', 'PoolB', 'PoolC', 'PoolD']
    fut_matches_df['matchname'] = np.select(conditions, choices, default=np.nan)

    sim_df, playoff_df, _ = sim_remaining('worldcup_2023', 1000, fut_matches_df, clubbase)
    sim_df['Pool'] = sim_df.Competition.str.split(" ").str[0]


    md_file.new_header(level = 1, title=f'Pool Predictions')
    for pool in choices:
        pool_subset = fut_matches_df[fut_matches_df.matchname == pool].copy()
        md_file.new_header(level = 2, title=f'{pool[0:4]} {pool[-1]}')

        for _, row in pool_subset.iterrows():
            matchname = row["Home Team"] + " V " + row["Away Team"] + " on " + row["Date"].strftime('%Y/%m/%d')
            one_match = sim_df[(sim_df.Club == row['Home Team']) & (sim_df.Opponent == row['Away Team'])].copy()
            one_match['Home_Rtng'] = one_match.Competition.str.split(" ").str[1].str.split("-").str[-1].astype(float)
            one_match['Away_Rtng'] = one_match.Competition.str.split(" ").str[-1].str.split("-").str[-1].astype(float)

            performance_path, spread_path, resultbar_path = glicko_club_plots(
                one_match['Home_Rtng'], 
                one_match['Away_Rtng'], 
                one_match['Club'].iloc[0], 
                one_match['Opponent'].iloc[0], 
                "wc_files/", 
                f"{one_match['Club'].iloc[0]}_V_{one_match['Opponent'].iloc[0]}_{pool}", 
                team_colors[team_colors.Team == one_match['Club'].iloc[0]].Primary.iloc[0], 
                team_colors[team_colors.Team == one_match['Opponent'].iloc[0]].Primary.iloc[0], 
                team_colors[team_colors.Team == one_match['Club'].iloc[0]].Secondary.iloc[0], 
                team_colors[team_colors.Team == one_match['Opponent'].iloc[0]].Secondary.iloc[0], 
                point_diff = None)

            average_line = np.round(one_match.Point_Diff.mean(), 1)
            winner = row["Home Team"] if average_line > 0 else row['Away Team']
            average_line_txt = f"{winner} by {abs(average_line)}"

            md_file.new_header(level = 3, title = matchname)
            md_file.new_paragraph(f"Average Margin: {average_line_txt}")
            md_file.new_paragraph(f'<p float="left">\n<img src="{performance_path}" width="32%" />\n<img src="{resultbar_path}" width="32%" />\n<img src="{spread_path}" width="32%" />\n</p>\n')


    md_file.create_md_file()


    clean_leading_space(f'temp//World_Cup_2023.md', f'wc_files//World_Cup_2023.md')
