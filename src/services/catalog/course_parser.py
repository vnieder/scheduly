"""
Course catalog parser service for extracting structured data from university websites.
This service uses web scraping and AI parsing to extract course information dynamically.
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse
import logging
from src.agents.gemini import client, MODEL

logger = logging.getLogger(__name__)

class CourseCatalogParser:
    """Parser for extracting course information from university websites."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def find_course_catalog_url(self, school: str) -> Optional[str]:
        """Find the course catalog URL for a university."""
        try:
            # Common patterns for course catalog URLs
            search_terms = [
                f"{school} course catalog",
                f"{school} academic bulletin",
                f"{school} course schedule",
                f"{school} course descriptions"
            ]
            
            for term in search_terms:
                # Use AI to find the catalog URL
                prompt = f"""Find the official course catalog URL for {school}.
                
                Search for the university's course catalog, academic bulletin, or course schedule page.
                Return ONLY the URL of the main course catalog page.
                If you can't find it, return null."""
                
                resp = client.models.generate_content(
                    model=MODEL,
                    config={
                        "tools": [{"google_search": {}}]
                    },
                    contents=[{"role": "user", "parts": [{"text": prompt}]}]
                )
                
                if resp.text:
                    # Extract URL from response
                    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                    urls = re.findall(url_pattern, resp.text)
                    if urls:
                        return urls[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding course catalog URL for {school}: {e}")
            return None
    
    def parse_course_page(self, url: str, course_code: str = None) -> List[Dict]:
        """Parse a course catalog page to extract course information."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Use AI to extract structured course data from the HTML
            html_content = str(soup)[:10000]  # Limit HTML size for AI processing
            
            prompt = f"""Extract course information from this university course catalog page.
            
            HTML Content (first 10000 characters):
            {html_content}
            
            {'Target course: ' + course_code if course_code else 'Extract all courses found'}
            
            Return a JSON array of course objects:
            [
                {{
                    "code": "course code (e.g., CS0401)",
                    "title": "course title",
                    "credits": number_of_credits,
                    "description": "course description",
                    "prerequisites": ["list of prerequisite course codes"],
                    "offered": ["semesters when offered"],
                    "instructor": "typical instructor (if mentioned)",
                    "department": "department name"
                }}
            ]
            
            Extract as many courses as possible from the page."""
            
            resp = client.models.generate_content(
                model=MODEL,
                config={
                    "response_mime_type": "application/json"
                },
                contents=[{"role": "user", "parts": [{"text": prompt}]}]
            )
            
            if resp.parsed and isinstance(resp.parsed, list):
                return resp.parsed
            
            return []
            
        except Exception as e:
            logger.error(f"Error parsing course page {url}: {e}")
            return []
    
    def search_course_by_code(self, school: str, course_code: str) -> Optional[Dict]:
        """Search for a specific course by code."""
        try:
            # First try to find the course catalog URL
            catalog_url = self.find_course_catalog_url(school)
            
            if catalog_url:
                # Try to parse the catalog page
                courses = self.parse_course_page(catalog_url, course_code)
                
                # Find the specific course
                for course in courses:
                    if course.get('code', '').upper() == course_code.upper():
                        return course
            
            # Fallback: use AI search
            prompt = f"""Find detailed information about {course_code} at {school}.
            
            Search the university's course catalog or department website.
            
            Return a JSON object with this structure:
            {{
                "code": "{course_code}",
                "title": "course title",
                "credits": number_of_credits,
                "description": "detailed course description",
                "prerequisites": ["list of prerequisite course codes"],
                "offered": ["semesters when offered"],
                "instructor": "typical instructor",
                "department": "department name",
                "url": "course catalog URL if found"
            }}"""
            
            resp = client.models.generate_content(
                model=MODEL,
                config={
                    "response_mime_type": "application/json",
                    "tools": [{"google_search": {}}]
                },
                contents=[{"role": "user", "parts": [{"text": prompt}]}]
            )
            
            if resp.parsed and isinstance(resp.parsed, dict):
                return resp.parsed
            
            return None
            
        except Exception as e:
            logger.error(f"Error searching for course {course_code} at {school}: {e}")
            return None
    
    def get_department_courses(self, school: str, department: str) -> List[Dict]:
        """Get all courses for a specific department."""
        try:
            prompt = f"""Find all courses offered by the {department} department at {school}.
            
            Search the department's course listing or the university's course catalog.
            
            Return a JSON array of course objects:
            [
                {{
                    "code": "course code",
                    "title": "course title",
                    "credits": number_of_credits,
                    "description": "brief description",
                    "prerequisites": ["prerequisite course codes"],
                    "offered": ["semesters offered"],
                    "level": "undergraduate/graduate"
                }}
            ]
            
            Include all courses from introductory to advanced levels."""
            
            resp = client.models.generate_content(
                model=MODEL,
                config={
                    "response_mime_type": "application/json",
                    "tools": [{"google_search": {}}]
                },
                contents=[{"role": "user", "parts": [{"text": prompt}]}]
            )
            
            if resp.parsed and isinstance(resp.parsed, list):
                return resp.parsed
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting courses for {department} at {school}: {e}")
            return []
    
    def extract_prerequisites(self, course_description: str) -> List[str]:
        """Extract prerequisite course codes from a course description."""
        try:
            # Common patterns for prerequisites
            prereq_patterns = [
                r'prerequisite[s]?:?\s*([A-Z]{2,4}\s*\d{3,4}(?:\s*,\s*[A-Z]{2,4}\s*\d{3,4})*)',
                r'prereq[s]?:?\s*([A-Z]{2,4}\s*\d{3,4}(?:\s*,\s*[A-Z]{2,4}\s*\d{3,4})*)',
                r'required:\s*([A-Z]{2,4}\s*\d{3,4}(?:\s*,\s*[A-Z]{2,4}\s*\d{3,4})*)',
                r'must have taken\s*([A-Z]{2,4}\s*\d{3,4}(?:\s*,\s*[A-Z]{2,4}\s*\d{3,4})*)'
            ]
            
            prerequisites = []
            for pattern in prereq_patterns:
                matches = re.findall(pattern, course_description, re.IGNORECASE)
                for match in matches:
                    # Split by comma and clean up course codes
                    courses = [re.sub(r'\s+', '', course.strip()) for course in match.split(',')]
                    prerequisites.extend(courses)
            
            # Remove duplicates and return
            return list(set(prerequisites))
            
        except Exception as e:
            logger.error(f"Error extracting prerequisites: {e}")
            return []

# Global parser instance
course_parser = CourseCatalogParser()

def get_course_info(school: str, course_code: str) -> Optional[Dict]:
    """Get detailed information about a specific course."""
    return course_parser.search_course_by_code(school, course_code)

def get_department_courses(school: str, department: str) -> List[Dict]:
    """Get all courses for a department."""
    return course_parser.get_department_courses(school, department)

def parse_course_catalog(school: str) -> List[Dict]:
    """Parse the entire course catalog for a university."""
    catalog_url = course_parser.find_course_catalog_url(school)
    if catalog_url:
        return course_parser.parse_course_page(catalog_url)
    return []
