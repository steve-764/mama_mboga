# Customer Recommendation Engine

A product recommender for grocery purchase data. It reads `purchases.csv`, finds customers with similar buying habits, and suggests products each customer has not bought yet. It uses core Python only (`csv` and `pathlib`), with no machine-learning libraries.

## Project structure

```
.
├── main.py                  # runs everything end to end
├── recommender.py           # the engine (reading, similarity, ranking, export)
├── requirements.txt
├── data/
│   └── purchases.csv        # input
└── output/
    └── recommendations.csv  # created when you run the program
```

## Setup

You need Python 3.9 or newer.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

The engine itself needs nothing beyond the standard library.

## How to run

Run these from the project folder (the paths to `data/` and `output/` are relative):

```bash
python main.py            # report for the first customer (C101)
python main.py C104       # report for a specific customer
```

The program does three things:

1. Prints a report for one customer.
2. Writes recommendations for every customer to `output/recommendations.csv`.
3. Prints a run summary.

An unknown customer ID prints an error such as `Unknown customer! 'C999' has no purchase history.` and exits with code 1.

## How it works

The idea is that customers who bought similar things will like similar things. In short: find people like you, then recommend what they bought that you haven't.

### `read_purchases(path)`

Reads the CSV and returns `(valid_rows, rejected_rows)`. Each rejected row is kept with a `reason`. Rules:

| Problem | What happens |
|---|---|
| Blank `product_id` or `product_name` | Rejected ("blank product") |
| Quantity not a whole number | Rejected |
| Quantity of 0 or less | Rejected |
| Repeated `purchase_id` | First one kept, later ones rejected |
| IDs in mixed case (e.g. `c106`) | Fixed by converting to uppercase, row kept |

All values are stripped of extra spaces.

### `jaccard(a, b)`

Measures how alike two sets are: the number of items they share divided by the number of distinct items in both. It ranges from 0 (nothing in common) to 1 (identical). If both sets are empty it returns 0.0.

### `RecommendationEngine`

Built once from the valid rows. It stores each customer's set of products, each product's name and category, and how many times each product was bought (its popularity).

| Method | What it does |
|---|---|
| `history(customer_id)` | The set of product IDs a customer has bought |
| `customers()` | All customer IDs, sorted |
| `customer_name(customer_id)` | The customer's name; raises `UnknownCustomerError` if unknown |
| `similarity(a, b)` | Jaccard similarity between two customers' histories |
| `similar_customers(id, k=3)` | The `k` closest other customers as `(id, score)`, best first. Ties are broken by customer ID. Customers below `min_similarity` are excluded |
| `candidate_products(id, k=3)` | Products the similar customers bought that this customer has not, with the customers who back each one |
| `score(evidence)` | Ranks a candidate (see below) |
| `recommend(id, n=3)` | The top `n` candidates, best first |
| `recommend_all(n=3)` | `recommend` for every customer |
| `export_csv(rows, path)` | Writes the recommendations to a CSV |

**Scoring.** A candidate's score is:

```
score = similarity_sum + 0.5 × (product popularity ÷ most popular product's popularity)
```

`similarity_sum` adds up the similarity of each neighbour who bought the product, so a product backed by several close neighbours scores higher. The popularity term (at most 0.5) gives a small boost to widely bought products and breaks near-ties.

**Fallback.** If a customer's neighbours have nothing new to offer, the engine recommends the most popular products the customer hasn't bought. These recommendations have no supporting customers.

## Understanding the output

### Console report

```
Customer C101 (Wanjiru) bought: {P04, P08}
Most similar customers:
  C117  jaccard=0.50
  C109  jaccard=0.33
  C113  jaccard=0.17
Recommendations:
  1. Festive Bread (Bakery)  score=1.500  because 3 similar customers bought it
  2. Pampers Size 3 (Baby)  score=0.929  because 1 similar customer bought it
  3. Kienyeji Eggs (tray) (Fresh)  score=0.524  because 1 similar customer bought it
```

- **bought** is the customer's purchase history.
- **jaccard** is how alike each neighbour's purchases are (1.00 means identical).
- **score** is the ranking score; higher is better.
- **because n similar customers bought it** is the evidence. For popularity fallback recommendations, it reads "because it is popular (n purchases)" instead.

### `output/recommendations.csv`

One row per customer and rank:

| Column | Meaning |
|---|---|
| `customer_id`, `customer_name` | The customer |
| `rank` | 1 is the best recommendation |
| `product_id`, `product_name`, `category` | The recommended product |
| `score` | The ranking score, to 3 decimal places |
| `supporting_customers` | IDs of the similar customers who bought it, separated by `;` (blank for popularity fallback) |

Every customer appears in the file. A customer with no possible recommendation gets a single row with the product columns left blank.

### Run summary

```
Purchases read: 63 | used: 60 | rejected: 3
Customers: 20 | Products: 15 | Recommendations written: 52
```

- **Purchases read** is every data row in the input file; **used** rows passed the rules above and **rejected** rows did not.
- **Customers** and **Products** count the distinct IDs in the used rows.
- **Recommendations written** is the number of recommendation rows in the CSV (blank placeholder rows are not counted).
