# Trie Service Package
from daTrie import DaTrie
from trie_utility import TrieUtility


from ranking_search_result import FrequencySearchRanking
from ranking_search_result import EquivalenceSimilaritySearchRanking
from ranking_search_result import CombineFrequencyAndEquivalencRanking

import os

TRIE_PATH = '/media/sunil/Others/project_marshall/college_cache/'
if not os.path.exists(TRIE_PATH):
    os.makedirs(TRIE_PATH)
COLLEGE_INFO_PATH = '/media/sunil/Others/project_marshall/usa_universities.txt'

def memoize(f):
    """ Memoization decorator for functions taking one or more arguments. """
    class memodict(dict):
        def __init__(self, f):
            self.f = f
        def __call__(self, *args):
            return self[args]
        def __missing__(self, key):
            ret = self[key] = self.f(*key)
            return ret
    return memodict(f)

@memoize
def get_college_information(college_info_path):
    college_id_name_map = dict()
    with open(college_info_path, 'r') as fp:
        for line in fp.readlines():
            line_split = line.split("|")
            college_id_name_map[str(line_split[0]).upper()] = str(line_split[1]).upper()
    return college_id_name_map


@DaTrie.cache_datrie_to_file(TRIE_PATH)
def get_college_detail_address_trie():
    """
        Service which gets a datab data with the single key column
        whose key will be the leaf node of the trie & the rest of the data is used to create a trie
        along with the key column

        The datrie cannot be serialized with cPickel and hence it requires customized serialization
        The trie to serialization will do the following
            - If the trie is not available in cache, tries to serialize the trie and write it to the appropriate path
                The file name will be the function name
            - If the trie is available in the cache, then deserialize the trie from the appropriate path where it
                was earlier serialized
    """
    print 'Reading the college information text file'
    college_info_dict = get_college_information(COLLEGE_INFO_PATH)
    trie_util = TrieUtility()
    datrie_obj = DaTrie()
    trie = trie_util.create_trie_from_dict(datrie_obj, college_info_dict)

    print 'Owned Deal Trie: Completed, Trie is ready to use'
    return trie


@memoize
def get_college_detail_trie():
    """
        Function to memorize the trie creation/fetch that was earlier executed
    """

    return get_college_detail_address_trie()


def get_college_details_top_search_results(leaf_node_key_list):
    """
        Service which returns a datab data for only the search result keys for futher ranking of the algorithm.
        Here Key will be the leaf node of the trie.

        Then create a datab same as that of datab used for creating trie
    """
    college_info_dict = get_college_information(COLLEGE_INFO_PATH)
    required_college_info = dict()
    college_ids = set()
    for val in leaf_node_key_list:
        college_ids.add(val)
        required_college_info[val] = college_info_dict[val]
    return required_college_info


def get_college_names(search_words):
    """
        Step 0: Load trie from cached data
        Step 1: Search in trie, get matching keys list (for each word, list of keys)
        Step 2: Frequency Match, get matching keys with ranking (for search strin,)
        Step 3: Fetch data corresponding to the keys from the Frequency match 
        Step 4: Equivalence  & Similarity Ranking, get matching keys with rank (keys from step2, data from step 3)
        Step 5: Combine both the frequency Match & Equivalence search algo (Input : Frequency search result,
        equivalence search result)
        Output: get matching keys with ranking

        For the searched trie results, the algorithm helps in providing the most appropriate results
            - Frequency Search
            - Equivalent & Similarity Search alogrithm
            - Combine both the results and provides the best probable match

        Please look at each function for more details for each implemented algorithm
    """

    # Fetch the trie object from redis & memorized data

    trie = get_college_detail_trie()

    # Call the factory class & set the trie object to the respective trie class ie, datrie or pytrie

    trie_obj = DaTrie()
    trie_obj.trie = trie

    # Search for the word in the trie using the trie utility

    trie_util = TrieUtility()
    search_trie_results = trie_util.search_from_trie(trie_obj, search_words)

    #
    # Call the ranking alogrithm as per your requirement
    #
    # Ranking Algorithm
    #   1. Frequency Search Ranking Algorithm
    #

    frq_obj = FrequencySearchRanking(search_trie_results)
    frequency_search_result = frq_obj.frequency_search_results()
    
    #
    # Ranking Algorithm
    #    2. Equivalence & Similarity Search Ranking Algorithm
    #       Since equivalence is time consuming process we use the frequency ranking as base
    #       and consider top 100 properties for equivalence search
    #

    frequency_search_key = frequency_search_result.keys()
    top_frq_dict = \
        get_college_details_top_search_results(frequency_search_key)
    eql_obj = EquivalenceSimilaritySearchRanking(search_words)
    
    equivalence_search_result = \
        eql_obj.equivalence_and_similarity_search_result(top_frq_dict)

    #
    # Ranking Algorithm
    #    2. Combine both Frequency Search and Equivalence Similarity Search Ranking Algorithm
    #       This is done to give equal weightage to both the results
    #

    
    cmb_frq_eql = \
        CombineFrequencyAndEquivalencRanking(frequency_search_result, equivalence_search_result)
    ranked_result = \
        cmb_frq_eql.combine_frequency_and_equivalence_search_result()
    
    # Fetch the ranked result from the datab in the same order

    return (top_frq_dict, ranked_result)

def possible_college_search(college_name, possible_college_rank):
    college_name = unicode(college_name, 'utf-8')

    (college_dict, ranked_college_result) = get_college_names(college_name.upper())
    for college_id, rank in ranked_college_result.items():
        if rank < 0.5:
            break
        possible_college_rank.append([college_dict[college_id], rank])
    return possible_college_rank
