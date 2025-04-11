import streamlit as st
import pandas as pd
import openai
import re
import io

st.set_page_config(page_title="Keyword Conversion Scorer", page_icon="🔍")
st.title("🔍 Keyword Conversion Scorer")

# Sidebar – API key input
openai_api_key = st.sidebar.text_input("Enter your OpenAI API Key", type="password").strip()

# Business inputs
st.header("📋 Business Context")
industry = st.text_input("Industry/Niche (e.g., SaaS, fitness, logistics)")
business_desc = st.text_area("Business Description")
conversion_goal = st.text_input("Conversion Goal (e.g., 'book a demo', 'purchase')")
services = st.text_area("Key Service/Product Pages")
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

    # Initialize OpenAI client
    try:
        client = openai.OpenAI(api_key=openai_api_key)
    except Exception as e:
        st.error(f"❌ Failed to initialize OpenAI client: {e}")
        st.stop()

    keywords = df['keywords'].tolist()
    batch_size = 10

    def score_keywords_batch(keywords):
        scored_keywords = []
        total = len(keywords)

        for i in range(0, total, batch_size):
            batch = keywords[i:i + batch_size]
            st.write(f"🧠 Processing batch {i // batch_size + 1} of {(total // batch_size) + 1}")

            prompt = f"""
You are a digital marketing expert. The business you're helping works in the following industry: {industry}.
Their description: {business_desc}
Primary conversion goal: {conversion_goal}
Key services: {services}
Target audience: {audience}

Score each keyword on a scale of 1–5:
- 5 = High intent to convert (direct service queries)
- 4 = Likely to convert soon (comparison or product-research terms)
- 3 = Mid-funnel (consideration)
- 2 = Informational (top-of-funnel)
- 1 = Not relevant or poor intent

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
                    temperature=0.2
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
    df['score'] = score_keywords_batch(keywords)
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
