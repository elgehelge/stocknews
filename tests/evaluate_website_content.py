def evaluate_website_content(articles):
    import string
    for article in articles:
        html = article['raw_html']
        most_words_path = _get_website_content(html, False)['path']
        # Build style out of path
        path = ''
        for elem in most_words_path[1:]:
            elem_name = elem[0]
            elem_attr_dict = eval(elem[1])
            path += elem_name
            for attr in elem_attr_dict:
                if (attr == 'class' or attr == 'id'):
                    if type(elem_attr_dict[attr]) == unicode:
                        elem_attr_dict[attr] = [elem_attr_dict[attr]]
                    for value in elem_attr_dict[attr]:
                        if value != '':
                            path += '[%s~=%s]' % (str(attr), str(value))
            path += ' '
        style = path + '{border: dashed 10px lightgreen;}\n'
        style += path + 'div {border: dashed 10px red;}'
        with open('tests/get_website_content/%s.html' % ''.join(
                [char for char in article['title'] if char in string.letters]
                ), 'w') as f:
            f.write(article['raw_html'])
            f.write('<style>%s</style>' % style)
            f.write('<p style="color: lightgreen; border: dashed 10px lightgreen;">%s</p>' % article['content'])