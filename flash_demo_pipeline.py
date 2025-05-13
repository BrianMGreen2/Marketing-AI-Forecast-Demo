
"""
Flash Demo: GA4 → AI Persona Generation → Instant Ad‑Copy Draft
Author: Brian M. Green
Description: Simulates a governance‑first AI pipeline that ingests GA4 data,
hashes PII, segments sessions with an LLM (stubbed), and drafts ad copy.
"""

import pandas as pd
import hashlib
import json
import uuid
import random
from datetime import datetime

# --------------------------------------------------------------------
# 1. Simulated GA4 Export
# --------------------------------------------------------------------
ga4_raw = pd.DataFrame({
    "session_id": [f"sess_{i}" for i in range(1, 11)],
    "user_id": [f"user_{i}" for i in range(1, 11)],
    "ga_client_id": [
        f"GA1.2.{random.randint(100000, 999999)}.{random.randint(100000, 999999)}"
        for _ in range(10)
    ],
    "pageviews": [random.randint(1, 12) for _ in range(10)],
    "total_value": [round(random.uniform(5, 250), 2) for _ in range(10)],
    "country": random.choices(["US", "CA", "GB"], k=10),
    "consent": random.choices([True, False], weights=[0.8, 0.2], k=10),
})

# --------------------------------------------------------------------
# 2. Governance‑First Guard
#    • PII hashing
#    • Consent filtering
#    • Immutable lineage ID
# --------------------------------------------------------------------
def sha256_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

# Drop non‑consented rows & hash user_id
ga4_clean = (
    ga4_raw[ga4_raw["consent"]]
    .assign(user_hash=lambda df: df["user_id"].apply(sha256_hash))
    .drop(columns=["user_id"])
)

lineage_id = str(uuid.uuid4())
ga4_clean.attrs["lineage_id"] = lineage_id
ga4_clean.attrs["processed_at"] = datetime.utcnow().isoformat() + "Z"

# --------------------------------------------------------------------
# 3. Feature Store (simplified)
# --------------------------------------------------------------------
feature_store_df = ga4_clean.copy()
feature_store_df["high_value_flag"] = feature_store_df["total_value"] > 100
feature_store_df["engagement_score"] = (
    feature_store_df["pageviews"] / feature_store_df["pageviews"].max()
)

# --------------------------------------------------------------------
# 4. “LLM” Segmenter (stub logic)
#    Replace this with an actual LLM call in production.
# --------------------------------------------------------------------
def segment_row(row):
    if row["high_value_flag"] and row["engagement_score"] > 0.6:
        return "Brand Loyalist"
    elif row["pageviews"] >= 6:
        return "Value Shopper"
    else:
        return "Speed Seeker"

feature_store_df["segment"] = feature_store_df.apply(segment_row, axis=1)

# --------------------------------------------------------------------
# 5. Generative‑AI Ad‑Copy Draft (stub)
#    Replace with OpenAI / Anthropic call.
# --------------------------------------------------------------------
def generate_copy(segment_name: str):
    base_headlines = {
        "Brand Loyalist": [
            "Because Loyalty Deserves Rewards",
            "Unlock Exclusive Perks—Just for You",
        ],
        "Value Shopper": [
            "Max Value, Zero Compromise",
            "Deals You Can’t Afford to Miss",
        ],
        "Speed Seeker": [
            "Fast Checkouts, Faster Rewards",
            "Skip the Hassle—Buy in 1‑Click",
        ],
    }
    base_bodies = {
        "Brand Loyalist": "Enjoy member‑only offers curated for our most dedicated customers.",
        "Value Shopper": "Shop top products at prices your wallet will love—no coupons needed.",
        "Speed Seeker": "Seamless shopping experience so you can get back to what matters.",
    }
    variants = []
    for headline in base_headlines[segment_name]:
        variants.append(
            {
                "headline": headline,
                "body": base_bodies[segment_name],
                "predicted_ctr": round(random.uniform(2.5, 6.5), 2),
                "compliance_score": random.choice(["green", "yellow"]),
            }
        )
    return variants

creative_library = {
    seg: generate_copy(seg) for seg in feature_store_df["segment"].unique()
}

# --------------------------------------------------------------------
# 6. Assemble JSON Payload for DSP push
# --------------------------------------------------------------------
dsp_payload = {
    "lineage_id": lineage_id,
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "campaign_name": "FlashDemo‑AutoPush",
    "creatives": creative_library,
}

# Pretty‑print payload & segment counts
if __name__ == "__main__":
    print("=== DSP Payload ===")
    print(json.dumps(dsp_payload, indent=2))
    print("\n=== Segment Counts ===")
    print(feature_store_df["segment"].value_counts())
