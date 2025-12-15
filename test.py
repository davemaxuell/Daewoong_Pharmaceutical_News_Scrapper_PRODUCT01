import feedparser

RSS_URL = "https://news.google.com/rss/search?q=artificial+intelligence&hl=en-US&gl=US&ceid=US:en"

feed = feedparser.parse(RSS_URL)

print("=" * 60)
print("FEED METADATA")
print("=" * 60)

for key, value in feed.feed.items():
    print(f"{key}: {value}")

print("\n" + "=" * 60)
print("ENTRIES (ARTICLES)")
print("=" * 60)
print("total articles: ", len(feed.entries))
for i, entry in enumerate(feed.entries[:5], start=1):
    print(f"\n--- Article {i} ---")

    for key in entry.keys():
        print(f"{key}: {entry.get(key)}")
