# Cinema Times Scraper

This project scrapes cinema showtimes and integrates with OMDb to fetch Rotten Tomatoes scores.

## Key Files

- `scraper.py` - Main scraper with integrated RT score fetching
- `fetch_omdb_scores.py` - Standalone RT score fetcher  
- `clean_titles.py` - Title cleaning (removes parentheticals)
- `generate_ical.py` - Generate iCal files for calendar import
- `index.html` - Web interface with score display and scheduler

## Usage

### Basic Scraping (with scores)
```bash
# Using environment variable (recommended)
export OMDB_API_KEY=your_api_key_here
python3 scraper.py

# Or pass API key directly
python3 scraper.py --omdb-key your_api_key_here
```

### Scraping without scores
```bash
python3 scraper.py --no-scores
```

## How It Works

1. **Scrapes** cinema times from The Light Cinema Sheffield
2. **Cleans** movie titles (removes parentheticals like "(50th Anniversary)")
3. **Fetches** RT/Metacritic/IMDb scores from OMDb API
4. **Calculates** composite scores (RT weighted 3x, Metacritic 2x, IMDb 1x)  
5. **Saves** complete data to `cinema-times.json`

## Generated Files

- `cinema-times.json` - Main data file with showings and scores
- `cinema-times.ics` - iCal format for calendar apps

## OMDb API Key

Get a free key at: http://www.omdbapi.com/apikey.aspx
Current key: `your_api_key_here`

## Commands

```bash
# Full scraping with scores
python3 scraper.py --omdb-key your_api_key_here

# Generate iCal after scraping  
python3 generate_ical.py

# Manual score refresh (if needed)
python3 fetch_omdb_scores.py --api-key your_api_key_here --force-refresh

# Help
python3 scraper.py --help
```