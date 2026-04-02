from ..constants import _MAI_VERSION_MAP
from ..storage import MaiSongORM
from ..score import PlayerMaiB50, PlayerMaiScore


def calc_dx_rating(level_value: float, ach: float) -> int:
    coefficient = 0.0
    if ach >= 100.5:
        coefficient = 0.224
    elif ach >= 100.0:
        coefficient = 0.216 + (ach - 100.0) * 0.016
    elif ach >= 99.5:
        coefficient = 0.211 + (ach - 99.5) * 0.01
    elif ach >= 99.0:
        coefficient = 0.208 + (ach - 99.0) * 0.006
    elif ach >= 98.0:
        coefficient = 0.203 + (ach - 98.0) * 0.005
    elif ach >= 97.0:
        coefficient = 0.2 + (ach - 97.0) * 0.003
    elif ach >= 94.0:
        coefficient = 0.168 + (ach - 94.0) * 0.008 / 3
    elif ach >= 90.0:
        coefficient = 0.152 + (ach - 90.0) * 0.004
    elif ach >= 80.0:
        coefficient = 0.136 + (ach - 80.0) * 0.0016
    elif ach >= 75.0:
        coefficient = 0.120 + (ach - 75.0) * 0.0032
    elif ach >= 70.0:
        coefficient = 0.112 + (ach - 70.0) * 0.0016
    elif ach >= 60.0:
        coefficient = 0.096 + (ach - 60.0) * 0.0016
    elif ach >= 50.0:
        coefficient = 0.08 + (ach - 50.0) * 0.0016
    elif ach >= 40.0:
        coefficient = 0.064 + (ach - 40.0) * 0.0016
    elif ach >= 30.0:
        coefficient = 0.048 + (ach - 30.0) * 0.0016
    elif ach >= 20.0:
        coefficient = 0.032 + (ach - 20.0) * 0.0016
    elif ach >= 10.0:
        coefficient = 0.016 + (ach - 10.0) * 0.0016
    else:
        coefficient = 0.0
    return round(level_value * coefficient * ach)


def get_players_n50(scores: list[PlayerMaiScore]) -> PlayerMaiB50:
    """
    获得玩家的拟合50
    """
    current_version = list(_MAI_VERSION_MAP.keys())[-1]
    previous_version_scores: list[PlayerMaiScore] = []
    current_version_scores: list[PlayerMaiScore] = []

    for score in scores:
        song = MaiSongORM.get_song_sync(score.song_id)
        song_type = score.song_type.value
        song_diff_value = score.song_difficulty.value

        if song is None or song_type == "utage":
            continue

        song_diff = (
            song.difficulties.dx[song_diff_value] if song_type == "dx" else song.difficulties.standard[song_diff_value]
        )
        score.song_level_value = song_diff.level_fit
        score.dx_rating = calc_dx_rating(score.song_level_value, score.achievements)

        if song.version / 100 >= current_version:
            current_version_scores.append(score)
        else:
            previous_version_scores.append(score)

    previous_version_scores.sort(key=lambda x: x.dx_rating, reverse=True)
    current_version_scores.sort(key=lambda x: x.dx_rating, reverse=True)

    return PlayerMaiB50(previous_version_scores[:35], current_version_scores[:15])
