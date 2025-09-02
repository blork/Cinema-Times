#!/usr/bin/env python3
"""
Fetch Rotten Tomatoes scores for movies and update cinema times JSON
"""

import json
import requests
import re
import time
from typing import Dict, Optional
import sys
from urllib.parse import quote_plus
import argparse

class RTScoreFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def clean_title_for_search(self, title: str) -> str:
        """Clean movie title for searching"""
        # Remove common parenthetical information
        title = re.sub(r'\s*\([^)]*\)\s*$', '', title)
        # Remove common suffixes
        title = re.sub(r'\s+(Re-Issue|Rerelease|Anniversary|Edition).*$', '', title, re.IGNORECASE)
        # Remove extra whitespace
        title = re.sub(r'\s+', ' ', title).strip()
        return title
        
    def search_rt_score(self, title: str) -> Optional[Dict]:
        """Search for RT score using RT search"""
        try:
            clean_title = self.clean_title_for_search(title)
            search_url = f"https://www.rottentomatoes.com/api/private/v1.0/movies?q={quote_plus(clean_title)}"
            
            print(f"Searching RT for: '{clean_title}'")
            
            response = self.session.get(search_url, timeout=10)
            if response.status_code != 200:
                print(f"  ❌ RT API returned {response.status_code}")
                return None
                
            data = response.json()
            movies = data.get('movies', [])
            
            if not movies:
                print(f"  ❌ No movies found")
                return None
                
            # Get the first result (usually most relevant)
            movie = movies[0]
            critics_score = movie.get('meterScore', 0) if movie.get('meterScore') is not None else 0
            audience_score = movie.get('audienceScore', 0) if movie.get('audienceScore') is not None else 0
            
            result = {
                'critics_score': critics_score,
                'audience_score': audience_score,
                'rt_url': f"https://www.rottentomatoes.com{movie.get('url', '')}"
            }
            
            print(f"  ✅ Found: Critics {critics_score}%, Audience {audience_score}%")
            return result
            
        except Exception as e:
            print(f"  ❌ Error fetching RT score: {e}")
            return None
    
    def get_fallback_score(self, title: str) -> Optional[Dict]:
        """Fallback method using web scraping"""
        try:
            clean_title = self.clean_title_for_search(title)
            search_term = clean_title.replace(' ', '_').lower()
            url = f"https://www.rottentomatoes.com/m/{search_term}"
            
            print(f"  Trying fallback URL: {url}")
            
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return None
                
            html = response.text
            
            # Look for critics score
            critics_match = re.search(r'tomatometer.*?(\d+)%', html, re.IGNORECASE | re.DOTALL)
            critics_score = int(critics_match.group(1)) if critics_match else 0
            
            # Look for audience score  
            audience_match = re.search(r'audience.*?(\d+)%', html, re.IGNORECASE | re.DOTALL)
            audience_score = int(audience_match.group(1)) if audience_match else 0
            
            if critics_score > 0 or audience_score > 0:
                result = {
                    'critics_score': critics_score,
                    'audience_score': audience_score,
                    'rt_url': url
                }
                print(f"  ✅ Fallback found: Critics {critics_score}%, Audience {audience_score}%")
                return result
                
        except Exception as e:
            print(f"  ❌ Fallback error: {e}")
            
        return None

def main():
    parser = argparse.ArgumentParser(description='Fetch RT scores for cinema times')
    parser.add_argument('input_file', nargs='?', default='cinema-times.json', help='Input JSON file')
    parser.add_argument('--output', '-o', help='Output file (defaults to input file)')
    parser.add_argument('--force-refresh', '-f', action='store_true', help='Force refresh all scores')
    args = parser.parse_args()
    
    input_file = args.input_file
    output_file = args.output or input_file
    
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {input_file} not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {input_file}")
        sys.exit(1)
        
    if 'showings' not in data:
        print("Error: No 'showings' found in JSON data")
        sys.exit(1)
        
    fetcher = RTScoreFetcher()
    
    # Get unique movie titles
    unique_titles = set()
    for showing in data['showings']:
        unique_titles.add(showing.get('title', ''))
    
    unique_titles.discard('')  # Remove empty titles
    unique_titles = sorted(unique_titles)
    
    print(f"Found {len(unique_titles)} unique movie titles")
    
    # Track RT scores
    rt_scores = {}
    processed = 0
    
    for title in unique_titles:
        print(f"\n[{processed + 1}/{len(unique_titles)}] Processing: {title}")
        
        # Skip if we already have a score and not forcing refresh
        if not args.force_refresh and any(
            showing.get('title') == title and 'rt_critics_score' in showing 
            for showing in data['showings']
        ):
            print("  ⏭️ Already has RT score, skipping")
            processed += 1
            continue
            
        # Try to get RT score
        score_data = fetcher.search_rt_score(title)
        if not score_data:
            score_data = fetcher.get_fallback_score(title)
            
        if score_data:
            rt_scores[title] = score_data
        else:
            print("  ❌ No RT score found")
            # Set default values to avoid repeated lookups
            rt_scores[title] = {
                'critics_score': 0,
                'audience_score': 0,
                'rt_url': ''
            }
            
        processed += 1
        
        # Be respectful - small delay between requests
        if processed < len(unique_titles):
            time.sleep(1)
    
    # Update all showings with RT scores
    updated_count = 0
    for showing in data['showings']:
        title = showing.get('title', '')
        if title in rt_scores:
            score_data = rt_scores[title]
            showing['rt_critics_score'] = score_data['critics_score']
            showing['rt_audience_score'] = score_data['audience_score']
            showing['rt_url'] = score_data['rt_url']
            updated_count += 1
    
    # Save updated data
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
        
    print(f"\n✅ Updated {updated_count} showings with RT scores")
    print(f"💾 Saved to {output_file}")

if __name__ == "__main__":
    main()