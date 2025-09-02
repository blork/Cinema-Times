# Cinema Times Scraper

This project scrapes cinema showtimes and integrates with OMDb to fetch Rotten Tomatoes scores.

## Key Files

- `scraper.py` - Main scraper with integrated RT score fetching
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

## OMDb API Key

Get a free key at: http://www.omdbapi.com/apikey.aspx
Set as environment variable or pass via command line.

## Commands

```bash
# Full scraping with scores
python3 scraper.py --omdb-key your_api_key_here

# Help
python3 scraper.py --help
```