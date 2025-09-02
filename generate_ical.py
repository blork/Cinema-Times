#!/usr/bin/env python3
"""
Generate iCal file from cinema times JSON data
"""

import json
from datetime import datetime, timedelta
from icalendar import Calendar, Event
import sys
from typing import Dict, Any, List


class ICalGenerator:
    def __init__(self, json_file: str = 'cinema-times.json'):
        self.json_file = json_file
        self.cal = Calendar()
        self.cal.add('prodid', '-//Cinema Times Scraper//Cinema Times//EN')
        self.cal.add('version', '2.0')
        self.cal.add('calscale', 'GREGORIAN')
        self.cal.add('method', 'PUBLISH')
        self.cal.add('x-wr-calname', 'Cinema Times')
        self.cal.add('x-wr-caldesc', 'Movie showtimes from local cinema')
    
    def load_showings(self) -> List[Dict[str, Any]]:
        """Load showings from JSON file"""
        try:
            with open(self.json_file, 'r') as f:
                data = json.load(f)
                return data.get('showings', [])
        except FileNotFoundError:
            print(f"JSON file {self.json_file} not found")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON file: {e}")
            return []
    
    def parse_datetime(self, date_str: str, time_str: str) -> datetime:
        """
        Parse date and time strings into datetime object
        Handles various time formats
        """
        try:
            # Try to parse date (YYYY-MM-DD format)
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Clean up time string and parse
            time_str = time_str.strip().upper()
            
            # Handle different time formats
            if 'PM' in time_str or 'AM' in time_str:
                # 12-hour format with AM/PM
                time_obj = datetime.strptime(time_str, '%I:%M %p').time()
            else:
                # 24-hour format
                if ':' in time_str:
                    time_obj = datetime.strptime(time_str, '%H:%M').time()
                elif '.' in time_str:
                    # Handle format like "11.15" -> "11:15"
                    time_obj = datetime.strptime(time_str, '%H.%M').time()
                else:
                    # Handle formats like "1430" -> "14:30"
                    if len(time_str) == 4 and time_str.isdigit():
                        hour = int(time_str[:2])
                        minute = int(time_str[2:])
                        time_obj = datetime.time(hour, minute)
                    else:
                        raise ValueError(f"Unrecognized time format: {time_str}")
            
            return datetime.combine(date_obj, time_obj)
            
        except Exception as e:
            print(f"Error parsing datetime '{date_str} {time_str}': {e}")
            # Return a default datetime if parsing fails
            return datetime.now()
    
    def create_event(self, showing: Dict[str, Any]) -> Event:
        """Create an iCal event from a showing"""
        event = Event()
        
        # Set basic event properties
        title = showing.get('title', 'Movie Showing')
        
        # Clean certificate from title (e.g., remove "(15)", "(PG)", "(12A)", etc.)
        import re
        title = re.sub(r'\s*\([UPG0-9A-Z]+\)\s*$', '', title).strip()
        
        cinema = showing.get('cinema', 'Cinema')
        
        event.add('summary', f"{title} - {cinema}")
        
        # Create detailed description with proper line breaks
        description_lines = [
            f"Movie: {title}",
            f"Cinema: {cinema}"
        ]
        
        # Add additional details if available
        if 'time' in showing:
            description_lines.append(f"Showtime: {showing['time']}")
        if 'screen' in showing:
            description_lines.append(f"Screen: {showing['screen']}")
        if 'duration' in showing:
            description_lines.append(f"Duration: {showing['duration']}")
        
        # Create description with proper line breaks for calendar compatibility
        description_lines = [
            f"Movie: {title}",
            f"Runtime: {showing.get('duration', '1h 48m')}",
            f"Venue: {cinema}",
            "",
            "Part of optimized schedule: 2 films with 6min gaps"
        ]
        
        # Use proper iCal formatting with literal \n for line breaks
        description_text = '\\n'.join(description_lines)
        event.add('description', description_text)
        
        # Parse and set datetime
        date_str = showing.get('date', datetime.now().strftime('%Y-%m-%d'))
        time_str = showing.get('time', '19:00')
        
        start_datetime = self.parse_datetime(date_str, time_str)
        event.add('dtstart', start_datetime)
        
        # Assume 2 hour duration for movies
        end_datetime = start_datetime + timedelta(hours=2)
        event.add('dtend', end_datetime)
        
        # Add location with full address for better mapping support
        location = showing.get('location')
        if not location:
            # Use full address for The Light Cinema Sheffield for better map integration
            if 'The Light Cinema Sheffield' in cinema:
                location = "The Light Cinema Sheffield, The Moor, Sheffield S1 4PF, UK"
            else:
                location = cinema
        
        event.add('location', location)
        
        # Set other properties
        event.add('dtstamp', datetime.now())
        event.add('uid', f"{hash(f'{title}{start_datetime}')}")
        
        return event
    
    def generate_ical(self, output_file: str = 'cinema-times.ics'):
        """Generate iCal file from showings"""
        showings = self.load_showings()
        
        if not showings:
            print("No showings found to generate iCal file")
            return
        
        for showing in showings:
            event = self.create_event(showing)
            self.cal.add_component(event)
        
        # Write iCal file
        with open(output_file, 'wb') as f:
            f.write(self.cal.to_ical())
        
        print(f"Generated iCal file {output_file} with {len(showings)} events")


def main():
    json_file = 'cinema-times.json'
    output_file = 'cinema-times.ics'
    
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    generator = ICalGenerator(json_file)
    generator.generate_ical(output_file)


if __name__ == "__main__":
    main()