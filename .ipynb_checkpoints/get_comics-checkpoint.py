import json
import re
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup

from nltk.metrics.distance import jaro_winkler_similarity

import spacy

##### Global variables
nlp = spacy.load("en_core_web_trf")
old_format_start = datetime(2017, 9, 20).date()
# episodes before Sept 20, 2017 had a different format
# data needs to be extracted differently


def get_comic_heads():
	# text that indicates a list of comics might follow

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




def get_non_comic_tags():
    # search strings for things that are not comic titles
    # compiled by manually inspecting text after timestamps
    noncomic_tags = ['last week in comics',
                     'intro',
                     '\\bstart\\b',
                     'wrap', 
                     'credits', 
                     'picks',
                     'interview with', 
                     'chatting with',
                     'ircb', 
                     'kickstarters', #note: singular okay
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



def get_timestamps(soup, url):
    # extract text after timestamps for a given episode

    timestamps = dict()

    heads = get_comic_heads() # search string for comic headers
    
    # first, look for bulletted lists
    for item in soup.find_all('ul'):

        # only if this list starts with a timestamp
        if item.text[0].isdigit():
            for stamp in item.find_all('li'):
                
                # special cases 
                if url == 'https://ircbpodcast.simplecast.com/episodes/books-dense-enough-for-killing-nEPrn9MT':
                    words = stamp.text.split()
                    time = words[0]
                    text = ' '.join(words[1:])
                    
                    split_stamp = [time, text]
                    
                # All other cases
                else:
                    # make all dashes the same character
                    stamp_text = stamp.text.replace('–', '-')
                    split_stamp = stamp_text.split('-')

                    # check we have enough items
                    if len(split_stamp) < 2:
                        if split_stamp[0] == 'Wrap/Credits': # special case
                            split_stamp = ['01:00:00', 'Wrap/Credits']
                        else:
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

                    # clean goodreads text so just comic name
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
                        
                # save timestamp and label to dictionary
                timestamps[rest] =  {'segment': 'Timestamps',
                                     'timestamp': clean_stamp,
                                     'direct_url':f'{url}?t={timestamp}'}
     
    # if we haven't found timestamps
    if len(timestamps) == 0:

        record = False

        for line in soup.text.split('\n'):
            
            if '00:00:00' in line:
                record = True
                
            check = re.search(heads+'|infinity shred', line.lower())

            if check:
                record = False

            if record:
                # clean fake bullets
                try:
                    if line.strip()[0] == '*':
                        line = line[1:].strip().strip('*').strip()
                except:
                    pass
                
                # make all dashes the same character
                stamp_text = line.replace('–', '-')
                split_stamp = [item.strip() for item in stamp_text.split('-')]

                try:
                    time = [val for val in split_stamp if val[0].isdigit()][0]
                    h,m,s = time.split(':')

                    text = [val for val in split_stamp if not val[0].isdigit()][0]

                    timestamps[text] = {'segment': 'Timestamps',
                                         'timestamp': time,
                                         'direct_url':f'{url}?t={h}h{m}m{s}s'}

                except:
                    pass
                    # print(f'Skipping: {line}, {url}')
                
    return timestamps


def get_bullets(soup):
    # extract text from bulleted list for a given episdoe
    bulletted = dict()
    heads = get_comic_heads() # search string for comic headers

    
    for p in soup.find_all('p'):
        bullets = p.find_next('ul')
        
        try:
            for bullet in bullets.find_all('li'):

                # only keep sub-bullets
                if len(bullet.find_all('li')) == 0:
                    bulletted[bullet.text] = p.text # segment name
        except:
            pass
        
    # if we haven't found bullets yet
    if len(bulletted) == 0:
        segment = ''
        
        for line in soup.text.split('\n'):
            if '*' in line.lower():
                text = line.split('*')

                for item in text:
                    if item != '':
                        text = item.strip() # possible comic
                        bulletted[text] = segment
                        
            elif line != '':
                segment = line.strip()
                
    # only keep items in a 'comic' segment
    comics = dict()
    
    for comic, segment in bulletted.items():
        check = re.search(heads, segment.lower())
        if check:
            comics[comic] = segment
                    
    return comics

def get_ents(summary_raw):
    # get entities (specifically WORK_OF_ART) from a given episode

    art = set()
    
    # cut off credits in searching for entities
    summary_raw = summary_raw[:summary_raw.find('Patreon')]
    
    # adjust nicknames
    summary_raw = summary_raw.replace('Wic+Div', 'The Wicked + The Divine')
    
    # convert to spacy doc
    doc = nlp(summary_raw)
    
    for ent in doc.ents:
        if ent.label_ == 'WORK_OF_ART':
            art.add(ent.text)
    
    return art


def match_segments(comics, art, timestamps, base_url):
    # match items extracted from timestamps, bulleted lists, and named entities
          
    ###### From bullets: Items without a timestamp
    timestamp_keys = dict((seg.lower(), seg) for seg in timestamps.keys()) 

    # check if this segment matches a timestamp
    max_sim = 0
    assign = ''

    matched = dict() # comics matched to timestamps
    for comic, segment in comics.items():
        seg = segment.lower()

        for key in timestamp_keys:
            sim = jaro_winkler_similarity(seg, key)

            if sim > max_sim:
                assign = timestamp_keys[key]
                max_sim = sim

            matched[comic] = assign

    # copy comics and timestamp comics over to final 'all_comics' dict
    all_comics = dict()
    skip = set() # timestamps we don't need any more
        
    for comic, segment in matched.items():
        stamp = timestamps[segment]['timestamp']
        url = timestamps[segment]['direct_url']

        # check if the segment is just the comic name
        sim = jaro_winkler_similarity(comic, segment)

        # if this segment is just the comic name
        if sim > .85:
            skip.add(segment)
            segment = 'Timestamps'
            

        all_comics[comic] = {'segment': segment,
                             'timestamp': stamp,
                             'direct_url': url,
        }
            
    # add timestamps that weren't matched
    non = get_non_comic_tags()

    for label, info in timestamps.items():
        if label not in skip:
            # check if we think this text is a comic
            check = re.search(non, label.lower())

            # only save if text does not match a non-comic string
            if not check:
                all_comics[label] = info  # same details as from timestamps
                

    # check if we need to add any addtional work_of_art
    if art:
        compare = set(all_comics.keys())
        
        for item in art:
            found = False
            
            for alt in compare:
                sim = jaro_winkler_similarity(item.lower(), alt.lower())
                
                # check if we've already found this art in all_comics
                if sim > .8:
                    found = True
                    
            if not found:
                check = re.search(non, item.lower())

                # only save if text does not match a non-comic string
                if not check:
                    all_comics[item] = {'segment': 'Other',
                                        'timestamp': '00:00:00',
                                         'direct_url': base_url
                                       }
                
        
    return all_comics   


def parse_episodes(rss, episodes):
    rows = list()

    for i, details in rss.items():
        # from previously parsed table
        row = episodes.loc[int(i)][['title', 'show_id']].to_list()
        
        # base url, timestamp will be added to this
        url = details['links'][0]['href']
        
        # format changes pre/post old_format_start
        date = datetime.strptime(details['published'], '%a, %d %b %Y %H:%M:%S %z').date()
        
        if date > old_format_start:
            # new
            summary_raw = details['content'][0]['value']
        else:
            # old
            summary_raw = details['summary']
        
        # extract summary as html
        soup = BeautifulSoup(summary_raw, features='html.parser')
        
        #### get timestamped items
        try:
            timestamps = get_timestamps(soup, url)
        except:
            timestamps = dict()
            
        #### get comics from bulletted lists
        try:
            comics = get_bullets(soup)
        except:
            comics = dict()

        # get named entities from title + summary        
        art = get_ents(row[0] + ' ' + summary_raw)

        # merge all sources into one list of comics
        all_comics = match_segments(comics, art, timestamps, url)

        # create unique row for each comic
        for comic, deets in all_comics.items():
            this_row = row.copy()

            this_row.append(comic)

            for k, v in deets.items():
                this_row.append(v)

            rows.append(this_row)

    return rows
   



def main():
    # raw rss data
    with open('public_feed.json', 'r') as fp:
        rss = json.loads(fp.read())
    
    # Table of previously parsed episode data
    episodes = pd.read_excel('tables/public_feed_episodes.xlsx')

    print(f'Extracting comics from {len(rss)} episodes...')

    rows = parse_episodes(rss, episodes)
    # number of rows = number of comics
    print(f'{len(rows)} comics found.')


    # save to dataframe
    header = ['episode_title',
              'show_id',
              'comic', 
              'segment',
              'timestamp',
              'direct_url']

    df = pd.DataFrame(rows, columns=header)

    df.to_excel('tables/public_feed_comics.xlsx', 
               index=False)


if __name__ == "__main__":
  main()

