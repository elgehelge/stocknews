stocknews
=========

A Python module for downloading stock related news.

At the moment Google Finance is the only source supported, but tweets tagged with '$' will be supported soon. And maybe more sources will be suported in the future.

Feel free to fork the code and add the sources you need!!!

Usage
-----

Arguments:

1. `short_name`    -- (string) the short name of the stock (e.g. 'GOOG')
2. `start_date`    -- (string formatted as `%Y-%m-%d`) the start date, articles published on this date will be included
3. `end_date`      -- (string formatted as `%Y-%m-%d`) the end date, articles published on this date will NOT be included
4. `order_by_date` -- (boolean - default: False) whether to sort the articles by date or by relevance

Example of how to get the most relevant Google Finance articles
related to the LinkedIn stock (LNKD) between the 15th of august and the 15th of
september 2013:

```python
>>> articles = get_google_finance_articles('LNKD', '2013-08-15', '2013-09-15')
>>> len(articles)
58
>>> most_relevant_article = articles[0]
>>> least_relevant_article = articles[-1]
>>> most_relevant_article['relevance']
1
>>> least_relevant_article['relevance']
58
>>> most_relevant_article['title']
u'Linkedin Corp (LNKD): Could Linkedin Substitute A Recruitment Agency?'
>>> most_relevant_article['content'][:20]
'Linkedin Corp (LNKD)'
```

Example of how to get the earliest and the latest Google Finance article
related to the same stock and within the same time frame as above:

```python
>>> articles = get_google_finance_articles('LNKD', '2013-08-15', '2013-09-15',
...                                        True)
>>> len(articles)
58
>>> earliest_article = articles[0]
>>> latest_article = articles[-1]
>>> import time
>>> time.strftime("%d %b %Y %H:%M:%S", earliest_article['datetime'])
'03 Sep 2013 12:13:00'
>>> time.strftime("%d %b %Y %H:%M:%S", latest_article['datetime'])
'14 Sep 2013 21:08:17'
```
