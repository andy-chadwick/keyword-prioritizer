# app.py

import streamlit as st
import pandas as pd
import openai
import re
import io

# Title
st.title("🔍 Keyword Prioritization Scorer (AI-powered)")

# Sidebar Inputs
st.sidebar.header("🛠️ Configuration")

api_key = st.sidebar.text_input("OpenAI API Key", type="password")
openai.api_key = api_key

# Business Context Inputs
st.header("📋 Business Context")

niche = st.text_input("Business Niche / Industry", help="e.g., Third-party logistics, Online fitness coaching")
description = st.text_area("Business Description", help="What does the business do? Products/services? Unique selling points?")
conversion_goal = st.text_input("Primary Conversion Goal", help="e.g., Sign up for service, Book a call, Buy product")
service_pages = st.text_area("Key Service/Product Pages", help="e.g., 3PL fulfillment, Nutrition plans")
audience = st.text_area("Target Audience", help="e.g., B2B brands, busy professionals, SMB owners")

# File Upload
st.header("📂 Upload Your Keyword CSV")
uploaded_file = st.file_uploader("Upload a CSV with a 'keywords' column", type=["csv"])

# Processing logic
if uploaded_file and api_key and niche and description and conversion_goal and service_pages and audience:
    df = pd.read_csv(uploaded_file)

    if 'keywords' not in df.columns:
        st.error("❌ Your CSV must contain a 'keywords' column.")
    else:
        keywords = df['keywords'].tolist()
        batch_size = 10

        st.info(f"✅ {len(keywords)} keywords loaded. Scoring in batches of {batch_size}...")

        def score_keywords_batch(keywords):
            scored_keywords = []
            total = len(keywords)

            for i in range(0, total, batch_size):
                batch = keywords[i:i + batch_size]
                st.write(f"Processing batch {i // batch_size + 1} of {total // batch_size + 1}")

                prompt = f"""
You are a digital marketing expert for the following business:

Industry: {niche}
Business Description: {description}
Conversion Goal: {conversion_goal}
Key Service/Product Pages: {service_pages}
Target Audience: {audience}

Your task is to score each keyword below from 1 to 5 based on likelihood of leading to a conversion:
- 5: Direct match to service-level page or very high commercial intent.
- 4: Closely related to services with clear intent.
- 3: Mid-funnel research or consideration intent.
- 2: Top-of-funnel informational queries.
- 1: Unrelated or low-intent content.

Return scores in the format:
1. 5
2. 3
3. 2

Keywords:
{chr(10).join(f"{j+1}. {kw}" for j, kw in enumerate(batch))}
"""

                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "You are a keyword intent scoring expert."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.2,
                        max_tokens=500
                    )
                    lines = response['choices'][0]['message']['content'].strip().split('\n')
                    scores = []

                    for line in lines:
                        match = re.match(r'^\d+\.\s*(\d+)', line.strip())
                        if match:
                            score = int(match.group(1))
                            scores.append(score)
                        else:
                            scores.append(1)  # fallback

                    while len(scores) < len(batch):
                        scores.append(1)

                    scored_keywords.extend(scores)

                except Exception as e:
                    st.error(f"Error in batch starting with '{batch[0]}': {e}")
                    scored_keywords.extend([1] * len(batch))

            return scored_keywords

        # Score keywords
        scores = score_keywords_batch(keywords)
        df['score'] = scores

        st.success("✅ Scoring complete!")

        st.dataframe(df.head(15))

        # Download link
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        st.download_button(
            label="📥 Download Scored CSV",
            data=csv_buffer.getvalue(),
            file_name="scored_keywords.csv",
            mime="text/csv"
        )

else:
    st.warning("⬅️ Fill in all the fields and upload a CSV to begin.")
