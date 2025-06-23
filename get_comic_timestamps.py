import json
import re
import pandas as pd
from bs4 import BeautifulSoup

def get_non_comic_tags():
    
    # search strings for things that are not comic titles
    # compiled by manually inspecting text after timestamps
    noncomic_tags = ['last week in comics',  
                     '\\bstart\\b',
                     'wrap', 
                     'credits', 
                     'picks',
                     'interview with', 
                     'chatting with',
                     'ircb', 
                     'kickstarters', #n ote: singular okay
                     'top of our pile', 
                     'top of the pile', 'top of your pile', 
                     'west michigan weather watch',
                     '\\bbreak\\b', 
                     'podcast',
                     'reading', 
                     'warning', 
                     'listener', 
                     'been digging']

    non = '|'.join(noncomic_tags)
    
    return non

def parse_episodes(episodes):
    rows = list()
    dropped = dict() # record non-comic entities
    
    non = get_non_comic_tags() # non-comic search string

    for i, details in episodes.items():
        row = list()
        
        # probably should load episode data, but easy enough to just do it again
        title = details['title']

        if ' | ' in title:
            ep = title.split(' | ')

            # update title field
            title = ep[-1].strip()
            
        show_id = details['id']

        if 'ircb' in show_id:
            show_id = show_id.split('?p=')[-1]

        # initialize row
        row = [title, show_id]
        
        # base url
        url = details['links'][0]['href']

        ##### clean summary text
        summary_raw = details['content'][0]['value']

        # only parse things that have timestamps
        if 'timestamp' in summary_raw.lower() or '00:00:00' in summary_raw:
            soup = BeautifulSoup(summary_raw, features='html.parser')

            # look for bulletted lists
            for item in soup.find_all('ul'):

                # only if this list starts with a timestamp
                if item.text[0].isdigit():
                    for stamp in item.find_all('li'):
                        this_row = row.copy()

                        # make all dashes the same character
                        stamp_text = stamp.text.replace('–', '-')

                        split_stamp = stamp_text.split('-')

                        # check we have enough items
                        if len(split_stamp) < 2:
                            split_stamp = stamp_text.split(':')
                            time = ':'.join([val for val in split_stamp if val.isdigit()])
                            text = ' '.join([val for val in split_stamp if not val.isdigit()])

                            split_stamp = [time, text]

                        clean_stamp = split_stamp[0].strip()

                        if clean_stamp == '':
                            clean_stamp = 'z' # just so there's a character

                        # only if this item is timestamp
                        if clean_stamp[0].isdigit():

                            try:
                                h,m,s = clean_stamp.split(':')
                            except:
                                # some items just have mm:ss
                                m, s = clean_stamp.split(':')
                                h = '00'

                            timestamp = f'{h}h{m}m{s}s'

                            # clean good reads text so just comic name
                            if 'goodreads' in split_stamp[1].lower():
                                rest = '-'.join(split_stamp[2:])
                            else:
                                rest = '-'.join(split_stamp[1:])

                            rest = rest.strip()

                            # special cases
                            if rest == 'Top of Our Pile / The Biggest Volume Ever (One Piece)':
                                rest = 'One Piece'
                            elif rest == 'Crackle: An Interview with Phillip Maira':
                                rest = 'Crackle Vol. 3'
                            elif rest == 'Orcs in Space! An Interview with Francois Vigneault and Michael Tanner':
                                rest = 'Orcs in Space!'
                            elif rest == 'Savage Wizard, Interview with Lesly Julien and Brian Flint':
                                rest = 'Savage Wizard'
                            elif rest == 'The O.Z. - Interview with David Pepose':
                                rest = 'The O.Z. #1-2'
                            elif rest == '“Everyone Is Tulip” Interview with Dave Baker and Nicole Goux':
                                rest = 'Everyone Is Tulip'
                            elif rest == 'Interview with David Pepose, writer for Spencer and Locke':
                                rest = 'Spencer and Locke'

                            # check if we think this text is a comic
                            check = re.search(non, rest.lower())

                            # if text matches a non-comic string
                            if check:
                                # save text and timestamped url for manual review
                                dropped[rest] = f'{url}?t={timestamp}'

                            else:
                                # save comic
                                this_row.append(rest)
                                this_row.append(clean_stamp)
                                this_row.append(f'{url}?t={timestamp}')

                                rows.append(this_row)

    print(f'{len(rows)} comics found')
    return rows, dropped
    

def main():
    # load rss data
    with open('public_feed.json', 'r') as fp:
        episodes = json.loads(fp.read())
    
    print(f'{len(episodes)} episodes pulled from RSS feed')
    
    # extract data
    rows, dropped = parse_episodes(episodes)
    
    # note: not doing anything with dropped here
    # but could save/print for manual inspection
    
    header = ['episode_title',
              'show_id',
              'comic', 
              'timestamp',
              'direct_url']
    
    # convert to dataframe and save to file
    df = pd.DataFrame(rows, columns=header)
    
    df.to_excel('tables/public_feed_comics_timestamps.xlsx', #, sep='\t', 
           index=False)
    
    print('All data written to file')
    
    # exported data then manually inspected to remove additional non-comic entities
    
    
if __name__ == "__main__":
    main()