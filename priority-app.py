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
    
    if not openai_api_key.startswith("sk-"):
        st.error("❌ Invalid OpenAI API key. It should start with 'sk-'.")
        st.stop()

    try:
        http_client = httpx.Client()
        client = openai.OpenAI(api_key=openai_api_key, http_client=http_client)
    except Exception as e:
        st.error(f"❌ Failed to initialize OpenAI client: {e}")
        st.stop()

    df['keywords'] = df['keywords'].fillna('')
    valid_keywords = df['keywords'].str.strip() != ''
    keywords = df.loc[valid_keywords, 'keywords'].tolist()

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
You are a digital marketing expert helping a business prioritize informational keywords for their blog content.

The business details are:
- Industry: {industry}
- Description: {business_desc}
- Key Products or Services: {services}
- Target Audience: {audience}
- Primary Conversion Goal: {conversion_goal}

You will receive a list of **informational keywords**, each representing a potential blog topic idea.

Your task is to **score each keyword from 1 to 5** based on:
1. **How naturally the keyword/topic relates to the business’s offerings**
2. **How easy it would be to include a meaningful and contextually relevant call-to-action (CTA)** toward the conversion goal within the content (e.g., linking to a product page, prompting a contact form, suggesting a demo or quote)

You're not assessing immediate buying intent. You're evaluating whether content targeting that keyword can:
- Attract the business’s target audience
- Align with the products or services the business offers
- Lead logically into a CTA without being forced or unrelated

Scoring Guidelines:
- 5 = Very strong alignment: Topic is highly relevant; CTAs fit naturally (e.g., “how to choose a fire exit door” for a business selling fire doors)
- 4 = Strong alignment: Closely related and engaging; CTAs fit smoothly
- 3 = Moderate alignment: Industry-relevant, but CTA would require a creative link
- 2 = Weak alignment: Loosely related; CTA would feel somewhat forced
- 1 = Poor alignment: Vague or off-topic; hard to link to services or conversion goal

Now, score the following keywords:
{chr(10).join(f"{j+1}. {kw}" for j, kw in enumerate(batch))}

Respond like:
1. 5
2. 4
3. 2
...
"""

            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a keyword scoring expert."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=800,
                    temperature=0.1
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
    df['score'] = 1
    valid_scores = score_keywords_batch(keywords)
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
