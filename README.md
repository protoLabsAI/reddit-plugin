# Reddit Plugin for protoAgent

A protoAgent plugin that integrates Reddit — giving your agent tools to read and interact with Reddit as you, plus a console view that renders your favorite subreddits.

## Features

- **15 agent tools** — browse feeds, search posts, read comments, vote, comment, submit posts, manage subscriptions, and more
- **Console view** — tabbed subreddit feed reader with sort controls, auto-refresh, and dark/light theme support
- **Research skill** — guided procedure for the agent to research topics via Reddit discussions

## Setup

### 1. Create a Reddit App

1. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps/)
2. Click "create another app..."
3. Select **"script"** as the type
4. Fill in a name (e.g. "protoAgent") and set redirect URI to `http://localhost:8080`
5. Note your **client ID** (string under the app name) and **client secret**

### 2. Configure Secrets

Add to your `secrets.yaml`:

```yaml
reddit_client_id: "your_client_id"
reddit_client_secret: "your_client_secret"
reddit_username: "your_reddit_username"
reddit_password: "your_reddit_password"
```

### 3. Configure Subreddits

In your agent config (`config.yaml`):

```yaml
reddit:
  subreddits:
    - LocalLLaMA
    - langchain
    - claudeai
  default_sort: hot
  posts_per_page: 25
  time_filter: day
```

### 4. Install & Enable

```
plugin install <repo-url>
```

## Tools

### Read (9 tools)
| Tool | Description |
|------|-------------|
| `reddit_feed` | Get posts from a subreddit (hot/new/top/rising) |
| `reddit_post` | Get a single post + top comments |
| `reddit_comments` | Full comment tree for a post |
| `reddit_search` | Search posts globally or within a subreddit |
| `reddit_user` | Get a user's profile info |
| `reddit_user_posts` | A user's submission history |
| `reddit_subscriptions` | List subscribed subreddits |
| `reddit_saved` | Saved posts and comments |
| `reddit_inbox` | Check inbox messages |

### Write (6 tools)
| Tool | Description |
|------|-------------|
| `reddit_comment` | Post a comment or reply |
| `reddit_vote` | Upvote/downvote |
| `reddit_save_item` | Save/unsave a post or comment |
| `reddit_subscribe` | Subscribe/unsubscribe from a subreddit |
| `reddit_submit` | Submit a new post (text or link) |
| `reddit_message` | Send a private message |

## Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest -q

# Lint
ruff check .
ruff format --check .
```

## Notes

- Uses Reddit's official OAuth2 API (free tier, ~100 req/min)
- **2FA limitation**: If you have 2FA on your Reddit account, the password grant won't work. Use a dedicated bot account or an app-specific password.
- Write tools require explicit content — the agent won't auto-generate posts or comments without you seeing them.

## License

MIT
