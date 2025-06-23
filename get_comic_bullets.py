import json
import re
import pandas as pd
from bs4 import BeautifulSoup


def get_comic_heads():
    heads_list = ['discussed', # some false positives
                  'comic picks',
                  'comics read',
                  'comic reads',
                  'what we read',
                  'picks for this week',
                  'recommendations', # some false positives
                  'recommended', # some false positives
                  'comics mentioned',
                  'manga mentioned',
                  'reading next',
                  'top of our pile',
                  'top of my pile',
                  'top of your pile',
                  'comics we loved',
                  'top comics',
                  'what we read']

    heads = '|'.join(heads_list)
    
    return heads


def parse_episodes(episodes):
    rows = list()
    dropped = list()
    no_bullets = list()
    
    heads = get_comic_heads() # search string for comic headers

    for i, details in episodes.items():

        # meta data for episode
        row = list()
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

        ##### new episodes
        if int(i) < 460:
            summary_raw = details['content'][0]['value']
            soup = BeautifulSoup(summary_raw, features='html.parser')

            # check each paragraph: is this heralding comics?
            for p in soup.find_all('p'):

                # check if this is intro in a list of comics
                check = re.search(heads, p.text.lower())

                if check:
                    try:
                        # check if this is a bulleted list
                        bullets = p.find_next('ul')

                        for b in bullets.find_all('li'):
                            # only keep sub-bullets
                            if len(b.find_all('li')) == 0:
                                this_row = row.copy()
                                this_row.append(b.text) # comic
                                this_row.append(p.text) # segment

                                rows.append(this_row)
                            else:
                                # keep record of what we dropped
                                dropped.append(b)
                    except:
                        no_bullets.append(p)


        ##### older episodes
        if int(i) >= 460:
            summary_raw = details['summary'] # new field who dis
            recs = False # only capture things that are in a "recs" segment

            for line in summary_raw.split('\n'):
                if recs == True and '*' in line.lower():
                    text = line.split('*')

                    for item in text:
                        if item != '':
                            this_row = row.copy()
                            this_row.append(item.strip()) # comic
                            this_row.append('') # show segment

                            rows.append(this_row)

                if 'picks for this week' in line.lower():
                    recs = True
                if 'relevant links/information' in line.lower():
                    recs = False


    print(f'{len(rows)} comics found')
    #print(f'{len(dropped)} items dropped')
    #print(f'{len(no_bullets)} items with header match but no bullets')
    
    return rows


def main():
    # load rss data
    with open('public_feed.json', 'r') as fp:
        episodes = json.loads(fp.read())
    
    print(f'{len(episodes)} episodes pulled from RSS feed')
    
    rows = parse_episodes(episodes)
    
    header = ['episode_title',
              'show_id',
              'comic',
              'segment']
    
    # convert to dataframe
    listed = pd.DataFrame(rows, columns=header)
    listed['timestamp']='' # add timestamp column
    listed['direct_url']='' # add url column
    
    # load comics with timestamps
    print('Merging timestamped comics...')
    timestamps = pd.read_excel('tables/public_feed_comics_timestamps.xlsx')
    timestamps['segment'] = 'Timestamps' # add segment title

    # concatinate dataframes
    merged = pd.concat([listed, timestamps])
          
    
    # drop duplicates, keepting last (timestamp)
    merged = merged.drop_duplicates(subset=['show_id', 'comic'], 
                                    keep='last' # timestamp if we have it
                                    )
          
    print(f'Final count of {len(merged)} comics found')
          
    # save to file
    merged.to_excel('tables/public_feed_comics_ALL.xlsx', #, sep='\t', 
           index=False)
    

    
if __name__ == "__main__":
    main()