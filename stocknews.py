from threading import Thread
from collections import Counter
from operator import itemgetter
import urllib
import urllib2
import re
import random
import datetime
import string
import feedparser
import nltk
import bs4
import shelve

class StockNews:
    """
    Fetch news related to stocks. At the moment Google Finance is the only source supported, but also tweets will be supported soon. And maybe more sources will be supported in the future.
	
    Feel free to fork the code on `github <http://www.github.com/elgehelge/stocknews>`_ and add the sources you need.
    
    .. note:: An instance can be created using either using short_names, start_date and end_date or the db_file_name.
    
    Arguments:
	
    - short_names -- (list of strings) the short name of the stock (e.g. 'GOOG')
    - start_date -- (string formatted as %Y-%m-%d) the start date, articles published on this date will be included
    - end_date -- (string formatted as %Y-%m-%d) the end date, articles published on this date will NOT be included
    - db_file_name -- (string) the file name of the database file

    Example showing how to get the most relevant Google Finance articles related to the LinkedIn stock (LNKD) between the 15th of august and the 15th of september 2013:

    >>> articles = StockNews(['LNKD', 'FB'], '2013-10-15', '2013-11-15')
    >>> len(articles)
    124
    >>> articles.get_short_names()
    ['FB', 'LNKD']
    >>> for short_name in articles.get_short_names():
    ...    count = sum([1 for _ in articles.iterate('title', short_name)])
    ...    print "%s has %i articles." % (short_name, count)
    FB has 59 articles.
    LNKD has 64 articles.
    >>> first_facebook_article = articles.iterate(['title', 'link', 'content', 'wordcounts'], 'FB').next()
    >>> title, link, content, wordcounts = first_facebook_article
    >>> title
    u'Facebook Inc (FB) Buying BlackBerry Ltd (BBRY): A Rumor That Makes Sense'
    >>> link
    u'http://www.valuewalk.com/2013/10/facebook-inc-fb-buying-blackberry-ltd-bbry-rumor/'
    >>> content[:200]
    u'Facebook Inc (NASDAQ:FB) has been linked with a deal to acquire BlackBerry Ltd (NASDAQ:BBRY) (TSE:BB). At this stage there is no reason to believe the rumors. Several companies have been linked with '
    >>> wordcounts.most_common(10)
    [('facebook', 20), ('mobil', 8), ('inc', 8), ('blackberri', 7), ('nasdaqfb', 7), ('ha', 6), ('busi', 5),
    ('year', 5), ('hardwar', 5), ('compani', 5)]

    """

    __version__ = 2.0
    # Changes since last update:
    # - Changed to class
    # - Iterator method for easily accessing the data

    USER_AGENT = "StockNewsCrawler/%s" % __version__ + \
                 "Source code available on github.com/elgehelge/stocknews"

    # Magic methods

    def __init__(self, short_names=None, start_date=None, end_date=None, db_file_name=None):
        if short_names and start_date and end_date:
            if db_file_name:
                self._db_filename = db_file_name
            else:
                self._db_filename = 'data/_stocknews_db_%d-stocks_%s-%s_%s.shelve'\
                                    % (len(short_names), start_date, end_date, self._id_generator())
                print 'Data will be stored in %s' % self._db_filename
            self._download_and_store_articles(short_names, start_date, end_date)
        elif db_file_name:
            self._db_filename = db_file_name
            db = self._open_db()
            db.close()
        else:
            raise ValueError("Please provide either of\n1) short_names, start_date and end_date\n2) db_file_name")

    def __len__(self):
        return sum([1 for _ in self.iterate('stock_short_name')])

    # Public methods

    def get_short_names(self):
        """
        Return a list of all stock names.
        """
        db = self._open_db()
        short_names = db.keys()
        db.close()
        return short_names

    def iterate(self, attributes=None, short_names=None):
        """
        Return a iterator that iterates the data as specified by the arguments:

        'attributes' is either a string or a list of strings specifying which attributes to iterate through
		
        'short_names' is uses to limit the iteration to specific stocks.

        """
    
        db = self._open_db()
        
        if len(db.keys()) == 0:
            raise StopIteration
        
        # If no attributes are given, then iterate through all attribute
        if not attributes:
            attributes = ['stock_short_name', 'datetime', 'title', 'wordcounts', 'link', 'relevance', 'content', 'raw_html']
        
        # If no stock names are given, then iterate through all stocks in the database
        if not short_names:
            short_names = db.keys()
        
        # Wrap short_name if only one is provided
        if not hasattr(short_names, '__iter__'):
            short_names = [short_names]

        # Iterate
        for short_name in short_names:
            article_list = db[short_name]
            if not hasattr(attributes, '__iter__'): # Only one or multiple attributes provided
                for article in article_list:
                    yield article[attributes]
            else:
                for article in article_list:
                    yield tuple(article[attribute] for attribute in attributes)

        db.close()

    # Private methods

    def _open_db(self):
        """
        Open the database file and return the database file object.

        This method reduces redundancy and makes it easy to switch the database without affecting the rest of the code.

        """
        try:
            return shelve.open(self._db_filename)
        except:
            raise IOError('Was not able to open the database file \'%s\'' % self._db_filename)

    def _download_and_store_articles(self, short_names, start_date, end_date):
        """Downloads the specified articles and stores it in the database file associated with this class instance."""
        db = self._open_db()
        for short_name in short_names:
            db[short_name] = self._download_articles_single_stock(short_name, start_date, end_date)
        db.close()

    def _download_articles_single_stock(self, short_name, start_date, end_date):
        """
        Downloads the articles for the specified stock in the specified time interval.

        Return a sorted list of dictionaries representing articles.

        Each dictionary represents an article and has the following keys:
        - 'stock_short_name'
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
        feed_items = self._get_google_finance_feed(short_name, start_date, end_date)
        for index, item in enumerate(feed_items):
            article = {}
            article['stock_short_name'] = short_name
            article['datetime'] =  datetime.datetime(*item['published_parsed'][:6])
            article['title'] = item['title']
            article['link'] = item['link']
            article['relevance'] = index + 1
            article_list.append(article)

        # Fetch articles in parallel
        number_of_articles = len(article_list)
        print "Fetching %i articles online in parallel..." % number_of_articles
        opener = urllib2.build_opener()
        opener.addheaders = [("User-agent", self.USER_AGENT)]
        def fetch_online(article):
            """
            Fetch online content.

            Request the url for an article dictionary (article['link']) and store
            the content within this dictionary (article['content']).

            """
            try:
                raw_html = opener.open(article['link'], timeout = 10).read()
            except: # Including URLError and timeout (but many other exceptions can be raised)
                article_list.remove(article)
            else:
                article['raw_html'] = raw_html
                article['content'] = self._get_website_content(raw_html)
        threads = [Thread(target=fetch_online, args = (article,))
                   for article in article_list] # takes tuple as args
        # Start all threads and wait for them to finish
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
            word_list = self._word_normalization(text)
            # Count words
            article['wordcounts'] = Counter(word_list)

        # Order by date instead of by relevance
        article_list = sorted(article_list, key=itemgetter('datetime'))

        return article_list


    #def get_tweets(short_name, start_date, end_date):
    #    # TODO: Implement this
    #    """
    #    Returns a sorted list of dictionaries with keys:
    #    - 'datetime'
    #    - 'content'
    #    - 'wordcounts'
    #    - 'no_retweets'
    #    - 'user_id'
    #    - 'user_followers'
    #
    #    """

    def _get_google_finance_feed(self, short_name, start_date, end_date):
        """
        Return a list of feedparser items sorted by relevance.
        """
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
        feedparser.USER_AGENT = self.USER_AGENT
        while not reached_end_of_feed:
            feed_url = 'https://www.google.com/finance/company_news?' \
                       + urllib.urlencode(args)
            feed = feedparser.parse(feed_url)
            all_feed_items += feed['items']
            reached_end_of_feed = len(feed['items']) != args['num']
            # Prepare for requesting next page
            args['start'] += args['num']

        return all_feed_items


    def _word_normalization(self, text):
        """
        Normalize a string.

        Normalize a string by...
        - tokenizing it.
        - converting all letters to lowercase.
        - stemming words.
        - removing stopwords.

        """
        # Tokenize
        word_list = self._tokenization(text)

        # Convert letters to lowercase
        word_list = [word.lower() for word in word_list]

        # Perform word stemming (using the Porter stemming algorithm)
        stemmer = nltk.PorterStemmer()
        word_list = [stemmer.stem(word) for word in word_list]

        # Remove stopwords
        stopwords = nltk.corpus.stopwords.words('english')
        word_list = [word for word in word_list if word not in stopwords]

        return word_list


    def _tokenization(self, text):
        """
        Tokenization a string. Remove non-alphanumeric characters and split on space.
        """
        alphanumeric = re.sub(r'[^\w\s]+', '', text)
        pattern = r"""(?ux)                 # Set Unicode and verbose flag
                  \w+
                  """
        return nltk.regexp_tokenize(alphanumeric, pattern)

    def _get_website_content(self, html, return_content_only=True):
        """
        Returns the larges block of text in terms of number of words, where a word is defined by a simple regex.
        """
        word_regex = r" [a-zA-Z]+" # Space followed by letters
        text_elements =  ['p', 'a', 'br', 'span', 'b', 'big', 'i', 'small', 'tt',
                         'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7', 'h8',
                         'abbr', 'acronym', 'cite', 'code', 'dfn', 'em', 'kbd',
                         'strong', 'samp', 'q', 'bdo', 'sub', 'sup']
        ignore_elements = ['script']

        def _most_words(soup_xml_tag):
            """
            Recursive method traversing a XML tree to find the tag with the largest block of text.
            """
            # Initialize variables
            current_node = {}
            child_nodes = []

            # Build current node and find child nodes
            current_node['text'] = ""
            for content in soup_xml_tag.contents:
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

            node_with_most_words['path'].insert(0, (soup_xml_tag.name, str(soup_xml_tag.attrs)))

            return node_with_most_words

        soup = bs4.BeautifulSoup(html)
        for elem in soup('script'): # Remove script elements
            elem.extract()
        element_with_most_words = _most_words(soup)
        if return_content_only:
            return element_with_most_words['text']
        else:
            return element_with_most_words

    def _id_generator(self, length=6, chars=string.ascii_uppercase + string.digits):
        """ Generate a unique id. Inspired by http://stackoverflow.com/questions/2257441/python-random-string-generation-with-upper-case-letters-and-digits"""
        return ''.join(random.choice(chars) for x in xrange(length))