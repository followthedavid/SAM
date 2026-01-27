"""
SAM Scraper System - Job Application Training Data Spiders

Scrapes job postings, SOQ requirements, resumes, and cover letters
for training an LLM to write job application materials.
"""

import re
import json
import hashlib
from typing import Dict, Any, Optional, Iterator, List
from urllib.parse import urljoin, urlencode, parse_qs, urlparse
from datetime import datetime

import scrapy
from scrapy.http import Request, Response

from ..storage.database import ScrapedItem
from .base_spider import BaseSpider


class CalCareersSpider(BaseSpider):
    """
    Spider for California State Government Jobs (CalCareers).

    Scrapes:
    - Job postings with full descriptions
    - Statement of Qualifications (SOQ) requirements
    - Minimum/desirable qualifications
    - Salary and classification info
    """

    name = "calcareers_spider"
    source = "calcareers"
    allowed_domains = ["calcareers.ca.gov", "jobs.ca.gov"]

    rate_limit = 2.0
    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 2.0,
        "CONCURRENT_REQUESTS": 2,
    }

    # Search URL for job listings
    SEARCH_URL = "https://www.calcareers.ca.gov/CalHRPublic/Search/JobSearchResults.aspx"

    # Job categories to search
    CATEGORIES = [
        "Administrative",
        "Accounting and Auditing",
        "Information Technology",
        "Legal",
        "Engineering",
        "Scientific",
        "Human Resources",
        "Program and Policy",
        "Communications",
        "Research and Statistics",
    ]

    def __init__(self, *args, category: str = None, max_jobs: int = 500, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_category = category
        self.max_jobs = max_jobs
        self.jobs_scraped = 0

    def start_requests(self) -> Iterator[Request]:
        """Start by searching for jobs."""
        progress = self.get_progress()
        self.jobs_scraped = progress.get("total_items", 0)

        # CalCareers uses a search form - start with the main search page
        yield self.make_request(
            "https://www.calcareers.ca.gov/CalHRPublic/Search/JobSearch.aspx",
            callback=self.parse_search_page
        )

    def parse_search_page(self, response: Response) -> Iterator[Request]:
        """Parse the search page and submit search."""
        # CalCareers uses ASP.NET WebForms - we'll scrape the job listing pages
        # The direct job listing URL pattern
        yield self.make_request(
            "https://www.calcareers.ca.gov/CalHRPublic/Search/JobSearchResults.aspx",
            callback=self.parse_job_list,
            meta={"page": 1}
        )

    def parse_job_list(self, response: Response) -> Iterator[Request]:
        """Parse job listing page."""
        page = response.meta.get("page", 1)
        self.logger.info(f"Parsing CalCareers page {page}")

        # Find job links - CalCareers uses table-based layout
        job_links = response.css("a[href*='JobPosting']::attr(href)").getall()

        if not job_links:
            # Try alternative selectors
            job_links = response.css("a[href*='JC-']::attr(href)").getall()

        if not job_links:
            # Try to find any job control number links
            job_links = response.xpath("//a[contains(@href, 'JobPosting') or contains(text(), 'JC-')]/@href").getall()

        self.logger.info(f"Found {len(job_links)} job links on page {page}")

        for link in job_links:
            if self.jobs_scraped >= self.max_jobs:
                return

            url = urljoin(response.url, link)
            yield self.make_request(
                url,
                callback=self.parse_job_posting,
                meta={"list_page": page}
            )

        # Check for next page
        next_page = response.css("a[title='Next']::attr(href), a:contains('Next')::attr(href)").get()
        if next_page and len(job_links) > 0 and self.jobs_scraped < self.max_jobs:
            yield self.make_request(
                urljoin(response.url, next_page),
                callback=self.parse_job_list,
                meta={"page": page + 1}
            )

    def parse_job_posting(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse a job posting page."""
        # Extract job control number
        jc_match = re.search(r'JC-(\d+)', response.text)
        job_id = jc_match.group(1) if jc_match else hashlib.md5(response.url.encode()).hexdigest()[:12]

        # Extract title
        title = response.css("h1::text, .job-title::text, #jobTitle::text").get()
        if not title:
            title = response.xpath("//td[contains(text(), 'Position')]/following-sibling::td/text()").get()
        title = title.strip() if title else "Unknown Position"

        self.logger.info(f"Parsing job: {title} (JC-{job_id})")

        # Extract department
        department = response.css("#department::text, .department::text").get()
        if not department:
            department = response.xpath("//td[contains(text(), 'Department')]/following-sibling::td/text()").get()
        department = department.strip() if department else ""

        # Extract salary
        salary = response.xpath("//td[contains(text(), 'Salary')]/following-sibling::td/text()").get()
        if not salary:
            salary = response.css(".salary::text").get()
        salary = salary.strip() if salary else ""

        # Extract location
        location = response.xpath("//td[contains(text(), 'Location')]/following-sibling::td/text()").get()
        location = location.strip() if location else ""

        # Extract filing deadline
        deadline = response.xpath("//td[contains(text(), 'Final Filing Date')]/following-sibling::td/text()").get()
        deadline = deadline.strip() if deadline else ""

        # Extract job description
        description = self._extract_section(response, ["Duties", "Position Description", "Job Description"])

        # Extract minimum qualifications
        min_quals = self._extract_section(response, ["Minimum Requirements", "Minimum Qualifications"])

        # Extract desirable qualifications
        desirable_quals = self._extract_section(response, ["Desirable Qualifications", "Preferred Qualifications"])

        # Extract SOQ requirements - THIS IS KEY
        soq = self._extract_section(response, [
            "Statement of Qualifications",
            "SOQ",
            "Statement of Qualifications Instructions",
            "SOQ Instructions"
        ])

        # Extract application instructions
        app_instructions = self._extract_section(response, [
            "Application Instructions",
            "How to Apply",
            "Application Requirements"
        ])

        # Build full content
        content_parts = []
        if title:
            content_parts.append(f"Position: {title}")
        if department:
            content_parts.append(f"Department: {department}")
        if salary:
            content_parts.append(f"Salary: {salary}")
        if location:
            content_parts.append(f"Location: {location}")
        if description:
            content_parts.append(f"\nJob Description:\n{description}")
        if min_quals:
            content_parts.append(f"\nMinimum Qualifications:\n{min_quals}")
        if desirable_quals:
            content_parts.append(f"\nDesirable Qualifications:\n{desirable_quals}")
        if soq:
            content_parts.append(f"\nStatement of Qualifications (SOQ) Requirements:\n{soq}")
        if app_instructions:
            content_parts.append(f"\nApplication Instructions:\n{app_instructions}")

        content = "\n".join(content_parts)

        if len(content) < 200:
            self.logger.warning(f"Insufficient content for job {job_id}")
            return

        metadata = {
            "job_id": f"JC-{job_id}",
            "department": department,
            "salary": salary,
            "location": location,
            "filing_deadline": deadline,
            "has_soq": bool(soq),
            "soq_text": soq,
            "min_qualifications": min_quals,
            "desirable_qualifications": desirable_quals,
            "word_count": len(content.split()),
            "tags": ["job_posting", "california", "state_government", "soq"],
        }

        item = ScrapedItem(
            source=self.source,
            url=response.url,
            title=title,
            content=content,
            metadata=metadata,
        )

        self.jobs_scraped += 1
        self.save_progress(total_items=self.jobs_scraped)

        yield item

    def _extract_section(self, response: Response, headers: List[str]) -> str:
        """Extract a section by its header."""
        for header in headers:
            # Try various patterns
            patterns = [
                f"//h2[contains(text(), '{header}')]/following-sibling::*",
                f"//h3[contains(text(), '{header}')]/following-sibling::*",
                f"//strong[contains(text(), '{header}')]/following-sibling::*",
                f"//td[contains(text(), '{header}')]/following-sibling::td",
                f"//div[contains(@class, 'section')][contains(., '{header}')]",
            ]

            for pattern in patterns:
                elements = response.xpath(pattern)
                if elements:
                    text_parts = []
                    for elem in elements[:5]:  # Limit to avoid grabbing too much
                        text = " ".join(elem.css("*::text").getall())
                        if text.strip():
                            text_parts.append(text.strip())
                        # Stop if we hit another header
                        if elem.xpath("self::h2 or self::h3"):
                            break
                    if text_parts:
                        return "\n".join(text_parts)

        return ""


class ResumeSpider(BaseSpider):
    """
    Spider for resume/CV samples.

    Scrapes resume examples from career sites.
    """

    name = "resume_spider"
    source = "resumes"
    allowed_domains = [
        "indeed.com",
        "resumegenius.com",
        "zety.com",
        "novoresume.com",
        "resume.io",
    ]

    rate_limit = 2.0
    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 2.0,
        "CONCURRENT_REQUESTS": 1,
    }

    # Resume example pages
    SOURCES = [
        ("https://www.indeed.com/career-advice/resume-samples", "indeed"),
        ("https://resumegenius.com/resume-examples", "resumegenius"),
        ("https://zety.com/resume-examples", "zety"),
    ]

    def __init__(self, *args, max_resumes: int = 200, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_resumes = max_resumes
        self.resumes_scraped = 0

    def start_requests(self) -> Iterator[Request]:
        """Start fetching resume example index pages."""
        for url, source_name in self.SOURCES:
            yield self.make_request(
                url,
                callback=self.parse_index,
                meta={"source_name": source_name}
            )

    def parse_index(self, response: Response) -> Iterator[Request]:
        """Parse resume examples index page."""
        source_name = response.meta.get("source_name")
        self.logger.info(f"Parsing {source_name} resume index")

        # Find links to resume examples
        resume_links = response.css("a[href*='resume']::attr(href)").getall()

        for link in resume_links:
            if self.resumes_scraped >= self.max_resumes:
                return

            url = urljoin(response.url, link)

            # Skip non-example pages
            if any(skip in url for skip in ["login", "signup", "pricing", "template"]):
                continue

            yield self.make_request(
                url,
                callback=self.parse_resume_page,
                meta={"source_name": source_name}
            )

    def parse_resume_page(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse a resume example page."""
        source_name = response.meta.get("source_name")

        # Extract title (usually the job title)
        title = response.css("h1::text").get()
        if not title:
            return
        title = title.strip()

        # Extract resume content
        content_selectors = [
            ".resume-content",
            ".resume-example",
            ".resume-sample",
            "article",
            ".content-body",
        ]

        content = ""
        for selector in content_selectors:
            elem = response.css(selector)
            if elem:
                content = " ".join(elem.css("*::text").getall())
                if len(content) > 500:
                    break

        if len(content) < 300:
            return

        # Clean up content
        content = re.sub(r'\s+', ' ', content).strip()

        # Try to extract structured sections
        sections = self._extract_resume_sections(content)

        metadata = {
            "source_site": source_name,
            "job_type": self._extract_job_type(title),
            "sections": list(sections.keys()),
            "word_count": len(content.split()),
            "tags": ["resume", "cv", "job_application", source_name],
        }

        item = ScrapedItem(
            source=self.source,
            url=response.url,
            title=f"Resume Example: {title}",
            content=content,
            metadata=metadata,
        )

        self.resumes_scraped += 1
        yield item

    def _extract_resume_sections(self, content: str) -> Dict[str, str]:
        """Try to extract common resume sections."""
        sections = {}
        section_headers = [
            "Summary", "Objective", "Professional Summary",
            "Experience", "Work Experience", "Employment History",
            "Education", "Skills", "Technical Skills",
            "Certifications", "Awards", "Projects",
        ]

        for header in section_headers:
            pattern = rf'{header}[:\s]*(.+?)(?={"|".join(section_headers)}|$)'
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                sections[header.lower()] = match.group(1).strip()[:500]

        return sections

    def _extract_job_type(self, title: str) -> str:
        """Extract job type from title."""
        title_lower = title.lower()
        job_types = [
            "engineer", "developer", "manager", "analyst", "designer",
            "administrator", "coordinator", "specialist", "director",
            "assistant", "associate", "consultant", "technician",
        ]
        for jt in job_types:
            if jt in title_lower:
                return jt
        return "general"


class CoverLetterSpider(BaseSpider):
    """
    Spider for cover letter examples.
    """

    name = "coverletter_spider"
    source = "coverletters"
    allowed_domains = [
        "indeed.com",
        "thebalancemoney.com",
        "zety.com",
        "resumegenius.com",
    ]

    rate_limit = 2.0
    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 2.0,
        "CONCURRENT_REQUESTS": 1,
    }

    SOURCES = [
        ("https://www.indeed.com/career-advice/cover-letter-samples", "indeed"),
        ("https://www.thebalancemoney.com/cover-letter-samples-2060208", "balance"),
        ("https://zety.com/cover-letter-examples", "zety"),
    ]

    def __init__(self, *args, max_letters: int = 200, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_letters = max_letters
        self.letters_scraped = 0

    def start_requests(self) -> Iterator[Request]:
        """Start fetching cover letter index pages."""
        for url, source_name in self.SOURCES:
            yield self.make_request(
                url,
                callback=self.parse_index,
                meta={"source_name": source_name}
            )

    def parse_index(self, response: Response) -> Iterator[Request]:
        """Parse cover letter examples index."""
        source_name = response.meta.get("source_name")
        self.logger.info(f"Parsing {source_name} cover letter index")

        links = response.css("a[href*='cover-letter']::attr(href)").getall()

        for link in links:
            if self.letters_scraped >= self.max_letters:
                return

            url = urljoin(response.url, link)

            if any(skip in url for skip in ["login", "signup", "pricing", "builder"]):
                continue

            yield self.make_request(
                url,
                callback=self.parse_letter_page,
                meta={"source_name": source_name}
            )

    def parse_letter_page(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse a cover letter example page."""
        source_name = response.meta.get("source_name")

        title = response.css("h1::text").get()
        if not title:
            return
        title = title.strip()

        # Look for the actual letter content
        content_selectors = [
            ".cover-letter-content",
            ".letter-example",
            ".example-content",
            "blockquote",
            ".sample-letter",
            "article",
        ]

        content = ""
        for selector in content_selectors:
            elem = response.css(selector)
            if elem:
                content = " ".join(elem.css("*::text").getall())
                if len(content) > 300:
                    break

        if len(content) < 200:
            return

        content = re.sub(r'\s+', ' ', content).strip()

        # Detect letter type
        letter_type = self._detect_letter_type(title, content)

        metadata = {
            "source_site": source_name,
            "letter_type": letter_type,
            "word_count": len(content.split()),
            "has_greeting": "dear" in content.lower(),
            "has_closing": any(c in content.lower() for c in ["sincerely", "regards", "best"]),
            "tags": ["cover_letter", "job_application", letter_type, source_name],
        }

        item = ScrapedItem(
            source=self.source,
            url=response.url,
            title=f"Cover Letter: {title}",
            content=content,
            metadata=metadata,
        )

        self.letters_scraped += 1
        yield item

    def _detect_letter_type(self, title: str, content: str) -> str:
        """Detect the type of cover letter."""
        combined = f"{title} {content}".lower()

        types = {
            "entry_level": ["entry level", "graduate", "first job", "no experience"],
            "career_change": ["career change", "transitioning", "new field"],
            "internal": ["internal", "promotion", "transfer"],
            "referral": ["referral", "referred", "recommendation"],
            "cold_contact": ["cold", "unsolicited", "prospecting"],
        }

        for letter_type, keywords in types.items():
            if any(kw in combined for kw in keywords):
                return letter_type

        return "standard"


class SOQExamplesSpider(BaseSpider):
    """
    Spider for Statement of Qualifications (SOQ) examples.

    Specifically targets California state job SOQ guides and examples.
    """

    name = "soq_spider"
    source = "soq_examples"
    allowed_domains = ["calcareers.ca.gov", "calhr.ca.gov"]

    rate_limit = 2.0
    custom_settings = {
        **BaseSpider.custom_settings,
        "DOWNLOAD_DELAY": 2.0,
        "CONCURRENT_REQUESTS": 1,
    }

    def start_requests(self) -> Iterator[Request]:
        """Start with SOQ guide pages."""
        urls = [
            "https://www.calcareers.ca.gov/CalHRPublic/Search/CommonJobDetails.aspx",
            "https://www.calhr.ca.gov/employees/Pages/statement-of-qualifications.aspx",
        ]

        for url in urls:
            yield self.make_request(url, callback=self.parse_soq_guide)

    def parse_soq_guide(self, response: Response) -> Iterator[ScrapedItem]:
        """Parse SOQ guide/example page."""
        title = response.css("h1::text").get()
        if not title:
            title = "SOQ Guide"
        title = title.strip()

        # Extract all text content
        content = " ".join(response.css("article *::text, .content *::text, main *::text").getall())
        content = re.sub(r'\s+', ' ', content).strip()

        if len(content) < 200:
            return

        metadata = {
            "document_type": "soq_guide",
            "word_count": len(content.split()),
            "tags": ["soq", "statement_of_qualifications", "california", "guide"],
        }

        item = ScrapedItem(
            source=self.source,
            url=response.url,
            title=title,
            content=content,
            metadata=metadata,
        )

        yield item
