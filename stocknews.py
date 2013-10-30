"""
Fetch news related to stocks.

At the moment Google Finance is the only source supported, but also tweets will
be supported soon. And maybe more sources will be suported in the future.

Feel free to fork the code on github.com/elgehelge/stocknews and add the
sources you need!

Arguments:
short_name    -- (string) the short name of the stock (e.g. 'GOOG')
start_date    -- (string formatted as %Y-%m-%d) the start date
                 - articles published on this date will be included
end_date      -- (string formatted as %Y-%m-%d) the end date
                 - articles published on this date will NOT be included
order_by_date -- (boolean) whether to sort the articles by date or by relevance
                 - the default value is False

Example of how to get the most relevant Google Finance articles
related to the LinkedIn stock (LNKD) between the 15th of august and the 15th of
september 2013:

>>> articles = get_google_finance_articles('LNKD', '2013-09-15', '2013-10-15')
>>> len(articles)
68
>>> most_relevant_article = articles[0]
>>> least_relevant_article = articles[-1]
>>> most_relevant_article['relevance']
1
>>> least_relevant_article['relevance']
68
>>> most_relevant_article['title']
u'LinkedIn Customers Allege Company Hacked E-Mail Addresses'

>>> most_relevant_article['link']
u'http://www.bloomberg.com/news/2013-09-20/linkedin-customers-say-company-
hacked-their-e-mail-address-books.html'

>>> most_relevant_article['content'][:200] + '...'
u'\n\n\nLinkedIn Corp. (LNKD), owner of the\nworld\u2019s most popular
professional-networking website, was sued\nby customers who claim the company
appropriated their identities\nfor marketing purposes by hacking...'

>>> most_relevant_article['wordcounts'].most_common()[:10]
[(u',', 67), (u'.', 46), (u'linkedin', 31), (u'e-m', 24), (u'ail', 24),
(u'said', 19), (u'address', 10), (u'account', 9), (u'compani', 9),
(u'complaint', 8)]

Example of how to get the earliest and the latest Google Finance article
related to the same stock and within the same time frame as above:

>>> articles = get_google_finance_articles('LNKD', '2013-09-15', '2013-10-15',
...                                        order_by_date=True)
>>> len(articles)
68
>>> earliest_article = articles[0]
>>> latest_article = articles[-1]
>>> import time
>>> time.strftime("%d %b %Y %H:%M:%S", earliest_article['datetime'])
'03 Sep 2013 12:13:00'
>>> time.strftime("%d %b %Y %H:%M:%S", latest_article['datetime'])
'14 Sep 2013 21:08:17'

"""

__version__ = 1.1
# Latest update:
# - Better tokentizing
# - Catching IncompleteRead exception
# - Timeouting url request after 10 seconds
# - Not printing while running in parallel (caused an error sometimes)

from threading import Thread
from collections import Counter
from operator import itemgetter
import urllib
import urllib2
import re
from socket import timeout
from httplib import IncompleteRead

import feedparser
import nltk
import bs4

USER_AGENT = 'StockNewsCrawler/%s' % __version__ + \
             'Source code available on github.com/elgehelge/stocknews'

def get_google_finance_articles(
                                short_name,
                                start_date,
                                end_date,
                                order_by_date=False,
                               ):
    """
    Return a sorted list of dictionaries representing articles.
    
    Each dictionary represents an article and has the following keys:
    - 'datetime'
    - 'title'
    - 'wordcounts'
    - 'link'
    - 'relevance'
    - 'content'
    - 'raw_html'
    
    By default the list is sorted according to relevance (defined by Google
    Finance), but can be sorted by date if preferred.
    
    """
    # Initializing variables
    article_list = []

    # Fetch feed and store 'datetime', 'title', 'link' and 'relevance'
    feed_items = _get_google_finance_feed(short_name, start_date, end_date)
    for index, item in enumerate(feed_items):
        article = {}
        article['datetime'] = item['published_parsed']
        article['title'] = item['title']    
        article['link'] = item['link']
        article['relevance'] = index + 1
        article_list.append(article)
    
    # Fetch articles in parallel
    number_of_articles = len(article_list)
    print "Fetching %i articles online..." % number_of_articles
    opener = urllib2.build_opener()
    opener.addheaders = [("User-agent", USER_AGENT)]
    def fetch_online(article):
        """
        Fetch online content.
        
        Request the url for an article dictionary (article['link']) and store
        the content within this dictionary (article['content']).
        
        """
        try:
            raw_html = opener.open(article['link'], timeout = 10).read()
        except (urllib2.URLError, timeout, IncompleteRead):
            article_list.remove(article)
        else:
            article['raw_html'] = raw_html  
            article['content'] = _get_website_content(raw_html)
    threads = [Thread(target=fetch_online, args = (article,))
               for article in article_list] # takes tuple as args
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    print "%i Articles fetched, %i failed." % (len(article_list),
                                               number_of_articles -
                                               len(article_list))
        
    # Count words and store 'wordcounts' in dictionary
    for article in article_list:
        # Concatenate titles and content
        text = article['title'].encode('utf8') + article['content'].encode('utf8')
        # Normalize (tokenize, lowercase, stem, remove stopwords)
        word_list = _word_normalization(text)
        # Count words
        article['wordcounts'] = Counter(word_list)

    # Order by date instead of relavance if requested
    if order_by_date:
        article_list = sorted(article_list, key=itemgetter('datetime'))
    
    return article_list


