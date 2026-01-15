# 🏥 Pharmaceutical News Agent (제약 뉴스 에이전트)

An automated pharmaceutical and regulatory news scraping, AI summarization, and email distribution system.

## 📋 Overview

This system collects pharmaceutical news from multiple Korean and international sources, analyzes them using Google Gemini AI, and distributes summarized news to relevant teams via email.

### Key Features

- **Multi-Source Scraping**: Collects news from 15+ sources (Korean FDA, industry journals, international regulators)
- **AI-Powered Analysis**: Uses Google Gemini for summarization, classification, and team routing
- **Keyword Classification**: Automated categorization based on pharmaceutical keywords
- **Email Distribution**: Team-based news distribution with HTML formatting
- **Regulatory Monitoring**: Tracks updates from ICH, PMDA, FDA, and other regulators

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/davemaxuell/Daewoong_Pharmaceutical_News_Scrapper_PRODUCT01.git
cd Daewoong_Pharmaceutical_News_Scrapper_PRODUCT01

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## ⚙️ Configuration

Create a `.env` file in the project root:

```env
# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key

# Email Configuration (optional)
EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# openFDA API (optional, for FDA Drug Recalls)
OPENFDA_API_KEY=your_openfda_key
```

## 🚀 Usage

### Run Full Pipeline

```bash
python run_pipeline.py
```

This executes:
1. **Phase 1**: Multi-source news scraping + AI summarization
2. **Phase 2**: Regulatory monitoring (ICH, PMDA)
3. **Phase 3**: Email distribution

### Run Individual Components

```bash
# Scrape news only
python multi_source_scraper.py

# AI Summarization only
python ai_summarizer_gemini.py -i news_file.json

# Monitoring only
python monitor_pipeline.py
```

## 📰 Supported News Sources

### Korean Sources
| Source | Type | Description |
|--------|------|-------------|
| DailyPharm | News | 데일리팜 제약뉴스 |
| Yakup | News | 약업신문 |
| KPANews | News | 대한약사회 뉴스 |
| MFDS | RSS | 식품의약품안전처 (40+ feeds) |
| KPBMA | News | 제약바이오협회 |

### International Sources
| Source | Type | Description |
|--------|------|-------------|
| FDA Recalls | API | openFDA Drug Enforcement API |
| EDQM | Web | European quality standards |
| EudraLex | Web | EU GMP guidelines |
| ICH | Web | International harmonization |
| PMDA | Web | Japan pharmaceutical agency |
| GMP Journal | Web | GMP regulatory news |
| PICS | RSS | Pharmaceutical inspection |

## 📁 Project Structure

```
├── run_pipeline.py          # Main pipeline orchestrator
├── multi_source_scraper.py  # Multi-source news collector
├── ai_summarizer_gemini.py  # AI summarization (Gemini)
├── email_sender.py          # Email distribution
├── monitor_pipeline.py      # Regulatory monitoring
├── keywords.py              # Keyword classification rules
├── team_definitions.py      # Team routing definitions
├── scrapers/                # Individual scraper modules
│   ├── base_scraper.py      # Base scraper class
│   ├── dailypharm_scraper.py
│   ├── yakup_scraper.py
│   ├── kpanews_scraper.py
│   ├── mfds_scraper.py
│   ├── kpbma_scraper.py
│   ├── edqm_scraper.py
│   ├── eudralex_scraper.py
│   ├── fda_warning_scraper.py  # FDA Recalls via openFDA
│   ├── gmpjournal_scraper.py
│   ├── pics_scraper.py
│   ├── pmda_scraper.py
│   └── ich_news_scraper.py
└── logs/                    # Log files
```

## 🔧 Key Components

### 1. Multi-Source Scraper
Collects news from all enabled sources with keyword filtering:
```python
from multi_source_scraper import MultiSourceScraper
scraper = MultiSourceScraper()
articles = scraper.fetch_all(days_back=1)
```

### 2. AI Summarizer (Gemini)
Analyzes articles and generates:
- Summary (2-3 sentences)
- Key points
- Industry impact
- Target teams
```python
from ai_summarizer_gemini import summarize_all_articles
summarize_all_articles("news.json", "summarized.json")
```

### 3. Keyword Classification
Automatic categorization based on:
- Policy/Regulation
- R&D/Clinical
- Product launches
- Market/Investment
- Company-specific news

## 📊 Output Format

```json
{
  "title": "Article Title",
  "link": "https://...",
  "published": "2026-01-07T00:00:00",
  "source": "DailyPharm",
  "summary": "Brief summary...",
  "full_text": "Complete article text...",
  "classifications": ["정책/행정", "업계/R&D"],
  "matched_keywords": ["FDA", "임상시험"],
  "ai_analysis": {
    "ai_summary": "AI-generated summary...",
    "key_points": ["Point 1", "Point 2"],
    "target_teams": ["RA팀", "임상팀"]
  }
}
```

## 📧 Email Distribution

News is automatically routed to relevant teams based on AI analysis:
- **RA Team**: Regulatory updates, guideline changes
- **Clinical Team**: Clinical trial news
- **BD Team**: Market, investment news
- **QA Team**: Quality, GMP updates

## ⏰ Scheduling

### Windows Task Scheduler
Use `run_daily_scraper.bat` or create a scheduled task.

### Cron (Linux)
```bash
0 8 * * 1-5 cd /path/to/project && python run_pipeline.py
```

### GitHub Actions
See `.github/workflows/` for automation examples.

## 🔑 API Keys Required

| Service | Required | Purpose |
|---------|----------|---------|
| Google Gemini | ✅ Yes | AI summarization |
| openFDA | ⚪ Optional | FDA drug recalls |
| Email SMTP | ⚪ Optional | Email distribution |

## 📝 License

MIT License

## 👥 Contributors

- Daewoong Pharmaceutical IT Team
