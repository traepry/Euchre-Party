import math
import random
import html
from itertools import combinations

import streamlit as st

st.set_page_config(page_title="Euchre Tournament Scheduler", layout="wide")

# =========================================================
# NORMALIZE INPUT
# =========================================================

def normalize_names(raw_text: str) -> list[str]:
    seen = set()
    names = []
    for line in raw_text.splitlines():
        name = line.strip()
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


# =========================================================
# STYLING
# =========================================================

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 2rem;
            max-width: 100%;
        }

        .main-title {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }

        .subtitle {
            font-size: 1.08rem;
            margin-bottom: 1rem;
            line-height: 1.5;
        }

        .table-title {
            font-size: 2rem;
            font-weight: 800;
            margin-bottom: 1rem;
        }

        .team-label {
            font-size: 0.95rem;
            color: #666;
            margin-bottom: 0.15rem;
        }

        .team-line {
            font-size: 1.75rem;
            font-weight: 700;
            line-height: 1.2;
            margin-bottom: 0.65rem;
        }

        .winner-text {
            font-size: 1rem;
            font-weight: 700;
            color: #0b6b34;
            margin-top: 0.25rem;
            margin-bottom: 0.5rem;
        }

        .sitout-box {
            font-size: 1.45rem;
            font-weight: 700;
            padding: 16px 18px;
            border-radius: 14px;
            background: #f4f0d2;
            color: #6b5300;
            margin-top: 8px;
            margin-bottom: 14px;
        }

        .leaderboard-title {
            font-size: 1.8rem;
            font-weight: 800;
            margin-top: 0.8rem;
            margin-bottom: 0.6rem;
        }

        .podium-card {
            border: 2px solid #d9d9d9;
            border-radius: 18px;
            padding: 16px;
            background: white;
            text-align: center;
            min-height: 130px;
        }

        .podium-place {
            font-size: 1rem;
            font-weight: 700;
            color: #555;
            margin-bottom: 0.35rem;
        }

        .podium-name {
            font-size: 1.4rem;
            font-weight: 800;
            line-height: 1.2;
            margin-bottom: 0.35rem;
        }

        .podium-stat {
            font-size: 1rem;
            font-weight: 700;
        }

        .leaderboard-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 0.5rem;
            margin-bottom: 1rem;
        }

        .leaderboard-table th, .leaderboard-table td {
            border-bottom: 1px solid #e6e6e6;
            padding: 10px 12px;
            text-align: left;
            font-size: 1rem;
        }

        .leaderboard-table th {
            font-weight: 800;
            background: #fafafa;
        }

        .leaderboard-top-row {
            background: #fff6cc;
            font-weight: 700;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# PRECOMPUTED EXACT TEMPLATES
# =========================================================

TEMPLATE_12 = [
    [[12, 1], [9, 10], [2, 8], [3, 6], [4, 11], [5, 7]],
    [[12, 2], [10, 11], [3, 9], [4, 7], [5, 1], [6, 8]],
    [[12, 3], [11, 1], [4, 10], [5, 8], [6, 2], [7, 9]],
    [[12, 4], [1, 2], [5, 11], [6, 9], [7, 3], [8, 10]],
    [[12, 5], [2, 3], [6, 1], [7, 10], [8, 4], [9, 11]],
    [[12, 6], [3, 4], [7, 2], [8, 11], [9, 5], [10, 1]],
    [[12, 7], [4, 5], [8, 3], [9, 1], [10, 6], [11, 2]],
    [[12, 8], [5, 6], [9, 4], [10, 2], [11, 7], [1, 3]],
    [[12, 9], [6, 7], [10, 5], [11, 3], [1, 8], [2, 4]],
    [[12, 10], [7, 8], [11, 6], [1, 4], [2, 9], [3, 5]],
    [[12, 11], [8, 9], [1, 7], [2, 5], [3, 10], [4, 6]],
]

TEMPLATE_13 = [
    {"pairs": [[5, 13], [11, 8], [2, 9], [4, 12], [6, 10], [7, 3]], "bye": 1},
    {"pairs": [[2, 1], [7, 10], [4, 13], [6, 9], [11, 12], [3, 8]], "bye": 5},
    {"pairs": [[4, 5], [3, 12], [6, 1], [11, 13], [7, 9], [8, 10]], "bye": 2},
    {"pairs": [[6, 2], [8, 9], [11, 5], [7, 1], [3, 13], [10, 12]], "bye": 4},
    {"pairs": [[11, 4], [10, 13], [7, 2], [3, 5], [8, 1], [12, 9]], "bye": 6},
    {"pairs": [[7, 6], [12, 1], [3, 4], [8, 2], [10, 5], [9, 13]], "bye": 11},
    {"pairs": [[3, 11], [9, 5], [8, 6], [10, 4], [12, 2], [13, 1]], "bye": 7},
    {"pairs": [[8, 7], [13, 2], [10, 11], [12, 6], [9, 4], [1, 5]], "bye": 3},
    {"pairs": [[10, 3], [1, 4], [12, 7], [9, 11], [13, 6], [5, 2]], "bye": 8},
    {"pairs": [[12, 8], [5, 6], [9, 3], [13, 7], [1, 11], [2, 4]], "bye": 10},
    {"pairs": [[9, 10], [2, 11], [13, 8], [1, 3], [5, 7], [4, 6]], "bye": 12},
    {"pairs": [[13, 12], [4, 7], [1, 10], [5, 8], [2, 3], [6, 11]], "bye": 9},
    {"pairs": [[1, 9], [6, 3], [5, 12], [2, 10], [4, 8], [11, 7]], "bye": 13},
]

TEMPLATE_14 = [
    {"pairs": [[14, 3], [4, 10], [11, 9], [6, 8], [13, 5], [7, 12]], "out": [1, 2]},
    {"pairs": [[5, 9], [12, 14], [1, 2], [11, 7], [8, 10], [6, 13]], "out": [3, 4]},
    {"pairs": [[1, 7], [2, 8], [3, 10], [4, 13], [9, 12], [11, 14]], "out": [5, 6]},
    {"pairs": [[11, 10], [5, 6], [12, 3], [2, 9], [14, 13], [1, 4]], "out": [7, 8]},
    {"pairs": [[14, 6], [3, 7], [1, 8], [4, 5], [13, 12], [2, 11]], "out": [9, 10]},
    {"pairs": [[1, 10], [2, 3], [6, 4], [7, 8], [14, 5], [9, 13]], "out": [11, 12]},
    {"pairs": [[11, 4], [7, 10], [1, 3], [12, 2], [9, 6], [5, 8]], "out": [13, 14]},
    {"pairs": [[13, 11], [3, 5], [12, 6], [9, 10], [14, 8], [4, 7]], "out": [1, 2]},
    {"pairs": [[12, 10], [5, 7], [14, 2], [11, 6], [1, 9], [13, 8]], "out": [3, 4]},
    {"pairs": [[11, 3], [4, 8], [1, 12], [13, 10], [14, 9], [2, 7]], "out": [5, 6]},
    {"pairs": [[14, 4], [9, 3], [12, 5], [10, 6], [1, 11], [13, 2]], "out": [7, 8]},
    {"pairs": [[1, 14], [5, 11], [3, 6], [2, 4], [7, 13], [8, 12]], "out": [9, 10]},
    {"pairs": [[3, 8], [4, 9], [1, 13], [2, 6], [5, 10], [7, 14]], "out": [11, 12]},
    {"pairs": [[1, 5], [7, 6], [12, 11], [3, 4], [10, 2], [8, 9]], "out": [13, 14]},
]

TEMPLATE_15 = [
    {"pairs": [[14, 5], [4, 10], [11, 9], [6, 8], [15, 13], [7, 12]], "out": [1, 2, 3]},
    {"pairs": [[9, 14], [13, 12], [15, 3], [11, 7], [1, 2], [8, 10]], "out": [4, 5, 6]},
    {"pairs": [[11, 5], [2, 6], [1, 13], [14, 12], [10, 3], [15, 4]], "out": [7, 8, 9]},
    {"pairs": [[14, 13], [1, 4], [15, 9], [2, 3], [5, 6], [7, 8]], "out": [10, 11, 12]},
    {"pairs": [[10, 6], [3, 7], [1, 8], [4, 5], [12, 9], [2, 11]], "out": [13, 14, 15]},
    {"pairs": [[15, 14], [10, 13], [9, 7], [6, 4], [5, 12], [11, 8]], "out": [1, 2, 3]},
    {"pairs": [[13, 11], [3, 9], [1, 15], [12, 2], [14, 8], [7, 10]], "out": [4, 5, 6]},
    {"pairs": [[11, 1], [15, 10], [13, 4], [6, 12], [2, 14], [3, 5]], "out": [7, 8, 9]},
    {"pairs": [[15, 7], [5, 13], [4, 2], [14, 6], [8, 3], [1, 9]], "out": [10, 11, 12]},
    {"pairs": [[11, 3], [4, 8], [1, 12], [5, 10], [9, 6], [2, 7]], "out": [13, 14, 15]},
    {"pairs": [[5, 15], [9, 4], [13, 7], [6, 11], [14, 10], [8, 12]], "out": [1, 2, 3]},
    {"pairs": [[1, 3], [10, 12], [2, 9], [8, 13], [7, 14], [11, 15]], "out": [4, 5, 6]},
    {"pairs": [[11, 10], [2, 5], [1, 14], [4, 12], [3, 13], [15, 6]], "out": [7, 8, 9]},
    {"pairs": [[1, 6], [4, 7], [14, 3], [2, 15], [5, 8], [9, 13]], "out": [10, 11, 12]},
    {"pairs": [[5, 1], [8, 9], [12, 11], [3, 4], [10, 2], [7, 6]], "out": [13, 14, 15]},
]

TEMPLATE_16 = [
    [[16, 1], [9, 14], [2, 4], [5, 8], [3, 10], [12, 13], [6, 15], [7, 11]],
    [[16, 2], [10, 15], [3, 5], [6, 9], [4, 11], [13, 14], [7, 1], [8, 12]],
    [[16, 3], [11, 1], [4, 6], [7, 10], [5, 12], [14, 15], [8, 2], [9, 13]],
    [[16, 4], [12, 2], [5, 7], [8, 11], [6, 13], [15, 1], [9, 3], [10, 14]],
    [[16, 5], [13, 3], [6, 8], [9, 12], [7, 14], [1, 2], [10, 4], [11, 15]],
    [[16, 6], [14, 4], [7, 9], [10, 13], [8, 15], [2, 3], [11, 5], [12, 1]],
    [[16, 7], [15, 5], [8, 10], [11, 14], [9, 1], [3, 4], [12, 6], [13, 2]],
    [[16, 8], [1, 6], [9, 11], [12, 15], [10, 2], [4, 5], [13, 7], [14, 3]],
    [[16, 9], [2, 7], [10, 12], [13, 1], [11, 3], [5, 6], [14, 8], [15, 4]],
    [[16, 10], [3, 8], [11, 13], [14, 2], [12, 4], [6, 7], [15, 9], [1, 5]],
    [[16, 11], [4, 9], [12, 14], [15, 3], [13, 5], [7, 8], [1, 10], [2, 6]],
    [[16, 12], [5, 10], [13, 15], [1, 4], [14, 6], [8, 9], [2, 11], [3, 7]],
    [[16, 13], [6, 11], [14, 1], [2, 5], [15, 7], [9, 10], [3, 12], [4, 8]],
    [[16, 14], [7, 12], [15, 2], [3, 6], [1, 8], [10, 11], [4, 13], [5, 9]],
    [[16, 15], [8, 13], [1, 3], [4, 7], [2, 9], [11, 12], [5, 14], [6, 10]],
]

TEMPLATE_17 = [
    {"pairs": [[2, 17], [14, 5], [4, 15], [6, 13], [10, 9], [16, 3], [11, 8], [12, 7]], "bye": 1},
    {"pairs": [[3, 1], [15, 6], [5, 16], [7, 14], [11, 10], [17, 4], [12, 9], [13, 8]], "bye": 2},
    {"pairs": [[4, 2], [16, 7], [6, 17], [8, 15], [12, 11], [1, 5], [13, 10], [14, 9]], "bye": 3},
    {"pairs": [[5, 3], [17, 8], [7, 1], [9, 16], [13, 12], [2, 6], [14, 11], [15, 10]], "bye": 4},
    {"pairs": [[6, 4], [1, 9], [8, 2], [10, 17], [14, 13], [3, 7], [15, 12], [16, 11]], "bye": 5},
    {"pairs": [[7, 5], [2, 10], [9, 3], [11, 1], [15, 14], [4, 8], [16, 13], [17, 12]], "bye": 6},
    {"pairs": [[8, 6], [3, 11], [10, 4], [12, 2], [16, 15], [5, 9], [17, 14], [1, 13]], "bye": 7},
    {"pairs": [[9, 7], [4, 12], [11, 5], [13, 3], [17, 16], [6, 10], [1, 15], [2, 14]], "bye": 8},
    {"pairs": [[10, 8], [5, 13], [12, 6], [14, 4], [1, 17], [7, 11], [2, 16], [3, 15]], "bye": 9},
    {"pairs": [[11, 9], [6, 14], [13, 7], [15, 5], [2, 1], [8, 12], [3, 17], [4, 16]], "bye": 10},
    {"pairs": [[12, 10], [7, 15], [14, 8], [16, 6], [3, 2], [9, 13], [4, 1], [5, 17]], "bye": 11},
    {"pairs": [[13, 11], [8, 16], [15, 9], [17, 7], [4, 3], [10, 14], [5, 2], [6, 1]], "bye": 12},
    {"pairs": [[14, 12], [9, 17], [16, 10], [1, 8], [5, 4], [11, 15], [6, 3], [7, 2]], "bye": 13},
    {"pairs": [[15, 13], [10, 1], [17, 11], [2, 9], [6, 5], [12, 16], [7, 4], [8, 3]], "bye": 14},
    {"pairs": [[16, 14], [11, 2], [1, 12], [3, 10], [7, 6], [13, 17], [8, 5], [9, 4]], "bye": 15},
    {"pairs": [[17, 15], [12, 3], [2, 13], [4, 11], [8, 7], [14, 1], [9, 6], [10, 5]], "bye": 16},
    {"pairs": [[1, 16], [13, 4], [3, 14], [5, 12], [9, 8], [15, 2], [10, 7], [11, 6]], "bye": 17},
]

TEMPLATE_18 = [
    {"pairs": [[5, 13], [7, 14], [6, 16], [8, 10], [4, 18], [12, 15], [11, 17], [3, 9]], "out": [1, 2]},
    {"pairs": [[7, 16], [8, 15], [18, 2], [17, 1], [6, 13], [9, 12], [5, 10], [14, 11]], "out": [3, 4]},
    {"pairs": [[15, 10], [13, 17], [16, 8], [2, 12], [7, 11], [4, 9], [18, 14], [1, 3]], "out": [5, 6]},
    {"pairs": [[9, 16], [3, 11], [15, 4], [1, 18], [5, 14], [6, 10], [2, 13], [12, 17]], "out": [7, 8]},
    {"pairs": [[14, 3], [13, 18], [11, 1], [16, 15], [2, 17], [4, 8], [5, 12], [6, 7]], "out": [9, 10]},
    {"pairs": [[5, 15], [8, 14], [3, 16], [6, 18], [1, 10], [17, 4], [7, 13], [2, 9]], "out": [11, 12]},
    {"pairs": [[3, 18], [2, 16], [17, 6], [9, 10], [7, 15], [4, 12], [1, 5], [8, 11]], "out": [13, 14]},
    {"pairs": [[1, 4], [5, 2], [10, 3], [6, 8], [14, 17], [12, 13], [11, 18], [7, 9]], "out": [15, 16]},
    {"pairs": [[10, 16], [9, 15], [2, 14], [12, 11], [5, 6], [3, 4], [1, 7], [8, 13]], "out": [17, 18]},
    {"pairs": [[17, 9], [5, 3], [4, 6], [7, 8], [10, 14], [13, 15], [11, 16], [18, 12]], "out": [1, 2]},
    {"pairs": [[10, 11], [12, 14], [1, 2], [16, 13], [9, 6], [8, 5], [18, 7], [15, 17]], "out": [3, 4]},
    {"pairs": [[17, 3], [2, 8], [10, 18], [4, 7], [12, 16], [14, 1], [15, 11], [9, 13]], "out": [5, 6]},
    {"pairs": [[5, 11], [13, 4], [2, 15], [14, 9], [10, 17], [3, 12], [16, 18], [1, 6]], "out": [7, 8]},
    {"pairs": [[1, 12], [18, 8], [5, 16], [13, 3], [11, 6], [15, 14], [2, 4], [7, 17]], "out": [9, 10]},
    {"pairs": [[5, 4], [6, 14], [3, 2], [17, 16], [1, 13], [18, 15], [7, 10], [9, 8]], "out": [11, 12]},
    {"pairs": [[2, 10], [4, 11], [5, 17], [9, 18], [7, 12], [16, 1], [8, 3], [6, 15]], "out": [13, 14]},
    {"pairs": [[8, 17], [5, 18], [1, 9], [3, 7], [2, 11], [6, 12], [4, 14], [10, 13]], "out": [15, 16]},
    {"pairs": [[16, 14], [1, 15], [2, 7], [4, 10], [11, 13], [5, 9], [3, 6], [12, 8]], "out": [17, 18]},
]

TEMPLATE_19 = [
    {"pairs": [[17, 19], [14, 5], [15, 9], [7, 6], [18, 8], [12, 4], [13, 16], [11, 10]], "out": [1, 2, 3]},
    {"pairs": [[12, 8], [18, 16], [9, 19], [13, 2], [11, 7], [1, 3], [14, 17], [10, 15]], "out": [4, 5, 6]},
    {"pairs": [[3, 10], [11, 16], [6, 12], [18, 17], [1, 14], [5, 15], [2, 4], [13, 19]], "out": [7, 8, 9]},
    {"pairs": [[4, 6], [17, 7], [1, 15], [5, 8], [2, 9], [19, 16], [3, 13], [18, 14]], "out": [10, 11, 12]},
    {"pairs": [[2, 5], [12, 9], [3, 18], [10, 16], [4, 11], [8, 17], [1, 7], [6, 19]], "out": [13, 14, 15]},
    {"pairs": [[1, 12], [7, 14], [4, 10], [8, 2], [3, 6], [9, 11], [19, 15], [5, 13]], "out": [16, 17, 18]},
    {"pairs": [[3, 11], [6, 15], [7, 10], [12, 14], [4, 17], [13, 18], [5, 9], [8, 16]], "out": [1, 2, 19]},
    {"pairs": [[7, 16], [18, 19], [6, 9], [13, 17], [1, 11], [12, 15], [2, 14], [8, 10]], "out": [3, 4, 5]},
    {"pairs": [[2, 15], [9, 17], [1, 16], [4, 14], [3, 5], [12, 18], [10, 13], [11, 19]], "out": [6, 7, 8]},
    {"pairs": [[1, 8], [5, 16], [2, 19], [6, 18], [15, 13], [12, 17], [4, 7], [14, 3]], "out": [9, 10, 11]},
    {"pairs": [[4, 15], [7, 19], [3, 16], [11, 5], [2, 17], [10, 6], [1, 18], [9, 8]], "out": [12, 13, 14]},
    {"pairs": [[3, 12], [7, 9], [4, 19], [8, 13], [1, 10], [5, 18], [2, 11], [6, 14]], "out": [15, 16, 17]},
    {"pairs": [[2, 7], [6, 11], [3, 8], [12, 13], [4, 9], [14, 15], [5, 10], [16, 17]], "out": [1, 18, 19]},
    {"pairs": [[9, 14], [12, 16], [1, 6], [8, 15], [5, 19], [11, 17], [13, 7], [10, 18]], "out": [2, 3, 4]},
    {"pairs": [[1, 17], [8, 19], [2, 16], [9, 18], [3, 15], [10, 12], [4, 13], [11, 14]], "out": [5, 6, 7]},
    {"pairs": [[2, 18], [11, 15], [3, 17], [7, 12], [4, 5], [6, 13], [1, 19], [16, 14]], "out": [8, 9, 10]},
    {"pairs": [[3, 19], [5, 17], [4, 18], [6, 16], [1, 9], [7, 15], [2, 10], [8, 14]], "out": [11, 12, 13]},
    {"pairs": [[4, 8], [9, 13], [1, 5], [10, 17], [2, 6], [11, 18], [3, 7], [12, 19]], "out": [14, 15, 16]},
    {"pairs": [[1, 2], [4, 3], [5, 6], [8, 7], [9, 10], [12, 11], [14, 13], [15, 16]], "out": [17, 18, 19]},
]

TEMPLATE_20 = [
    [[20, 1], [13, 18], [2, 19], [7, 15], [3, 16], [5, 6], [4, 11], [10, 14], [8, 17], [9, 12]],
    [[20, 2], [14, 19], [3, 1], [8, 16], [4, 17], [6, 7], [5, 12], [11, 15], [9, 18], [10, 13]],
    [[20, 3], [15, 1], [4, 2], [9, 17], [5, 18], [7, 8], [6, 13], [12, 16], [10, 19], [11, 14]],
    [[20, 4], [16, 2], [5, 3], [10, 18], [6, 19], [8, 9], [7, 14], [13, 17], [11, 1], [12, 15]],
    [[20, 5], [17, 3], [6, 4], [11, 19], [7, 1], [9, 10], [8, 15], [14, 18], [12, 2], [13, 16]],
    [[20, 6], [18, 4], [7, 5], [12, 1], [8, 2], [10, 11], [9, 16], [15, 19], [13, 3], [14, 17]],
    [[20, 7], [19, 5], [8, 6], [13, 2], [9, 3], [11, 12], [10, 17], [16, 1], [14, 4], [15, 18]],
    [[20, 8], [1, 6], [9, 7], [14, 3], [10, 4], [12, 13], [11, 18], [17, 2], [15, 5], [16, 19]],
    [[20, 9], [2, 7], [10, 8], [15, 4], [11, 5], [13, 14], [12, 19], [18, 3], [16, 6], [17, 1]],
    [[20, 10], [3, 8], [11, 9], [16, 5], [12, 6], [14, 15], [13, 1], [19, 4], [17, 7], [18, 2]],
    [[20, 11], [4, 9], [12, 10], [17, 6], [13, 7], [15, 16], [14, 2], [1, 5], [18, 8], [19, 3]],
    [[20, 12], [5, 10], [13, 11], [18, 7], [14, 8], [16, 17], [15, 3], [2, 6], [19, 9], [1, 4]],
    [[20, 13], [6, 11], [14, 12], [19, 8], [15, 9], [17, 18], [16, 4], [3, 7], [1, 10], [2, 5]],
    [[20, 14], [7, 12], [15, 13], [1, 9], [16, 10], [18, 19], [17, 5], [4, 8], [2, 11], [3, 6]],
    [[20, 15], [8, 13], [16, 14], [2, 10], [17, 11], [19, 1], [18, 6], [5, 9], [3, 12], [4, 7]],
    [[20, 16], [9, 14], [17, 15], [3, 11], [18, 12], [1, 2], [19, 7], [6, 10], [4, 13], [5, 8]],
    [[20, 17], [10, 15], [18, 16], [4, 12], [19, 13], [2, 3], [1, 8], [7, 11], [5, 14], [6, 9]],
    [[20, 18], [11, 16], [19, 17], [5, 13], [1, 14], [3, 4], [2, 9], [8, 12], [6, 15], [7, 10]],
    [[20, 19], [12, 17], [1, 18], [6, 14], [2, 15], [4, 5], [3, 10], [9, 13], [7, 16], [8, 11]],
]

TEMPLATE_21 = [
    {"pairs": [[2,3],[13,16],[6,4],[7,19],[5,12],[8,21],[9,20],[14,18],[15,10],[11,17]], "bye": 1},
    {"pairs": [[3,4],[14,17],[7,5],[8,20],[6,13],[9,1],[10,21],[15,19],[16,11],[12,18]], "bye": 2},
    {"pairs": [[4,5],[15,18],[8,6],[9,21],[7,14],[10,2],[11,1],[16,20],[17,12],[13,19]], "bye": 3},
    {"pairs": [[5,6],[16,19],[9,7],[10,1],[8,15],[11,3],[12,2],[17,21],[18,13],[14,20]], "bye": 4},
    {"pairs": [[6,7],[17,20],[10,8],[11,2],[9,16],[12,4],[13,3],[18,1],[19,14],[15,21]], "bye": 5},
    {"pairs": [[7,8],[18,21],[11,9],[12,3],[10,17],[13,5],[14,4],[19,2],[20,15],[16,1]], "bye": 6},
    {"pairs": [[8,9],[19,1],[12,10],[13,4],[11,18],[14,6],[15,5],[20,3],[21,16],[17,2]], "bye": 7},
    {"pairs": [[9,10],[20,2],[13,11],[14,5],[12,19],[15,7],[16,6],[21,4],[1,17],[18,3]], "bye": 8},
    {"pairs": [[10,11],[21,3],[14,12],[15,6],[13,20],[16,8],[17,7],[1,5],[2,18],[19,4]], "bye": 9},
    {"pairs": [[11,12],[1,4],[15,13],[16,7],[14,21],[17,9],[18,8],[2,6],[3,19],[20,5]], "bye": 10},
    {"pairs": [[12,13],[2,5],[16,14],[17,8],[15,1],[18,10],[19,9],[3,7],[4,20],[21,6]], "bye": 11},
    {"pairs": [[13,14],[3,6],[17,15],[18,9],[16,2],[19,11],[20,10],[4,8],[5,21],[1,7]], "bye": 12},
    {"pairs": [[14,15],[4,7],[18,16],[19,10],[17,3],[20,12],[21,11],[5,9],[6,1],[2,8]], "bye": 13},
    {"pairs": [[15,16],[5,8],[19,17],[20,11],[18,4],[21,13],[1,12],[6,10],[7,2],[3,9]], "bye": 14},
    {"pairs": [[16,17],[6,9],[20,18],[21,12],[19,5],[1,14],[2,13],[7,11],[8,3],[4,10]], "bye": 15},
    {"pairs": [[17,18],[7,10],[21,19],[1,13],[20,6],[2,15],[3,14],[8,12],[9,4],[5,11]], "bye": 16},
    {"pairs": [[18,19],[8,11],[1,20],[2,14],[21,7],[3,16],[4,15],[9,13],[10,5],[6,12]], "bye": 17},
    {"pairs": [[19,20],[9,12],[2,21],[3,15],[1,8],[4,17],[5,16],[10,14],[11,6],[7,13]], "bye": 18},
    {"pairs": [[20,21],[10,13],[3,1],[4,16],[2,9],[5,18],[6,17],[11,15],[12,7],[8,14]], "bye": 19},
    {"pairs": [[21,1],[11,14],[4,2],[5,17],[3,10],[6,19],[7,18],[12,16],[13,8],[9,15]], "bye": 20},
    {"pairs": [[1,2],[12,15],[5,3],[6,18],[4,11],[7,20],[8,19],[13,17],[14,9],[10,16]], "bye": 21},
]

PRECOMPUTED_TEMPLATES = {
    12: TEMPLATE_12,
    13: TEMPLATE_13,
    14: TEMPLATE_14,
    15: TEMPLATE_15,
    16: TEMPLATE_16,
    17: TEMPLATE_17,
    18: TEMPLATE_18,
    19: TEMPLATE_19,
    20: TEMPLATE_20,
    21: TEMPLATE_21,
}


# =========================================================
# Template conversion / mapping
# =========================================================

def map_num_to_name(x, players: list[str]) -> str:
    if isinstance(x, str):
        return x
    return players[x - 1]


def convert_round_from_template(round_template, players: list[str], round_number: int) -> dict:
    if isinstance(round_template, dict):
        raw_pairs = round_template.get("pairs", [])
        bye = round_template.get("bye")
        out_players = round_template.get("out", [])
    else:
        raw_pairs = round_template
        bye = None
        out_players = []

    partner_pairs = [[map_num_to_name(a, players), map_num_to_name(b, players)] for a, b in raw_pairs]

    tables = []
    for i in range(0, len(partner_pairs), 2):
        if i + 1 >= len(partner_pairs):
            break
        tables.append({
            "table": len(tables) + 1,
            "team1": partner_pairs[i],
            "team2": partner_pairs[i + 1],
        })

    sit_out = []

    if bye is not None:
        sit_out.append(map_num_to_name(bye, players))

    for p in out_players:
        sit_out.append(map_num_to_name(p, players))

    return {
        "round_number": round_number,
        "partner_pairs": partner_pairs,
        "bye": map_num_to_name(bye, players) if bye is not None else None,
        "sit_out_team": [],
        "sit_out": sit_out,
        "tables": tables,
    }

def build_schedule_from_template(players: list[str]) -> list[dict]:
    n = len(players)
    template = PRECOMPUTED_TEMPLATES.get(n)

    if template is None:
        raise ValueError(f"The precomputed perfect template for {n} players is not loaded.")

    return [
        convert_round_from_template(round_template, players, i + 1)
        for i, round_template in enumerate(template)
    ]


# =========================================================
# Partner schedule (hard constraint for heuristic path)
# =========================================================

def generate_partner_rounds(players: list[str]) -> list[dict]:
    arr = players[:]
    ghost = None

    if len(arr) % 2 == 1:
        ghost = "__BYE__"
        arr.append(ghost)

    n = len(arr)
    rounds = []

    for _ in range(n - 1):
        pairs = []
        bye = None

        for i in range(n // 2):
            a = arr[i]
            b = arr[n - 1 - i]

            if ghost in (a, b):
                bye = b if a == ghost else a
            else:
                pairs.append((a, b))

        rounds.append({"pairs": pairs, "bye": bye})
        arr = [arr[0]] + [arr[-1]] + arr[1:-1]

    return rounds


# =========================================================
# Heuristic fallback
# =========================================================

def opponent_target(players: list[str], partner_rounds: list[dict]) -> float:
    total_pairs = math.comb(len(players), 2)
    total_opponent_pair_events = 0
    for rnd in partner_rounds:
        table_count = len(rnd["pairs"]) // 2
        total_opponent_pair_events += table_count * 4
    return total_opponent_pair_events / total_pairs


def opponent_low_high(players: list[str], partner_rounds: list[dict]) -> tuple[int, int, float]:
    target = opponent_target(players, partner_rounds)
    return math.floor(target), math.ceil(target), target


def make_empty_opp_counts(players: list[str]) -> dict:
    return {p: {q: 0 for q in players if q != p} for p in players}


def apply_tables_to_opp_counts(opp_counts: dict, tables: list) -> None:
    for team1, team2 in tables:
        a, b = team1
        c, d = team2
        for x in (a, b):
            for y in (c, d):
                opp_counts[x][y] += 1
                opp_counts[y][x] += 1


def edge_penalty(c: int, low: int, high: int) -> float:
    if c < low:
        return 1000 * (low - c) ** 2
    if c > high:
        return 3000 * (c - high) ** 2
    mid = (low + high) / 2.0
    return (c - mid) ** 2


def incremental_match_cost(team_a, team_b, opp_counts, low, high):
    a1, a2 = team_a
    b1, b2 = team_b
    cost = 0
    for x in (a1, a2):
        for y in (b1, b2):
            before = opp_counts[x][y]
            after = before + 1
            cost += edge_penalty(after, low, high) - edge_penalty(before, low, high)
    return cost


def compute_sitout_targets(players: list[str], partner_rounds: list[dict], rng: random.Random):
    n = len(players)
    mandatory = {p: 0 for p in players}
    total_slots = 0

    for rnd in partner_rounds:
        round_slots = 0
        if rnd["bye"] is not None:
            mandatory[rnd["bye"]] += 1
            round_slots += 1
        if len(rnd["pairs"]) % 2 == 1:
            round_slots += 2
        total_slots += round_slots

    low = total_slots // n
    high = low + (1 if total_slots % n else 0)
    num_high = total_slots - low * n

    targets = {p: low for p in players}
    required_high = [p for p in players if mandatory[p] > low]
    required_high = list(dict.fromkeys(required_high))

    if len(required_high) > num_high:
        for p in players:
            targets[p] = max(low, mandatory[p])
        return targets, low, high

    chosen_high = set(required_high)
    remaining = [p for p in players if p not in chosen_high]
    rng.shuffle(remaining)

    for p in remaining[:max(0, num_high - len(chosen_high))]:
        chosen_high.add(p)

    for p in chosen_high:
        targets[p] = high

    for p in players:
        if targets[p] < mandatory[p]:
            targets[p] = mandatory[p]

    return targets, low, high


def choose_sitout_team(teams, sit_counts, sit_targets, rng):
    scored = []
    for team in teams:
        a, b = team
        after_a = sit_counts[a] + 1
        after_b = sit_counts[b] + 1

        over_target = max(0, after_a - sit_targets[a]) + max(0, after_b - sit_targets[b])
        remaining_deficit = max(0, sit_targets[a] - after_a) + max(0, sit_targets[b] - after_b)
        current_total = sit_counts[a] + sit_counts[b]

        scored.append((over_target, remaining_deficit, current_total, rng.random(), team))

    scored.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    shortlist = scored[:min(4, len(scored))]
    return rng.choice(shortlist)[4]


def greedy_pair_tables(teams, opp_counts, low, high, rng):
    remaining = teams[:]
    tables = []

    while remaining:
        team_scores = []
        for i, team_a in enumerate(remaining):
            costs = []
            for j, team_b in enumerate(remaining):
                if i == j:
                    continue
                costs.append(incremental_match_cost(team_a, team_b, opp_counts, low, high))
            if costs:
                team_scores.append((min(costs), rng.random(), i))

        team_scores.sort(reverse=True)
        _, _, idx_a = team_scores[0]
        team_a = remaining.pop(idx_a)

        match_options = []
        for j, team_b in enumerate(remaining):
            cost = incremental_match_cost(team_a, team_b, opp_counts, low, high)
            match_options.append((cost, rng.random(), j, team_b))

        match_options.sort(key=lambda x: (x[0], x[1]))
        shortlist = match_options[:min(3, len(match_options))]
        _, _, idx_b, team_b = rng.choice(shortlist)

        remaining.pop(idx_b)
        tables.append((team_a, team_b))

    return tables


def round_cost(tables, opp_counts, low, high):
    cost = 0
    for team1, team2 in tables:
        cost += incremental_match_cost(team1, team2, opp_counts, low, high)
    return cost


def improve_round_layout(tables, opp_counts_before_round, low, high):
    tables = tables[:]
    improved = True

    while improved:
        improved = False
        for i in range(len(tables)):
            for j in range(i + 1, len(tables)):
                t1a, t1b = tables[i]
                t2a, t2b = tables[j]

                original = [tables[i], tables[j]]
                original_cost = round_cost(original, opp_counts_before_round, low, high)

                candidates = [
                    [(t1a, t2a), (t1b, t2b)],
                    [(t1a, t2b), (t1b, t2a)],
                ]

                best_local = original
                best_local_cost = original_cost

                for cand in candidates:
                    cand_cost = round_cost(cand, opp_counts_before_round, low, high)
                    if cand_cost < best_local_cost:
                        best_local = cand
                        best_local_cost = cand_cost

                if best_local_cost < original_cost:
                    tables[i], tables[j] = best_local[0], best_local[1]
                    improved = True

    return tables


def final_opponent_score(players: list[str], opp_counts: dict, low: int, high: int, target: float):
    vals = []
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            a = players[i]
            b = players[j]
            vals.append(opp_counts[a][b])

    min_count = min(vals)
    max_count = max(vals)
    spread = max_count - min_count
    outside_band = sum(1 for v in vals if v < low or v > high)
    band_penalty = sum(edge_penalty(v, low, high) for v in vals)
    sse = sum((v - target) ** 2 for v in vals)

    return outside_band, band_penalty, sse, spread, max_count, min_count


def build_schedule_heuristic(players: list[str], attempts: int = 120, seed: int = 42) -> list[dict]:
    partner_rounds = generate_partner_rounds(players)
    opp_low, opp_high, opp_target = opponent_low_high(players, partner_rounds)

    best_schedule = None
    best_score = None

    for attempt in range(attempts):
        rng = random.Random(seed + attempt)

        sit_targets, _, _ = compute_sitout_targets(players, partner_rounds, rng)
        opp_counts = make_empty_opp_counts(players)
        sit_counts = {p: 0 for p in players}
        schedule = []

        for round_index, rnd in enumerate(partner_rounds, start=1):
            teams = [tuple(pair) for pair in rnd["pairs"]]
            bye = rnd["bye"]

            sit_out_players = []
            sit_out_team = None

            if bye is not None:
                sit_out_players.append(bye)
                sit_counts[bye] += 1

            active_teams = teams[:]
            if len(active_teams) % 2 == 1:
                sit_out_team = choose_sitout_team(active_teams, sit_counts, sit_targets, rng)
                active_teams.remove(sit_out_team)
                for p in sit_out_team:
                    sit_out_players.append(p)
                    sit_counts[p] += 1

            tables = greedy_pair_tables(active_teams, opp_counts, opp_low, opp_high, rng)
            tables = improve_round_layout(tables, opp_counts, opp_low, opp_high)
            apply_tables_to_opp_counts(opp_counts, tables)

            round_data = {
                "round_number": round_index,
                "partner_pairs": [list(pair) for pair in teams],
                "bye": bye,
                "sit_out_team": list(sit_out_team) if sit_out_team is not None else [],
                "sit_out": sit_out_players,
                "tables": [],
            }

            for table_num, (team1, team2) in enumerate(tables, start=1):
                round_data["tables"].append({
                    "table": table_num,
                    "team1": list(team1),
                    "team2": list(team2),
                })

            schedule.append(round_data)

        opp_score = final_opponent_score(players, opp_counts, opp_low, opp_high, opp_target)
        sit_vals = [sit_counts[p] for p in players]
        sit_spread = max(sit_vals) - min(sit_vals)
        sit_target_miss = sum(abs(sit_counts[p] - sit_targets[p]) for p in players)

        score = (
            sit_target_miss,
            sit_spread,
            *opp_score,
        )

        if best_score is None or score < best_score:
            best_score = score
            best_schedule = schedule

    return best_schedule


def build_schedule(players: list[str]) -> tuple[list[dict], str]:
    n = len(players)

    if n < 4 or n > 21:
        raise ValueError("This version supports between 4 and 21 players.")

    if n in PRECOMPUTED_TEMPLATES and PRECOMPUTED_TEMPLATES[n] is not None:
        return build_schedule_from_template(players), "Perfect bracket"

    return build_schedule_heuristic(players), "Best available bracket"


# =========================================================
# RESULTS / LEADERBOARD
# =========================================================

def ensure_result_state_for_schedule(schedule: list[dict]) -> None:
    if "saved_results" not in st.session_state:
        st.session_state.saved_results = {}

    for rnd in schedule:
        round_no = rnd["round_number"]
        st.session_state.saved_results.setdefault(round_no, {})


def get_table_result(round_no: int, table_no: int):
    return st.session_state.saved_results.get(round_no, {}).get(table_no)


def toggle_table_winner(round_no: int, table_no: int, team_key: str):
    st.session_state.saved_results.setdefault(round_no, {})
    current = st.session_state.saved_results[round_no].get(table_no)

    if current == team_key:
        st.session_state.saved_results[round_no].pop(table_no, None)
    else:
        st.session_state.saved_results[round_no][table_no] = team_key


def compute_leaderboard(players: list[str], schedule: list[dict], saved_results: dict) -> list[dict]:
    wins = {p: 0 for p in players}
    games_played = {p: 0 for p in players}

    for rnd in schedule:
        round_no = rnd["round_number"]
        round_results = saved_results.get(round_no, {})

        for table in rnd["tables"]:
            result = round_results.get(table["table"])
            team1 = table["team1"]
            team2 = table["team2"]

            if result == "team1":
                winners = team1
                losers = team2
            elif result == "team2":
                winners = team2
                losers = team1
            else:
                continue

            for p in winners:
                wins[p] += 1
                games_played[p] += 1
            for p in losers:
                games_played[p] += 1

    sorted_players = sorted(players, key=lambda p: (-wins[p], games_played[p], str(p)))

    leaderboard = []
    for player in sorted_players:
        leaderboard.append({
            "Player": player,
            "Wins": wins[player],
            "Games Played": games_played[player],
            "Win %": f"{(wins[player] / games_played[player] * 100):.0f}%" if games_played[player] > 0 else "—",
        })

    return leaderboard


def render_leaderboard(leaderboard: list[dict]) -> None:
    st.markdown('<div class="leaderboard-title">Leaderboard</div>', unsafe_allow_html=True)

    if not leaderboard:
        st.info("No results have been entered yet.")
        return

    top_three = leaderboard[:3]
    podium_cols = st.columns(3)

    for i in range(3):
        with podium_cols[i]:
            if i < len(top_three):
                row = top_three[i]
                st.markdown(
                    f"""
                    <div class="podium-card">
                        <div class="podium-place">Top {i+1}</div>
                        <div class="podium-name">{html.escape(str(row["Player"]))}</div>
                        <div class="podium-stat">{row["Wins"]} wins</div>
                        <div class="podium-stat">{row["Games Played"]} games</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    top_wins = leaderboard[0]["Wins"] if leaderboard else 0
    rows_html = ""

    for row in leaderboard:
        row_class = "leaderboard-top-row" if row["Wins"] == top_wins and top_wins > 0 else ""
        rows_html += f"""
        <tr class="{row_class}">
            <td>{html.escape(str(row["Player"]))}</td>
            <td>{row["Wins"]}</td>
            <td>{row["Games Played"]}</td>
            <td>{row["Win %"]}</td>
        </tr>
        """

    st.markdown(
        f"""
        <table class="leaderboard-table">
            <thead>
                <tr>
                    <th>Player</th>
                    <th>Wins</th>
                    <th>Games Played</th>
                    <th>Win %</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# Validation helpers
# =========================================================

def partner_summary(players: list[str], schedule: list[dict]) -> dict:
    counts = {p: {q: 0 for q in players if q != p} for p in players}
    for rnd in schedule:
        for a, b in rnd["partner_pairs"]:
            counts[a][b] += 1
            counts[b][a] += 1
    return counts


def opponent_summary(players: list[str], schedule: list[dict]) -> dict:
    counts = {p: {q: 0 for q in players if q != p} for p in players}
    for rnd in schedule:
        for t in rnd["tables"]:
            a, b = t["team1"]
            c, d = t["team2"]
            for x in (a, b):
                for y in (c, d):
                    counts[x][y] += 1
                    counts[y][x] += 1
    return counts


def opponent_balance_report(players: list[str], schedule: list[dict]) -> list[tuple[str, str, int]]:
    counts = opponent_summary(players, schedule)
    rows = []
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            a = players[i]
            b = players[j]
            rows.append((a, b, counts[a][b]))
    return rows


def count_sitouts(schedule: list[dict]) -> dict:
    sit = {}
    for rnd in schedule:
        for p in rnd["sit_out"]:
            sit[p] = sit.get(p, 0) + 1
    return sit


def opponent_target_from_schedule(players: list[str], schedule: list[dict]) -> float:
    total_pairs = math.comb(len(players), 2)
    total_opponent_pair_events = 0
    for rnd in schedule:
        total_opponent_pair_events += len(rnd["tables"]) * 4
    return total_opponent_pair_events / total_pairs


# =========================================================
# Session helpers
# =========================================================

def reset_tournament():
    st.session_state.players = []
    st.session_state.schedule = []
    st.session_state.current_round = 0
    st.session_state.generated = False
    st.session_state.error = ""
    st.session_state.schedule_mode = ""
    st.session_state.saved_results = {}


def generate_tournament(names_text: str):
    players = normalize_names(names_text)

    if len(players) < 4:
        st.session_state.error = "You need at least 4 players."
        st.session_state.generated = False
        st.session_state.schedule = []
        st.session_state.current_round = 0
        st.session_state.schedule_mode = ""
        st.session_state.saved_results = {}
        return

    try:
        schedule, mode = build_schedule(players)
        st.session_state.players = players
        st.session_state.schedule = schedule
        st.session_state.current_round = 0
        st.session_state.generated = True
        st.session_state.error = ""
        st.session_state.schedule_mode = mode
        st.session_state.saved_results = {}
        ensure_result_state_for_schedule(schedule)
    except Exception as e:
        st.session_state.error = str(e)
        st.session_state.generated = False
        st.session_state.schedule = []
        st.session_state.current_round = 0
        st.session_state.schedule_mode = ""
        st.session_state.saved_results = {}


def next_round():
    if st.session_state.current_round < len(st.session_state.schedule) - 1:
        st.session_state.current_round += 1


def prev_round():
    if st.session_state.current_round > 0:
        st.session_state.current_round -= 1


# =========================================================
# Session state init
# =========================================================

if "players" not in st.session_state:
    st.session_state.players = []
if "schedule" not in st.session_state:
    st.session_state.schedule = []
if "current_round" not in st.session_state:
    st.session_state.current_round = 0
if "generated" not in st.session_state:
    st.session_state.generated = False
if "error" not in st.session_state:
    st.session_state.error = ""
if "schedule_mode" not in st.session_state:
    st.session_state.schedule_mode = ""
if "saved_results" not in st.session_state:
    st.session_state.saved_results = {}


# =========================================================
# UI
# =========================================================

st.markdown('<div class="main-title">Euchre Tournament Scheduler</div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="subtitle">
        <strong>Recommended player counts for a perfect bracket:</strong> 12, 13, 16, 17, 20, 21<br>
        Other player counts from 4 to 21 can still generate a <strong>best available bracket</strong>.
        That version keeps partner assignments exact and aims to balance opponent counts and sit-outs as evenly as possible.
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("Enter player names", expanded=not st.session_state.generated):
    names_text = st.text_area(
        "One player per line",
        value="",
        height=220,
        key="names_input",
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        st.button(
            "Generate Bracket",
            key="generate_btn",
            on_click=generate_tournament,
            args=(names_text,),
        )
    with c2:
        st.button(
            "Reset",
            key="reset_btn",
            on_click=reset_tournament,
        )

if st.session_state.error:
    st.error(st.session_state.error)

if st.session_state.generated and st.session_state.schedule:
    schedule = st.session_state.schedule
    ensure_result_state_for_schedule(schedule)

    idx = st.session_state.current_round
    round_data = schedule[idx]
    players = st.session_state.players
    leaderboard = compute_leaderboard(players, schedule, st.session_state.saved_results)

    current_leader_text = "—"
    if leaderboard and leaderboard[0]["Wins"] > 0:
        top_wins = leaderboard[0]["Wins"]
        top_names = [row["Player"] for row in leaderboard if row["Wins"] == top_wins]
        current_leader_text = ", ".join(map(str, top_names[:3]))
        if len(top_names) > 3:
            current_leader_text += "..."

    top1, top2, top3, top4, top5 = st.columns([1, 1, 1, 1.2, 1.4])
    with top1:
        st.metric("Players", len(players))
    with top2:
        st.metric("Current Round", f"{idx + 1} / {len(schedule)}")
    with top3:
        st.metric("Tables This Round", len(round_data["tables"]))
    with top4:
        st.metric("Bracket Type", st.session_state.schedule_mode)
    with top5:
        st.metric("Current Leader", current_leader_text)

    if len(players) not in (12, 13, 16, 17, 20, 21):
        st.info(
            "This screen is using a best-available bracket. Partner assignments remain exact, and the layout aims to keep opponent counts and sit-outs as balanced as possible."
        )

    st.subheader(f"Round {round_data['round_number']}")

    tables = round_data["tables"]
    cols_per_row = 2 if len(tables) >= 2 else 1

    for row_start in range(0, len(tables), cols_per_row):
        row_tables = tables[row_start:row_start + cols_per_row]
        cols = st.columns(len(row_tables))

        for col, table in zip(cols, row_tables):
            with col:
                round_no = round_data["round_number"]
                table_no = table["table"]
                result = get_table_result(round_no, table_no)

                team1_selected = result == "team1"
                team2_selected = result == "team2"

                with st.container(border=True):
                    st.markdown(
                        f'<div class="table-title">Table {table_no}</div>',
                        unsafe_allow_html=True,
                    )

                    team_col1, team_col2 = st.columns(2)

                    with team_col1:
                        st.markdown('<div class="team-label">Team 1</div>', unsafe_allow_html=True)
                        st.markdown(
                            f'<div class="team-line">{html.escape(str(table["team1"][0]))} + {html.escape(str(table["team1"][1]))}</div>',
                            unsafe_allow_html=True,
                        )
                        if team1_selected:
                            st.markdown('<div class="winner-text">Selected winner</div>', unsafe_allow_html=True)

                        st.button(
                            "✓ Winner" if team1_selected else "Select",
                            key=f"btn_r{round_no}_t{table_no}_team1",
                            type="primary" if team1_selected else "secondary",
                            on_click=toggle_table_winner,
                            args=(round_no, table_no, "team1"),
                            use_container_width=True,
                        )

                    with team_col2:
                        st.markdown('<div class="team-label">Team 2</div>', unsafe_allow_html=True)
                        st.markdown(
                            f'<div class="team-line">{html.escape(str(table["team2"][0]))} + {html.escape(str(table["team2"][1]))}</div>',
                            unsafe_allow_html=True,
                        )
                        if team2_selected:
                            st.markdown('<div class="winner-text">Selected winner</div>', unsafe_allow_html=True)

                        st.button(
                            "✓ Winner" if team2_selected else "Select",
                            key=f"btn_r{round_no}_t{table_no}_team2",
                            type="primary" if team2_selected else "secondary",
                            on_click=toggle_table_winner,
                            args=(round_no, table_no, "team2"),
                            use_container_width=True,
                        )

    if round_data["sit_out"]:
        st.markdown(
            f'<div class="sitout-box">Sitting out this round: {", ".join(map(str, round_data["sit_out"]))}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.success("No sit-outs this round.")

    nav1, nav2, nav3 = st.columns([1, 1, 1])
    with nav1:
        st.button("Previous Round", key="prev_round_btn", on_click=prev_round)
    with nav2:
        st.button("Next Round", key="next_round_btn", on_click=next_round)
    with nav3:
        if idx == len(schedule) - 1:
            st.success("Final round reached.")

    render_leaderboard(leaderboard)

    with st.expander("Validation / stats"):
        partner_counts = partner_summary(players, schedule)
        opp_counts = opponent_summary(players, schedule)
        opp_target = opponent_target_from_schedule(players, schedule)

        st.write(f"Ideal average opponent count per pair: {opp_target:.4f}")
        st.write(f"Desired opponent band: {math.floor(opp_target)} to {math.ceil(opp_target)}")

        outside = sum(
            1 for a, b in combinations(players, 2)
            if not (math.floor(opp_target) <= opp_counts[a][b] <= math.ceil(opp_target))
        )
        max_opp = max(opp_counts[a][b] for a, b in combinations(players, 2))
        min_opp = min(opp_counts[a][b] for a, b in combinations(players, 2))
        sse = sum(
            (opp_counts[a][b] - opp_target) ** 2
            for a, b in combinations(players, 2)
        )

        st.write(
            f"Pairs outside desired band: {outside} | "
            f"SSE from target: {sse:.2f} | "
            f"Spread: {max_opp - min_opp} | "
            f"Max: {max_opp} | "
            f"Min: {min_opp}"
        )

        sits = count_sitouts(schedule)
        sit_vals = [sits.get(p, 0) for p in players]

        st.markdown("**Sit-out balance**")
        st.write(
            f"Total sit-out slots: {sum(sit_vals)} | "
            f"Actual sit-out minimum: {min(sit_vals)} | "
            f"Actual sit-out maximum: {max(sit_vals)}"
        )

        st.markdown("**Partner counts**")
        partner_issues = []
        for a, b in combinations(players, 2):
            if partner_counts[a][b] != 1:
                partner_issues.append(f"{a} & {b}: {partner_counts[a][b]}")

        if partner_issues:
            st.error("Some partner counts are not exactly 1:")
            for issue in partner_issues:
                st.write(issue)
        else:
            st.success("Every player partners every other player exactly once.")

        st.markdown("**Opponent counts by pair**")
        rows = opponent_balance_report(players, schedule)
        for a, b, c in rows:
            st.write(f"{a} vs {b}: {c}")
