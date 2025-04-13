import streamlit as st
import pandas as pd
import openai
import re
import io
import httpx

st.set_page_config(page_title="Keyword Conversion Scorer", page_icon="🔍")
st.title("🔍 Keyword Conversion Scorer")

# Sidebar – API key input
openai_api_key = st.sidebar.text_input("Enter your OpenAI API Key", type="password").strip()

# Business inputs
st.header("📋 Business Context")
industry = st.text_input("Industry/Niche (e.g., SaaS, fitness, logistics, e-commerce)")
business_desc = st.text_area("Business Description")
conversion_goal = st.text_input("Conversion Goal (e.g., 'book a demo', 'purchase')")
services = st.text_area("Key Services or Products (e.g., steel doors, fire exit doors, security front doors)")
audience = st.text_area("Target Audience")

# Upload CSV
st.header("📂 Upload CSV File")
csv_file = st.file_uploader("Upload a CSV with a 'keywords' column", type=["csv"])

# All fields must be filled to proceed
can_run = all([
    openai_api_key,
    industry.strip(),
    business_desc.strip(),
    conversion_goal.strip(),
    services.strip(),
    audience.strip(),
    csv_file
])

if can_run:
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        st.error(f"❌ Failed to read CSV file: {e}")
        st.stop()

    if 'keywords' not in df.columns:
        st.error("❌ The uploaded CSV must contain a column named 'keywords'.")
        st.stop()
    
    # Validate API key format
    if not openai_api_key.startswith("sk-"):
        st.error("❌ Invalid OpenAI API key. It should start with 'sk-'.")
        st.stop()

    # Initialize OpenAI client with custom HTTP client
    try:
        http_client = httpx.Client()  # No proxies
        client = openai.OpenAI(api_key=openai_api_key, http_client=http_client)
    except Exception as e:
        st.error(f"❌ Failed to initialize OpenAI client: {e}")
        st.stop()

    # Clean keywords and track valid ones
    df['keywords'] = df['keywords'].fillna('')  # Replace NaN with empty string
    valid_keywords = df['keywords'].str.strip() != ''  # Valid keywords are non-empty
    keywords = df.loc[valid_keywords, 'keywords'].tolist()  # Only valid keywords for scoring
    if not keywords:
        st.error("❌ No valid keywords found in the CSV.")
        st.stop()

    batch_size = 10

    def score_keywords_batch(keywords):
        scored_keywords = []
        total = len(keywords)

        for i in range(0, total, batch_size):
            batch = keywords[i:i + batch_size]
            st.write(f"🧠 Processing batch {i // batch_size + 1} of {(total // batch_size) + 1}")

            prompt = f"""
You are a digital marketing expert specializing in content marketing. The business you're helping works in the following industry: {industry}.
Their description: {business_desc}
Primary conversion goal: {conversion_goal}
Key services or products: {services}
Target audience: {audience}

Score each keyword (representing a content idea) on a scale of 1–5 based on how closely it aligns with the business’s specific offerings (as described in the key services or products) and its potential to guide the target audience toward the conversion goal (e.g., through CTAs, content engagement, or natural progression into the sales funnel). Prioritize keywords that directly mention or strongly relate to the business’s products, services, or conversion goal, as these are most likely to drive conversions:

- 5 = Extremely aligned: The content idea directly mentions the business’s products, services, or conversion goal, with strong potential to drive conversions by addressing specific customer needs or pain points (e.g., for a business selling '{services}', a keyword like 'best {services} for {audience}' would score 5).
- 4 = Highly aligned: The content idea is closely tied to the business’s offerings or audience needs, attracting users who are researching solutions that could lead to the business’s products/services, with clear opportunities for CTAs (e.g., for a business with conversion goal '{conversion_goal}', a keyword like 'how to achieve {conversion_goal}' would score 4).
- 3 = Moderately aligned: The content idea is relevant to the business’s industry or audience interests and could attract potential customers, but requires more education or nurturing to convert (e.g., for an industry '{industry}', a keyword like 'top trends in {industry}' would score 3).
- 2 = Loosely aligned: The content idea has a weak connection to the business’s industry or audience, with low or indirect conversion potential (e.g., for a business selling '{services}', a keyword like 'general tips for {industry}' might score 2).
- 1 = Minimally aligned: The content idea is only tangentially related to the business’s offerings, industry, or audience, with minimal likelihood of driving conversions (e.g., for a business selling '{services}', a keyword like 'unrelated topic in {industry}' would score 1).

Here is the list of keywords:
{chr(10).join(f"{j+1}. {kw}" for j, kw in enumerate(batch))}

Return scores like:
1. 5
2. 3
3. 2
"""

            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a keyword conversion scoring expert."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=800,
                    temperature=0.1  # Reduced for more deterministic scoring
                )

                lines = response.choices[0].message.content.strip().split('\n')
                scores = []

                for line in lines:
                    match = re.match(r'^\d+\.\s*(\d)', line.strip())
                    score = int(match.group(1)) if match else 1
                    scores.append(score)

                while len(scores) < len(batch):
                    scores.append(1)

                scored_keywords.extend(scores)

            except Exception as e:
                st.error(f"❌ Error processing batch starting with '{batch[0]}': {e}")
                scored_keywords.extend([1] * len(batch))

        return scored_keywords

    st.info("⚙️ Scoring in progress. This may take a minute...")
    # Initialize score column with default value (1) for all rows
    df['score'] = 1
    # Score valid keywords
    valid_scores = score_keywords_batch(keywords)
    # Assign scores to valid rows
    df.loc[valid_keywords, 'score'] = valid_scores[:len(df[valid_keywords])]
    st.success("✅ Scoring complete!")

    st.dataframe(df.head(20))

    csv_out = io.StringIO()
    df.to_csv(csv_out, index=False)
    st.download_button(
        "📥 Download Scored CSV",
        data=csv_out.getvalue(),
        file_name="scored_keywords.csv",
        mime="text/csv"
    )
else:
    st.warning("🚧 Please complete all fields and upload a CSV to begin.")
