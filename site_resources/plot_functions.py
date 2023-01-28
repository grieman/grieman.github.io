import plotly.graph_objects as go
import matplotlib.pyplot as plt
#import seaborn as sns
import matplotlib.patheffects as pe
import numpy as np
import datetime
import pandas as pd
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
import seaborn as sns

#sns.set_style("darkgrid")

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

def score_plot(match_events, file_name, recent_game, home_color1, away_color1, home_color2, away_color2):

    plt.plot(match_events.Time, match_events['Home Points'], color=home_color1, lw=3, path_effects=[pe.Stroke(linewidth=5, foreground=home_color2), pe.Normal()])
    plt.plot(match_events.Time, match_events['Away Points'], color=away_color1, lw=3, path_effects=[pe.Stroke(linewidth=5, foreground=away_color2), pe.Normal()])
    plt.legend(labels=[recent_game['home_team_name'],recent_game['away_team_name']])
    plt.ylabel('Score')
    plt.xlabel('Minute')

    plt.savefig(f"reviews/recap_scores_{file_name}.png")
    plt.close()
    return f'recap_scores_{file_name}.png'

def prob_plot(match_events, file_name, home_color1, away_color1, home_color2, away_color2):

    ## Mask when the condition is met
    home_pred = np.ma.masked_where(match_events.prediction < 0.5, match_events.prediction)
    away_pred = np.ma.masked_where(match_events.prediction >= 0.5,  match_events.prediction)
    fig, ax = plt.subplots()
    if match_events.prediction[0] >= 0.5:
        ax.plot(match_events.Time, match_events.prediction, color=home_color1, lw=3, path_effects=[pe.Stroke(linewidth=5, foreground=home_color2), pe.Normal()])
    else:
        ax.plot(match_events.Time, match_events.prediction, color=away_color1, lw=3, path_effects=[pe.Stroke(linewidth=5, foreground=away_color2), pe.Normal()])

    ax.plot(match_events.Time, home_pred, color=home_color1, lw=3, path_effects=[pe.Stroke(linewidth=5, foreground=home_color2), pe.Normal()])
    ax.plot(match_events.Time, away_pred, color=away_color1, lw=3, path_effects=[pe.Stroke(linewidth=5, foreground=away_color2), pe.Normal()])
    plt.ylabel('Home Team Win Probability')
    plt.xlabel('Minute')

    plt.savefig(f"reviews/recap_prob_{file_name}.png")
    plt.close()
    return f'recap_prob_{file_name}.png'

def player_history_plot(player_df, percentile_df):
    fig, ax = plt.subplots()
    playername = player_df.Full_Name.iloc[0]
    player_df['play_position'] = np.where(player_df.Position == 'R', np.nan, player_df.Position)
    player_df['play_position'] = player_df['play_position'].fillna(method = 'bfill')
    player_df['play_position'] = player_df['play_position'].fillna(method = 'ffill')

    player_df = player_df.merge(percentile_df, how='left', left_on = ['play_position','year','month'], right_on = ['Position','year','month'])
    
    ax.plot(player_df.Date, player_df.elo_mean, color = 'white')
    ax.plot(player_df.Date, player_df.Percentile_50, color = 'grey')
    ax.fill_between(player_df.Date, player_df.Percentile_5, player_df.Percentile_95, alpha=0.2, color = 'grey')
    ax.fill_between(player_df.Date, player_df.Percentile_10, player_df.Percentile_90, alpha=0.2, color = 'grey')
    ax.fill_between(player_df.Date, player_df.Percentile_25, player_df.Percentile_75, alpha=0.2, color = 'grey')

    for _, sub1 in player_df.groupby('Team'):
        for _, team_subset in sub1.groupby(sub1.Competition):
            ax.scatter(team_subset.Date, team_subset.end_elo,c = team_subset.Primary, edgecolors=team_subset.Secondary)
    plt.title(f'{playername}: elo History')
    ax.set_ylabel('elo score')

    # Creating legend with color box
    Interval50 = mpatches.Patch(color='grey', label='50% elo Interval', alpha = 0.6)
    Interval80 = mpatches.Patch(color='grey', label='80% elo Interval', alpha = 0.4)
    Interval95 = mpatches.Patch(color='grey', label='95% elo Interval', alpha = 0.2)
    point = mlines.Line2D([0], [0], marker='o', color='w', label='Post Match elo',
                      markerfacecolor='black', markersize=10, ls = '')
    plt.legend(handles=[Interval50, Interval80, Interval95, point])
    #plt.savefig(f"playerfiles/history_{playername.replace(' ','')}.png")
    plt.savefig(f"playerfiles/history_{playername.replace(' ','')}.png")
    plt.close()
    return f"history_{playername.replace(' ','')}.png"

