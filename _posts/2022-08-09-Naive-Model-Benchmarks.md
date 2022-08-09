---
layout: post
title:  "Naive Model Benchmarks"
date:   2022-08-09 18:00:00 -0500
categories: model update
---

The first naive model that was tried was very simple: in every game, the home team was predicted to win, with a likelihood of 1, by a score 5 points (the home advantage). This gave us a rough idea of how our elo scores predicted match results, but is likely not the best benchmark to we can likely achieve better accuracy metrics with some simple changes. First, the home advantage of 5 was somewhat arbitrary, and selecting the average margin of victory may achieve a better RMSE. And second, setting the likelihood of victory for each home team to 1 may cause the Brier score to be higher than if we used a prediction like 0.75. There is naturally some correlation between the spread and likelihood to win, but to avoid calculating that now our naive model can have one best binary prediction that minimizes the Brier score and one independent margin of victory that minimizes RMSE. A sweep of possible predictions and margins produce these plots:

![Brier by Prediction](/docs/assets/brier_by_spread.png)
![Spread by Margin](/docs/assets/rmse_by_margin.png)


From these sweeps, our best prediction is 0.63 that gives a Brier score of 0.2322, and the best spread is 1.1 that gives a RMSE of 18.636.


| Model | Brier Score | RMSE|
|-----|------|-----|
|Best Naive Models| 0.2322 | 18.636 |
|elo | 0.23052 | 11.68 |

Good news her, our basic elo model still performs better.