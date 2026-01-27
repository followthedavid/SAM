#!/usr/bin/env python3
"""
Additional Scrapers for SAM Perpetual Learning
==============================================
Plug these into perpetual_learner.py to expand data collection.
"""

import re
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

DATA_PATH = Path(__file__).parent / "data"


class ScraperBase:
    """Base class for all scrapers."""

    def __init__(self, add_example_fn, log_fn):
        self.add_example = add_example_fn
        self.log = log_fn
        self.headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}

    def fetch(self, url: str, timeout: int = 30) -> str:
        """Fetch URL with error handling."""
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode('utf-8', errors='ignore')
        except Exception as e:
            return ""


class StackOverflowScraper(ScraperBase):
    """Scrape Stack Overflow Q&A pairs."""

    TAGS = ['swift', 'ios', 'swiftui', 'python', 'rust', 'frida', 'reverse-engineering', 'macos']

    def run_cycle(self, running_flag) -> int:
        """Run one scraping cycle."""
        scraped = 0

        for tag in self.TAGS:
            if not running_flag():
                break

            try:
                # Get questions list
                url = f"https://stackoverflow.com/questions/tagged/{tag}?sort=votes&pagesize=15"
                html = self.fetch(url)
                if not html:
                    continue

                # Extract question IDs
                question_ids = re.findall(r'/questions/(\d+)/', html)[:10]

                for qid in question_ids:
                    if not running_flag():
                        break

                    # Get question page
                    q_url = f"https://stackoverflow.com/questions/{qid}"
                    q_html = self.fetch(q_url)
                    if not q_html:
                        continue

                    # Extract question title
                    title_match = re.search(r'<h1[^>]*class="[^"]*fs-headline1[^"]*"[^>]*>.*?<a[^>]*>([^<]+)</a>', q_html, re.DOTALL)
                    if not title_match:
                        title_match = re.search(r'<title>([^<]+)</title>', q_html)

                    # Extract accepted/top answer
                    answer_match = re.search(r'<div class="s-prose js-post-body"[^>]*>(.*?)</div>', q_html, re.DOTALL)

                    if title_match and answer_match:
                        question = title_match.group(1).strip()
                        answer = re.sub(r'<[^>]+>', '', answer_match.group(1)).strip()[:2000]

                        if len(answer) > 100:
                            if self.add_example(question, answer, f"stackoverflow_{tag}"):
                                scraped += 1

                    time.sleep(2)  # Rate limit

            except Exception as e:
                self.log(f"[StackOverflow] Error on {tag}: {e}")

            time.sleep(5)  # Between tags

        return scraped


class GitHubScraper(ScraperBase):
    """Scrape GitHub READMEs for project documentation."""

    SEARCHES = [
        'swift ios app',
        'swiftui example',
        'frida script ios',
        'reverse engineering tool',
        'python automation macos',
        'rust cli tool',
    ]

    def run_cycle(self, running_flag) -> int:
        """Run one scraping cycle."""
        scraped = 0

        for search in self.SEARCHES:
            if not running_flag():
                break

            try:
                # Search GitHub
                query = urllib.parse.quote(search)
                url = f"https://github.com/search?q={query}&type=repositories"
                html = self.fetch(url)
                if not html:
                    continue

                # Extract repo paths
                repos = re.findall(r'href="/([^/]+/[^/]+)"[^>]*class="[^"]*v-align-middle[^"]*"', html)[:5]

                for repo in repos:
                    if not running_flag():
                        break

                    # Get README
                    readme_url = f"https://raw.githubusercontent.com/{repo}/main/README.md"
                    readme = self.fetch(readme_url)
                    if not readme:
                        readme_url = f"https://raw.githubusercontent.com/{repo}/master/README.md"
                        readme = self.fetch(readme_url)

                    if readme and len(readme) > 200:
                        # Create Q&A from README
                        question = f"Tell me about the {repo.split('/')[-1]} project"
                        answer = readme[:2500]

                        if self.add_example(question, answer, "github_readme"):
                            scraped += 1

                    time.sleep(3)

            except Exception as e:
                self.log(f"[GitHub] Error: {e}")

            time.sleep(10)

        return scraped


