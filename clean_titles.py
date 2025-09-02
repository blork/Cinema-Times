#!/usr/bin/env python3
"""
Clean movie titles by removing parentheticals and adding them as tags
"""

import json
import sys
import re
import html

def extract_title_and_tags(title):
    """Extract clean title and tags from a title with parentheticals ONLY"""
    # Decode HTML entities first
    clean_title = html.unescape(title)
    
    tags = []
    
    # ONLY extract content within parentheses as tags
    tag_patterns = [
        (r'\s*\((\d+th Anniversary.*?)\)', 'anniversary'),
        (r'\s*\((Re-Issue|Rerelease)\)', 'rerelease'),  
        (r'\s*\((4K Re-release)\)', 'remaster'),
        (r'\s*\((Dubbed|Subbed)\)', 'language'),
        (r'\s*\(Uncut\)', 'version'),
        (r'\s*\(Double Bill.*?\)', 'collection'),
        (r'\s*\(.*?Anniversary.*?\)', 'anniversary')
    ]
    
    # Extract tags and remove from title
    for pattern, tag_type in tag_patterns:
        match = re.search(pattern, clean_title, re.IGNORECASE)
        if match:
            tag_text = match.group(1) if match.lastindex else match.group(0).strip('()')
            tags.append({
                'type': tag_type,
                'text': tag_text
            })
            clean_title = re.sub(pattern, '', clean_title, flags=re.IGNORECASE).strip()
    
    # Handle a few special cases that aren't in parentheses
    # but are clearly format indicators, not part of the core title
    if clean_title.startswith('NT Live: '):
        tags.append({'type': 'format', 'text': 'NT Live'})
        clean_title = clean_title.replace('NT Live: ', '').strip()
    
    # Clean up any remaining extra whitespace
    clean_title = re.sub(r'\s+', ' ', clean_title).strip()
    
    return clean_title, tags

def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'cinema-times.json'
    
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {input_file} not found")
        sys.exit(1)
    
    if 'showings' not in data:
        print("Error: No 'showings' found in JSON data")
        sys.exit(1)
    
    # Track changes
    changes = {}
    updated_count = 0
    
    for showing in data['showings']:
        original_title = showing.get('title', '')
        
        if not original_title:
            continue
            
        clean_title, tags = extract_title_and_tags(original_title)
        
        # Only update if title actually changed
        if clean_title != original_title:
            if original_title not in changes:
                changes[original_title] = {
                    'clean_title': clean_title,
                    'tags': tags,
                    'count': 0
                }
            changes[original_title]['count'] += 1
            
            showing['title'] = clean_title
            if tags:
                showing['title_tags'] = tags
            updated_count += 1
        
        # Remove mock data fields if they exist
        mock_fields = ['rt_url', 'omdb_title', 'omdb_year']
        for field in mock_fields:
            if field in showing:
                del showing[field]
    
    # Display changes
    if changes:
        print(f"Cleaned {len(changes)} unique titles affecting {updated_count} showings:\n")
        
        for original, info in sorted(changes.items()):
            print(f"'{original}'")
            print(f"  → '{info['clean_title']}'")
            if info['tags']:
                tag_strs = [f"{tag['type']}: {tag['text']}" for tag in info['tags']]
                print(f"  → Tags: {', '.join(tag_strs)}")
            print(f"  → {info['count']} showings affected\n")
    
    # Save updated data
    with open(input_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Updated {updated_count} showings")
    print(f"💾 Saved to {input_file}")
    
    # Show some statistics
    unique_titles = set(showing.get('title', '') for showing in data['showings'])
    tagged_showings = sum(1 for showing in data['showings'] if 'title_tags' in showing)
    
    print(f"\n📊 Statistics:")
    print(f"  • {len(unique_titles)} unique clean titles")
    print(f"  • {tagged_showings} showings with tags")

if __name__ == "__main__":
    main()