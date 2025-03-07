import os
import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

BASE_URL = 'http://collegecatalog.uchicago.edu/'
CATALOG_URL = BASE_URL + 'thecollege/programsofstudy/'


def clean_text(text: str) -> str:
    if not text:
        return 'N/A'
    text = text.replace('\xa0', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def get_department_links():
    resp = requests.get(CATALOG_URL)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.content, 'html.parser')
    department_links = []
    for a in soup.select('ul.nav.leveltwo a[href]'):
        full_url = BASE_URL + a['href']
        department_links.append(full_url)

    print(f'Found {len(department_links)} department links.')
    return department_links


def parse_course_page(url: str) -> list:
    time.sleep(1)
    resp = requests.get(url)
    if resp.status_code != 200:
        print(f"[Warning] Could not retrieve {url}; skipping.")
        return []

    soup = BeautifulSoup(resp.content, 'html.parser')
    course_blocks = soup.find_all('div', class_='courseblock')
    courses = []

    for block in course_blocks:
     
        title_p = block.find('p', class_='courseblocktitle')
        raw_title = clean_text(title_p.get_text()) if title_p else 'N/A'
     
        match = re.match(r'^(.*?)\.\s*(.*)$', raw_title)
        if match:
            course_number = clean_text(match.group(1))
            course_title  = clean_text(match.group(2))
        else:
            course_number = raw_title
            course_title  = 'N/A'

        desc_p = block.find('p', class_='courseblockdesc')
        description = clean_text(desc_p.get_text()) if desc_p else 'N/A'

        block_text = block.get_text()

        terms_m   = re.search(r'Terms Offered:\s*(.*)', block_text)
        equiv_m   = re.search(r'Equivalent Course\(s\):\s*(.*)', block_text)
        prereq_m  = re.search(r'Prerequisite\(s\):\s*(.*)', block_text)
        instr_m   = re.search(r'Instructor\(s\):\s*(.*)', block_text)

        terms_offered = clean_text(terms_m.group(1)) if terms_m else 'N/A'
        equivalents   = clean_text(equiv_m.group(1)) if equiv_m else 'N/A'
        prerequisites = clean_text(prereq_m.group(1)) if prereq_m else 'N/A'

        if instr_m:
            raw_instr = instr_m.group(1)
            if 'Terms Offered:' in raw_instr:
                raw_instr = raw_instr.split('Terms Offered:')[0]
            instructors = clean_text(raw_instr)
        else:
            instructors = 'N/A'

        course_info = {
            'Course Number':      course_number,
            'Course Title':       course_title,
            'Description':        description,
            'Terms Offered':      terms_offered,
            'Equivalent Courses': equivalents,
            'Prerequisites':      prerequisites,
            'Instructors':        instructors
        }
        courses.append(course_info)

    return courses


def save_to_csv(data, filename):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False, encoding='utf-8')
    print(f"Saved {len(df)} rows to {filename}")


class UnionFind:

    def __init__(self):
        self.parent = {}
    
    def find(self, x):
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    
    def union(self, a, b):
        rootA = self.find(a)
        rootB = self.find(b)
        if rootA != rootB:
            self.parent[rootB] = rootA
    
    def ensure_present(self, x):
        if x not in self.parent:
            self.parent[x] = x

def deduplicate_crosslisted(infile: str, outfile: str = 'deduplicated.csv'):

    df = pd.read_csv(infile, encoding='utf-8')
    uf = UnionFind()

    for idx, row in df.iterrows():
        main_num = row['Course Number']
        uf.ensure_present(main_num)

        eqv = row['Equivalent Courses']
        if isinstance(eqv, str) and eqv != 'N/A':
            eq_list = [x.strip() for x in eqv.split(',') if x.strip()]
            for eq_course in eq_list:
                uf.ensure_present(eq_course)
                uf.union(main_num, eq_course)


    group_ids = []
    for idx, row in df.iterrows():
        main_num = row['Course Number']
        uf.ensure_present(main_num)
        root = uf.find(main_num)
        group_ids.append(root)

    df['GroupID'] = group_ids


    df_dedup = df.groupby('GroupID', sort=False, as_index=False).head(1).copy()

    df_dedup.drop(columns=['GroupID'], inplace=True)
    df_dedup.to_csv(outfile, index=False, encoding='utf-8')

    print(f"Deduplicated cross-listed courses from {len(df)} down to {len(df_dedup)} (saved to {outfile})")


def department_statistics(filename, out_csv='departments.csv'):

    df = pd.read_csv(filename, encoding='utf-8')

    def get_dept(num):
        if isinstance(num, str):
            return num.split()[0]
        return 'Unknown'

    df['Department'] = df['Course Number'].apply(get_dept)
    dept_counts = df.groupby('Department').size().reset_index(name='Course Count')
    dept_counts.sort_values('Course Count', ascending=False, inplace=True)
    dept_counts.to_csv(out_csv, index=False, encoding='utf-8')
    print(f"Department stats saved to {out_csv}")
    return dept_counts


def write_answers(catalog_csv, dedup_csv, dept_csv, out_txt='answers.txt'):

    df_catalog = pd.read_csv(catalog_csv, encoding='utf-8')
    df_dedup   = pd.read_csv(dedup_csv,  encoding='utf-8')
    df_dept    = pd.read_csv(dept_csv,   encoding='utf-8')

    total_catalog = len(df_catalog)
    total_dedup   = len(df_dedup)

    top_dept      = df_dept.iloc[0]['Department']
    top_count     = df_dept.iloc[0]['Course Count']

    with open(out_txt, 'w', encoding='utf-8') as f:
        f.write(f"Total classes: {total_catalog}\n")
        f.write(f"Total unique classes: {total_dedup}\n")
        f.write(f"Department with most courses: {top_dept} ({top_count} courses)\n")

    print(f"Answers written to {out_txt}")


def main():
    dept_links = get_department_links()

    all_courses = []
    for link in dept_links:
        all_courses.extend(parse_course_page(link))

    save_to_csv(all_courses, 'catalog.csv')

    deduplicate_crosslisted('catalog.csv', 'deduplicated.csv')

    department_statistics('deduplicated.csv', 'departments.csv')

    write_answers('catalog.csv', 'deduplicated.csv', 'departments.csv', 'answers.txt')

    print("\nAll files created successfully.")

if __name__ == '__main__':
    main()
