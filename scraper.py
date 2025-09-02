#!/usr/bin/env python3
"""
Cinema Times Scraper
Scrapes cinema showtimes and generates JSON and iCal outputs
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import re
from typing import List, Dict, Any
import sys
import os
import time


class CinemaScraper:
    def __init__(self, cinema_url: str, cinema_name: str):
        self.cinema_url = cinema_url
        self.cinema_name = cinema_name
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def scrape_times(self) -> List[Dict[str, Any]]:
        """
        Scrape cinema times from The Light Cinema website
        Returns list of showings with movie title, time, and date
        """
        try:
            response = self.session.get(self.cinema_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            showings = []
            
            # Try to parse JavaScript data first (contains full week data)
            movie_data = self.extract_javascript_data(soup)
            if movie_data:
                return self.parse_javascript_data(movie_data)
            else:
                # Fallback to HTML parsing (single day only)
                print("JavaScript parsing failed, falling back to HTML parsing")
                return self.scrape_from_html(soup)
            
        except requests.RequestException as e:
            print(f"Error fetching {self.cinema_url}: {e}")
            return []
        except Exception as e:
            print(f"Error parsing cinema times: {e}")
            return []
    
    def get_week_dates(self) -> List[Dict[str, str]]:
        """Get the next 7 days with formatted dates"""
        dates = []
        today = datetime.now()
        
        for i in range(7):
            date = today + timedelta(days=i)
            dates.append({
                'date': date.strftime('%Y-%m-%d'),
                'display': date.strftime('%a %d %b'),
                'day_name': date.strftime('%A').lower()
            })
        
        return dates
    
    def get_film_elements_from_soup(self, soup: BeautifulSoup) -> List:
        """Extract film elements from soup - helper method"""
        film_elements = []
        potential_film_containers = soup.find_all(['div', 'article', 'section'])
        
        for container in potential_film_containers:
            container_text = container.get_text()
            if (re.search(r'\d{1,2}[:\.]?\d{2}', container_text) and 
                len(container_text.strip()) > 20 and
                not (container.get('class') and 'sessions' in ' '.join(container.get('class')))):
                
                title_candidates = container.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'b', 'span'])
                has_title = False
                for candidate in title_candidates:
                    candidate_text = candidate.get_text(strip=True)
                    if (len(candidate_text) > 3 and 
                        not re.match(r'^\d{1,2}[:\.]?\d{2}', candidate_text) and
                        not candidate_text.lower() in ['captioned', 'rewind', 'explore', 'iconic']):
                        has_title = True
                        break
                
                if has_title:
                    film_elements.append(container)
        
        return film_elements
    
    def extract_title_from_element(self, element) -> str:
        """Extract title from a film element - helper method"""
        full_text = element.get_text(separator=' ', strip=True)
        title = None
        
        # Strategy 1: Look for title in header tags and strong/b tags
        title_elements = element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'b'])
        for title_elem in title_elements:
            candidate = title_elem.get_text(strip=True)
            if len(candidate) > 3 and not re.match(r'^\d{1,2}[:\.]?\d{2}', candidate):
                title = candidate
                break
        
        if not title:
            # Extract from beginning of text (before first time)
            title_patterns = [
                r'^([A-Z][^0-9]+?)(?=\s*\d{1,2}[:\.]?\d{2})',
                r'^([^0-9]{4,}?)(?=\s*\d{1,2}[:\.]?\d{2})',
                r'^(.*?)(?=\s*\d{1,2}[:\.]?\d{2})'
            ]
            
            for pattern in title_patterns:
                title_match = re.match(pattern, full_text)
                if title_match:
                    candidate = title_match.group(1).strip()
                    if len(candidate) > 3:
                        title = candidate
                        break
        
        return title if title else "Unknown Movie"
    
    def extract_javascript_data(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract movie data from JavaScript variables in the page"""
        script_tags = soup.find_all('script')
        
        for script in script_tags:
            if script.string:
                script_content = script.string
                
                # Look for __guideData variable
                if '__guideData' in script_content:
                    try:
                        # Find the __guideData assignment
                        start_patterns = ['__guideData = ', '__guideData=']
                        
                        for pattern in start_patterns:
                            start_idx = script_content.find(pattern)
                            if start_idx != -1:
                                start_idx += len(pattern)
                                
                                # More robust JSON boundary detection
                                # Look for matching brackets instead of semicolon
                                bracket_count = 0
                                end_idx = start_idx
                                in_string = False
                                escape_next = False
                                
                                for i, char in enumerate(script_content[start_idx:], start_idx):
                                    if escape_next:
                                        escape_next = False
                                        continue
                                    
                                    if char == '\\':
                                        escape_next = True
                                        continue
                                    
                                    if char == '"' and not escape_next:
                                        in_string = not in_string
                                        continue
                                    
                                    if not in_string:
                                        if char == '[':
                                            bracket_count += 1
                                        elif char == ']':
                                            bracket_count -= 1
                                            if bracket_count == 0:
                                                end_idx = i + 1
                                                break
                                
                                if end_idx > start_idx:
                                    json_str = script_content[start_idx:end_idx]
                                    try:
                                        movie_data = json.loads(json_str)
                                        print(f"Successfully parsed JavaScript data with {len(movie_data)} movies")
                                        return movie_data
                                    except json.JSONDecodeError as e:
                                        print(f"JSON decode error: {e}")
                                        print(f"Problematic JSON snippet: {json_str[:200]}...")
                                        continue
                        
                    except Exception as e:
                        print(f"Error parsing JavaScript: {e}")
                        continue
        
        return None
    
    def parse_javascript_data(self, movie_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse the JavaScript movie data into showings"""
        showings = []
        
        try:
            for movie in movie_data:
                title = movie.get('Title', 'Unknown Movie')
                cert = movie.get('Cert', '')
                runtime = movie.get('Runtime', '')
                
                # Get showtimes from dates array
                dates = movie.get('Dates', [])
                for date_info in dates:
                    date_key = date_info.get('Key', '')
                    date_display = date_info.get('Display', '')
                    
                    # Convert date key (YYYYMMDD) to proper date format
                    if len(date_key) == 8:
                        year = date_key[:4]
                        month = date_key[4:6]
                        day = date_key[6:8]
                        formatted_date = f"{year}-{month}-{day}"
                    else:
                        formatted_date = datetime.now().strftime('%Y-%m-%d')
                    
                    # Get sessions for this date
                    sessions = date_info.get('Sessions', [])
                    for session in sessions:
                        time_display = session.get('Display', '')
                        css_class = session.get('CssClass', '')
                        format_type = session.get('Format', '')
                        
                        # Skip unavailable sessions
                        if 'unavailable' in css_class.lower() or 'soldout' in css_class.lower():
                            continue
                        
                        showing = {
                            'title': title,
                            'time': time_display,
                            'date': formatted_date,
                            'date_display': date_display,
                            'cinema': self.cinema_name,
                            'cert': cert,
                            'runtime': runtime,
                            'format': format_type,
                            'availability': css_class,
                            'source': 'javascript_data'
                        }
                        
                        showings.append(showing)
            
            print(f"Parsed {len(showings)} showings from JavaScript data")
            return showings
            
        except Exception as e:
            print(f"Error parsing JavaScript movie data: {e}")
            return []
    
    def scrape_from_html(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """
        Scrape from HTML structure using The Light Cinema's specific layout
        Parse the full week of showtimes
        """
        all_showings = []
        week_dates = self.get_week_dates()
        
        try:
            # First, try to scrape data for today
            showings = self.scrape_day_from_html(soup, week_dates[0])
            all_showings.extend(showings)
            
            # Try to get other days by looking for date tabs or navigation
            # The Light Cinema might load other days via AJAX, but let's try to find them
            date_links = soup.find_all('a', href=re.compile(r'date|day', re.I))
            tab_elements = soup.find_all(['div', 'li', 'a'], class_=re.compile(r'tab|day|date', re.I))
            
            # Check if the current page contains data for multiple days already
            # Look for date tabs or other day indicators in the HTML
            date_tabs = soup.find_all(['div', 'li', 'a', 'button'], class_=re.compile(r'tab|day|date', re.I))
            
            print(f"Found {len(date_tabs)} potential date navigation elements")
            
            # If tabs exist, the data for other days might be in hidden divs
            # Look for content containers that might be hidden for other days
            all_day_containers = soup.find_all(['div', 'section'], 
                                             attrs={'data-date': True, 'data-day': True, 'id': re.compile(r'day|date', re.I)})
            
            if all_day_containers:
                print(f"Found {len(all_day_containers)} day-specific containers in page")
                # Process each day container
                for container in all_day_containers:
                    # Try to extract date from container
                    container_day = None  # Would need specific parsing
                    # This would require examining the actual HTML structure
            
            # Try different URL patterns, but also check response content for differences
            for date_info in week_dates[1:]:  # Skip today, already scraped
                try:
                    # Try Light Cinema specific URL patterns
                    date_urls = [
                        f"{self.cinema_url}?showdate={date_info['date']}",
                        f"{self.cinema_url}?date={date_info['date']}",  
                        f"{self.cinema_url}#{date_info['day_name']}",
                        f"https://sheffield.thelight.co.uk/cinema/guide/{date_info['date']}",
                    ]
                    
                    success = False
                    for url in date_urls:
                        try:
                            response = self.session.get(url, timeout=5)
                            if response.status_code == 200:
                                day_soup = BeautifulSoup(response.content, 'html.parser')
                                
                                # Check if this page actually has different content
                                day_text = day_soup.get_text()
                                original_text = soup.get_text()
                                
                                # Check if this is actually different content (different films)
                                day_titles = set()
                                day_film_elements = self.get_film_elements_from_soup(day_soup)
                                for elem in day_film_elements:
                                    title = self.extract_title_from_element(elem)
                                    if title and title != "Unknown Movie":
                                        day_titles.add(title)
                                
                                original_titles = set()
                                original_film_elements = self.get_film_elements_from_soup(soup)
                                for elem in original_film_elements:
                                    title = self.extract_title_from_element(elem)
                                    if title and title != "Unknown Movie":
                                        original_titles.add(title)
                                
                                # If we have significantly different films, it's a different day
                                unique_films = day_titles - original_titles
                                if len(unique_films) > 0:
                                    day_showings = self.scrape_day_from_html(day_soup, date_info)
                                    all_showings.extend(day_showings)
                                    print(f"Scraped {len(day_showings)} showings for {date_info['display']} - found {len(unique_films)} new films: {list(unique_films)[:3]}")
                                    success = True
                                    break
                                else:
                                    print(f"URL {url} returned same films as today - likely static content")
                        except Exception as e:
                            print(f"Failed to fetch {url}: {e}")
                            continue
                    
                    if not success:
                        print(f"Could not find different content for {date_info['display']} - may be AJAX loaded")
                            
                except Exception as e:
                    print(f"Could not scrape {date_info['display']}: {e}")
                    continue
            
            print(f"Total showings scraped for the week: {len(all_showings)}")
            return all_showings
            
        except Exception as e:
            print(f"Error in weekly HTML parsing: {e}")
            # Fallback to single day
            return self.scrape_day_from_html(soup, week_dates[0])
    
    def scrape_day_from_html(self, soup: BeautifulSoup, date_info: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Scrape showings for a specific day from HTML
        """
        showings = []
        seen_combinations = set()  # Track unique title+time combinations
        
        try:
            # Look for proper film containers with titles, not just sessions
            film_elements = []
            
            # Strategy 1: Look for film/movie containers with both title and times
            potential_film_containers = soup.find_all(['div', 'article', 'section'])
            
            for container in potential_film_containers:
                container_text = container.get_text()
                # Must have both times AND substantial text (likely title)
                if (re.search(r'\d{1,2}[:\.]?\d{2}', container_text) and 
                    len(container_text.strip()) > 20 and
                    # Skip if it's just a sessions container (no title info)
                    not (container.get('class') and 'sessions' in ' '.join(container.get('class')))):
                    
                    # Look for title elements within this container
                    title_candidates = container.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'b', 'span'])
                    has_title = False
                    for candidate in title_candidates:
                        candidate_text = candidate.get_text(strip=True)
                        if (len(candidate_text) > 3 and 
                            not re.match(r'^\d{1,2}[:\.]?\d{2}', candidate_text) and
                            not candidate_text.lower() in ['captioned', 'rewind', 'explore', 'iconic']):
                            has_title = True
                            break
                    
                    if has_title:
                        film_elements.append(container)
            
            print(f"Found {len(film_elements)} film elements for {date_info['display']}")
            
            for element in film_elements:
                # Get all text from the element
                full_text = element.get_text(separator=' ', strip=True)
                
                # Look for movie title using multiple strategies
                title = None
                
                # Strategy 1: Look for title in header tags and strong/b tags
                title_elements = element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'b'])
                for title_elem in title_elements:
                    candidate = title_elem.get_text(strip=True)
                    # Skip if it's just times or short text
                    if len(candidate) > 3 and not re.match(r'^\d{1,2}[:\.]?\d{2}', candidate):
                        title = candidate
                        break
                
                # Strategy 2: Look for data-title or title attributes
                if not title:
                    title_attr = element.get('data-title') or element.get('title')
                    if title_attr and len(title_attr) > 3:
                        title = title_attr
                
                # Strategy 3: Look for movie title in class names or ids
                if not title:
                    classes = ' '.join(element.get('class', []))
                    elem_id = element.get('id', '')
                    if 'film' in classes.lower() or 'movie' in classes.lower():
                        # Look for nested elements with meaningful text
                        for child in element.find_all(['span', 'div', 'p']):
                            candidate = child.get_text(strip=True)
                            if len(candidate) > 3 and not re.match(r'^\d{1,2}[:\.]?\d{2}', candidate):
                                # Check if this looks like a movie title (not just times)
                                if not re.search(r'^\d+[\s:]+\d+', candidate):
                                    title = candidate
                                    break
                
                # Strategy 4: Extract from beginning of text (before first time) - improved
                if not title:
                    # More sophisticated regex to capture movie titles
                    title_patterns = [
                        r'^([A-Z][^0-9]+?)(?=\s*\d{1,2}[:\.]?\d{2})',  # Starts with capital letter
                        r'^([^0-9]{4,}?)(?=\s*\d{1,2}[:\.]?\d{2})',     # At least 4 chars before time
                        r'^(.*?)(?=\s*\d{1,2}[:\.]?\d{2})'               # Anything before time
                    ]
                    
                    for pattern in title_patterns:
                        title_match = re.match(pattern, full_text)
                        if title_match:
                            candidate = title_match.group(1).strip()
                            if len(candidate) > 3:
                                title = candidate
                                break
                
                # Fallback if no title found
                if not title:
                    title = "Unknown Movie"
                
                # Clean up title
                title = re.sub(r'\s+', ' ', title)  # Normalize whitespace
                title = title.replace('|', '').strip()  # Remove separators
                
                # Filter out non-movie titles
                excluded_phrases = [
                    'stay in touch', 'contact us', 'newsletter', 'subscribe',
                    'follow us', 'social media', 'coming soon', 'book now',
                    'buy tickets', 'gift cards', 'membership', 'accessibility'
                ]
                
                if any(phrase in title.lower() for phrase in excluded_phrases):
                    continue
                
                # Find all time patterns in this element
                time_matches = re.findall(r'\b(\d{1,2}[:\.]?\d{2})\b', full_text)
                
                if title and len(title) > 2 and time_matches:
                    for time_str in time_matches:
                        # Normalize time format
                        if ':' not in time_str:
                            # Convert "1430" to "14:30"
                            if len(time_str) == 4:
                                time_str = f"{time_str[:2]}:{time_str[2:]}"
                        
                        # Create unique key to avoid duplicates
                        unique_key = f"{title.lower()}_{time_str}_{date_info['date']}"
                        
                        if unique_key not in seen_combinations:
                            seen_combinations.add(unique_key)
                            
                            showing = {
                                'title': title,
                                'time': time_str,
                                'date': date_info['date'],
                                'date_display': date_info['display'],
                                'cinema': self.cinema_name,
                                'source': 'html_direct'
                            }
                            showings.append(showing)
            
            print(f"Extracted {len(showings)} unique showings for {date_info['display']}")
            return showings
            
        except Exception as e:
            print(f"Error in HTML parsing: {e}")
            return []
    
    def save_json(self, showings: List[Dict[str, Any]], filename: str = 'cinema-times.json'):
        """Save showings to JSON file"""
        data = {
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S UK'),
            'cinema': self.cinema_name,
            'showings': showings
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Saved {len(showings)} showings to {filename}")


def clean_movie_titles(showings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Clean movie titles by removing parentheticals and adding tags"""
    try:
        from clean_titles import extract_title_and_tags
    except ImportError:
        print("⚠️  Title cleaner not available - skipping title cleaning")
        return showings
    
    print("🧹 Cleaning movie titles...")
    
    cleaned_count = 0
    for showing in showings:
        original_title = showing.get('title', '')
        if original_title:
            clean_title, tags = extract_title_and_tags(original_title)
            if clean_title != original_title:
                showing['title'] = clean_title
                if tags:
                    showing['title_tags'] = tags
                cleaned_count += 1
    
    if cleaned_count > 0:
        print(f"✅ Cleaned {cleaned_count} movie titles")
    
    return showings


def fetch_and_add_rt_scores(showings: List[Dict[str, Any]], api_key: str = None) -> List[Dict[str, Any]]:
    """Fetch RT/OMDb scores and add them to showings data"""
    try:
        # Import the OMDb fetcher
        from fetch_omdb_scores import OMDbFetcher
    except ImportError:
        print("⚠️  OMDb score fetcher not available - skipping score fetching")
        return showings
    
    # Get API key from environment or parameter
    if not api_key:
        api_key = os.environ.get('OMDB_API_KEY')
    
    if not api_key:
        print("⚠️  No OMDb API key found - skipping score fetching")
        print("   Set OMDB_API_KEY environment variable or pass --omdb-key parameter")
        return showings
    
    print(f"🎬 Fetching RT/OMDb scores with API key: {api_key[:8]}...")
    
    fetcher = OMDbFetcher(api_key)
    
    # Get unique movie titles
    unique_titles = set()
    for showing in showings:
        title = showing.get('title', '')
        if title:
            unique_titles.add(title)
    
    unique_titles.discard('')
    unique_titles = sorted(unique_titles)
    
    print(f"📊 Found {len(unique_titles)} unique movies to score")
    
    # Fetch scores for each unique title
    rt_scores = {}
    processed = 0
    
    for title in unique_titles:
        print(f"[{processed + 1}/{len(unique_titles)}] {title}")
        
        movie_data = fetcher.fetch_movie_data(title)
        
        if movie_data:
            rt_scores[title] = movie_data
        else:
            # Set default values
            rt_scores[title] = {
                'rt_critics_score': 0,
                'metacritic_score': 0,
                'imdb_score': 0,
                'composite_score': 0,
                'available_scores': [],
                'imdb_rating': 'N/A',
                'year': '',
                'omdb_title': ''
            }
        
        processed += 1
        
        # Be respectful - delay between requests
        if processed < len(unique_titles):
            time.sleep(1)
    
    # Update all showings with scores
    updated_count = 0
    for showing in showings:
        title = showing.get('title', '')
        if title in rt_scores:
            score_data = rt_scores[title]
            showing['rt_critics_score'] = score_data.get('rt_critics_score', 0)
            showing['metacritic_score'] = score_data.get('metacritic_score', 0)
            showing['imdb_score'] = score_data.get('imdb_score', 0)
            showing['composite_score'] = score_data.get('composite_score', 0)
            showing['available_scores'] = score_data.get('available_scores', [])
            showing['imdb_rating'] = score_data.get('imdb_rating', 'N/A')
            showing['omdb_title'] = score_data.get('omdb_title', '')
            showing['omdb_year'] = score_data.get('year', '')
            updated_count += 1
    
    scored_movies = sum(1 for scores in rt_scores.values() if scores.get('composite_score', 0) > 0)
    print(f"✅ Updated {updated_count} showings with scores")
    print(f"📈 Found scores for {scored_movies}/{len(unique_titles)} movies")
    
    return showings


def main():
    # Default to The Light Cinema Sheffield
    cinema_url = "https://sheffield.thelight.co.uk/cinema/guide"
    cinema_name = "The Light Cinema Sheffield"
    omdb_api_key = None
    
    # Parse command line arguments
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] in ['-h', '--help']:
            print("Cinema Times Scraper with RT Score Integration")
            print()
            print("Usage:")
            print("  python3 scraper.py [URL] [CINEMA_NAME] [OPTIONS]")
            print()
            print("Options:")
            print("  --omdb-key KEY    OMDb API key for RT/score fetching")
            print("  --no-scores       Skip RT score fetching entirely")
            print("  -h, --help        Show this help message")
            print()
            print("Environment Variables:")
            print("  OMDB_API_KEY      OMDb API key (alternative to --omdb-key)")
            print()
            print("Examples:")
            print("  python3 scraper.py")
            print("  python3 scraper.py --omdb-key your_api_key")
            print("  python3 scraper.py --no-scores")
            print("  export OMDB_API_KEY=your_key && python3 scraper.py")
            sys.exit(0)
        elif sys.argv[i] == '--omdb-key' and i + 1 < len(sys.argv):
            omdb_api_key = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--no-scores':
            omdb_api_key = 'skip'  # Special value to skip scoring
            i += 1
        elif i == 1:  # First non-flag argument is URL
            cinema_url = sys.argv[i]
            i += 1
        elif i == 2:  # Second non-flag argument is name
            cinema_name = sys.argv[i]
            i += 1
        else:
            i += 1
    
    print(f"🎭 Scraping cinema times from: {cinema_name}")
    print(f"🔗 URL: {cinema_url}")
    
    scraper = CinemaScraper(cinema_url, cinema_name)
    showings = scraper.scrape_times()
    
    if not showings:
        print("❌ No showings found - exiting")
        sys.exit(1)
    
    # Clean movie titles first
    showings = clean_movie_titles(showings)
    
    # Add RT scores unless explicitly skipped
    if omdb_api_key != 'skip':
        showings = fetch_and_add_rt_scores(showings, omdb_api_key)
    
    # Detect new films before saving - need to clean old titles for fair comparison
    old_films = set()
    try:
        import json
        with open('cinema-times.json', 'r') as f:
            old_data = json.load(f)
            # Clean old titles the same way we clean new ones for accurate comparison
            try:
                from clean_titles import extract_title_and_tags
                for showing in old_data.get('showings', []):
                    original_title = showing.get('title', '')
                    if original_title:
                        clean_title, _ = extract_title_and_tags(original_title)
                        old_films.add(clean_title)
            except ImportError:
                # Fallback if clean_titles not available
                old_films = set(showing.get('title', '') for showing in old_data.get('showings', []))
    except (FileNotFoundError, json.JSONDecodeError):
        print("📄 No previous data found - this appears to be first run")
        old_films = set()
    
    # Find new films (current films are already cleaned)
    current_films = set(s.get('title', '') for s in showings)
    new_films = current_films - old_films
    
    # Save the updated data
    scraper.save_json(showings)
    
    print(f"🎉 Scraping complete! Found {len(showings)} total showings")
    
    # Show statistics and new films
    unique_movies = len(current_films)
    scored_movies = len(set(s.get('title', '') for s in showings if s.get('composite_score', 0) > 0))
    print(f"📊 {unique_movies} unique movies, {scored_movies} with scores")
    
    if new_films:
        print(f"🆕 {len(new_films)} new films detected:")
        for film in sorted(new_films):
            # Get best composite score for this film
            film_showings = [s for s in showings if s.get('title') == film]
            best_score = max((s.get('composite_score', 0) for s in film_showings), default=0)
            score_display = f" ({best_score}★)" if best_score > 0 else ""
            print(f"   • {film}{score_display}")
        
        # Write new films summary for GitHub Actions
        with open('new-films.txt', 'w') as f:
            f.write(f"🎬 {len(new_films)} New Films at {cinema_name}:\n\n")
            for film in sorted(new_films):
                film_showings = [s for s in showings if s.get('title') == film]
                best_score = max((s.get('composite_score', 0) for s in film_showings), default=0)
                # Get showing dates
                dates = sorted(set(s.get('date', '') for s in film_showings))
                date_range = f"{dates[0]} to {dates[-1]}" if len(dates) > 1 else dates[0] if dates else "TBD"
                
                f.write(f"• {film}")
                if best_score > 0:
                    score_emoji = "🟢" if best_score >= 80 else "🟡" if best_score >= 65 else "🟠" if best_score >= 50 else "🔴"
                    f.write(f" {score_emoji} {best_score}/100")
                f.write(f"\n  📅 {date_range}\n\n")
        
        print("📧 New films summary written to new-films.txt for notifications")
    else:
        print("📽️ No new films detected since last run")
        # Create empty file to indicate no new films
        with open('new-films.txt', 'w') as f:
            f.write("No new films detected in this update.\n")


if __name__ == "__main__":
    main()