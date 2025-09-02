# Cinema Times Scraper

A simple Python-based cinema times scraper that runs on GitHub Actions and publishes results as JSON and iCal feeds.

## Setup

1. **Fork/clone this repository**

2. **Customize the scraper for your cinema:**
   - Edit `scraper.py` - update the `cinema_url` and scraping logic in the `scrape_times()` method
   - You'll need to inspect your cinema's website HTML and write CSS selectors to extract movie titles and times

3. **Enable GitHub Pages:**
   - Go to your repository Settings → Pages
   - Set Source to "Deploy from a branch"
   - Choose `main` branch and `/ (root)` folder
   - Your site will be available at `https://yourusername.github.io/cinema-times/`

4. **The scraper will run automatically every 6 hours**, or you can trigger it manually:
   - Go to Actions tab → "Scrape Cinema Times" workflow → "Run workflow"

## Files

- `scraper.py` - Main scraping script (customize this for your cinema)
- `generate_ical.py` - Converts JSON to iCal format
- `cinema-times.json` - Generated movie times (updated automatically)
- `cinema-times.ics` - iCal feed for calendar apps (updated automatically)
- `index.html` - Simple web viewer
- `.github/workflows/scrape.yml` - GitHub Actions workflow

## Usage

### Web Interface
Visit your GitHub Pages URL to see a simple web interface showing current movie times.

### Calendar Subscription
Add the iCal feed to your calendar app:
- **URL**: `https://yourusername.github.io/cinema-times/cinema-times.ics`
- **iOS Calendar**: Settings → Calendar → Accounts → Add Account → Other → Add Subscribed Calendar
- **Google Calendar**: Settings → Add calendar → From URL
- **Outlook**: Calendar → Add calendar → Subscribe from web

## Customization

### Adding More Cinemas
1. Modify `scraper.py` to handle multiple cinema URLs
2. Update the JSON structure to include cinema information
3. Adjust the HTML viewer to display multiple cinemas

### Changing Update Frequency
Edit `.github/workflows/scrape.yml` and modify the cron expression:
- Every 3 hours: `0 */3 * * *`
- Twice daily: `0 9,21 * * *`
- Daily at 6 AM: `0 6 * * *`

## Local Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Test scraper
python scraper.py

# Generate iCal
python generate_ical.py

# Open index.html in your browser to test the viewer
```