#def get_tweets(short_name, start_date, end_date):
#    # TODO: Implement this
#    """
#    Returns a sorted list of dictionaries with keys:
#    - 'datetime'
#    - 'content'
#    - 'wordcounts'
#    - 'retweets'
#    - 'user_id'
#    - 'user_followers'
#    """


    # PRIVATE METHODS
    # ---------------


def _get_google_finance_feed(short_name, start_date, end_date):
    """Return a list of feedparser items sorted by relevance."""
    
    # Setup URL parameters
    args = {}
    args['q'] = short_name
    args['output'] = 'rss'
    args['startdate'] = start_date
    args['enddate'] = end_date
    args['start'] = 0 # pagination (start from item number <'start'> ...)
    args['num'] = 100 # pagination (... and show the next <'num'> items.)

    # Initialize variables
    reached_end_of_feed = False
    all_feed_items = []

    # Fetch feed items until end of feed
    feedparser.USER_AGENT = USER_AGENT
    while not reached_end_of_feed:
        feed_url = 'https://www.google.com/finance/company_news?' \
                   + urllib.urlencode(args)
        feed = feedparser.parse(feed_url)
        all_feed_items += feed['items']
        reached_end_of_feed = len(feed['items']) != args['num']
        # Prepare for requesting next page
        args['start'] += args['num']

    return all_feed_items


def _word_normalization(text):
    """
    Normalize a string.
    
    Normalize a string by...
    - tokenizing it.
    - converting all letters to lowercase.
    - stemming words.
    - removing stopwords.
    
    """

    # Tokenize
    word_list = _tokenization(text)

    # Convert letters to lowercase
    word_list = [word.lower() for word in word_list]

    # Perform word stemming (using the Porter stemming algorithm)
    stemmer = nltk.PorterStemmer()
    word_list = [stemmer.stem(word) for word in word_list]

    # Remove stopwords    
    stopwords = nltk.corpus.stopwords.words('english')
    word_list = [word for word in word_list if word not in stopwords]
    
    return word_list
    
    
def _tokenization(text):
    """Tokenization a string. Remove non-alphanumeric characters and split on
    space"""
    alphanumeric = re.sub(r'[^\w\s]+', '', text)
    pattern = r"""(?ux)                 # Set Unicode and verbose flag
              \w+
              """
    return nltk.regexp_tokenize(alphanumeric, pattern)

def _get_website_content(html, return_content_only=True):
    """
    Returns the larges block of text in terms of number of words, where a word
    is defined by a simple regex.
    """
    word_regex = r" [a-zA-Z]+" # Space followed by letters
    text_elements =  ['p', 'a', 'br', 'span', 'b', 'big', 'i', 'small', 'tt',
                     'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7', 'h8',
                     'abbr', 'acronym', 'cite', 'code', 'dfn', 'em', 'kbd',
                     'strong', 'samp', 'q', 'bdo', 'sub', 'sup']
    ignore_elements = ['script']
    
    def _most_words(tag):
        """
        Recursive method traversing the tree to find the largest block of text.
        """
        # Initialize variables
        current_node = {}
        child_nodes = []
        
        # Build current node and find child nodes
        current_node['text'] = ""
        for content in tag.contents:
            # Grap all text not within another element
            if type(content) is bs4.element.NavigableString:
                current_node['text'] += "\n" + content
            # Grap content from inline elements
            elif (
                    type(content) is bs4.element.Tag and
                    content.name in text_elements
                  ):
                current_node['text'] += "\n" + content.text
            # Ignore script tags
            elif (
                    type(content) is bs4.element.Tag and
                    content.name in ignore_elements
                 ):
                pass
            # Continue traversing the html tree
            elif type(content) is bs4.element.Tag:
                child_nodes.append(_most_words(content))
        current_node['number_of_words'] = len(re.findall(word_regex,
                                              current_node['text']))
        current_node['path'] = [] #empty path
        
        # Select the node containing most words
        # and add the current location to the path
        node_with_most_words = max(child_nodes + [current_node],
                                   key=lambda x:x['number_of_words'])
        
        node_with_most_words['path'].insert(0, (tag.name, str(tag.attrs)))
        
        return node_with_most_words
        
    soup = bs4.BeautifulSoup(html)
    for elem in soup('script'): # Remove script elements
        elem.extract()
    element_with_most_words = _most_words(soup)
    if return_content_only:
        return element_with_most_words['text']
    else:
        return element_with_most_words
