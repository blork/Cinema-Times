# 🎬 Cinema Times Scraper

Automated cinema showings scraper with Rotten Tomatoes integration, featuring intelligent scheduling and calendar export.

## 🌟 Features

- **Automated Scraping**: Scrapes The Light Cinema Sheffield every 6 hours
- **RT Score Integration**: Fetches Rotten Tomatoes, Metacritic, and IMDb scores
- **Smart Scheduling**: Optimized movie viewing schedules with minimal gaps
- **Calendar Export**: Generate iCal files for importing into calendar apps
- **Live Filtering**: Interactive web interface with real-time filtering
- **Score Visualization**: Color-coded movie ratings and tooltips

## 🚀 Live Site

Visit the live version at: `https://[username].github.io/cinema-times/`

## 🔧 GitHub Actions Setup

1. **Enable GitHub Pages:**
   - Go to repository Settings → Pages
   - Source: **"GitHub Actions"** (not "Deploy from branch")

2. **Add API Key Secret:**
   - Go to Settings → Secrets and variables → Actions
   - Add secret: `OMDB_API_KEY` = `your_omdb_key`

3. **Automatic Deployment:**
   - Scraper runs every 6 hours automatically
   - Push to master triggers immediate deployment
   - Manual trigger available in Actions tab

## 📊 Data Sources

- **Cinema Data**: The Light Cinema Sheffield
- **Movie Ratings**: OMDb API (aggregates RT, Metacritic, IMDb)
- **Scoring System**: Weighted composite (RT×3 + Metacritic×2 + IMDb×1)

## 📱 Usage

### Web Interface
- Browse all cinema showings with RT scores
- Filter by movies and dates  
- Generate custom viewing schedules
- Export to calendar apps
- Color-coded ratings with hover tooltips

### Score Legend
- 🟢 **80+**: Excellent (Fresh)
- 🟡 **65+**: Good 
- 🟠 **50+**: Fair
- 🔴 **<50**: Poor
- ⚫ **—**: No Score

### Calendar Export
Use the individual "Add to Calendar" buttons on each movie showing to export specific events to your calendar app.

## 🛠 Development

### Local Setup
```bash
git clone https://github.com/[username]/cinema-times.git
cd cinema-times

# Install dependencies
pip install requests beautifulsoup4

# Set API key
export OMDB_API_KEY=your_api_key_here

# Run scraper with scores
python scraper.py
```

### Manual Commands
```bash
# Scrape with scores
python scraper.py --omdb-key your_key

# Scrape without scores (faster)
python scraper.py --no-scores

# Get help
python scraper.py --help
```

## 📁 Files Generated
- `cinema-times.json` - Main data file with showings and scores
- `index.html` - Interactive web interface

## 🔄 Update Frequency
- **Automatic**: Every 6 hours via GitHub Actions
- **Manual**: Trigger via GitHub Actions tab
- **Development**: On every push to master