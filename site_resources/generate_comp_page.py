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
from support_files.team_colors import team_color_dict



with open('../Rugby_ELO/processed_data/matchlist.pickle', 'rb') as handle:
    matchlist = pickle.load(handle)
with open('../Rugby_ELO/processed_data/clubbase.pickle', 'rb') as handle:
    clubbase = pickle.load(handle)

comp = "United Rugby Championship 2022"