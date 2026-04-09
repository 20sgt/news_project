import streamlit as st
from google.cloud import storage
from dotenv import load_dotenv
import os
import json
from datetime import datetime
import pandas as pd 
import plotly.express as px
import re

load_dotenv()
BUCKET_NAME = os.getenv("GCP_BUCKET")

def get_gcs_client():
    return storage.Client()

def get_latest_csv(bucket_name: str, prefix: str) -> str:
    client = get_gcs_client()
    blobs = list(client.list_blobs(bucket_name, prefix=prefix))
    if not blobs:
        raise ValueError(f"No files found in gs://{bucket_name}/{prefix}")
    blobs.sort(key=lambda b: b.updated, reverse=True)
    latest = blobs[0].name
    return f"gs://{bucket_name}/{latest}"


def load_data_from_gcs(gcs_path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(gcs_path)
    except Exception as e:
        st.error(f"Failed to load data from GCS: {e}")
        return pd.DataFrame()


#Upload data to GCS
def upload_to_gcs(blob_name, data):
    client = get_gcs_client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(json.dumps(data))
    st.success(f"Data saved to GCS as {blob_name}")

#Read data from GCS
def read_from_gcs(blob_name):
    client = get_gcs_client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_name)
    if blob.exists():
        content = blob.download_as_text()
        return json.loads(content)
    return []

def calculate_sentiment_score(comment):
    """
    Calculate sentiment score based on comment characteristics.
    Score ranges from 0 (apathetic) to 10+ (highly captivated)
    """
    if not comment or not isinstance(comment, str):
        return 0
    
    score = 0
    
    # Base score from length (longer comments = more engagement)
    length = len(comment)
    if length > 200:
        score += 3
    elif length > 100:
        score += 2
    elif length > 50:
        score += 1
    
    # Exclamation points (excitement/strong emotion)
    exclamation_count = comment.count('!')
    score += min(exclamation_count * 1.5, 4)  # Cap at 4 points
    
    # Question marks (engagement/curiosity)
    question_count = comment.count('?')
    score += min(question_count * 0.5, 2)  # Cap at 2 points
    
    # ALL CAPS words (strong emotion)
    caps_words = len([word for word in comment.split() if word.isupper() and len(word) > 2])
    score += min(caps_words * 0.5, 2)  # Cap at 2 points
    
    # Emojis/emoticons (emotional expression)
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        "]+", flags=re.UNICODE)
    emoji_count = len(emoji_pattern.findall(comment))
    score += min(emoji_count * 1, 3)  # Cap at 3 points
    
    # Repetition of punctuation (emphasis)
    repeated_punct = len(re.findall(r'[!?.]{2,}', comment))
    score += min(repeated_punct * 0.5, 2)
    
    return round(score, 1)


def read_all_platform_data():
    """Read scraped data from ALL platforms in GCS"""
    client = get_gcs_client()
    bucket = client.bucket(BUCKET_NAME)
    
    all_posts = []
    platforms = ['Bluesky/', 'truth/', 'tweets/']

    for platform_prefix in platforms:
        blobs = bucket.list_blobs(prefix=platform_prefix)
        for blob in blobs:
            if blob.name.endswith('.json'):
                try:
                    content = blob.download_as_text()
                    data = json.loads(content)
                    all_posts.extend(data)
                except Exception as e:
                    st.warning(f"Could not read {blob.name}: {str(e)}")
    
    return all_posts

#config
st.set_page_config(page_title="Newscaster", layout="centered")
st.title("Newscaster")

st.markdown("""
<p style='font-size:16px; color:#CCCCCC;'>
There are so many news sources available to the public, yet most of them report on the same events differently depending on what political party they are most affiliated with.  
Using <b>Newscaster</b>, you can see what the vibe is! We look into the comments, rating them as “positive”, “negative”, or “neutral”, and compile them into visualizations so you can see what the sentiment is across platforms!
</p>
""", unsafe_allow_html=True)

try:
    gcs_path = get_latest_csv(BUCKET_NAME, "log/")
    df = load_data_from_gcs(gcs_path)

    #show only one clean chart
    if "platform" in df.columns and "sentiment" in df.columns:
        st.subheader("Sentiment by Platform")

        #converting column 'sentiments' to numeric scores
        if df["sentiment"].dtype == "object":
            mapping = {"positive": 1, "neutral": 0, "negative": -1}
            df["sentiment"] = df["sentiment"].map(mapping)

        avg_sentiment = df.groupby("platform")["sentiment"].mean().reset_index()

        platform_colors = {
            "BlueSky": "#2c85e6",
            "Truth Social": "#a14047",
            "Reddit": "#fa6a28"}

        fig = px.bar(
            avg_sentiment,
            x="platform",
            y="sentiment",
            text="sentiment",
            color="platform",
            color_discrete_map=platform_colors)
        fig.update_layout(
            xaxis_title="Platform",
            yaxis_title="Average Sentiment",
            xaxis_tickangle=0,
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False)
        fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Columns 'platform' and 'sentiment' not found in the dataset.")

except Exception as e:
    st.warning(f"Could not load CSV: {e}")

st.markdown("""
<p style='font-size:16px; color:#CCCCCC;'>
Starting from a neutral baseline of zero, we can see which platform has an overall positive or negative “Sentiment”.
</p>
""", unsafe_allow_html=True)

# ----- (2) SCATTER: sentiment over last 5 days -----
st.subheader("Sentiment Over Time — Last 5 Days (Scatter)")

