"""
Planning Q&A Generator - Creates synthetic planning scenarios

Generates training data for planning capabilities:
1. Project planning scenarios
2. Architecture decision questions
3. Feature breakdown exercises
4. Technical specification prompts
5. Estimation and scoping questions

Uses templates + scraped data to generate high-quality Q&A pairs.
"""

import json
import logging
import random
import hashlib
from typing import Iterator, Dict, Any, List, Optional
from datetime import datetime

from ..storage.database import ScrapedItem, get_database

logger = logging.getLogger(__name__)


class PlanningQAGenerator:
    """
    Generator for synthetic planning Q&A pairs.

    Creates instruction-response pairs for:
    - App planning scenarios
    - Architecture decisions
    - Feature breakdowns
    - Technical specifications
    - Project scoping

    Usage:
        generator = PlanningQAGenerator()
        generator.initialize()
        examples = generator.generate_all(count=1000)
        generator.export_jsonl("planning_qa.jsonl")
    """

    # App types for scenarios
    APP_TYPES = [
        "social media app",
        "e-commerce app",
        "fitness tracking app",
        "note-taking app",
        "weather app",
        "todo list app",
        "recipe app",
        "podcast player",
        "meditation app",
        "language learning app",
        "budget tracker",
        "habit tracker",
        "photo editor",
        "music streaming app",
        "news reader",
        "travel planner",
        "dating app",
        "food delivery app",
        "video streaming app",
        "messaging app",
    ]

    # Features for scenarios
    FEATURES = [
        "user authentication",
        "push notifications",
        "offline mode",
        "dark mode",
        "search functionality",
        "user profiles",
        "settings screen",
        "onboarding flow",
        "in-app purchases",
        "social sharing",
        "analytics tracking",
        "crash reporting",
        "data sync",
        "image upload",
        "video playback",
        "location services",
        "biometric authentication",
        "widgets",
        "Siri shortcuts",
        "Apple Watch app",
    ]

    # Architecture patterns
    ARCHITECTURES = [
        "MVVM",
        "MVC",
        "Clean Architecture",
        "The Composable Architecture (TCA)",
        "VIPER",
        "Redux-like",
        "MVI",
    ]

    # Planning question templates
    PLANNING_TEMPLATES = [
        # Project structure
        {
            "type": "project_structure",
            "questions": [
                "How should I structure a {app_type} in SwiftUI?",
                "What's the best folder structure for a {app_type}?",
                "Plan the directory layout for a {app_type} using {architecture}",
                "How do I organize my Swift files for a {app_type}?",
            ],
            "response_template": """Here's a recommended project structure for a {app_type} using {architecture}:

```
{app_name}/
├── App/
│   ├── {app_name}App.swift
│   └── AppDelegate.swift (if needed)
├── Features/
│   ├── {feature1}/
│   │   ├── Views/
│   │   ├── ViewModels/
│   │   └── Models/
│   ├── {feature2}/
│   │   ├── Views/
│   │   ├── ViewModels/
│   │   └── Models/
├── Core/
│   ├── Network/
│   ├── Storage/
│   ├── Extensions/
│   └── Utilities/
├── Resources/
│   ├── Assets.xcassets
│   └── Localizable.strings
└── Tests/
    ├── UnitTests/
    └── UITests/
```

Key principles:
1. **Feature-based organization**: Group related code by feature
2. **Clear separation**: Keep Views, ViewModels, and Models separate
3. **Shared code in Core**: Reusable components in Core folder
4. **Testability**: Mirror structure in Tests folder
"""
        },

        # Feature breakdown
        {
            "type": "feature_breakdown",
            "questions": [
                "Break down the implementation of {feature} for a {app_type}",
                "What are the steps to implement {feature}?",
                "Plan the {feature} feature for my iOS app",
                "How do I approach building {feature} in SwiftUI?",
            ],
            "response_template": """Here's a breakdown for implementing {feature}:

## 1. Requirements Analysis
- Define user stories and acceptance criteria
- Identify edge cases and error scenarios
- Determine data requirements

## 2. Technical Design
- Choose appropriate architecture pattern
- Design data models
- Plan API endpoints (if needed)
- Consider offline support

## 3. Implementation Steps

### Step 1: Data Layer
- Create models/entities
- Implement repository/service
- Set up persistence (if needed)

### Step 2: Business Logic
- Implement ViewModel/Reducer
- Handle state management
- Add validation logic

### Step 3: UI Layer
- Build SwiftUI views
- Connect to ViewModel
- Add animations/transitions

### Step 4: Integration
- Connect to backend (if applicable)
- Handle errors gracefully
- Add loading states

## 4. Testing
- Unit tests for business logic
- Integration tests for data layer
- UI tests for critical flows

## 5. Polish
- Accessibility support
- Localization
- Performance optimization
"""
        },

        # Architecture decision
        {
            "type": "architecture_decision",
            "questions": [
                "Should I use {architecture} for my {app_type}?",
                "Compare {architecture} vs MVC for a {app_type}",
                "What architecture pattern is best for {feature}?",
                "Help me decide on an architecture for my {app_type}",
            ],
            "response_template": """## Architecture Decision: {architecture} for {app_type}

### Context
Building a {app_type} with features like {feature1} and {feature2}.

### Decision
Recommend using **{architecture}** for this project.

### Rationale

**Pros:**
- Clear separation of concerns
- Testable business logic
- Scalable for team growth
- SwiftUI-friendly

**Cons:**
- Initial setup complexity
- Learning curve for team
- More boilerplate code

### Alternatives Considered
1. **MVC**: Simpler but harder to test
2. **VIPER**: More structured but verbose
3. **Redux-like**: Good for complex state

### Consequences
- Team needs to understand {architecture} patterns
- Consistent code structure across features
- Easier onboarding for new developers
- Better testability and maintainability
"""
        },

        # Technical specification
        {
            "type": "tech_spec",
            "questions": [
                "Write a technical spec for {feature} in a {app_type}",
                "Create a design document for implementing {feature}",
                "What should the tech spec include for {feature}?",
                "Draft a technical specification for {feature}",
            ],
            "response_template": """# Technical Specification: {feature}

## Overview
Implementation of {feature} for the {app_type}.

## Goals
- Provide users with {feature} functionality
- Ensure smooth user experience
- Maintain app performance

## Non-Goals
- Not implementing advanced features in v1
- Not supporting legacy iOS versions

## Technical Design

### Data Models
```swift
struct {model_name}: Codable, Identifiable {{
    let id: UUID
    var name: String
    var createdAt: Date
}}
```

### API Endpoints
- `GET /api/{endpoint}` - Fetch data
- `POST /api/{endpoint}` - Create new item
- `PUT /api/{endpoint}/{{id}}` - Update item
- `DELETE /api/{endpoint}/{{id}}` - Delete item

### State Management
Using ObservableObject with @Published properties.

### UI Components
- Main list view
- Detail view
- Edit/Create form
- Empty state
- Loading state
- Error state

## Testing Strategy
- Unit tests: 80% coverage
- Integration tests: API layer
- UI tests: Critical user flows

## Rollout Plan
1. Internal testing
2. TestFlight beta
3. Staged rollout (10% → 50% → 100%)

## Metrics
- Feature adoption rate
- Error rate
- User engagement
"""
        },

        # Sprint planning
        {
            "type": "sprint_planning",
            "questions": [
                "Plan a sprint to build {feature} for a {app_type}",
                "How should I break down {feature} into sprint tasks?",
                "Create a sprint plan for implementing {feature}",
                "What tasks do I need for a 2-week sprint on {feature}?",
            ],
            "response_template": """# Sprint Plan: {feature}

## Sprint Goal
Deliver a functional {feature} for the {app_type}.

## User Stories

### Story 1: Basic {feature}
As a user, I want to use {feature} so that I can accomplish my goal.
**Points:** 5

### Story 2: {feature} Settings
As a user, I want to customize {feature} behavior.
**Points:** 3

### Story 3: {feature} Persistence
As a user, I want my {feature} data to persist across sessions.
**Points:** 3

## Tasks Breakdown

### Week 1
- [ ] Design data models (2h)
- [ ] Implement repository layer (4h)
- [ ] Build main UI view (4h)
- [ ] Add ViewModel logic (4h)
- [ ] Write unit tests (4h)

### Week 2
- [ ] Implement settings screen (4h)
- [ ] Add persistence layer (4h)
- [ ] Error handling (2h)
- [ ] UI polish and animations (4h)
- [ ] Integration testing (2h)
- [ ] Code review and fixes (4h)

## Risks
- API changes from backend team
- Design iterations needed
- Performance issues with large data

## Definition of Done
- [ ] All acceptance criteria met
- [ ] Unit tests passing (>80% coverage)
- [ ] UI tests for critical paths
- [ ] Code reviewed and approved
- [ ] No P1/P2 bugs
"""
        },

        # App Store planning
        {
            "type": "appstore_planning",
            "questions": [
                "How do I prepare my {app_type} for App Store submission?",
                "What's the checklist for App Store submission?",
                "Plan the App Store release for my {app_type}",
                "What do I need before submitting to the App Store?",
            ],
            "response_template": """# App Store Submission Checklist

## Pre-Submission

### App Requirements
- [ ] Minimum iOS version set correctly
- [ ] All device sizes supported
- [ ] Dark mode supported
- [ ] Accessibility features implemented
- [ ] Localization complete

### Technical
- [ ] No crashes in testing
- [ ] No memory leaks
- [ ] Performance optimized
- [ ] All APIs use HTTPS
- [ ] Privacy manifest included

### Legal & Compliance
- [ ] Privacy policy URL
- [ ] Terms of service (if needed)
- [ ] GDPR compliance
- [ ] COPPA compliance (if kids)
- [ ] Export compliance

## App Store Connect

### App Information
- [ ] App name (30 chars max)
- [ ] Subtitle (30 chars max)
- [ ] Description (4000 chars max)
- [ ] Keywords (100 chars max)
- [ ] Category selected
- [ ] Age rating completed

### Media
- [ ] App icon (1024x1024)
- [ ] Screenshots (all required sizes)
- [ ] App preview videos (optional)

### Pricing & Availability
- [ ] Price tier selected
- [ ] Territories selected
- [ ] Pre-order settings (if applicable)

### In-App Purchases
- [ ] IAPs configured (if applicable)
- [ ] IAPs tested in sandbox

## Build & Submit
- [ ] Archive created
- [ ] Build uploaded to App Store Connect
- [ ] Build processing complete
- [ ] Submit for review

## Post-Submission
- [ ] Monitor review status
- [ ] Respond to any App Review questions
- [ ] Prepare marketing materials
- [ ] Plan launch announcement
"""
        },
    ]

    def __init__(self):
        self._db = None
        self.examples = []

    def initialize(self):
        """Initialize database connection."""
        try:
            self._db = get_database()
        except Exception as e:
            logger.warning(f"Database not available: {e}")

    def generate_all(self, count: int = 1000) -> List[Dict]:
        """Generate synthetic planning Q&A pairs."""
        logger.info(f"Generating {count} planning Q&A examples")

        examples_per_type = count // len(self.PLANNING_TEMPLATES)

        for template in self.PLANNING_TEMPLATES:
            for _ in range(examples_per_type):
                example = self._generate_from_template(template)
                if example:
                    self.examples.append(example)

        random.shuffle(self.examples)
        logger.info(f"Generated {len(self.examples)} examples")

        return self.examples

    def _generate_from_template(self, template: Dict) -> Optional[Dict]:
        """Generate a single Q&A from template."""
        # Select random values
        app_type = random.choice(self.APP_TYPES)
        feature = random.choice(self.FEATURES)
        feature1 = random.choice(self.FEATURES)
        feature2 = random.choice([f for f in self.FEATURES if f != feature1])
        architecture = random.choice(self.ARCHITECTURES)

        # Generate app name from type
        app_name = app_type.replace(" ", "").title().replace("App", "") + "App"

        # Model name
        model_name = feature.replace(" ", "").title()
        endpoint = feature.replace(" ", "_").lower()

        # Format question
        question_template = random.choice(template["questions"])
        question = question_template.format(
            app_type=app_type,
            feature=feature,
            architecture=architecture,
        )

        # Format response
        response = template["response_template"].format(
            app_type=app_type,
            app_name=app_name,
            feature=feature,
            feature1=feature1,
            feature2=feature2,
            architecture=architecture,
            model_name=model_name,
            endpoint=endpoint,
        )

        # Create unique ID
        content_hash = hashlib.md5(f"{question}{response}".encode()).hexdigest()[:12]

        return {
            "id": f"planning_{template['type']}_{content_hash}",
            "messages": [
                {
                    "role": "system",
                    "content": "You are SAM, an expert iOS developer and technical planner. You help developers plan, architect, and build high-quality Apple platform apps."
                },
                {"role": "user", "content": question},
                {"role": "assistant", "content": response},
            ],
            "metadata": {
                "type": "planning_qa",
                "subtype": template["type"],
                "app_type": app_type,
                "feature": feature,
                "architecture": architecture,
                "quality": 0.85,
                "synthetic": True,
            }
        }

    def export_jsonl(self, filepath: str) -> str:
        """Export generated examples to JSONL."""
        with open(filepath, 'w') as f:
            for example in self.examples:
                f.write(json.dumps(example) + '\n')

        logger.info(f"Exported {len(self.examples)} examples to {filepath}")
        return filepath

    def save_to_database(self):
        """Save generated examples as ScrapedItems."""
        if not self._db:
            logger.warning("Database not available")
            return

        for example in self.examples:
            item = ScrapedItem(
                source="planning_qa",
                url=f"synthetic://planning/{example['id']}",
                title=example["messages"][1]["content"][:100],
                content=example["messages"][2]["content"],
                metadata=example["metadata"],
            )
            self._db.save_item(item)

        logger.info(f"Saved {len(self.examples)} items to database")


