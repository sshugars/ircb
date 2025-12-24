import feedparser
import json

def update():
    # download new data
    main()
    
    # load new data
    with open('public_feed.json', 'r') as fp:
        rss = json.loads(fp.read())
        
    return rss

def main():
    
    # retrieve data from RSS feed
    rss_url = 'https://feeds.simplecast.com/U93zjuSN'
    feed = feedparser.parse(rss_url)
    
    # save entries as dictionary
    entries = dict()
    
    if feed.status == 200:
        for i, entry in enumerate(feed.entries):
            # 0 is newest episode
            entries[i] = entry

    else:
        print("Failed to get RSS feed. Status code:", feed.status)

    print(f'{len(entries)} episodes found')

    with open('public_feed.json', 'w') as fp:
        fp.write(json.dumps(entries))
    
    print('RSS data written to file.')
    
    
if __name__ == "__main__":
    main()