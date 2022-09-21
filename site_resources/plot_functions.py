import plotly.graph_objects as go
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.patheffects as pe
import numpy as np


sns.set_style("darkgrid")

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
    plt.clf()
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
    plt.clf()
    return f'recap_prob_{file_name}.png'