def glicko_club_plots(home_sims, away_sims, home_team_name, away_team_name, file_loc, file_name, home_color1, away_color1, home_color2, away_color2, point_diff = None):
    fig, ax = plt.subplots()
    sns.kdeplot(data=home_sims, ax=ax, color=home_color1, fill=True)#, label=f'{home_team_name} Simulated Performances')
    sns.kdeplot(data=home_sims, ax=ax, color=home_color2, fill=False)#, label=f'{home_team_name} Simulated Performances')
    sns.kdeplot(data=away_sims, ax=ax, color=away_color1, fill=True)#, label=f'{away_team_name} Simulated Performances')
    sns.kdeplot(data=away_sims, ax=ax, color=away_color2, fill=False)#, label=f'{away_team_name} Simulated Performances')
    legend_elements = [
        mpatches.Patch(edgecolor=away_color2, facecolor=away_color1, label=f'{away_team_name} Simulated Performances', alpha=0.5),
        mpatches.Patch(edgecolor=home_color2, facecolor=home_color1, label=f'{home_team_name} Simulated Performances', alpha=0.5)
    ]
    if point_diff:
        performance_diff = point_diff * 20
        '''if home_sims.mean() > away_sims.mean():
            high_mean = home_sims.mean()
            low_mean = away_sims.mean()
            high_std = home_sims.std()
            low_std = away_sims.std()
            high_color = home_color2
            low_color = away_color2
        else:
            high_mean = away_sims.mean()
            low_mean = home_sims.mean()
            high_std = away_sims.std()
            low_std = home_sims.std()
            high_color = away_color2
            low_color = home_color2'''
        
        y_height = np.max(ax.get_ylim()) * 0.2
        rating_diff = home_sims.mean() - away_sims.mean()
        perf_home = home_sims.mean() + ((performance_diff - rating_diff) * (home_sims.std() / (home_sims.std() + away_sims.std())))
        perf_away = away_sims.mean() - ((performance_diff - rating_diff) * (away_sims.std() / (away_sims.std() + away_sims.std())))

        '''rating_diff = high_mean - low_mean
        #axis_midpoint = np.mean(ax.get_xlim())
        y_height = np.max(ax.get_ylim()) * 0.2
        diff_low = low_mean - ((performance_diff - rating_diff) * (low_std / (low_std + high_std)))
        diff_high = high_mean + ((performance_diff - rating_diff) * (high_std / (low_std + high_std)))'''
          
        plt.plot([perf_home, perf_home], [0, y_height], color = home_color2)
        plt.plot([perf_away, perf_away], [0, y_height], color = away_color2)
        plt.plot([perf_home, perf_away], [y_height/2, y_height/2], color = "black")
        plt.text(x=(perf_home + perf_away)/2, y=y_height/1.9, s="Observed Performance Gap", ha='center')

    ax.legend(handles = legend_elements)
    sns.move_legend(ax, "lower center", bbox_to_anchor=(.5, 1), ncol=3, title=None, frameon=False)
    #plt.show()
    plt.tight_layout()
    plt.savefig(f"{file_loc}_performances_{file_name}.png")
    plt.close()

    fig, ax = plt.subplots()
    spreads = (home_sims - away_sims) / 20
    spread_df = pd.DataFrame({'spread': np.round(spreads, 0).astype(int)})
    spread_df['result_numeric'] = ((np.sign(spread_df.spread) + 1) / 2)
    spread_df['result'] = spread_df['result_numeric'].map({1:f'{home_team_name} Victory', 0:f'{away_team_name} Victory', 0.5:'Tie'})
    spread_df['hue1'] = spread_df['result_numeric'].map({1:home_color1, 0:away_color1, 0.5:'silver'})
    spread_df['hue2'] = spread_df['result_numeric'].map({1:home_color2, 0:away_color2, 0.5:'black'})
    spread_df = spread_df.sort_values('result_numeric')
    wins = spread_df[spread_df.result_numeric == 1]
    losses = spread_df[spread_df.result_numeric == 0]
    ties = spread_df[spread_df.result_numeric == 0.5]
    sns.histplot(wins, ax=ax, x='spread', discrete=True, color = home_color1, edgecolor=home_color2)
    sns.histplot(losses, ax=ax, x='spread', discrete=True, color = away_color1, edgecolor=away_color2)
    sns.histplot(ties, ax=ax, x='spread', discrete=True, color = 'silver', edgecolor='black')
    legend_elements = [
        mpatches.Patch(edgecolor=away_color2, facecolor=away_color1, label=f'{away_team_name} Victories', alpha=0.5),
        mpatches.Patch(edgecolor=home_color2, facecolor=home_color1, label=f'{home_team_name} Victories', alpha=0.5),
        mpatches.Patch(facecolor='silver', label='Ties', alpha=0.5)
    ]
    if point_diff:
        actual = spread_df[spread_df.spread == int(point_diff)]
        if actual.shape[0] == 0:
            actual = spread_df[np.sign(spread_df.spread) == np.sign(int(point_diff))][0:1]
            actual.spread = int(point_diff)
        if actual.shape[0] != 0:
            sns.histplot(actual, ax=ax, x='spread', discrete=True, hatch='x', color = actual.hue1.iloc[0], edgecolor=actual.hue2.iloc[0])
            legend_elements.append(mpatches.Patch(hatch='x', facecolor = actual.hue1.iloc[0], edgecolor=actual.hue2.iloc[0], label='Observed Point Difference', alpha=0.75))
        else:
            plt.plot([int(point_diff), int(point_diff)], [0, 10], color = "black")
            legend_elements.append(mlines.Line2D([0], [0], color="black", lw=2))

    ax.legend(handles = legend_elements)
    sns.move_legend(ax, "lower center", bbox_to_anchor=(.5, 1), ncol=3, title=None, frameon=False)
    plt.savefig(f"{file_loc}_spreads_{file_name}.png")
    plt.close()

    return f"{file_loc}_performances_{file_name}.png".split("/")[1], f"{file_loc}_spreads_{file_name}.png".split("/")[1]