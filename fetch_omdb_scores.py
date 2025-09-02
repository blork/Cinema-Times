#!/usr/bin/env python3
"""
Fetch real Rotten Tomatoes scores using OMDb API
"""

import json
import requests
import time
import sys
import html
import re
import argparse
from typing import Dict, Optional

class OMDbFetcher:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://www.omdbapi.com/"
        self.session = requests.Session()
        
    def clean_title_for_search(self, title: str) -> str:
        """Clean movie title for searching - only remove parentheticals"""
        # Decode HTML entities
        title = html.unescape(title)
        
        # Remove only parenthetical information (anniversary editions, language versions, etc.)
        title = re.sub(r'\s*\([^)]*\)', '', title)
        
        # Handle a few special format cases
        if title.startswith('NT Live: '):
            title = title.replace('NT Live: ', '')
        
        # Handle special cases for better matching
        if 'F1 ®' in title or 'F1 &#174;' in title:
            title = 'F1'
        elif 'Double Bill' in title or '& Aliens' in title:
            # For double bills, search for the first movie
            if 'Alien' in title:
                title = 'Alien'
        elif 'Spinal Tap II: The End Continues' in title:
            title = 'Spinal Tap II'
        
        return title.strip()
        
    def fetch_movie_data(self, title: str, year: str = None) -> Optional[Dict]:
        """Fetch movie data from OMDb API"""
        try:
            clean_title = self.clean_title_for_search(title)
            
            params = {
                'apikey': self.api_key,
                't': clean_title,
                'type': 'movie'
            }
            
            if year:
                params['y'] = year
            
            print(f"Searching OMDb for: '{clean_title}'" + (f" ({year})" if year else ""))
            
            response = self.session.get(self.base_url, params=params, timeout=10)
            if response.status_code != 200:
                print(f"  ❌ API returned {response.status_code}")
                return None
                
            data = response.json()
            
            if data.get('Response') == 'False':
                print(f"  ❌ Movie not found: {data.get('Error', 'Unknown error')}")
                return None
            
            # Extract all available scores
            rt_critics_score = 0
            imdb_score = 0
            metacritic_score = 0
            
            # Parse ratings array
            ratings = data.get('Ratings', [])
            for rating in ratings:
                source = rating.get('Source', '')
                value = rating.get('Value', '')
                
                if 'Rotten Tomatoes' in source and '%' in value:
                    rt_critics_score = int(value.replace('%', ''))
                elif 'Metacritic' in source and '/100' in value:
                    metacritic_score = int(value.split('/')[0])
            
            # Get IMDb rating (convert from 10-point to 100-point scale)
            imdb_rating = data.get('imdbRating', 'N/A')
            if imdb_rating != 'N/A' and imdb_rating != '':
                try:
                    imdb_score = int(float(imdb_rating) * 10)  # 7.3 -> 73
                except:
                    imdb_score = 0
            
            # Calculate composite score (weighted average of available scores)
            scores = []
            if rt_critics_score > 0:
                scores.append(('RT', rt_critics_score, 3))  # Weight RT highest
            if metacritic_score > 0:
                scores.append(('MC', metacritic_score, 2))  # Weight Metacritic medium
            if imdb_score > 0:
                scores.append(('IMDb', imdb_score, 1))  # Weight IMDb lowest
            
            if scores:
                # Calculate weighted average
                total_weighted = sum(score * weight for _, score, weight in scores)
                total_weight = sum(weight for _, _, weight in scores)
                composite_score = int(total_weighted / total_weight)
                
                result = {
                    'rt_critics_score': rt_critics_score,
                    'metacritic_score': metacritic_score, 
                    'imdb_score': imdb_score,
                    'composite_score': composite_score,
                    'available_scores': [name for name, _, _ in scores],
                    'imdb_rating': data.get('imdbRating', 'N/A'),
                    'year': data.get('Year', ''),
                    'omdb_title': data.get('Title', '')
                }
                
                score_info = ', '.join([f"{name}: {score}" for name, score, _ in scores])
                print(f"  ✅ Found: '{data.get('Title')}' ({data.get('Year')}) - {score_info} (Composite: {composite_score})")
                return result
            else:
                print(f"  ⚠️  Found movie but no usable scores available")
                return None
                
        except Exception as e:
            print(f"  ❌ Error fetching data: {e}")
            return None

