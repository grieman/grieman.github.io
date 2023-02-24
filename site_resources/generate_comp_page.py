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
from support_files.comp_funcs import *
from support_files.team_colors import team_color_dict

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

def make_comp_page(comp):

    team_colors = pd.DataFrame(team_color_dict).T
    team_colors.columns = ['Primary', 'Secondary']
    team_colors = team_colors.rename_axis('Team').reset_index()

    match_df, club_histories, clubbase = get_comp_history(comp)
    fut_matches_df = get_fut_comp_matches(comp)
    sim_df, playoff_df = sim_remaining(comp, n_sims=1000, fut_matches_df=fut_matches_df, clubbase=clubbase)

    md_file = MdUtils(file_name=f'temp//{comp.replace(" ", "_")}')
    # yaml header
    md_file.new_line("HEADERSTART")
    md_file.new_line("---")
    md_file.new_line("layout: page")
    md_file.new_line(f'title: {comp[-5:]} Status')
    md_file.new_line(f'date: ')
    md_file.new_line("categories: model review projection")
    md_file.new_line("---")

    md_file.new_header(level = 1, title = f"{comp[-5:]} Status")
    md_file.new_header(level=1, title = "Completed Match Review")

    club_histories['name'] = club_histories['Club'] + " V " + club_histories['Opponent'] + " on "+ club_histories['Date'].dt.strftime('%Y/%m/%d')
    club_histories['point_diff'] = club_histories.Point_Diff
    pred_df = np.round(match_df[['name', 'point_diff', 'adv_lineup_spread', 'adv_spread']].merge(club_histories[['name', 'point_diff', 'Predicted_Spread']], how='outer'), 1)
    pred_df.columns = ['Match', 'Result', 'Lineup Prediction', 'Minutes Prediction', 'Club Prediction']

    lineup_pred_df = pred_df[~pred_df['Lineup Prediction'].isna()]
    minutes_pred_df = pred_df[~pred_df['Minutes Prediction'].isna()]
    club_pred_df = pred_df[~pred_df['Club Prediction'].isna()]
    lineup_binary_acc = np.round(100 * np.mean((lineup_pred_df['Result'] * lineup_pred_df['Lineup Prediction']) > 0), 1)
    minutes_binary_acc = np.round(100 * np.mean((minutes_pred_df['Result'] * minutes_pred_df['Minutes Prediction']) > 0), 1)
    club_binary_acc = np.round(100 * np.mean((club_pred_df['Result'] * club_pred_df['Club Prediction']) > 0), 1)
    lineup_margin_error = np.round(metrics.mean_absolute_error(lineup_pred_df['Result'], lineup_pred_df['Lineup Prediction']), 1)
    minutes_margin_error = np.round(metrics.mean_absolute_error(minutes_pred_df['Result'], minutes_pred_df['Minutes Prediction']), 1)
    club_margin_error = np.round(metrics.mean_absolute_error(club_pred_df['Result'], club_pred_df['Club Prediction']), 1)

    pred_table = tabulate(pred_df, tablefmt="pipe", headers="keys", showindex=False)
    pred_table = pred_table +\
        "\n|" +\
        f"\n| Average Error |       - | {lineup_margin_error} | {minutes_margin_error} | {club_margin_error} |" +\
        f"\n| Correct Winner |       - | {lineup_binary_acc}% | {minutes_binary_acc}% | {club_binary_acc}% |"

    md_file.new_paragraph(pred_table)

    md_file.new_header(level = 2, title = "Future Club-Level Match Predictions")

    all_weeks = pd.concat([club_histories.Date.dt.isocalendar().week.astype(int), fut_matches_df.Date.dt.isocalendar().week.astype(int)]).drop_duplicates()
    week_mapping = {x: y for x, y in zip(all_weeks, all_weeks.rank().astype(int))}

    fut_matches_df['weeknum'] = fut_matches_df.Date.dt.isocalendar().week.astype(int).map(week_mapping)

    for week in fut_matches_df.weeknum.unique():
        week_subset = fut_matches_df[fut_matches_df.weeknum == week].copy()
        md_file.new_header(level = 3, title=f'Week {week.astype(int)}')

        for _, row in week_subset.iterrows():
            matchname = row["Home Team"] + " V " + row["Away Team"] + " on " + row["Date"].strftime('%Y/%m/%d')
            one_match = sim_df[(sim_df.Club == row['Home Team']) & (sim_df.Opponent == row['Away Team'])].copy()
            one_match['Home_Rtng'] = one_match.Competition.str.split(" ").str[1].astype(float)
            one_match['Away_Rtng'] = one_match.Competition.str.split(" ").str[-1].astype(float)

            performce_path, spread_path, resultbar_path = glicko_club_plots(
                one_match['Home_Rtng'], 
                one_match['Away_Rtng'], 
                one_match['Club'].iloc[0], 
                one_match['Opponent'].iloc[0], 
                "comp_files/", 
                f"{one_match['Club'].iloc[0]}_V_{one_match['Opponent'].iloc[0]}_{week}", 
                team_colors[team_colors.Team == one_match['Club'].iloc[0]].Primary.iloc[0], 
                team_colors[team_colors.Team == one_match['Opponent'].iloc[0]].Primary.iloc[0], 
                team_colors[team_colors.Team == one_match['Club'].iloc[0]].Secondary.iloc[0], 
                team_colors[team_colors.Team == one_match['Opponent'].iloc[0]].Secondary.iloc[0], 
                point_diff = None)

            average_line = np.round(one_match.Point_Diff.mean(), 1)
            winner = row["Home Team"] if average_line > 0 else row['Away Team']
            average_line_txt = f"{winner} by {abs(average_line)}"

            md_file.new_header(level = 4, title = matchname)
            md_file.new_paragraph(f"Average Margin: {average_line_txt}")
            md_file.new_paragraph(f'<p float="left">\n<img src="{performce_path}" width="32%" />\n<img src="{resultbar_path}" width="32%" />\n<img src="{spread_path}" width="32%" />\n</p>\n')


    md_file.create_md_file()

    clean_leading_space(f'temp//{comp.replace(" ", "_")}.md', f'comp_files//{comp.replace(" ", "_")}.md')
