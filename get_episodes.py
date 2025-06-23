import json
import re
import pandas as pd
from bs4 import BeautifulSoup

def parse_episodes(episodes):
    # extract data from each episode
    # save as list of row data
    
    rows = list()

    for i, details in episodes.items():
        row = list()

        #### easy meta data
        title = details['title']
        subtitle = details['subtitle']
        url = details['links'][0]['href']
        date = details['published']
        authors = details['authors'][0]['name']
        
        # show id
        show_id = details['id']

        # if the show_id is a url, just keep the number
        if 'ircb' in show_id:
            show_id = show_id.split('?p=')[-1]

        # create single str from keyword list
        try:
            terms = [item['term'] for item in details['tags']]
            keywords = ', '.join(terms)
        except:
            keywords = ''


        ##### clean summary text
        summary_raw = details['content'][0]['value'] 

        # if we have paragraph structure, clean each paragraph
        if '<p>' in summary_raw:
            summary = ''
            soup = BeautifulSoup(summary_raw, features='html.parser')

            # remove weird space characters that pop up sometimes
            for item in soup.find_all('p'):
                raw = item.get_text(separator=' ')
                words = [re.sub(r'\s', ' ', word) for word in raw.split()]
                
                # replace line breaks, etc with just a space
                text = ' '.join(words)

                summary += text + ' '

            summary = summary.strip() # strip excess whitespace as needed

        # if we don't have html, just clean everything at once
        else:
            raw = summary_raw

            words = [re.sub(r'\s', ' ', word) for word in raw.split()]
            summary = ' '.join(words)

        ### determine if episode has timestamps 
        if 'timestamp' in summary.lower() or '00:00:00' in summary_raw:
            has_timestamps = 1
        else:
            has_timestamps = 0

        #### try to get episode number
        episode_num = 'Unknown'

        try:
            episode_num = details['itunes_episode']
        except:
            pass

        if ' | ' in title:
            ep = title.split(' | ')

            # extract number from first half
            for word in ep[0].split():
                if word.isdigit():
                    episode_num = int(word)

            # update title field
            title = ep[-1].strip()

        else:
            # if all else fails, estimate a value
            episode_num = 78 - int(i) + 400

        # create row of data for this episode
        row = [title, subtitle, has_timestamps,
               date, 
               authors, keywords, url,
               episode_num, 
               summary, show_id]

        rows.append(row)
        
    return rows
    
    

def main():
    # load rss data
    with open('public_feed.json', 'r') as fp:
        episodes = json.loads(fp.read())
    
    print(f'{len(episodes)} episodes pulled from RSS feed')
    
    # extract data
    rows = parse_episodes(episodes)
    
    # table header
    header = ['title',
              'subtitle',
              'has_timestamps',
              'date', 
              'authors',
              'keywords',
              'simplecast_url', 
              'episode_number', 
              'full_summary', 
              'show_id']
    
    # turn to dataframe
    df = pd.DataFrame(rows, columns=header)
    
    # save data
    # save to excel because otherwise excel gets snipy about character encoding
    df.to_excel('tables/public_feed_episodes.xlsx', 
           index=False)
    
    print(f'Data from {len(df)} episodes extracted and saved to file')
    
    
if __name__ == "__main__":
    main()