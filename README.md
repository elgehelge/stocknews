stocknews
=========

A Python module for downloading stock related news.

At the moment Google Finance is the only source supported, but tweets tagged with '$' will be supported soon. And maybe more sources will be suported in the future.

Feel free to fork the code and add the sources you need!!! Remember to send pull requests.

Usage
-----

Arguments:

1. `short_name`     (string) the short name of the stock (e.g. 'GOOG').
2. `start_date`     (string formatted as `%Y-%m-%d`) the start date, articles published on this date will be included.
3. `end_date`       (string formatted as `%Y-%m-%d`) the end date, articles published on this date will NOT be included.
4. `order_by_date`  (boolean - default: False) whether to sort the articles by date or by relevance.

Output: A list of articles prepresented by dictionaries containing the following keys:
- `datetime`		(time.struct_time object) The date and time of when the article was published.
- `title`			(unicode) The title of the article (given by Google).
- `wordcounts`		(collections.Counter object) The bag-of-words representation of the article.
- `link`			(unicode) The URL of the article.
- `relevance`		(int) The order in which Google finds the article relavant relative to the other articles.
- `content`			(unicode) The content found by selecting the HTML element with most words.
- `raw_html`		(unicode) The HTML from where the content is extracted.

Example of how to get the most relevant Google Finance articles
related to the LinkedIn stock (LNKD) between the 15th of september and the 15th of
october 2013:

```python
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
```

Example of how to get the earliest and the latest Google Finance article
related to the same stock and within the same time frame as above:

```python
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
```
