# %%
"""
Customer Recommendation Engine

Core Python only for the engine (csv, collections, math are fine). No ML libraries.
"""
from __future__ import annotations

import csv
from pathlib import Path

DATA_PATH = Path("data") / "purchases.csv"
OUTPUT_PATH = Path("output") / "recommendations.csv"

# %%
def read_purchases(path: Path = DATA_PATH) -> tuple[list[dict], list[dict]]:
    """Return (valid_rows, rejected_rows). Decide what makes a purchase row unusable."""
    # store valid and rejected rows
    valid, rejected = [], []
    # 
    id_set = set()

    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row = {k: (v or "").strip() for k, v in row.items()}
            # clean cust id and prod id y making them  uppercase
            row["customer_id"] = row["customer_id"].upper()
            row["product_id"] = row["product_id"].upper()

            # if no prod_id or prod_name reject row
            if not row["product_id"] or not row["product_name"]:
                rejected.append({**row, "reason": "blank product"})
                continue

            # verify quantity is a number
            try:
                row["quantity"] = int(row["quantity"])
            except ValueError:
                rejected.append({**row, "reason": "quantity must be a number"})
                continue
            # reject quantity less than 0
            if row["quantity"] <= 0:
                rejected.append({**row, "reason": "quantity must be above 0"})
                continue

            # purchase id is considered unique, reject duplicate
            if row["purchase_id"] in id_set:
                rejected.append({**row, "reason": "duplicate purchase_id"})
                continue
            id_set.add(row["purchase_id"])

            valid.append(row)

    return valid, rejected


# %%
def jaccard(a: set, b: set) -> float:
    """|A intersection B| / |A union B|. Define (and test) what happens when both are empty."""
    union = a | b
    # if no data in either set, return 0
    if not union:
        return 0.0
    # find similarity rate, 
    # find len(matching data in set a and set b)
    # divide by len of total data
    return len(a & b) / len(union)



# %%
class UnknownCustomerError(KeyError):
    # call if cust_id has no purchases made
    def __init__(self, customer_id: str) -> None:
        super().__init__(customer_id)
        self.customer_id = customer_id

    def __str__(self) -> str:
        return f"Unknown customer! {self.customer_id!r} has no purchase history. "

