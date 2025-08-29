# LinkedIn Job Application Automation System

An automated pipeline for scraping, filtering, and analyzing LinkedIn job postings with AI-powered job fit evaluation and Notion database integration.

## 🚀 Features

- **LinkedIn Job Scraping**: Uses Apify API to scrape job postings based on custom search criteria
- **Smart Filtering**: Filters jobs based on company blacklists, keywords, location, and posting date
- **AI Job Analysis**: Uses OpenAI GPT models to evaluate job fit with automatic backup model switching
- **Notion Integration**: Automatically adds qualified jobs to Notion database with application tracking
- **Caching System**: Prevents duplicate processing and API calls
- **Test Mode**: Run pipeline with dummy data for testing without API costs

## 📁 Project Structure

```
src/
├── scraped/           # Job scraping module
│   ├── scrape_apify_jobs.py
│   └── scraped/       # Raw scraped job data
├── condensed/         # Data processing module
│   ├── condense_jobs.py
│   ├── condense_data/ # Processed job data
│   └── log/          # Processing logs
├── filtered/          # Job filtering module
│   ├── filter_condensed_jobs.py
│   ├── config.json   # Filtering configuration
│   ├── filter_data/  # Filtered job data
│   └── log/          # Filtering logs
├── analyze/           # AI analysis module
│   ├── analyze.py    # Main analyzer script
│   ├── job_analyzer_lib/
│   │   ├── config.py
│   │   ├── evaluator.py
│   │   ├── services.py
│   │   └── utils.py
│   ├── rated_jobs.json # Evaluation cache
│   ├── resume.txt    # Your resume for job matching
│   └── log/          # Analysis logs
└── pipeline.py       # Main orchestration script
```

## ⚙️ Setup

### 1. Environment Variables

Create a `.env` file in the project root:

```bash
# OpenAI API
OPENAI_API_KEY=your_openai_api_key
PRIMARY_MODEL=gpt-4o-mini
BACKUP_MODEL=gpt-4o

# Apify API
APIFY_API_TOKEN=your_apify_token

# Notion API
NOTION_API_KEY=your_notion_integration_token
NOTION_DB_ID=your_notion_database_id
NOTION_DB_ID_TEST=your_test_database_id
```

### 2. Dependencies

```bash
pip install openai notion-client python-dotenv tqdm tiktoken
```

### 3. Configuration

1. **Add your resume**: Place `resume.txt` in `/src/analyze/`
2. **Configure filtering**: Edit `/src/filtered/config.json` with your preferences:
   ```json
   {
     "bad_companies": ["Company1", "Company2"],
     "excluded_keywords": ["senior", "lead", "manager"],
     "allowed_locations": ["remote", "boston", "san francisco"],
     "days_limit": 7
   }
   ```

## 🏃 Usage

### Run Complete Pipeline

```bash
# From /src/ directory
cd src

# Production mode (uses real APIs)
python pipeline.py

# Test mode (uses dummy data)
python pipeline.py --test
```

### Run Individual Components

```bash
# Scraper only
cd src/scraped
python scrape_apify_jobs.py --test

# Analyzer only
cd src/analyze
python analyze.py
```

## 🔄 Pipeline Flow

1. **Scraper** → Fetches jobs from LinkedIn via Apify API
2. **Condenser** → Processes and standardizes raw job data
3. **Filter** → Removes unwanted jobs based on criteria
4. **Analyzer** → Uses AI to evaluate job fit and adds to Notion

## 🤖 AI Analysis

The analyzer uses a two-model approach:

- **Primary Model**: Fast initial evaluation (gpt-4o-mini)
- **Backup Model**: Higher quality re-evaluation for unclear cases (gpt-4o)

Evaluation criteria (weighted):
- Technical Skills Match (40%)
- Experience Level (25%)
- Domain Relevance (20%)
- Soft Skills Alignment (15%)

## 📊 Application Type Detection

Automatically detects application systems:
- Greenhouse, Workday, Lever, BambooHR
- SmartRecruiters, Jobvite, Ashby, iCIMS
- LinkedIn, Indeed, AngelList, ZipRecruiter
- Company career sites and other ATS systems

## 🗂️ Data Management

- **Caching**: Prevents re-processing the same jobs
- **Logging**: Comprehensive logs for debugging and monitoring
- **Timestamped Files**: All outputs include timestamps for tracking
- **Notion Integration**: Automatic database population with job details

## 🧪 Testing

The system includes comprehensive test mode functionality:
- Dummy job data for testing without API costs
- All pipeline components work in test mode
- Preserves cache and configuration behavior

## 🔧 Troubleshooting

### Common Issues

1. **Cache JSON errors**: Delete corrupted cache file to reset
2. **Path issues**: Ensure running from correct directory (`/src/`)
3. **API rate limits**: Check logs for timeout/throttling messages
4. **Notion permissions**: Verify integration has database access

### Logs Location

- Scraper: `/src/scraped/scraped/`
- Condenser: `/src/condensed/log/`
- Filter: `/src/filtered/log/`
- Analyzer: `/src/analyze/log/`
- Pipeline: `/src/logs/`

## 📝 License

This project is for personal use. Ensure compliance with LinkedIn's Terms of Service and API usage policies.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

**Note**: This system is designed for personal job search automation. Please use responsibly and in accordance with all applicable terms of service.