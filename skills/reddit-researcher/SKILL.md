# Skill: reddit-researcher

Research a topic by searching Reddit for relevant discussions, threads, and community insights.

## When to use

When asked to research what Reddit thinks about a topic, find community discussions, gather opinions and experiences, or survey a subreddit for trends and sentiment.

## Procedure

1. **Clarify the research question.** What specifically does the operator want to know? Which subreddits are most relevant?

2. **Search broadly first.** Use `reddit_search` with the topic query, sorted by relevance, across all of Reddit (no subreddit filter). Note which subreddits appear most in the results — these are the community hubs for this topic.

3. **Drill into top subreddits.** For the 2-3 most relevant subreddits from step 2, use `reddit_search` scoped to each subreddit individually. Also check `reddit_feed` with `sort=top` and `time_filter=month` to see if the topic appears in trending posts.

4. **Read key threads.** For the 3-5 most relevant or highly-upvoted posts, use `reddit_post` to read the post content and top comments. Pay attention to:
   - Highly upvoted comments (community consensus)
   - Controversial or nuanced takes
   - Links to external resources people recommend
   - Common complaints or praise patterns
   - Expert-sounding voices vs. casual opinions

5. **Synthesize findings.** Summarize:
   - What the Reddit community generally thinks about this topic
   - Key points of agreement and disagreement
   - Notable insights, recommendations, or warnings from experienced users
   - Which subreddits are the main hubs for this topic
   - Any caveats (e.g. sample bias, recency of discussions, Reddit's demographic skew)

6. **Cite sources.** Include permalinks to the most relevant threads and comments so the operator can verify and dig deeper.
