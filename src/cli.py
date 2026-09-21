"""CLI: python -m src.cli --biome desert --month 11 --days 2-3"""
from __future__ import annotations
import argparse
from .features import UserProfile
from .recommender import ParkRecommender

ORIGINS = {
    "san_diego": (32.72, -117.16),
    "los_angeles": (34.05, -118.24),
    "phoenix": (33.45, -112.07),
    "denver": (39.74, -104.99),
    "seattle": (47.61, -122.33),
    "salt_lake": (40.76, -111.89),
    "nyc": (40.71, -74.01),
}

def parse_args():
    parser = argparse.ArgumentParser(description="Recommend U.S. National Parks")
    parser.add_argument("--biome", action="append", default=[])
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--difficulty", default="easy", choices=["easy","moderate","challenging"])
    parser.add_argument("--days", default="2-3", choices=["1","2-3","4-7","7+"])
    parser.add_argument("--crowd", default="medium", choices=["low","medium","high"])
    parser.add_argument("--budget", default="mid", choices=["low","mid","high"])
    parser.add_argument("--month", type=int, default=None)
    parser.add_argument("--origin", choices=sorted(ORIGINS), default=None)
    parser.add_argument("--max-hours", type=float, default=None)
    parser.add_argument("--no-remote", action="store_true")
    parser.add_argument("--no-permits", action="store_true")
    parser.add_argument("-k", type=int, default=5)
    return parser.parse_args()

def pd_isna(value):
    return value != value

def main():
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
        print("No parks matched those filters.")
        return
    for i, row in ranked.iterrows():
        hours = "" if pd_isna(row["drive_hours"]) else f"  {row['drive_hours']:.1f}h"
        print(f"{i+1}. {row['name']} ({row['park_code']})  score={row['score']:.3f}{hours}")
        print(f"   {row['why']}")

if __name__ == "__main__":
    main()
