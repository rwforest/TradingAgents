"""Test URL filtering to ensure image URLs are excluded."""

import re
from urllib.parse import urlparse

# Sample URLs from actual reports
test_urls = [
    # Image URLs (should be excluded)
    "https://cdn.benzinga.com/files/images/story/2025/10/29/AI--chips-shutterstock-2198551397.jpeg?width=1200&height=800&fit=crop",
    "https://g.foolcdn.com/editorial/images/838371/oil-rig-construction-industrial-energy.jpg",
    "https://staticx-tuner.zacks.com/images/articles/main/06/2358.jpg",

    # News article URLs (should be kept)
    "https://www.benzinga.com/news/25/10/48494920/magnificent-seven-market-cap-today-china-japan-gdp-nvidia-5-trillion-ai-jensen-huang-mags-etf",
    "https://www.fool.com/investing/2025/10/29/does-billionaire-philippe-laffont-know-something-w/",
    "https://www.zacks.com/stock/news/2779736/zacks-investment-ideas-feature-highlights-microsoft",
    "https://www.globenewswire.com/news-release/2025/10/29/3176727/0/en/Tevogen-Senior-Management.html",
]

# Filtering logic from run_with_logging_v2.py
exclude_patterns = [
    r'\.png$', r'\.jpg$', r'\.jpeg$', r'\.gif$', r'\.svg$', r'\.ico$',
    r'\.webp$', r'\.bmp$',
    r'/images/', r'/cdn/', r'/assets/', r'/static/',
    r'schema\.png', r'logo\.',
    r'width=', r'height=', r'fit=crop',
]

news_domains = [
    'yahoo.com', 'finance.yahoo.com',
    'bloomberg.com', 'reuters.com',
    'cnbc.com', 'marketwatch.com', 'wsj.com',
    'fool.com', 'seekingalpha.com',
    'benzinga.com', 'globenewswire.com',
    'cointelegraph.com', 'decrypt.co',
    'zacks.com', 'finhub.io',
    'reddit.com',
]

filtered_urls = set()

for url in test_urls:
    # Clean up URL
    url = re.sub(r'[,;.)\]]+$', '', url)

    # Skip very long URLs
    if len(url) > 200:
        continue

    # Check if URL matches exclude patterns
    if any(re.search(pattern, url, re.IGNORECASE) for pattern in exclude_patterns):
        print(f"❌ EXCLUDED (image): {url[:80]}...")
        continue

    # Parse domain
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Only keep if from known news domains
        if any(news_domain in domain for news_domain in news_domains):
            # For Benzinga, only keep article URLs, not image CDN
            if 'benzinga.com' in domain:
                if '/cdn.benzinga.com/' in url or 'cdn-cgi' in url:
                    print(f"❌ EXCLUDED (CDN): {url[:80]}...")
                    continue
                # Keep actual article URLs
                if any(path in url for path in ['/news/', '/markets/', '/insights/', '/opinion/', '/pressreleases/', '/trading-ideas/']):
                    filtered_urls.add(url)
                    print(f"✅ KEPT (article): {url[:80]}...")
            else:
                filtered_urls.add(url)
                print(f"✅ KEPT (news): {url[:80]}...")
        else:
            print(f"❌ EXCLUDED (not news): {url[:80]}...")
    except:
        print(f"❌ EXCLUDED (malformed): {url[:80]}...")

print(f"\n{'='*60}")
print(f"Results: {len(filtered_urls)} news URLs kept out of {len(test_urls)} total")
print("="*60)

for url in sorted(filtered_urls):
    print(f"  - {url}")
