import plotly.graph_objects as go
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.patheffects as pe


sns.set_style("darkgrid")

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

    plt.savefig(f"reviews/recap_scores_{file_name}.png")
    plt.clf()
    return f'recap_scores_{file_name}.png'

def prob_plot(match_events, file_name):
    prob_plot = sns.lineplot(x = 'Time', y = 'prediction', data = match_events)
    prob_plot.figure.savefig(f"reviews/recap_prob_{file_name}.png")
    prob_plot.figure.clf()
    return f'recap_prob_{file_name}.png'