# %%
class RecommendationEngine:
    """Recommends products a customer has not bought, based on similar customers."""

    def __init__(self, purchases: list[dict], min_similarity: float = 0.0) -> None:
        # TODO: build customer -> set of products, product -> name/category,
        # and product -> purchase count (popularity) structures here, once.
        self.min_similarity = min_similarity

        # create history based on cust ids
        self._histories: dict[str, set[str]] = {}
        # set of prod ids
        self._products: dict[str, dict[str, str]] = {}
        # no of purchases per prod id
        self._popularity: dict[str, int] = {}
        # collect cust names
        self._customer_names: dict[str, str] = {}
        


        # loop over the data
        for row in purchases:
            # collect cust id and prod id from data
            cust_id, prod_id = row["customer_id"], row["product_id"]

            self._customer_names.setdefault(cust_id, row["customer_name"])
            # find each cust id and the prod in the purchase
            self._histories.setdefault(cust_id, set()).add(prod_id)
            # get prod id, and its category
            self._products.setdefault(
                prod_id, {"name": row["product_name"], "category": row["category"]}
            )

            # count every time a unique prod id is found
            self._popularity[prod_id] = self._popularity.get(prod_id, 0) + 1
           
        self._max_popularity = max(self._popularity.values(), default=1)


    def history(self, customer_id: str) -> set[str]:
        # return cust purchase history when called, else return empty
        return set(self._histories.get(customer_id, ()))


    def customers(self) -> list[str]:
        return sorted(self._histories)


    def customer_name(self, customer_id: str) -> str:
        if customer_id not in self._customer_names:
            raise UnknownCustomerError(customer_id)
        return self._customer_names[customer_id]


    def similarity(self, customer_a: str, customer_b: str) -> float:
        # using jaccard function to compare 2 customers
        # pass history func to get customer purchase hist
        return jaccard(self.history(customer_a), self.history(customer_b))
    

    def similar_customers(self, customer_id: str, k: int = 3) -> list[tuple[str, float]]:
        """Return the k most similar other customers as (customer_id, score), best first."""

        # if cust not in data
        if customer_id not in self._histories:
            raise UnknownCustomerError(customer_id)

        scored = [
            # calculate similarity against passed cust id
            (other_cust, self.similarity(customer_id, other_cust))
            for other_cust in self._histories
            # ensure current cust id is not compared to itself
            if other_cust != customer_id
        ]

        # unpack cust and similarity score, check if score is greater than min similarity passed
        # round off score to 3 decimal places
        scored = [(c, round(s, 4)) for c, s in scored if s >= self.min_similarity]
        # sort by first cheking the score, incase of tie, sort by cust id
        scored.sort(key=lambda pair: (-pair[1], pair[0]))

        return scored[:k]


    def candidate_products(self, customer_id: str, k: int = 3) -> dict[str, dict]:
        """Products bought by similar customers but not by this one, with the evidence for each."""
        # get products cust has already purchased, 
        owned = self.history(customer_id)
        # set to store possible products to recommend
        candidates: dict[str, dict] = {}

        # call similar_customers funct to get cust ids and similarity scores 
        for other_cust, sim in self.similar_customers(customer_id, k):
            # find prod other cust purchased that current cust has not
            for prod_id in self._histories[other_cust] - owned:
                # use setdefault to retrieve products, does not replace already existing products
                entry = candidates.setdefault(
                    prod_id, 
                    {
                        # dynamically unpack products into variables
                        **self._products[prod_id],
                        # indicate prod is recommended by similar purchases
                        "source": "Others also bought",
                        # list of cust who also bought product
                        "supporters": [],
                        "similarity_sum": 0.0,
                        # popularity value from popularity func
                        "popularity": self._popularity[prod_id]
                    },
                )
                # evidence for recommendation
                # store cust who bought recommended prod, and similarity score
                entry["supporters"].append((other_cust, sim))
                entry["similarity_sum"] += sim

        
        if candidates:
            return candidates
        
        # products not owned by current cust
        not_owned = [
                    # return  prod id
                     prod_id 
                     # loop through prods ids returned by popularity func
                     for prod_id in self._popularity 
                    # for products curent cust doesnt own
                     if prod_id not in owned]

        # sort prod ids by popularity in ascending order, if a tie sort by prod id
        not_owned.sort(key=lambda prod_id: (-self._popularity[prod_id], prod_id))

        # returning fallback recommendations
        # recommending by popularity
        return {
            prod_id: {
                **self._products[prod_id],
                "source": "popular products",
                "similarity_sum": 0.0,
                "supporters": [],
                "popularity": self._popularity[prod_id],
            }
            for prod_id in not_owned[:k]
        }


    # set popularity base at 0.5 to be gauge from center 
    POPULARITY_BASE = 0.5

    def score(self, evidence: dict) -> float:
        # score = similarity_sum * popularity_base (popularity / highest popularity prod)
        popularity_level = evidence["popularity"] / self._max_popularity
        return evidence["similarity_sum"] + round(self.POPULARITY_BASE * popularity_level, 3)


    def recommend(self, customer_id: str, n: int = 3) -> list[dict]:
        recommendations = self.candidate_products(customer_id)

        ranked = [
            {"product_id": prod_id, **evidence, "score": self.score(evidence)}
            for prod_id, evidence in recommendations.items()
        ]

        # sort by score in descending order, if any ties sort by product id
        ranked.sort(key=lambda r: (-r["score"], r["product_id"]))

        # return slice upto n value passed
        return ranked[:n]


    def recommend_all(self, n: int = 3) -> list[dict]:
        # recommend for all customers
        if n < 1:
            raise ValueError("n must be greater than zero")
        # use customers() func to collect cust id and products they have purchased
        # call recommend to get products they havent purchased
        return [
            {"customer_id": cust_id, "recommendations": self.recommend(cust_id, n)}
            for cust_id in self.customers()
        ]
    

    CSV_COLUMNS = [
        "customer_id", "customer_name", "rank", "product_id", "product_name", "category",
        "score", "supporting_customers"
    ]


    def export_csv(self, rows: list[dict], path: Path = OUTPUT_PATH) -> None:
        by_customer = {}

        for row in rows:
            if row["customer_id"] not in self._histories:
                raise UnknownCustomerError(row["customer_id"])
            by_customer[row["customer_id"]] = row["recommendations"]


        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self.CSV_COLUMNS)

            for cust_id in self.customers():
                name = self._customer_names[cust_id]
                rcmd = by_customer.get(cust_id, [])

                # if no recommendations create empty columns
                if not rcmd:
                    writer.writerow([cust_id, name, "", "", "", "", "", ""])
                    continue

                for rank, r in enumerate(rcmd, start=1):
                    writer.writerow([
                        cust_id, name, rank, r["product_id"], r["name"], r["category"],
                        f"{r['score']:.4f}",
                        ";".join(c for c, _ in r["supporters"]),
                    ])



# %%
if __name__ == "__main__":
    valid, rejected = read_purchases()
    engine = RecommendationEngine(valid)
    results = engine.recommend_all(n=3)
    engine.export_csv(results)
    print("Exported recommendations to csv file ")
