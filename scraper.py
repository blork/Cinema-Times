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
                    # Debug: Print the problematic element text
                    print(f"DEBUG - Unknown Movie found. Element text: '{full_text[:200]}...'")
                    print(f"DEBUG - Element HTML snippet: '{str(element)[:300]}...'")
                    print("---")
                
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
            'last_updated': datetime.now().isoformat(),
            'cinema': self.cinema_name,
            'showings': showings
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Saved {len(showings)} showings to {filename}")


def main():
    # Default to The Light Cinema Sheffield
    cinema_url = "https://sheffield.thelight.co.uk/cinema/guide"
    cinema_name = "The Light Cinema Sheffield"
    
    if len(sys.argv) > 1:
        cinema_url = sys.argv[1]
    if len(sys.argv) > 2:
        cinema_name = sys.argv[2]
    
    scraper = CinemaScraper(cinema_url, cinema_name)
    showings = scraper.scrape_times()
    scraper.save_json(showings)


if __name__ == "__main__":
    main()