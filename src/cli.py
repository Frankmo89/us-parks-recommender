"""CLI: python -m src.cli --biome desert --month 11 --days 2-3"""

from __future__ import annotations

import argparse

import pandas as pd

from .features import UserProfile
from .origins import ORIGINS
from .recommender import ParkRecommender


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recommend U.S. National Parks")
    parser.add_argument("--biome", action="append", default=[])
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--difficulty", default="easy", choices=["easy", "moderate", "challenging"])
    parser.add_argument("--days", default="2-3", choices=["1", "2-3", "4-7", "7+"])
    parser.add_argument("--crowd", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--budget", default="mid", choices=["low", "mid", "high"])
    parser.add_argument("--month", type=int, default=None)
    parser.add_argument("--origin", choices=sorted(ORIGINS), default=None)
    parser.add_argument("--max-hours", type=float, default=None)
    parser.add_argument("--no-remote", action="store_true")
    parser.add_argument("--no-permits", action="store_true")
    parser.add_argument("-k", type=int, default=5)
    parser.add_argument("--explain", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    lat = lon = None
    if args.origin:
        lat, lon = ORIGINS[args.origin]
    profile = UserProfile(
        biomes=args.biome,
        tags=args.tag or ["hiking"],
        difficulty=args.difficulty,
        days_needed=args.days,
        crowd_pref=args.crowd,
        budget_tier=args.budget,
        month=args.month,
        origin_lat=lat,
        origin_lon=lon,
        max_drive_hours=args.max_hours,
        allow_remote=not args.no_remote,
        allow_permits=not args.no_permits,
    )
    ranked = ParkRecommender().recommend(profile, k=args.k)
    if ranked.empty:
        print("No parks matched those filters. Relax month, distance or remote/permit flags.")
        return
    for i, row in ranked.iterrows():
        hours = "" if pd.isna(row["drive_hours"]) else f"  {row['drive_hours']:.1f}h"
        print(f"{i + 1}. {row['name']} ({row['park_code']})  score={row['score']:.3f}{hours}")
        print(f"   {row['why']}")
        if args.explain:
            print(
                f"   content={row['content']:.2f} days={row['days_fit']:.2f} "
                f"diff={row['diff_fit']:.2f} budget={row['budget_fit']:.2f} "
                f"crowd_pen={row['crowd_penalty']:.2f} month_pen={row['month_penalty']:.2f}"
            )


if __name__ == "__main__":
    main()