# Spider wrapper for integration with scraper system
class PlanningQASpider:
    """Spider wrapper for planning Q&A generator."""

    name = "planning_qa_spider"
    source = "planning_qa"

    def __init__(self, *args, count: int = 1000, **kwargs):
        self.count = int(count)
        self.generator = PlanningQAGenerator()

    def run(self):
        """Generate and save planning Q&A."""
        self.generator.initialize()
        self.generator.generate_all(self.count)
        self.generator.save_to_database()

        # Also export to file
        output_path = "/Volumes/David External/scraper_data/training_data/planning_qa.jsonl"
        self.generator.export_jsonl(output_path)

        return {
            "examples_generated": len(self.generator.examples),
            "output_file": output_path,
        }


def register():
    return {
        "name": "planning_qa",
        "spider_class": PlanningQASpider,
        "description": "Planning Q&A Generator",
        "type": "planning",
        "priority": 1,
    }


# CLI entry point
if __name__ == "__main__":
    import sys

    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1000

    generator = PlanningQAGenerator()
    generator.initialize()
    generator.generate_all(count)

    output_path = "/Volumes/David External/scraper_data/training_data/planning_qa.jsonl"
    generator.export_jsonl(output_path)

    print(f"Generated {len(generator.examples)} planning Q&A examples")
    print(f"Saved to: {output_path}")
