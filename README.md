This repo contains the following scripts and data:

* `get_rss.py` : Downloads all data (episodes) from public RSS feed. Saves as `public_feed.json`

* `get_episodes.py` : Parses RSS feed (`public_feed.json`) to create table of episode metadata. Saves as `tables/public_feed_episodes.xlxs`. Includes metadata for all public episodes.

* `get_comics.py` : Parses RSS feed (`public_feed.json`) and episode data (`tables/public_feed_episodes.xlxs`) to create a table of comics mentioned in episodes. Comics are identified through timestamps, bullets, and named entity recogninition.  Saves as `tables/public_feed_comics.xlsx`. Manually filtered with the intention to only capture items a person may be searching (eg, comic names or franchises). 

* `update_tables.py` : Collects current RSS feed and updates `tables/public_feed_episodes.xlxs` and `tables/public_feed_comics.xlsx` to include data from any new episodes.

More details of each of these files and the data extraction process are included below:

# get_episodes.py -> public_feed_episodes.xlsx
The RSS feed returns a JSON / dictionary of episode details. All items (episodes, minisodes, etc) are included. Extracted properties and associated fields are as follows. All fields are strings unless noted otherwise.

Fields:
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



# get_comics.py -> public_feed_comics.xlsx
For each episode, (1) timestamps, (2) items in bulletted lists, and (3) named entities that are a `WORK_OF_ART`, are extracted from the episode description. These items are then merged together and given a timestamp assignment. Items with segment name `Timestamp` have a timestamp directly listed in the episode descriptions. All other timestamps are best guesses as to when a comic was discussed. If no match to a timestamp is possible, segment is labeled "Other" and given timestamp of 00:00:00. Minisodes, which typically don't have timestamps are denoted as such all comics are similarly assigned the timestamp of 00:00:00.

Fields:
* **episode_title**: Taken from entry in `public_feed_episodes.xlsx`. Technically not needed in this table, but adds character.
* **show_id**: Taken from entry in `public_feed_episodes.xlsx`. For joining tables.
* **comic**: Hopefully, the name of a specific comic or franchise. Definitely a string extracted from the show description. Details below.
* **segment**: The segment in which the comic was (presumably) discussed. Segment name `Timestamp` indicates this comic was listed as its own segment/timestamped item. 
* **timestamp**: Text form of timestamp in form hh:mm:ss. This is the timestamp associated with the given segment. If segment is `Other` or `Minisode`, timestamp is set to `00:00:00`.
* **direct_url**: URL to this specific timestamp in the audio. Created as: ‘{simplecast_url}t={h}h{m}m{s}s’ 

Comic extraction is done in three steps:
(1) Get timestamps from episode
(2) Get items in bulleted list from "comic" headers
(3) Extract named entities which are identified as a `WORK_OF_ART`

These items are then merged together to create a single comic list for each episode.

_Extracting text associated with timestamps_
First we go through the text to create a dictionary indicating the timestamp associated with pieces of text. The `segment` is considered to be the text associated with a timestamp within the episode description. At this stage, we retain all text/segment names whether we think it indicates a comic or not. In the merging stage, we will drop any items that do not appear to be comics.

_Extracting comics from bulleted lists_
Next, we extract all items from bulleted lists. The `segment` is considered to be the text that immediately precedes the bulleted list. We only keep items where the segment name suggests that this might be a list of comics.


Specifically, items in bulleted lists were retained if their `segment` included any of the following terms:

* discussed 
* comic picks
* comics read
* comic reads
* what we read
* picks for this week
* recommendations 
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

This list of terms was determined through a manual process in which all text appearing in bold (\<strong\>) was extracted from every episode description. Segment names typically, but not always, appear in bold within the episode summaries. These possible segment names were manually reviewed to identify those relating to comics. This resulted in about 45 unique comic-related segment names across public episodes. Since this wasn’t necessarily a complete list of all comic-related segment names (eg, names that did not appear in bold), this list was used to develop the above search string for segment names. 

_Extracting Named Entities_
Finally, Spacy was used to identify all named entities in the episode description identified as a `WORK_OF_ART`. Episode text cut off the "credits" to avoid identifying named entities in that portion of the text.


_Merging comic sources_
Finally, these three sources of comic names were merged together. First, the `segments` associated with bulleted lists of comics in the episode description were matched to segments named in the timestamps of the episode. For example, if a bulleted list was preceded with the text "Top of Our Pile" this segment might be matched to a timestamped segment named "Top of the Pile". Comics were always matched to the timestamp segment with the closest semantic similarity. This means that text did not need to be an exact match and that all comics were matched to some timestamped item.

Next, the name of a comic from a bullet was compared to the name of its segment. If these had high semantic similarity, it suggests the "segment" was actually just the name of the comic and that comic was given its own timestamp. In this case, the segment name was updated to "Timestamps" and the comic name as it appeared in the bulleted list was retained. 

In the next phase, we add items extracted by timestamp. Any timestamp item that was already added to our list of comics through the above process was skipped. Here, we recognize that we may encounter text associated with a timestamp that does not represent a comic. We therefore drop any timestamped "segments" that contain any of the following terms. Note that ‘\b’ indicates a word boundary, meaning that only the word itself (not words that contain that word) are dropped.

* last week in comics
* intro
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

Finally, we check if any `WORK_OF_ART` has high semantic similarity with a comic we have already identified. If not, that means this work is not yet in the list for this episode. We add it with the segment name "Other" and Timestamp 00:00:00. This primarily serves to identify comics in the episode title (eg, especially for minisodes and bonus episodes) as well as Kickstarters and other works promoted in the episode but not given an official timestamp.

_Comic data cleaning_
The resulting table of comics was then manually inspected and cross-checked against the episode description to ensure that items were indeed comics or related franchises/properties, as well as to check the timestamp associated with the item. Note that in many earlier episodes, "Comic Reads/Picks for this week" were included in a single bulleted list. Therefore, these items were assigned the segment "Start/Last Week in Comics" and given the timestamp 00:00:00, even though the comics were discussed over different timestamps.


Additional notes: 
* I left all capitalization as-is. Titles not intended to be in all-caps could be auto-turned into Title Case, but that will mess up titles intended to be in all-caps. May want to look more closely to determine if manual or automated is less trouble