class RedditScraper(ScraperBase):
    """Scrape Reddit discussions."""

    SUBREDDITS = [
        ('swift', 'apple'),
        ('iOSProgramming', 'apple'),
        ('reverseengineering', 'reverse_engineering'),
        ('rust', 'rust'),
        ('Python', 'python'),
        ('WritingPrompts', 'roleplay'),
        ('MacOS', 'apple'),
    ]

    def run_cycle(self, running_flag) -> int:
        """Run one scraping cycle."""
        scraped = 0

        for subreddit, category in self.SUBREDDITS:
            if not running_flag():
                break

            try:
                # Get subreddit JSON (old.reddit.com allows this)
                url = f"https://old.reddit.com/r/{subreddit}/top/.json?t=month&limit=10"
                json_data = self.fetch(url)
                if not json_data:
                    continue

                data = json.loads(json_data)
                posts = data.get('data', {}).get('children', [])

                for post in posts:
                    if not running_flag():
                        break

                    post_data = post.get('data', {})
                    title = post_data.get('title', '')
                    selftext = post_data.get('selftext', '')

                    # Get top comment
                    permalink = post_data.get('permalink', '')
                    if permalink:
                        comments_url = f"https://old.reddit.com{permalink}.json?limit=1"
                        comments_json = self.fetch(comments_url)
                        if comments_json:
                            try:
                                comments_data = json.loads(comments_json)
                                if len(comments_data) > 1:
                                    top_comments = comments_data[1].get('data', {}).get('children', [])
                                    if top_comments:
                                        top_comment = top_comments[0].get('data', {}).get('body', '')

                                        if title and top_comment and len(top_comment) > 50:
                                            question = title
                                            if selftext:
                                                question += f"\n{selftext[:500]}"

                                            if self.add_example(question, top_comment[:1500], f"reddit_{category}"):
                                                scraped += 1
                            except:
                                pass

                    time.sleep(2)

            except Exception as e:
                self.log(f"[Reddit] Error on r/{subreddit}: {e}")

            time.sleep(10)

        return scraped


class AppleDocsScraper(ScraperBase):
    """Scrape Apple Developer Documentation."""

    FRAMEWORKS = [
        'swiftui',
        'uikit',
        'foundation',
        'combine',
        'coreml',
        'vision',
        'homekit',
        'appintents',
    ]

    def run_cycle(self, running_flag) -> int:
        """Run one scraping cycle."""
        scraped = 0

        for framework in self.FRAMEWORKS:
            if not running_flag():
                break

            try:
                # Apple docs overview page
                url = f"https://developer.apple.com/documentation/{framework}"
                html = self.fetch(url)
                if not html:
                    continue

                # Extract description
                desc_match = re.search(r'<div class="abstract"[^>]*>(.*?)</div>', html, re.DOTALL)
                if desc_match:
                    description = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()

                    question = f"What is {framework.title()} in Apple development?"
                    if self.add_example(question, description[:1500], "apple_docs"):
                        scraped += 1

                # Extract API links for more detail
                api_links = re.findall(rf'/documentation/{framework}/([^"]+)"', html)[:5]

                for api in api_links:
                    if not running_flag():
                        break

                    api_url = f"https://developer.apple.com/documentation/{framework}/{api}"
                    api_html = self.fetch(api_url)
                    if api_html:
                        api_desc = re.search(r'<div class="abstract"[^>]*>(.*?)</div>', api_html, re.DOTALL)
                        if api_desc:
                            desc = re.sub(r'<[^>]+>', '', api_desc.group(1)).strip()
                            question = f"How do I use {api} in {framework.title()}?"
                            if self.add_example(question, desc[:1500], "apple_docs"):
                                scraped += 1

                    time.sleep(2)

            except Exception as e:
                self.log(f"[AppleDocs] Error on {framework}: {e}")

            time.sleep(5)

        return scraped


