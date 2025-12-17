import json
import re
import pandas as pd
from bs4 import BeautifulSoup


#### set up text matching
import spacy
from spacy.matcher import Matcher
from spacy.language import Language
from spacy.tokens.span import Span

nlp = spacy.load('en_core_web_trf')
matcher = Matcher(nlp.vocab)

@Language.component('no_possesive')
def no_possesive(doc):
    doc.ents = _no_possesive_generator(doc)
    return doc

def _no_possesive_generator(doc):
    """Yields non possessive versions of the given document's entities."""
    for ent in doc.ents:
        if ent.text.endswith("'s") or ent.text.endswith("’s"):  # Jean Grey's
            yield Span(doc, ent.start, ent.end-2, label=ent.label)
        elif ent.text.endswith("s'") or ent.text.endswith("’s"): # Cyclops'
            yield Span(doc, ent.start, ent.end-1, label=ent.label)
        else:
            yield ent
            
nlp.add_pipe('no_possesive')

def init_matcher():
    # for credits
    matcher.add("Executive Producer", [[{"LOWER": 'executive'},
                                        {"LOWER": 'producer'}]
                            ])

    matcher.add("Producer", [[{"LOWER": 'producer'}],
                             [{"LOWER": 'produced'}]
                            ])
    matcher.add("Prooflistener", [[{"LOWER": 'prooflistener'}]])
    matcher.add("Editor", [[{"LOWER": 'editor'}],
                           [{"LOWER": 'edited'}]
                          ])
    
    return


def parse_episodes(rss):
    ''' 
    Inital parse

    Extract data from each episode. Save as list of row data for dataframe

    Input: JSON of RSS feedt
    Output: list of rows
    '''

    
    rows = list()

    for i, details in rss.items():
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

        ## new episodes
        if int(i) < 460:
            summary_raw = details['content'][0]['value']
            
        # older episodes    
        elif int(i) >= 460:
            summary_raw = details['summary']

        # if we have html, clean each paragraph
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
        if 'timestamp' in summary.lower() or 'timecodes' in summary.lower() or '00:00:00' in summary_raw:
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

def initial_parse(rss):
    # extract data
    rows = parse_episodes(rss)
    
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
    
    print(f'Initial parse completed.')

    return df

#### Functions for extracting names from summary
def get_count(df, col):
    
    # count times name appears in col
    counts = dict()

    for i, name_list in df[col].items():
        for n in name_list.split(','):
            name = n.strip()

            counts.setdefault(name, 0)
            counts[name] += 1
            
    return counts


def get_people(x, full):
    '''
    Extract host names from summary
    '''
    
    # people who appeared in this episode
    people = set()
    
    searching = True
    
    for sent in x.sents:            
        if len(people) >= 3:
            # if we've already found 3 guests, we don't need to keep looking
            searching = False
            
        # special case of first sentence with non-guest name
        if 'donate in support of the protests calling for racial justice' not in sent.text:

            # search entities in this sentence
            for ent in sent.ents:
                if searching:

                    # if we have people and encounter a creative work, stop searching for names
                    if len(people) > 0 and ent.label_ in ['WORK_OF_ART', 'PRODUCT', 'ORG']:
                        searching = False
                        break

                    # Assume entities tagged PERSON are, in fact, people
                    is_person = True
                    
                    if ent.label_ == 'PERSON':
                        name = ent.text
                        names = name.split()

                        # if we only have one name, try to get full
                        if len(names)==1:
                            try:
                                name = full[names[0]]

                            # if not in our dictionary, don't need to keep
                            except:
                                is_person = False

                        if is_person:
                            people.add(name)
                            
                            
    # sort found people by last name
    people_dict = dict((name.split()[-1], name) for name in people)
    people_sorted = [name for l,name in sorted(people_dict.items())]

    return ', '.join(people_sorted)


def get_crew(x):
    crew = dict()
    
    # look for matches
    matches = matcher(x)
    
    # save spans for each match
    spans = dict()

    for match_id, start, end in matches:
        role = nlp.vocab.strings[match_id] # title of pattern
        found = True

        # only keep 'producer' span if not exec producer
        if role == 'Producer':
            if 'Executive Producer' in spans.keys():
                ep_end = spans['Executive Producer'][1]

                if end <= ep_end:
                    found = False

        if found:
            spans[role] = [start, end]
    
    # ensure spans are in order of text
    spans = dict(sorted(spans.items(), key=lambda item: item[1]))
    
    # search for names between role spans
    search = dict()
    old_role = ''

    for role, (start, end) in spans.items():

        # search for the name in this role after role span ends
        search.setdefault(role, list())
        search[role].append(end)

        # if we have an old role, end the last search
        if old_role != '':
            search[old_role].append(start)

        # save old_rold
        old_role = role
        
    # extract names
    for role, span in search.items():
        crew.setdefault(role, list())
        
        if len(span) < 2:
            span.append(-1) # end of string

        for ent in x[span[0]:span[1]].ents:
            if ent.label_=='PERSON':
                crew[role].append(ent.text)        
        
    return crew


