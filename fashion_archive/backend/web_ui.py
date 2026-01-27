#!/usr/bin/env python3
"""
Fashion Archive - Web UI
A simple, beautiful web interface for browsing the fashion archive.
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Config
API_URL = "http://localhost:8420"
st.set_page_config(
    page_title="Fashion Archive",
    page_icon="👗",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .article-card {
        padding: 1rem;
        border-radius: 8px;
        background: #f8f9fa;
        margin-bottom: 1rem;
    }
    .article-title {
        font-size: 1.2rem;
        font-weight: bold;
        color: #1a1a1a;
    }
    .article-meta {
        color: #666;
        font-size: 0.85rem;
    }
    .source-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        background: #e3f2fd;
        color: #1565c0;
        font-size: 0.75rem;
    }
</style>
""", unsafe_allow_html=True)

def fetch_api(endpoint):
    """Fetch data from API."""
    try:
        r = requests.get(f"{API_URL}{endpoint}", timeout=10)
        return r.json()
    except:
        return None

def main():
    # Sidebar
    st.sidebar.title("👗 Fashion Archive")

    # Get stats
    stats = fetch_api("/stats")
    if stats:
        st.sidebar.metric("Total Articles", f"{stats['total_articles']:,}")
        st.sidebar.metric("Total Words", f"{stats['total_words']:,}")
        st.sidebar.metric("Images", f"{stats['total_images']:,}")

        st.sidebar.markdown("---")
        st.sidebar.subheader("Sources")
        for source in stats.get('by_source', []):
            st.sidebar.write(f"**{source['name']}**: {source['count']:,}")

    # Main content
    tab1, tab2, tab3, tab4 = st.tabs(["🔍 Search", "📚 Browse", "📊 Analytics", "🤖 SAM"])

    # SEARCH TAB
    with tab1:
        st.header("Search the Archive")

        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_input("Search articles", placeholder="Enter search term (e.g., Gucci, sustainability, runway)")
        with col2:
            limit = st.selectbox("Results", [10, 25, 50, 100], index=1)

        if query:
            results = fetch_api(f"/search?q={query}&limit={limit}")
            if results and results.get('articles'):
                st.success(f"Found {results['count']} articles for '{query}'")

                for article in results['articles']:
                    with st.container():
                        st.markdown(f"### {article['title']}")

                        col1, col2, col3 = st.columns([2, 2, 1])
                        with col1:
                            st.caption(f"📰 {article.get('source_name', article['source'])}")
                        with col2:
                            st.caption(f"📅 {article.get('publish_date', 'Unknown')[:10] if article.get('publish_date') else 'Unknown'}")
                        with col3:
                            st.caption(f"📝 {article.get('word_count', 0):,} words")

                        # Show excerpt
                        content = article.get('content', '')[:500]
                        st.write(content + "..." if len(article.get('content', '')) > 500 else content)

                        # Expandable full content
                        with st.expander("Read full article"):
                            st.write(article.get('content', 'No content available'))
                            if article.get('url'):
                                st.link_button("View Original", article['url'])

                        st.markdown("---")
            else:
                st.warning(f"No results for '{query}'")

    # BROWSE TAB
    with tab2:
        st.header("Browse Articles")

        col1, col2 = st.columns(2)
        with col1:
            sources = ["All"] + [s['source'] for s in stats.get('by_source', [])] if stats else ["All"]
            source_filter = st.selectbox("Source", sources)
        with col2:
            categories = ["All"] + list(stats.get('top_categories', {}).keys())[:20] if stats else ["All"]
            category_filter = st.selectbox("Category", categories)

        # Build query
        endpoint = "/articles?limit=50"
        if source_filter != "All":
            endpoint += f"&source={source_filter}"
        if category_filter != "All":
            endpoint += f"&category={category_filter}"

        articles = fetch_api(endpoint)
        if articles and articles.get('articles'):
            for article in articles['articles']:
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**{article['title']}**")
                        st.caption(f"{article.get('source_name', '')} • {article.get('publish_date', '')[:10] if article.get('publish_date') else ''} • {article.get('word_count', 0)} words")
                    with col2:
                        if st.button("Read", key=article['id']):
                            st.session_state.selected_article = article
                    st.markdown("---")

    # ANALYTICS TAB
    with tab3:
        st.header("Analytics")

        if stats:
            # Articles by year chart
            st.subheader("Articles by Year")
            year_data = stats.get('by_year', {})
            if year_data:
                df = pd.DataFrame([
                    {"Year": k, "Articles": v}
                    for k, v in sorted(year_data.items())
                ])
                st.bar_chart(df.set_index("Year"))

            # Top categories
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Top Categories")
                cat_data = stats.get('top_categories', {})
                for cat, count in list(cat_data.items())[:10]:
                    st.write(f"**{cat.title()}**: {count:,}")

            with col2:
                st.subheader("Sources Breakdown")
                for source in stats.get('by_source', []):
                    pct = source['count'] / stats['total_articles'] * 100 if stats['total_articles'] > 0 else 0
                    st.write(f"**{source['name']}**: {source['count']:,} ({pct:.1f}%)")

            # Trend analysis
            st.subheader("Trend Analysis")
            trend_term = st.text_input("Analyze trend for term", placeholder="e.g., sustainability, streetwear")
            if trend_term:
                trend = fetch_api(f"/trends/{trend_term}")
                if trend and trend.get('data'):
                    df = pd.DataFrame(trend['data'])
                    st.line_chart(df.set_index("period")["mentions"])
                    total = sum(d['mentions'] for d in trend['data'])
                    st.caption(f"'{trend_term}' mentioned {total:,} times across the archive")

    # SAM TAB
    with tab4:
        st.header("Ask SAM")
        st.write("Query the fashion archive with natural language.")

        sam_query = st.text_area("Ask a question about fashion", placeholder="e.g., What were the major trends in 2023?")

        if st.button("Ask SAM"):
            if sam_query:
                with st.spinner("Searching archive..."):
                    context = fetch_api(f"/sam/context/{sam_query}?limit=5")
                    if context and context.get('articles'):
                        st.success(f"Found {len(context['articles'])} relevant articles")

                        st.subheader("Relevant Articles:")
                        for article in context['articles']:
                            st.markdown(f"**{article['title']}** ({article['source']}, {article.get('date', 'Unknown')[:10] if article.get('date') else 'Unknown'})")
                            st.write(article.get('excerpt', '')[:200] + "...")
                            st.markdown("---")
                    else:
                        st.warning("No relevant articles found")

if __name__ == "__main__":
    main()