class FridaDocsScraper(ScraperBase):
    """Scrape Frida documentation and examples."""

    PAGES = [
        ('https://frida.re/docs/javascript-api/', 'JavaScript API'),
        ('https://frida.re/docs/ios/', 'iOS'),
        ('https://frida.re/docs/macos/', 'macOS'),
        ('https://frida.re/docs/examples/ios/', 'iOS Examples'),
    ]

    def run_cycle(self, running_flag) -> int:
        """Run one scraping cycle."""
        scraped = 0

        for url, topic in self.PAGES:
            if not running_flag():
                break

            try:
                html = self.fetch(url)
                if not html:
                    continue

                # Extract content sections
                sections = re.findall(r'<h[23][^>]*>([^<]+)</h[23]>\s*(<p>.*?)</(?:h[23]|div)', html, re.DOTALL)

                for heading, content in sections[:10]:
                    clean_content = re.sub(r'<[^>]+>', '', content).strip()
                    if len(clean_content) > 100:
                        question = f"How do I {heading.lower()} with Frida on {topic}?"
                        if self.add_example(question, clean_content[:1500], "frida_docs"):
                            scraped += 1

                time.sleep(3)

            except Exception as e:
                self.log(f"[FridaDocs] Error: {e}")

        return scraped


class WikipediaScraper(ScraperBase):
    """Scrape Wikipedia for general knowledge."""

    TOPICS = [
        'Swift_(programming_language)',
        'Reverse_engineering',
        'iOS',
        'MacOS',
        'Apple_Inc.',
        'LLVM',
        'Objective-C',
        'Xcode',
        'ARM_architecture_family',
        'Machine_learning',
        'Natural_language_processing',
    ]

    def run_cycle(self, running_flag) -> int:
        """Run one scraping cycle."""
        scraped = 0

        for topic in self.TOPICS:
            if not running_flag():
                break

            try:
                # Use Wikipedia API for clean text
                url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic}"
                json_data = self.fetch(url)
                if not json_data:
                    continue

                data = json.loads(json_data)
                title = data.get('title', '')
                extract = data.get('extract', '')

                if title and extract and len(extract) > 100:
                    question = f"What is {title.replace('_', ' ')}?"
                    if self.add_example(question, extract[:1500], "wikipedia"):
                        scraped += 1

                time.sleep(1)  # Wikipedia is generous with rate limits

            except Exception as e:
                self.log(f"[Wikipedia] Error on {topic}: {e}")

        return scraped


class LiteroticaScraper(ScraperBase):
    """Scrape Literotica for dialogue patterns (roleplay training)."""

    CATEGORIES = [
        'gay-male',
        'romance',
    ]

    def run_cycle(self, running_flag) -> int:
        """Run one scraping cycle."""
        scraped = 0

        for category in self.CATEGORIES:
            if not running_flag():
                break

            try:
                url = f"https://www.literotica.com/c/{category}"
                html = self.fetch(url)
                if not html:
                    continue

                # Extract story links
                story_links = re.findall(r'href="(https://www\.literotica\.com/s/[^"]+)"', html)[:5]

                for story_url in story_links:
                    if not running_flag():
                        break

                    story_html = self.fetch(story_url)
                    if not story_html:
                        continue

                    # Extract story text
                    content_match = re.search(r'<div class="panel article[^"]*"[^>]*>(.*?)</div>', story_html, re.DOTALL)
                    if content_match:
                        text = re.sub(r'<[^>]+>', '', content_match.group(1))

                        # Extract dialogue pairs
                        dialogues = self._extract_dialogues(text)
                        for q, a in dialogues[:15]:
                            if self.add_example(q, a, "roleplay_literotica"):
                                scraped += 1

                    time.sleep(3)

            except Exception as e:
                self.log(f"[Literotica] Error: {e}")

            time.sleep(10)

        return scraped

    def _extract_dialogues(self, text: str) -> List[Tuple[str, str]]:
        """Extract dialogue pairs from text."""
        dialogues = []
        quotes = re.findall(r'"([^"]{10,200})"', text)

        for i in range(0, len(quotes) - 1, 2):
            if i + 1 < len(quotes):
                q1 = quotes[i].strip()
                q2 = quotes[i + 1].strip()
                if q1 and q2:
                    dialogues.append((q1, q2))

        return dialogues[:20]


# Export all scrapers
ALL_SCRAPERS = {
    'stackoverflow': StackOverflowScraper,
    'github': GitHubScraper,
    'reddit': RedditScraper,
    'apple_docs': AppleDocsScraper,
    'frida_docs': FridaDocsScraper,
    'wikipedia': WikipediaScraper,
    'literotica': LiteroticaScraper,
}
