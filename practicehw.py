import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import csv
import re

BASE_URL = 'http://collegecatalog.uchicago.edu/'
CATALOG_URL = BASE_URL + 'thecollege/programsofstudy/'

def get_department_links():
    """Fetch all department page links from the catalog."""
    response = requests.get(CATALOG_URL)
    soup = BeautifulSoup(response.content, 'html.parser')
    lsts = soup.find_all('ul', class_='nav leveltwo')
    
    hrefs = []
    for lst in lsts:
        for a_tag in lst.find_all('a', href=True):
            hrefs.append(BASE_URL + a_tag['href'])
    return hrefs

def parse_course_page(url):
    """Extract all course details from a department page."""
    time.sleep(3)  # Enforce 3-second delay
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    courses = []
    
    course_blocks = soup.find_all('div', class_='courseblock main')
    for block in course_blocks:
        number = block.find('p', class_='courseblocktitle')
        desc = block.find('p', class_='courseblockdesc')
        terms = re.search(r'Terms Offered: (.*?)<', str(block))
        equivalents = re.search(r'Equivalent Course\(s\): (.*?)<', str(block))
        prerequisites = re.search(r'Prerequisite\(s\): (.*?)<', str(block))
        instructors = re.search(r'Instructor\(s\): (.*?)<', str(block))
        
        courses.append({
            'Course Number': number.text.strip() if number else 'N/A',
            'Description': desc.text.strip() if desc else 'N/A',
            'Terms Offered': terms.group(1) if terms else 'N/A',
            'Equivalent Courses': equivalents.group(1) if equivalents else 'N/A',
            'Pre Requisites': prerequisites.group(1) if prerequisites else 'N/A',
            'Instructors': instructors.group(1) if instructors else 'N/A'
        })
    return courses

def save_to_csv(data, filename):
    """Save list of dictionaries to CSV file."""
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False, encoding='utf-8')

def deduplicate_courses(filename):
    """Remove duplicate courses based on course number and save to deduplicated.csv."""
    df = pd.read_csv(filename)
    df.drop_duplicates(subset=['Course Number'], keep='first', inplace=True)
    df.to_csv('deduplicated.csv', index=False, encoding='utf-8')

def department_statistics(filename):
    """Generate department-wise course counts and save to departments.csv."""
    df = pd.read_csv(filename)
    df['Department'] = df['Course Number'].apply(lambda x: x.split()[0] if isinstance(x, str) else 'Unknown')
    dept_counts = df.groupby('Department')['Course Number'].count().reset_index()
    dept_counts.columns = ['Department', 'Course Count']
    dept_counts.to_csv('departments.csv', index=False, encoding='utf-8')
    return dept_counts

def write_answers(catalog_file, dedup_file, dept_file):
    """Write answers to questions in answers.txt."""
    total_courses = pd.read_csv(catalog_file).shape[0]
    dedup_courses = pd.read_csv(dedup_file).shape[0]
    dept_counts = pd.read_csv(dept_file)
    top_dept = dept_counts.sort_values(by='Course Count', ascending=False).iloc[0]
    
    with open('answers.txt', 'w') as f:
        f.write(f'Total classes: {total_courses}\n')
        f.write(f'Total unique classes: {dedup_courses}\n')
        f.write(f'Department with most courses: {top_dept["Department"]} ({top_dept["Course Count"]} courses)\n')

if __name__ == '__main__':
    department_links = get_department_links()
    
    all_courses = []
    for link in department_links:
        all_courses.extend(parse_course_page(link))
    
    if not all_courses:
        print("No courses found. Exiting.")
    else:
        save_to_csv(all_courses, 'catalog.csv')
        deduplicate_courses('catalog.csv')
        department_statistics('deduplicated.csv')
        write_answers('catalog.csv', 'deduplicated.csv', 'departments.csv')
        print("All files created successfully.")
