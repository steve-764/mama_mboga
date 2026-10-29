"""Run the recommendation engine end to end.

Usage:  python main.py [customer_id]
Prints one customer's report, writes output/recommendations.csv for every
customer, then prints a run summary.
"""
import sys

from recommender import (
    DATA_PATH,
    OUTPUT_PATH,
    RecommendationEngine,
    UnknownCustomerError,
    read_purchases,
)

N_SIMILAR = 3
N_RECOMMENDATIONS = 3


def print_customer_report(engine: RecommendationEngine, customer_id: str) -> None:
    name = engine.customer_name(customer_id)
    bought = sorted(engine.history(customer_id))

    print(f"Customer {customer_id} ({name}) bought: {{{', '.join(bought)}}}")

    print("Most similar customers:")
    for other_id, jac in engine.similar_customers(customer_id, N_SIMILAR):
        print(f"  {other_id}  jaccard={jac:.2f}")

    print("Recommendations:")
    for rank, rec in enumerate(engine.recommend(customer_id, N_RECOMMENDATIONS), start=1):
        supporters = len(rec["supporters"])
        if supporters:
            noun = "customer" if supporters == 1 else "customers"
            reason = f"{supporters} similar {noun} bought it"
        else:
            # popularity fallback: no similar customer backs this product
            reason = f"it is popular ({rec['popularity']} purchases)"
        print(
            f"  {rank}. {rec['name']} ({rec['category']})  "
            f"score={rec['score']:.3f}  because {reason}"
        )


def main() -> int:
    valid, rejected = read_purchases(DATA_PATH)
    engine = RecommendationEngine(valid)

    # 1. console report for one customer (first customer unless one is given)
    customer_id = sys.argv[1].strip().upper() if len(sys.argv) > 1 else engine.customers()[0]
    try:
        print_customer_report(engine, customer_id)
    except UnknownCustomerError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    # 2. recommendations for everyone -> CSV
    results = engine.recommend_all(n=N_RECOMMENDATIONS)
    engine.export_csv(results, OUTPUT_PATH)

    # 3. run summary
    written = sum(len(r["recommendations"]) for r in results)
    products = len({row["product_id"] for row in valid})
    print()
    print(
        f"Purchases read: {len(valid) + len(rejected)} | "
        f"used: {len(valid)} | rejected: {len(rejected)}"
    )
    print(
        f"Customers: {len(engine.customers())} | Products: {products} | "
        f"Recommendations written: {written}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())