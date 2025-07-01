import itertools as it
import pandas as pd
import numpy as np

import re
from nltk.metrics.distance import jaro_winkler_similarity


def main():

	# load comics data
	comics = pd.read_excel('tables/public_feed_comics_ALL.xlsx')
	print(f'{len(comics)} comics loaded')

	# add column with lowercase version of comic string
	comics['doc'] = [comic.lower() for comic in comics['comic'].fillna('')]

	# get list of show ids
	eps = set(comics['show_id'])
	print(f'{len(eps)} unique episodes')

	# identify titles that may need to be checked
	check = set()

	for ep in eps:
	    sub = comics[comics['show_id']==ep]
	    
	    for e1, e2 in it.combinations(sub['doc'], 2):
	        sim = jaro_winkler_similarity(e1, e2)
	        
	        # threshod determined by manual evaluation
	        if sim > .86:
	            check.add(e1)
	            check.add(e2)
	            #print(e1, '|', e2, sim)


    # add a column indicating if a comic has a name to be checked
    # throws a warning but not relevant to our use case
	comics['check'] = comics['doc'].str.contains('|'.join(check))

	# save to file
	comics.to_excel('tables/CHECK_public_feed_comics_ALL.xlsx')

	print(f'Comics written to file, with flag for checking possible duplicates.')


if __name__ == "__main__":
    main()