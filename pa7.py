import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import os
from urllib.parse import urljoin

# Base URL for the college catalog
base_url = "http://collegecatalog.uchicago.edu/"

# Headers to mimic a browser request
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Function to make HTTP requests with proper delay
def make_request(url):
    print(f"Requesting: {url}")
    time.sleep(3)  # Wait at least 3 seconds between queries
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to retrieve {url}: Status code {response.status_code}")
        return None

# Function to get all department links from the main page
def get_department_links():
    html = make_request(urljoin(base_url, "thecollege/courses/"))
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    departments = []
    
    # Find links to departments
    content_div = soup.find('div', class_='courseblock')
    if content_div:
        for link in content_div.find_all('a', href=True):
            href = link['href']
            if '/thecollege/' in href and not href.endswith('thecollege/courses/'):
                full_url = urljoin(base_url, href)
                departments.append((link.text.strip(), full_url))
    
    return departments

# Function to parse course information
def parse_course_info(soup):
    courses = []
    course_blocks = soup.find_all('div', class_='courseblock')
    
    for block in course_blocks:
        course_data = {
            'course_number': '',
            'course_title': '',
            'description': '',
            'terms_offered': '',
            'equivalent_courses': '',
            'prerequisites': '',
            'instructors': ''
        }
        
        # Get course title and number
        title_div = block.find('p', class_='courseblocktitle')
        if title_div:
            title_text = title_div.text.strip()
            # Extract course number
            course_number_match = re.search(r'([A-Z]{4}\s\d{5})', title_text)
            if course_number_match:
                course_data['course_number'] = course_number_match.group(1)
            
            # Extract course title
            title_parts = title_text.split('.')
            if len(title_parts) > 1:
                course_data['course_title'] = title_parts[1].strip()
        
        # Get course description
        desc_div = block.find('p', class_='courseblockdesc')
        if desc_div:
            course_data['description'] = desc_div.text.strip()
        
        # Get additional information
        extra_info = block.find_all('p', class_='courseblockextra')
        for info in extra_info:
            text = info.text.strip()
            
            if "Terms Offered" in text:
                course_data['terms_offered'] = text.replace("Terms Offered:", "").strip()
            elif "Equivalent Course(s)" in text or "Equivalent Courses" in text:
                course_data['equivalent_courses'] = text.replace("Equivalent Course(s):", "").replace("Equivalent Courses:", "").strip()
            elif "Prerequisite(s)" in text:
                course_data['prerequisites'] = text.replace("Prerequisite(s):", "").strip()
            elif "Instructor(s)" in text:
                course_data['instructors'] = text.replace("Instructor(s):", "").strip()
        
        courses.append(course_data)
    
    return courses

# Main function to scrape the catalog
def scrape_catalog(limit=None):
    all_courses = []
    departments = get_department_links()
    
    # For testing, limit the number of departments
    if limit:
        departments = departments[:limit]
    
    print(f"Found {len(departments)} departments")
    
    for dept_name, dept_url in departments:
        print(f"Processing department: {dept_name}")
        html = make_request(dept_url)
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            courses = parse_course_info(soup)
            for course in courses:
                course['department'] = dept_name
            all_courses.extend(courses)
            print(f"Added {len(courses)} courses from {dept_name}")
    
    return all_courses

# Function to deduplicate courses
def deduplicate_courses(df):
    # Remove exact duplicates
    df_dedup = df.drop_duplicates()
    
    # Group by course number and deduplicate while keeping the most complete information
    grouped = df_dedup.groupby('course_number')
    
    deduplicated_rows = []
    for _, group in grouped:
        if len(group) == 1:
            deduplicated_rows.append(group.iloc[0])
        else:
            # Merge information from duplicate entries
            merged_row = {}
            for col in group.columns:
                # For each column, take the non-empty value with the most information (longest string)
                non_empty_values = [val for val in group[col] if isinstance(val, str) and val.strip()]
                if non_empty_values:
                    merged_row[col] = max(non_empty_values, key=len)
                else:
                    merged_row[col] = ''
            
            deduplicated_rows.append(pd.Series(merged_row))
    
    return pd.DataFrame(deduplicated_rows)

# Function to count courses by department and quarter
def count_by_department_quarter(df):
    # Initialize quarters
    quarters = ['Autumn', 'Winter', 'Spring', 'Summer']
    
    # Create a DataFrame to store counts
    dept_counts = pd.DataFrame(columns=['Department'] + quarters + ['Total'])
    
    # Group by department
    grouped = df.groupby('department')
    
    rows = []
    for dept, group in grouped:
        row = {'Department': dept}
        total = 0
        
        # Count for each quarter
        for quarter in quarters:
            count = sum(group['terms_offered'].str.contains(quarter, case=False, na=False))
            row[quarter] = count
            total += count
        
        row['Total'] = total
        rows.append(row)
    
    dept_counts = pd.DataFrame(rows)
    
    # Sort by total, descending
    dept_counts = dept_counts.sort_values('Total', ascending=False)
    
    return dept_counts

# Main execution
if __name__ == "__main__":
    # For testing, you can set a limit
    # courses = scrape_catalog(limit=2)
    
    # For full run, no limit
    courses = scrape_catalog()
    
    # Create DataFrame
    df = pd.DataFrame(courses)
    
    # Save to CSV
    df.to_csv('catalog.csv', index=False)
    print(f"Saved {len(df)} courses to catalog.csv")
    
    # Deduplicate courses
    df_dedup = deduplicate_courses(df)
    df_dedup.to_csv('deduplicated.csv', index=False)
    print(f"Saved {len(df_dedup)} deduplicated courses to deduplicated.csv")
    
    # Count by department and quarter
    dept_counts = count_by_department_quarter(df_dedup)
    dept_counts.to_csv('departments.csv', index=False)
    print(f"Saved department counts to departments.csv")
    
    # Answer the questions
    with open('answers.txt', 'w') as f:
        f.write(f"1. How many classes are there overall? {len(df)}\n")
        f.write(f"2. How many classes do you get if you put a fair attempt into de-duplicating them? {len(df_dedup)}\n")
        most_classes_dept = dept_counts.iloc[0]['Department']
        most_classes_count = dept_counts.iloc[0]['Total']
        f.write(f"3. Which department offers the most (different) classes? {most_classes_dept} with {most_classes_count} classes\n")