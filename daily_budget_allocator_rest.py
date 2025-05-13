
"""
daily_budget_allocator_rest.py
--------------------------------
Calculates channel‑level budget reallocations and pushes them to
external ad platforms via REST.  All API calls are stubbed / commented
for safety—uncomment and fill in real endpoint URLs, auth headers,
and payload shapes.
"""

import os
import uuid
import json
import datetime
import logging
from typing import Dict, List

import pandas as pd
import numpy as np
import requests
from requests.adapters import HTTPAdapter, Retry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

# ----------------------------------------------------------------------
# 1. Simulated channel KPI pull
#    Replace with BigQuery, Snowflake, or GA4 API call.
# ----------------------------------------------------------------------
def fetch_channel_kpis() -> pd.DataFrame:
    # Pretend we pulled yesterday’s spend + tomorrow’s forecast CPA
    return pd.DataFrame(
        {
            "channel": [
                "Programmatic Display",
                "CTV",
                "SEO Content",
                "Search PPC",
            ],
            "current_spend": [5000, 3000, 2000, 4000],  # USD
            "forecast_cpa": [25, 40, 15, 20],  # USD per acquisition
        }
    )


# ----------------------------------------------------------------------
# 2. Budget allocation logic
# ----------------------------------------------------------------------
def compute_new_budgets(df: pd.DataFrame) -> pd.DataFrame:
    total_budget = df["current_spend"].sum()

    # Weight inversely to CPA
    df["weight"] = 1 / df["forecast_cpa"]
    df["alloc_share"] = df["weight"] / df["weight"].sum()
    df["new_budget_raw"] = df["alloc_share"] * total_budget

    # Guardrails: 50‑150 % of yesterday’s spend
    df["new_budget_capped"] = np.maximum(
        df["new_budget_raw"], df["current_spend"] * 0.5
    )
    df["new_budget_capped"] = np.minimum(
        df["new_budget_capped"], df["current_spend"] * 1.5
    )

    # Re‑normalize
    scaling_factor = total_budget / df["new_budget_capped"].sum()
    df["new_budget"] = (df["new_budget_capped"] * scaling_factor).round(2)

    return df[["channel", "current_spend", "new_budget"]]


# ----------------------------------------------------------------------
# 3. REST client helper (retries, timeouts)
# ----------------------------------------------------------------------
def build_http_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.mount("http://", HTTPAdapter(max_retries=retries))
    return session


# ----------------------------------------------------------------------
# 4. Push allocation to each channel’s API endpoint
# ----------------------------------------------------------------------
CHANNEL_ENDPOINTS = {
    "Programmatic Display": "https://api.dsp.example.com/budget",
    "CTV": "https://api.ctv.example.com/budget",
    "SEO Content": "https://api.cms.example.com/budget",
    "Search PPC": "https://googleads.googleapis.com/v14/customers/123456/budgetOrders",
}

API_KEY = os.getenv("AD_PLATFORM_API_KEY", "REPLACE_ME")

def push_budget_updates(df: pd.DataFrame) -> List[Dict]:
    session = build_http_session()
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    results = []
    for _, row in df.iterrows():
        channel = row["channel"]
        endpoint = CHANNEL_ENDPOINTS.get(channel)
        if not endpoint:
            logging.warning("No endpoint configured for %s", channel)
            continue

        payload = {
            "lineage_id": str(uuid.uuid4()),
            "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
            "channel": channel,
            "budget": float(row["new_budget"]),
            "currency": "USD",
        }

        logging.info("POST %s -> %.2f", channel, row["new_budget"])
        # resp = session.post(endpoint, headers=headers, json=payload, timeout=10)
        # For stub demo we skip actual call
        resp = type("Resp", (object,), {"status_code": 202, "text": "stub"})()

        results.append(
            {
                "channel": channel,
                "endpoint": endpoint,
                "status_code": resp.status_code,
                "response_body": resp.text,
            }
        )
    return results


# ----------------------------------------------------------------------
# 5. Main entry
# ----------------------------------------------------------------------
if __name__ == "__main__":
    kpis = fetch_channel_kpis()
    allocation_df = compute_new_budgets(kpis)

    print("\n=== New Budget Allocation ===")
    print(allocation_df.to_string(index=False))

    updates = push_budget_updates(allocation_df)
    print("\n=== Push Results ===")
    print(json.dumps(updates, indent=2))
