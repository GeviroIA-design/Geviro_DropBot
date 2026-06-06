import argparse

from app.orchestrator import execute


def main() -> None:
    parser = argparse.ArgumentParser(description="GEVIRO Dropshipping Bot")
    parser.add_argument("--n", type=int, default=None, help="number of products")
    parser.add_argument("--seed", type=int, default=None, help="random seed")
    parser.add_argument("--out", type=str, default=None, help="output directory")
    args = parser.parse_args()

    products, scorecards, forecasts, summary = execute(
        n=args.n, seed=args.seed, out_dir=args.out
    )
    print(
        f"Run complete: {len(products)} products scored. "
        f"Decisions: {summary}. "
        f"Forecasts: {len(forecasts)}."
    )


if __name__ == "__main__":
    main()
