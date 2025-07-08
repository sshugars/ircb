This repo contains the following scripts and data:

* `get_rss.py` : Downloads all data (episodes) from public RSS feed. Saves as `public_feed.json`

* `get_episodes.py` : Parses RSS feed (`public_feed.json`) to create table of episode metadata. Saves as `tables/public_feed_episodes.xlxs`. Includes meta data for list of all (N=513) public episodes.

* `get_comic_timestamps.py` : Parses RSS feed (`public_feed.json`) to create a table of comics with timestamps associated with them. Saves as `tables/public_feed_comics_timestamps.xlsx`. Includes data for N=1139 comics. Filtered with the intention to only capture items a person may be searching (eg, comic names or franchises). 

* `get_comic_bullets.py` : Parses RSS feed (`public_feed.json`) to create a table of all comics named in an episode. Merges in comics with timestamps. Saves as `tables/public_feed_comics_ALL.xlsx`. Includes N=4341 comics.

* `dedup_comics.py` : Checks for within-episode comic duplicates in `tables/public_feed_comics_ALL.xlsx` and creates a file that can be used to manually check duplicates.


More details of each of these files and the data extraction process are included below:

# public_feed_episodes
The RSS feed returns a JSON / dictionary of episode details. All items (episodes, minisodes, etc) are included. Extracted properties and associated fields are as follows. All fields are strings unless noted otherwise.

* **title**: From `episode['title']`
* **subtitle**: From `episode['subtitle']`
* **has_timestamps**: Boolean, indicating whether or not the strings “timestamp”, "timecodes", or “00:00:00" appears in the episode’s `full_summary` (see below). 
* **date**: from `episode['published']`
* **people**: Hosts and guests of a particular episode. Full name when available. Comma-separated string alphabetized by last name when possible. Extracted from `full_summary` (see below) with full names supplemented by data from `episode['authors'][0]['name']`.
* **keywords**: From `details['tags']`. Converted from list to string. Includes commas.
* **simplecast_url**: Link to show audio. From `episode['links'][0]['href']`
* **producer**: Full name of credited Producer, if available. Extracted from `full_summary` (see below).
* **prooflistener**: Full name of credited Prooflistener, if available. Extracted from `full_summary` (see below). 
* **editor**: Full name of credited Editor, if available. Extracted from `full_summary` (see below).
* **episode_number**: Estimated episode number. When possible, taken from `episode['itunes_episode']`. Then, when possible, extracted as numerical entity within `episode['title']`. Note that `itunes_episode` seems to be systematically higher than those listed in episode title. As last effort, estimate episode number as ​​78 - int(i) + 400.  Where `i` is the entry-order of the current episode (newest = 0). This is a poor estimate.
* **full_summary**: For older episodes (Episode 128 and before), this is taken from `episode['summary']`. For newer episodes, from `episode['content'][0]['value']`. Minimal parsing to remove HTML tags and special characters. Line breaks replaced with space (‘ ‘).
*  **show_id**: From episode['id']. If id is a url (older episodes) retrieve only numerical value after ‘?p=’.


Additional notes: 
Names of `people` on episode extracted from `full_summary` using named entity recognition (in Spacy). This was challenging because most summaries include multiple named `PERSON` entities who were not necessarily on the show. This includes creators (sometimes special guests, other times non-guest creators whose work was discussed), as well as named comic entities, e.g. "Wonder Woman" and "Scott Summers" who, as far as I know, have never appeared in person on the show. Basic heuristic for extraction was as follows:

* Scan through `full_summary` sentence by sentence. Searching for named entities. Save entities labeled as `PERSON`.
* If we have already found at least 3 named `PERSON` entities, stop searching later sentences. Guests/hosts were most frequently the first 3 named people in summary.
* If you encounter a named entity that is a `WORK_OF_ART`, `PRODUCT`, or `ORG`, stop searching for additional named entities mid-sentence. Oftentimes (but not always) this indicated a shift to naming creators not necessarily on the show.
* If only a first name is used (typical for show regulars), compare to a dictionary of {first_name: full_name}. Dictionary constructed using the `episode['authors'][0]['name']` field, retaining all names which appeared at least 3 times across episodes. This field was missing data for all older episodes and therefore could not be used to determine who was on the show, but could be used to identify show regulars.

All extracted people entries were then manually reviewed against show description for accuracy.



# public_feed_comic_timestamps
If an episode of the public RSS feed contains a timestamp (has_timestamp=1), full_summary is parsed to extract timestamp and named items. Numerous exceptions included after field list. All fields are strings.
* **episode_title**: Matches entry in public_feed_episodes. Technically not needed in this table, but adds character.
* **show_id**: Matches entry in public_feed_episodes. For joining tables.
* **comic**: Hopefully, the name of a specific comic or franchise. Definitely the text that follows after the timestamp. Numerous items excluded, details below.
* **timestamp**: Text from bullet point starting with a numerical character. Typically of form hh:mm:ss.
* **direct_url**: URL to this specific timestamp in the audio. Created as: ‘{simplecast_url}t={h}h{m}m{s}s’ 

