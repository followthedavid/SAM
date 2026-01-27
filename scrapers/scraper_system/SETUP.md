# SAM Scraper System - Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
cd /Users/davidquinton/ReverseLab/SAM/scrapers/scraper_system

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Install Playwright browsers (for JS-heavy sites)
playwright install chromium
```

### 2. Start Services

```bash
# PostgreSQL (metadata storage)
brew services start postgresql@15

# Create database
createdb sam_scraper

# Redis (task queue)
brew services start redis

# Verify services are running
brew services list
```

### 3. Initialize Database

```bash
source .venv/bin/activate
python -m scraper_system init-db
```

### 4. Start Prefect Server (optional - for UI)

```bash
# In a separate terminal
source .venv/bin/activate
prefect server start

# Open UI at http://localhost:4200
```

### 5. Test the System

```bash
# Activate venv first
source .venv/bin/activate

# Check status
python -m scraper_system status

# Check resources (will show if VLM/Ollama is blocking)
python -m scraper_system resources

# List available scrapers
python -m scraper_system list

# View statistics
python -m scraper_system stats
```

## Running Scrapers

### Run Now (Blocking)

```bash
# Run a specific scraper
python -m scraper_system run ao3 --pages 10

# Run with full scrape
python -m scraper_system run nifty
```

### Schedule (Cron)

```bash
# Schedule AO3 for 2am daily
python -m scraper_system schedule ao3 "0 2 * * *"

# Schedule Nifty for 3am daily
python -m scraper_system schedule nifty "0 3 * * *"
```

### Monitor

```bash
# View statistics
python -m scraper_system stats

# View job history
python -m scraper_system history

# View history for specific scraper
python -m scraper_system history ao3
```

## Configuration

### Edit Settings

```bash
# Main configuration
$EDITOR config/settings.py
```

Key settings:
- `RUNNER`: "prefect" or "celery"
- `MIN_FREE_RAM_BYTES`: Minimum RAM to start scraping (default 2GB)
- `RATE_LIMITS`: Per-source rate limits
- `DATA_SOURCES`: Enabled scrapers

### Swap to Celery (if needed)

1. Edit `config/settings.py`:
   ```python
   RUNNER = "celery"  # Was "prefect"
   ```

2. Install Celery deps:
   ```bash
   pip install celery flower
   ```

3. Start Celery worker:
   ```bash
   celery -A scraper_system.runners.celery_runner worker --loglevel=info
   ```

4. Start Celery beat (scheduler):
   ```bash
   celery -A scraper_system.runners.celery_runner beat --loglevel=info
   ```

5. Start Flower (monitoring):
   ```bash
   celery -A scraper_system.runners.celery_runner flower
   # Open http://localhost:5555
   ```

## Directory Structure

```
scraper_system/
├── __init__.py          # Package init
├── __main__.py          # CLI entry point
├── requirements.txt     # Dependencies
├── SETUP.md            # This file
├── SCRAPER_REGISTRY.md # All data sources
│
├── config/
│   └── settings.py     # Configuration
│
├── core/
│   ├── task_runner.py      # Abstraction layer
│   └── resource_governor.py # RAM/CPU monitoring
│
├── runners/
│   ├── prefect_runner.py   # Prefect 3.x implementation
│   └── celery_runner.py    # Celery implementation (backup)
│
├── spiders/
│   ├── base_spider.py      # Base class for all spiders
│   ├── scrapy_settings.py  # Scrapy configuration
│   └── [specific spiders]
│
├── pipelines/
│   └── database_pipeline.py # Save to PostgreSQL
│
└── storage/
    └── database.py         # PostgreSQL interface
```

## Resource Management

The system automatically:
- Pauses when RAM < 2GB
- Pauses when VLM/Ollama is running
- Runs one spider at a time (8GB Mac)
- Resumes when resources available

Check status:
```bash
python -m scraper_system resources
```

## CLI Commands Reference

```bash
# System status
python -m scraper_system status

# List scrapers
python -m scraper_system list

# Run a scraper now
python -m scraper_system run <name> [--pages N]

# Schedule a scraper
python -m scraper_system schedule <name> "<cron>"

# Pause/resume all scrapers
python -m scraper_system pause
python -m scraper_system resume

# View statistics
python -m scraper_system stats

# View job history
python -m scraper_system history [name] [--limit N]

# Check resource status
python -m scraper_system resources

# Initialize database
python -m scraper_system init-db
```

## Troubleshooting

### PostgreSQL not connecting

```bash
# Check if running
brew services list | grep postgresql

# Start if needed
brew services start postgresql@15

# Create database if needed
createdb sam_scraper

# Verify
psql -d sam_scraper -c "SELECT 1"
```

### Redis not connecting

```bash
# Check if running
brew services list | grep redis

# Start if needed
brew services start redis

# Verify
redis-cli ping  # Should return PONG
```

### Prefect not working

```bash
# Check version (should be 3.x)
prefect version

# Start server
prefect server start

# Check config
prefect config view
```

### Resource check failing

```bash
# See what's using RAM (macOS)
top -l 1 | head -20

# Kill Ollama if running
pkill ollama

# Check resources again
python -m scraper_system resources
```

### Module not found errors

Make sure you're running from the parent directory:
```bash
cd /Users/davidquinton/ReverseLab/SAM/scrapers
source scraper_system/.venv/bin/activate
python -m scraper_system status
```

## Data Storage

Data is stored in:
- **Primary**: `/Volumes/David External/scraper_data/` (if writable)
- **Fallback**: `~/.sam/scraper_data/`

Subdirectories:
- `raw_archives/` - Raw scraped content
- `processed/` - Cleaned/processed content
- `training_data/` - Data ready for training

## Next Steps

1. Convert existing scrapers (ao3_ripper.py, nifty_ripper.py, etc.) to Scrapy spiders
2. Add Playwright integration for JS-heavy sites (WWD, etc.)
3. Build training data pipeline
4. Fine-tune SAM model
