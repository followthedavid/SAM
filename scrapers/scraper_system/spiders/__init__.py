"""
SAM Scraper System - Spiders Package

All Scrapy spiders for data collection.
"""

from .base_spider import BaseSpider
from .ao3_spider import AO3Spider
from .nifty_spider import NiftySpider
from .literotica_spider import LiteroticaSpider
from .dark_psych_spider import DarkPsychSpider
from .flist_spider import FListSpider, BlueMoonSpider
from .wwd_spider import WWDSpider, VMagSpider, WMagSpider
from .gq_esquire_spider import GQSpider, EsquireSpider
from .thecut_spider import TheCutSpider
from .reddit_spider import RedditRoleplaySpider, AO3RoleplaySpider
from .jobs_spider import CalCareersSpider, ResumeSpider, CoverLetterSpider, SOQExamplesSpider
from .news_spider import BiasRatingsSpider, RSSNewsSpider, FullArticleSpider
from .github_spider import GitHubSpider
from .stackoverflow_spider import StackOverflowSpider
from .devto_spider import DevToSpider, HashNodeSpider
from .docs_spider import DocsSpider
from .uiux_spider import UIUXSpider
from .apple_spider import AppleDevSpider
from .swift_spider import SwiftCommunitySpider
from .wwdc_spider import WWDCSpider
from .realtime_spider import GitHubEventsSpider, HackerNewsSpider, RedditStreamSpider
from .error_corpus_spider import ErrorCorpusSpider, SwiftErrorDatabaseSpider
from .curriculum_spider import CurriculumSpider
from .architecture_spider import ArchitectureSpider
from .templates_spider import ProjectTemplatesSpider
from .specs_spider import SpecificationSpider
from .planning_qa_spider import PlanningQASpider

__all__ = [
    "BaseSpider",
    "AO3Spider",
    "NiftySpider",
    "LiteroticaSpider",
    "DarkPsychSpider",
    "FListSpider",
    "BlueMoonSpider",
    "WWDSpider",
    "VMagSpider",
    "WMagSpider",
    "GQSpider",
    "EsquireSpider",
    "TheCutSpider",
    "RedditRoleplaySpider",
    "AO3RoleplaySpider",
    "CalCareersSpider",
    "ResumeSpider",
    "CoverLetterSpider",
    "SOQExamplesSpider",
    "BiasRatingsSpider",
    "RSSNewsSpider",
    "FullArticleSpider",
    "GitHubSpider",
    "StackOverflowSpider",
    "DevToSpider",
    "HashNodeSpider",
    "DocsSpider",
    "UIUXSpider",
    "AppleDevSpider",
    "SwiftCommunitySpider",
    "WWDCSpider",
    "GitHubEventsSpider",
    "HackerNewsSpider",
    "RedditStreamSpider",
    "ErrorCorpusSpider",
    "SwiftErrorDatabaseSpider",
    "CurriculumSpider",
    "ArchitectureSpider",
    "ProjectTemplatesSpider",
    "PlanningQASpider",
    "SpecificationSpider",
]
