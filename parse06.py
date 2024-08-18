from bs4 import BeautifulSoup
from html_to_plain import html_to_plain
import io
import os
import pyperclip
import re
import requests
from time import sleep

# Save user inputs
inputs = input("Enter id, doc url, and filing url...\n  ").split('\t')
if len(inputs) != 3: exit('Error: Exactly three inputs (id, doc URL, and filing URL) not received.')
[id, doc_url, filing_url] = inputs

# Define helper function
clear = lambda: os.system('cls')

def format_fund(str):
    str = str.lower()
    str = str.replace('-', ' ').replace('&reg;', '®').replace('&', 'and')
    str = re.sub(r'[^a-zA-Z\s®]', '', str)
    str = str.replace('fund name', '')
    str = str.strip()
    return str

# Get filing
headers = {"User-Agent": "Mozilla/5.0 (Joel Malissa jmaliska@gmail.com)"}
response = requests.get(filing_url, headers=headers)
sleep(1)
if response.status_code == 200:
    filing = response.text
else:
    print("Failed to retrieve the content. Status code:", response.status_code)

# Get document
response = requests.get(doc_url, headers=headers)
sleep(1)
if response.status_code == 200:
    doc = response.text
else:
    print("Failed to retrieve the content. Status code:", response.status_code)

# Create fund-ticker map
filing_soup = BeautifulSoup(filing, 'html.parser')
fund_tickers = {}
rows = filing_soup.find_all('tr')
state = 'init'
for row in rows:
    tds = row.find_all('td')
    match state:
        case 'init':
            texts = [td.get_text(strip=True) for td in tds if td.get_text(strip=True) != '']
            if texts[:-1] == ['Status', 'Name', 'Ticker Symbol']:
                state = 'headers'
        case 'headers':
            state = 'spacer'
        case 'spacer':
            state = 'fund'
            fund = tds[2].get_text()
            fund_tickers[format_fund(fund)] = [fund, []]
        case 'fund':
            texts = [td.get_text(strip=True) for td in tds if td.get_text(strip=True) != '']
            if texts[:-1] == ['Status', 'Name', 'Ticker Symbol']:
                state = 'headers'
            else:
                if len(texts) == 3:
                    ticker = texts[2]
                    fund_tickers[format_fund(fund)][1].append(ticker)

for fund in fund_tickers:
    fund_tickers[fund][1] = ', '.join(sorted(fund_tickers[fund][1]))

fund_tickers = dict(sorted(fund_tickers.items()))
print(fund_tickers)

# Get last one or two words of each name
keywords = []
keywords2 = []
for f in list(fund_tickers.keys()):
    f_array = f.split()
    keyword = f_array[-1]
    keyword2 = ' '.join(f_array[-2:])
    # if f_array[-1] in ['i', 'ii', 'iii']:  # Exception for fidelity contrafund k or largecap growth account i
    #     keyword = ' '.join(f_array[-2:])
    keywords.append(keyword)
    keywords2.append(keyword2)

# De-dupe and sort
keywords = list(dict.fromkeys(keywords))
keywords2 = list(dict.fromkeys(keywords2))
keywords.sort()
keywords2.sort()

# Count funds from filing
n_filing_funds = len(fund_tickers)

# Extract doc text
print('Extracting text.')
doc = doc.replace('&nbsp;', ' ').replace('\xa0', ' ')
buffer = io.StringIO()
html_to_plain(doc, buffer)  # 8/18/2024 Switched to Sebastien's renderer
doc_text = buffer.getvalue()
# doc_soup = BeautifulSoup(doc, 'html.parser')  # Note: lxml truncations to 10 MB
# doc_text = doc_soup.get_text(separator='\n')
lines = doc_text.splitlines()
lines = [line for line in lines if line.strip() != '']
print('Extracted text.')
# lines = [l for l in lines if l != '']  # Remove empty lines

