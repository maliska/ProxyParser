from bs4 import BeautifulSoup
import re
import csv
import requests
from time import sleep


# Constants
headers = {"User-Agent": "Mozilla/5.0 (Joel Malissa jmaliska@gmail.com)"}
tags_check = 'issuerName(,cusip)?(,isin)?(,figi)?,meetingDate,voteDescription(,voteCategories)?(,voteCategory)?(,categoryType)?(,otherVoteDescription)?(,voteSource)?,sharesVoted,sharesOnLoan(,vote)?(,voteRecord)?(,howVoted)?(,managementRecommendation)?(,voteManager)?(,otherManagers)?(,otherManager)?(,voteSeries)?(,voteOtherInfo)?'

def get_col(col_in):
    if col_in is None:
        return ''
    else:
        return col_in.get_text(strip=True)

# def get_all_col(vote, col_in):
#     if col_in is None:
#         return ''
#     else:
#         col_in = [tag.get_text(strip=True) for tag in vote.find_all(col_in.name)]
#         print()
#         print(col_in)
#         print()
#         input('Check get_all_col()')
#         return ', '.join(col_in)

with open('in.csv', 'r') as fin:
    with open('out.csv', 'a', newline='') as fout:
        reader = csv.reader(fin)
        writer = csv.writer(fout)
        for i, csv_row in enumerate(reader):
            match i:
                case x if x < 1361:
                    pass
                case 0:
                    result = csv_row + ['fund', 'ticker symbols', 'issuerName', 'voteDescription', 'category', 'otherVoteDescription', 'voteSource', 'sharesVoted', 'sharesOnLoan', 'howVoted', 'sharesVoted', 'managementRecommendation', 'voteSeries', 'voteOtherInfo', 'otherManager']
                    writer.writerow(result)
                case x if x == 667 and csv_row[2].strip() == 'NEOS ETF Trust':
                    pass
                case _:
                    doc_id = csv_row[0]
                    print(doc_id)
                    filing_url = csv_row[5]
                    doc_url = csv_row[6]

                    # Get filing
                    response = requests.get(filing_url, headers=headers)
                    sleep(1)
                    if response.status_code == 200:
                        filing = response.text
                    else:
                        exit(str(doc_id) + ": Failed to retrieve the filing. Status code:", response.status_code)
                    
                    # Parse filing for fund names and tickers if available
                    filing_soup = BeautifulSoup(filing, 'lxml')
                    tables = filing_soup.find_all('table', attrs={'class':'tableSeries'})
                    n_tables = len(tables)
                    if n_tables > 1:
                        exit('Error: Count of filing ticker tables > 1.  (Count = ' + str(n_tables) + ')')
                    elif n_tables == 1:
                        funds = {}
                        table = tables[0]
                        rows = table.find_all('tr')
                        for row in rows:
                            series_col = row.find('td', attrs={'class':'seriesName'})
                            if series_col is not None:
                                series = series_col.get_text(strip=True)
                                series = series.replace('Series', '')
                                funds[series] = ['', []]
                            name_cols = row.find_all('td', attrs={'class':'seriesCell'})
                            if len(name_cols) > 0:
                                for col in name_cols:
                                    if col.get_text(strip=True) != '':
                                        name = col.get_text(strip=True)
                                        funds[series] = [name, []]
                            if 'class' in row.attrs and row['class'][0] == 'contractRow':
                                cols = row.find_all('td')
                                ticker = cols[-1].get_text(strip=True)
                                funds[series][1].append(ticker)

                        # Sort funds
                        funds = dict(sorted(funds.items()))

                        # Sort tickers
                        for fund in funds:
                            funds[fund][1] = ', '.join(sorted(funds[fund][1]))
                    else:
                        series = ''
                        funds = {}
                        funds[series] = ['', '']
                    
                    # Parse document
                    response = requests.get(doc_url, headers=headers)
                    sleep(1)
                    if response.status_code == 200:
                        doc = response.text
                    else:
                        exit(str(doc_id) + ": Failed to retrieve the document. Status code:", response.status_code)
                    
                    doc_soup = BeautifulSoup(doc, 'lxml-xml')  # 'html.parser')
                    n_pvt = len(doc_soup.find_all('proxyVoteTable'))
                    if n_pvt != 1:
                        exit("Count of proxyVoteTable: " + str(n_pvt))
                    
                    xml_table = doc_soup.proxyVoteTable
                    votes = xml_table.find_all('proxyTable')
                    for vote in votes:
                        issuerName = vote.issuerName.get_text(strip=True)
                        # if 'tesla' in issuerName.lower():
                        if 'tesla' in vote.get_text(strip=True).lower():
                            # print(vote)
                            tags = [tag.name for tag in list(vote.find_all()) if tag != '\n']
                            tags = ','.join(list(dict.fromkeys(tags)))
                            if not re.fullmatch(tags_check, tags):
                                print(doc_id)
                                print(vote)
                                print(tags)
                                print(tags_check)
                                exit("Error: tags != expected tags.")
                            voteDescription = get_col(vote.voteDescription)
                            categories = [c.get_text(strip=True) for c in vote.find_all('categoryType')]
                            categories = list(dict.fromkeys(categories))  # De-dupe
                            categories.sort()
                            categories = ', '.join(categories)
                            otherVoteDescription = get_col(vote.otherVoteDescription)
                            voteSource = get_col(vote.voteSource)
                            sharesVoted = get_col(vote.sharesVoted)
                            sharesOnLoan = get_col(vote.sharesOnLoan)
                            voteRecords = vote.find_all('voteRecord')
                            n_records = len(voteRecords)
                            if n_records == 0:
                                howVoted = ['']
                                voteSharesVoted = ['']
                                managementRecommendation = ['']
                            # elif n_records == 1:
                            #     howVoted = [get_col(vote.howVoted)]
                            #     if vote.vote is None:
                            #         voteSharesVoted = ''
                            #     else:
                            #         voteSharesVoted = get_col(vote.vote.sharesVoted)
                            #     managementRecommendation = get_col(vote.managementRecommendation)
                            else:
                                howVoted = []
                                voteSharesVoted = []
                                managementRecommendation = []
                                for record in voteRecords:
                                    howVoted.append(get_col(record.howVoted))
                                    voteSharesVoted.append(get_col(record.sharesVoted))
                                    managementRecommendation.append(get_col(record.managementRecommendation))
                            voteSeries = get_col(vote.voteSeries)
                            voteOtherInfo = get_col(vote.voteOtherInfo)
                            otherManager = vote.otherManager
                            if otherManager is None:
                                otherManager = ''
                            else:
                                otherManager = [om.get_text(strip=True) for om in vote.find_all('otherManager')]
                                otherManager = ', '.join(otherManager)
                            for i in range(max(n_records, 1)):
                                result = csv_row + [funds[series][0], funds[series][1], issuerName, voteDescription, categories, otherVoteDescription, voteSource, sharesVoted, sharesOnLoan, howVoted[i], voteSharesVoted[i], managementRecommendation[i], voteSeries, voteOtherInfo, otherManager]
                                # print('|'.join(result))
                                writer.writerow(result)
                                fout.flush()
                            # sleep(0.5)