_Identifying “comic” titles_
If a line begins with a timestamp, the text following the timestamp is considered. That text is assumed to not be a comic (eg, is dropped from the table) if it contains any of the following terms. Note that ‘\b’ indicates a word boundary, meaning that only the word itself (not words that contain that word) are dropped.

* last week in comics
* \bstart\b
* wrap
* credits
* picks
* interview with
* chatting with
* ircb
* kickstarters [Note: comics described with the singular ‘kickstarter’ not dropped]
* top of our pile
* top of the pile
* top of your pile
* west michigan weather watch
* \bbreak\b
* podcast
* reading
* warning
* listener 
* been digging

Excluded text (137 entries) was manually inspected to confirm it did not appear to be the title of a comic or comic property. This process resulted in 1323 rows of possible comic names associated with timestamps. Happy to share this full list if that would be helpful.

These were manually inspected to remove additional non-comic entities. Particularly in the older episodes, the text associated with timestamps were frequently not names of comics or comic properties (though I was, for a moment, hopeful that there was a cross-over called Gambit: Broke-ass Batman”). If possible, text descriptions were replaced by the names of specific comics or comic franchises discussed. This resulted in this final list of 1,139 comics mentioned in episodes and affiliated with a timestamp.


Two particular titles of note:
* “CONCENTRATED BOOMER ENERGY: DO NOT READ” was replaced with the comic title “Cancel America #1”. I left this in, but one might be inclined to drop it altogether.
* “Batman Fell In Love With a Ghost Lady” was left as-is. I’m pretty sure this refers to Batman #227 (Dec 1970), but the art from the comic (in which Batman does fall in love with a ghost) doesn’t seem to match the episode art, so I wasn’t sure.

Additional notes: 
* I realized after doing this that the way I parsed the timestamps + text doesn’t work for older episodes:
  * Episodes 128 and earlier use ‘*’ instead of \<li\> bullets
  * Some episodes, possibly just #85, put the text before the timestamp. 
I can re-do the parse to account for this, but the text associated with older episode timestamps is frequently not comic titles, so I’m not sure it's worth doing.


* I left all capitalization as-is. Titles not intended to be in all-caps could be auto-turned into Title Case, but that will mess up titles intended to be in all-caps. May want to look more closely to determine if manual or automated is less trouble

# public_feed_comics_ALL
For each episode of the public RSS, text was parsed to try to identify comic titles. Timestamps were explicitly ignored in this parse, as titles included in public_feed_comic_timestamps were later merged back in. All fields are strings.

* **episode_title**: Matches entry in public_feed_episodes. Technically not needed in this table, but adds character.
* **show_id**: Matches entry in public_feed_episodes. For joining tables.
* **comic**: Text extracted from show summary. Details below.
* **segment**: Text introducing list of (presumed) comic titles. Set to “Timestamps” for all titles merged from  public_feed_comic_timestamps
* **timestamp**: Empty field unless entry merged from  public_feed_comic_timestamps
* **direct_url**:  Empty field unless entry merged from  public_feed_comic_timestamps. Could have include the general episode URL for other titles, but that can be merged in from the episode table if needed

_Extracting comic names from summary_

**Step 1: Identifying episode segments**
Episode summaries typically include multiple bulleted lists. For example, (1) Timestamps, (2) Comics Discussed, and (3) Relevant Links. We consider any text followed by a bulleted list to be a “segment.” 

For the purposes of this list, we want to ignore the “Timestamp” segment (merged in later from public_feed_comic_timestamps) as well as any non-comic segments (eg, “Relevant Links”). To identify relevant segments, first all text appearing in bold (\<strong\>) was extracted from every public episode. Segment names typically, but not always, appear in bold within the episode summaries. These possible segment names were extracted and manually reviewed to identify those relating to comics. This resulted in about 45 unique comic-related segment names across public episodes. Since this wasn’t necessarily a complete list of all comic-related segment names (eg, names that did not appear in bold), this list was used to develop a search string for segment names. Ultimately, a piece of text (whether bold or not) was assumed to be introducing a comic-related segment if it included any of the following terms:

* discussed (Note: resulted in some false positives, these were manually removed)
* comic picks
* comics read
* comic reads
* what we read
* picks for this week
* recommendations (Note: false positives manually removed)
* recommended
* comics mentioned
* manga mentioned
* reading next
* top of our pile
* top of my pile
* top of your pile
* comics we loved
* top comics
* what we read

**Step 2: Extracting comic names**
Once a comic-related segment is identified, the following block of text is parsed for comic names.
Episodes 128 and earlier: script extracts text following a ‘*’ character
Newer episodes: script extracts text in \<li\> tags. Note: if the list includes a sublist, only sub items are included. 

**Step 3: Merging with timestamps**
The table of extracted comic items was then stacked with the cleaned table of comics with timestamps. For rows where the show_id and comic were an exact match, only the last row (from the timestamps table) was retained. Comic names within episodes were then dedupted using `dedup_comics.py`.

Additional notes:
* At least one episode has the mentioned books in the links section. These would be excluded given the process above.
* May make sense to make a list of episodes with no comics listed and then manually review. Many of these are specials/minisodes, but there are probably a few others missed through the above process. 