def get_api_key():
    """Get OMDb API key from user or environment"""
    import os
    
    # Try environment variable first
    api_key = os.environ.get('OMDB_API_KEY')
    if api_key:
        return api_key
    
    # Prompt user for API key
    print("OMDb API key required. Get one free at: http://www.omdbapi.com/apikey.aspx")
    api_key = input("Enter your OMDb API key: ").strip()
    
    if not api_key:
        print("Error: API key is required")
        sys.exit(1)
        
    return api_key

def main():
    parser = argparse.ArgumentParser(description='Fetch real RT scores from OMDb API')
    parser.add_argument('input_file', nargs='?', default='cinema-times.json', help='Input JSON file')
    parser.add_argument('--output', '-o', help='Output file (defaults to input file)')
    parser.add_argument('--api-key', '-k', help='OMDb API key (or set OMDB_API_KEY env var)')
    parser.add_argument('--force-refresh', '-f', action='store_true', help='Force refresh all scores')
    parser.add_argument('--limit', '-l', type=int, help='Limit number of movies to process (for testing)')
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or get_api_key()
    
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
        
    fetcher = OMDbFetcher(api_key)
    
    # Get unique movie titles
    unique_titles = set()
    for showing in data['showings']:
        unique_titles.add(showing.get('title', ''))
    
    unique_titles.discard('')  # Remove empty titles
    unique_titles = sorted(unique_titles)
    
    if args.limit:
        unique_titles = unique_titles[:args.limit]
        print(f"Limited to first {args.limit} movies for testing")
    
    print(f"Found {len(unique_titles)} unique movie titles")
    
    # Track RT scores
    rt_scores = {}
    processed = 0
    
    for title in unique_titles:
        print(f"\n[{processed + 1}/{len(unique_titles)}] Processing: {title}")
        
        # Skip if we already have a score and not forcing refresh
        if not args.force_refresh and any(
            showing.get('title') == title and showing.get('rt_critics_score', 0) > 0
            for showing in data['showings']
        ):
            print("  ⏭️ Already has RT score, skipping")
            processed += 1
            continue
            
        # Try to get movie data from OMDb
        movie_data = fetcher.fetch_movie_data(title)
        
        if movie_data:
            rt_scores[title] = movie_data
        else:
            print("  ❌ No scores found")
            # Set default values to avoid repeated lookups
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
        
        # Be respectful - delay between requests (OMDb allows 1000/day on free tier)
        if processed < len(unique_titles):
            time.sleep(1)
    
    # Update all showings with scores
    updated_count = 0
    for showing in data['showings']:
        title = showing.get('title', '')
        if title in rt_scores:
            score_data = rt_scores[title]
            # Update with all available scores
            showing['rt_critics_score'] = score_data.get('rt_critics_score', 0)
            showing['metacritic_score'] = score_data.get('metacritic_score', 0) 
            showing['imdb_score'] = score_data.get('imdb_score', 0)
            showing['composite_score'] = score_data.get('composite_score', 0)
            showing['available_scores'] = score_data.get('available_scores', [])
            showing['imdb_rating'] = score_data.get('imdb_rating', 'N/A')
            showing['omdb_title'] = score_data.get('omdb_title', '')
            showing['omdb_year'] = score_data.get('year', '')
            updated_count += 1
    
    # Save updated data
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
        
    print(f"\n✅ Updated {updated_count} showings with RT scores from OMDb")
    print(f"💾 Saved to {output_file}")
    print("\nNote: OMDb free tier allows 1000 requests per day")

if __name__ == "__main__":
    main()