try:
    gcs_path = get_latest_csv(BUCKET_NAME, "log/")
    df_scatter = load_data_from_gcs(gcs_path)

    if not df_scatter.empty and "date" in df_scatter.columns:
        if df_scatter["sentiment"].dtype == "object":
            mapping = {"positive": 1, "neutral": 0, "negative": -1}
            df_scatter["sentiment"] = df_scatter["sentiment"].map(mapping)

        # --- normalize columns ---
        df_scatter["date"] = pd.to_datetime(df_scatter["date"], errors="coerce").dt.date
        df_scatter["platform"] = df_scatter["platform"].astype(str).str.strip().str.title()
        df_scatter["platform"] = df_scatter["platform"].replace({
            "Truthsocial": "Truth Social",
            "Truth": "Truth Social"
        })

        # --- last 5 days only ---
        recent_cutoff = pd.Timestamp.now().date() - pd.Timedelta(days=5)
        df_scatter = df_scatter[df_scatter["date"] >= recent_cutoff]

        # --- plot ---
        if not df_scatter.empty:
            import altair as alt
            chart = alt.Chart(df_scatter).mark_circle(size=70).encode(
                x=alt.X("date:T", title="Date (last 5 days)"),
                y=alt.Y("sentiment:Q", title="Sentiment scale (−1 = neg, +1 = pos)"),
                color=alt.Color("platform:N", legend=alt.Legend(title="Platform")),
                tooltip=["platform", "sentiment", "date"]
            ).properties(height=350)

            st.altair_chart(chart, use_container_width=True)
            st.caption("Each dot is one comment. More clusters on a day ⇒ more similar sentiments that day.")
        else:
            st.info("No recent sentiment data found for the last 5 days.")
    else:
        st.info("No 'date' column found in CSV or data unavailable.")

except Exception as e:
    st.warning(f"Could not load scatter data: {e}")



#sidebar
st.sidebar.title("Navigation")
section = st.sidebar.radio("Go to:", ["Keywords", "Comments", "Sentiment Analysis"])

#keywords
if section == "Keywords":
    st.header("Keywords")
    st.write("Enter a topic or phrase to store and later analyze trending keywords.")

    keyword = st.text_input("Enter a keyword or topic:")
    if st.button("Save Keyword"):
        if keyword:
            existing_keywords = read_from_gcs("keywords.json")
            existing_keywords.append({
                "keyword": keyword,
                "timestamp": datetime.now().isoformat()})
            upload_to_gcs("keywords.json", existing_keywords)
        else:
            st.warning("Please enter a keyword before saving.")

    #saved keywords
    st.subheader("Stored Keywords")
    keywords_data = read_from_gcs("keywords.json")
    if keywords_data:
        for item in reversed(keywords_data[-5:]):
            st.write(f"- **{item['keyword']}** ({item['timestamp'][:19]})")
    else:
        st.write("No keywords saved yet.")

#Comments
elif section == "Comments":
    st.header("Comments")
    st.write("Share your thoughts about the latest news below!")

    comment = st.text_area("Write your comment:")
    if st.button("Submit Comment"):
        if comment.strip():
            existing_comments = read_from_gcs("comments.json")
            existing_comments.append({
                "comment": comment.strip(),
                "timestamp": datetime.now().isoformat()})
            upload_to_gcs("comments.json", existing_comments)
        else:
            st.warning("Please enter a comment before submitting.")

    #recent comments
    st.subheader("Recent Comments")
    comments_data = read_from_gcs("comments.json")
    if comments_data:
        for c in reversed(comments_data[-5:]):
            st.info(f"{c['timestamp'][:19]} — {c['comment']}")
    else:
        st.write("No comments yet.")

# Sentiment Analysis
elif section == "Sentiment Analysis":
    st.header("Sentiment Analysis Across Platforms")
    st.write("""
    By assigning a value of -1 to negative comments, 0 to neutral, and +1 to positive comments, we can create a "score". Using these scores, 
    we can get a birds-eye view of the general sentiment scale across platforms.
    """)

    try:
        gcs_path = get_latest_csv(BUCKET_NAME, "log/")
        df = load_data_from_gcs(gcs_path)

        # Ensure 'sentiment' column is numeric
        if df["sentiment"].dtype == "object":
            mapping = {"positive": 1, "neutral": 0, "negative": -1}
            df["sentiment"] = df["sentiment"].map(mapping)

        # Calculate average sentiment per platform
        sentiment_by_platform = (
            df.groupby("platform")["sentiment"]
            .agg(['mean', 'count'])
            .reset_index()
            .rename(columns={"mean": "Average Sentiment Score", "count": "Number of Comments"})
        )
        sentiment_by_platform = sentiment_by_platform.sort_values("Average Sentiment Score", ascending=False)

        # Display quick metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Comments Analyzed", len(df))
        with col2:
            st.metric("Average Sentiment Score", f"{df['sentiment'].mean():.2f}")
        with col3:
            st.metric("Platforms Tracked", df["platform"].nunique())

        st.markdown("---")

        # Bar chart
        st.subheader("Sentiment Score by Platform")
        fig = px.bar(
            sentiment_by_platform,
            x="platform",
            y="Average Sentiment Score",
            title="Average Sentiment Score Across Social Media Platforms",
            labels={"Average Sentiment Score": "Sentiment Score (−1 = Negative, 0 = Neutral, +1 = Positive)"},
            color="Average Sentiment Score",
            color_continuous_scale="RdYlGn",
            text="Average Sentiment Score",
        )
        fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
        fig.update_layout(
            xaxis_title="Platform",
            yaxis_title="Sentiment Score",
            showlegend=False,
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Detailed table
        st.subheader("Detailed Statistics by Platform")
        st.dataframe(
            sentiment_by_platform.style.background_gradient(
                subset=["Average Sentiment Score"], cmap="RdYlGn"
            ),
            use_container_width=True,
        )

    except Exception as e:
        st.warning(f"Could not load CSV: {e}")
