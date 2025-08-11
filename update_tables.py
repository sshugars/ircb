import pandas as pd

# custom scripts
import get_rss
import get_episodes
import get_comics


### global variables ###
comic_file = 'tables/public_feed_comics.xlsx'
episode_file = 'tables/public_feed_episodes.xlsx'

def main():

	# load existing data
	episodes = pd.read_excel(episode_file)
	comics = pd.read_excel(comic_file)

	print(f'Found {len(episodes)} episodes in existing table')
	print(f'Found {len(comics)} comics in existing table')


	# download all episodes from RSS feed
	rss = get_rss.update()

	# parse new rss feed as dataframe
	df = get_episodes.initial_parse(rss)


	##### update Episode table

	# identify new episodes
	new_df = df[~df['show_id'].isin(episodes['show_id'])].copy()

	# full parse for new episodes only
	new = get_episodes.update(new_df, episodes)

	updated_episodes = pd.concat([new, episodes])

	# save to file
	updated_episodes.to_excel(episode_file, index=False)

	print(f'{len(new)} episodes added to episode table for {len(updated_episodes)} total episodes')

	###### update Comics table

	# episodes we need to get comics from
	new_rss = dict((i, details) for i, details in rss.items() if int(i) in new.index)
	rows = get_comics.parse_episodes(new_rss, new_df)

	# insert 'Timestamps' as segment 
	# note: rows updated in place
#	__ = [row.insert(3, 'Timestamps') for row in rows]

	# convert to dataframe
	#print(rows[0])
	#print(comics.columns)
	new_comics = pd.DataFrame(rows, columns=comics.columns)

	updated_comics = pd.concat([new_comics, comics])

	# save to file
	updated_comics.to_excel(comic_file, index=False)

	print(f'{len(new_comics)} comics added to comics table for {len(updated_comics)} total comics')

	print('Update complete.')


if __name__ == "__main__":
	main()