def merge_producers(ep, prod):
    producers = list()

    for e, p, in zip(ep, prod):
        if e != '':
            item = f'Executive Producer: {e}, Producer(s): {p}'
        else:
            item = p

        producers.append(item)
        
    return producers

def parse_crew(df):
    df['crew'] = df['doc'].apply(lambda x: get_crew(x))
    
    # get producer lists
    ep = df['crew'].apply(lambda x: ', '.join(x['Executive Producer']) if 'Executive Producer' in x.keys() else '')
    prod = df['crew'].apply(lambda x: ', '.join(x['Producer']) if 'Producer' in x.keys() else '')
    
    # merge producer lists
    df['producer'] = merge_producers(ep, prod)
    
    df['editor'] = df['crew'].apply(lambda x: ', '.join(x['Editor']) if 'Editor' in x.keys() else '')
    df['prooflistener'] = df['crew'].apply(lambda x: ', '.join(x['Prooflistener']) if 'Prooflistener' in x.keys() else '')
    
    # updates dataframe in place, do not need to return anything
    return 
    
def get_names(episodes):
    counts = get_count(episodes, 'people')
    
    # create dict of first_name : full_name
    full = dict()

    for name_list in episodes['people']:
        for n in name_list.split(','):
            name = n.strip()
            
            if counts[name] > 2:
                names = name.split()
                full[names[0]] = name
                
    return full

    
def update(new, old):
    full = get_names(old)
    
    # for parsing a df of new episodes
    new['doc'] = [nlp(doc) for doc in new['full_summary']]
    
    # inialize matching search
    init_matcher()

    # extract people and crew roles from text
    new['people'] = new['doc'].apply(lambda x: get_people(x, full))
    new['crew'] = new['doc'].apply(lambda x: get_crew(x))
    parse_crew(new)

    return new[old.columns]
    

def main():
    # load rss data
    with open('public_feed.json', 'r') as fp:
        rss = json.loads(fp.read())
    
    print(f'{len(rss)} episodes pulled from RSS feed')
    
    # inital parse of data
    episodes = initial_parse(rss)

    # Get names of regulars
    counts = get_count(episodes, 'authors')

    # create dict of first_name : full_name
    full = dict()

    for name_list in episodes['authors']:
        for n in name_list.split(','):
            name = n.strip()
            
            if counts[name] > 2:
                names = name.split()

                full[names[0]] = name
            
    # Rene Rodriguez --> René Rodriguez
    full['Rene'] = 'René Rodriguez'

    # inialize matching search
    init_matcher()

    # convert raw text to spacy object
    print('Creating Spacy documents')
    episodes['doc'] = [nlp(doc) for doc in episodes['full_summary']]

    # extract people and crew roles from text
    episodes['people'] = episodes['doc'].apply(lambda x: get_people(x, full))
    episodes['crew'] = episodes['doc'].apply(lambda x: get_crew(x))
    parse_crew(episodes)

    #### missing people
    # some older episodes name people in subtitle, not in summary
    sub = episodes[episodes['people']==''].copy()

    sub['doc'] = [nlp(doc) for doc in sub['subtitle']]
    sub['people'] = sub['doc'].apply(lambda x: get_people(x, full))

    # get crew 
    parse_crew(sub)


    # replace episode values with sub values
    for i, row in sub.iterrows():
        episodes.loc[i, 'people'] = row['people']
        episodes.loc[i, 'producer'] = row['producer']
        episodes.loc[i, 'editor'] = row['editor']
        episodes.loc[i, 'prooflistener'] = row['prooflistener']

    # fix typo
    for i in np.where(episodes['producer']=='Mike RapinEditor, Zander Riggs')[0]:
        episodes.loc[i, 'producer'] = 'Mike Rapin'
        episodes.loc[i, 'editor'] = 'Zander Riggs'
      

    # save to file for manual review
    cols = ['title', 'subtitle', 'has_timestamps', 'date', 'people', 'keywords',
            'simplecast_url', 'producer', 'prooflistener', 'editor', 
            'episode_number', 'full_summary', 'show_id']

    episodes = episodes[cols]


    # save to excel because otherwise excel gets snipy about character encoding
    episodes .to_excel('tables/public_feed_episodes.xlsx', 
           index=False)
    
    print(f'Data from {len(episodes)} episodes extracted and saved to file')

    
    
if __name__ == "__main__":
    main()