# Count fund mentions from doc
names = list(fund_tickers.keys())
re_keywords = [k + '[^a-zA-Z]*$' for k in keywords]  # in keywords2]  (Option for using last one or two words in fund names)
names_minus_keywords = [n.rsplit(' ', 1)[0] for n in names]
regex = r"(^fund name|" + "|".join(names + names_minus_keywords + re_keywords) + r")"
fund_pattern = re.compile(regex, re.IGNORECASE)
n_doc_funds = sum(1 for line in lines if fund_pattern.search(format_fund(line)))

# Count tesla mentions from doc
n_tesla = sum(1 for line in lines if 'tesla' in line.lower())

print('Filing: Count of funds: ' + str(n_filing_funds))
print('Doc: Count of funds: ' + str(n_doc_funds) + ', count of "tesla": ' + str(n_tesla) + '\n')


# For iterating through lines, define helper function
def get_fund(i):
    line = lines[i]
    raw_line = line
    line = format_fund(line)
    exact_matches = 0
    substring_matches = 0
    exact_match = None
    substring_match = None
    for name in names:  # Global variable names is the keys of fund_tickers
        if line == name or line == name.lower().replace('fund', '').strip():
            exact_matches += 1
            exact_match = name
        if line in name or name in line:
            substring_matches += 1
            substring_match = name
    if exact_matches == 1:
        return exact_match, raw_line
    elif substring_matches == 1:
        return substring_match, raw_line
    else:
        # Else manually specify name (with recommendations)
        print('Funds:')
        print('\n'.join(list(fund_tickers.keys())))
        print('Doc funds: ' + str(n_doc_funds) + ' (Filing funds:  ' + str(n_filing_funds) + ', Tesla: ' + str(n_tesla) + ')\n')
        print(lines[i-2] + '\n' + lines[i-1] + '\n' + str(i) + '>>   ' + line + '\nraw: ' + raw_line + '\n' + lines[i+1] + '\n' + lines[i+2])
        temp = input('\n  [Enter]: Skip\n  [Fund name]: Copy inputted fund name\n  ')
        temp = temp.strip()
        if temp == '':
            return None, None
        else:
            return temp, raw_line

# Init variables to be used while processing document
fund_inds = []
tesla_ind = -1
latest = -1
fund_line = None
if n_filing_funds == 1:
    fund = list(fund_tickers.keys())[0]
    print('Only filing fund: ' + fund)
    input('TEST: n_filing_funds == 1.  (Press enter.)')
else:
    fund = None

# Iterate through lines
i = 0
j = 0
while i < len(lines):
    line = lines[i]
    # print(line)
    raw_line = line
    line = format_fund(line)
    # if 'alternative' in line:
    #     print(raw_line)
    #     input()
    if fund_pattern.search(line) or any([name in line for name in names]):
        fund_inds.append(i)
    if 'tesla' in raw_line.lower():
        # Get fund
        if latest != fund_inds[-1]:
            fund = None
            fund_raw = None
            j = 0
            while fund is None:
                fund, fund_raw = get_fund(fund_inds[-1 - j])
                j += 1
            latest = fund_inds[-1]
        print(fund)
        print(fund_raw)
        sleep(1)
        # exit()
        
        # Process the vote
        print('Tesla: ' + str(n_tesla))
        print('tesla line: ' + str(i))
        [print(l) for l in lines[i:i+40]]
        print('  [0 or Enter]: Skip\n  [1]: For\n  [2]: Against\n  [3]: -\n  ')
        sleep(1)
        temp = input()
        
        if temp == '' or temp == '0':
            vote = None
        elif temp == '1':
            vote = 'For'
        elif temp == '2':
            vote = 'Against'
        elif temp == '3':
            vote = '-'
        if vote is not None:
            output = '\t'.join([id, doc_url, filing_url, fund_tickers[format_fund(fund)][0], fund_tickers[format_fund(fund)][1], 'Approve Stock Option Grant to Elon Musk', 'For', vote, 'Management'])
            print(output)
            pyperclip.copy(output)
            input('Press Enter to continue...')
        clear()
    i += 1

print('Doc funds: ' + str(n_doc_funds) + ' (Filing funds:  ' + str(n_filing_funds) + ')')
print('Count of "tesla": ' + str(n_tesla))
