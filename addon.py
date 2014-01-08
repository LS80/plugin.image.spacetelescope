# coding=utf-8
##########################################################################
#
#  Copyright 2013 Lee Smith
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
# 
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
# 
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##########################################################################

import urllib2
import urlparse
import re

from xbmcswift2 import Plugin
from bs4 import BeautifulSoup

BASE_URL = "http://www.spacetelescope.org"

CAT_RE = re.compile("/images/archive/category/([a-z]+)/$")
IMG_RE = re.compile("/images/(.+?)/$")

plugin = Plugin()

def get_soup(url):
    html = urllib2.urlopen(url).read()
    # script.module.html5lib is a requirement
    # so html5lib will automatically be used instead of HTMLParser.
    return BeautifulSoup(html, 'html.parser')

def get_categories():
    soup = get_soup(urlparse.urljoin(BASE_URL, 'images'))
    left_menu = soup.find('div', id='leftmenu')

    for cat_link in left_menu.find('a', 'level_2 ', text='Categories').find_all_next('a', 'level_3 '):
        item = {'label': cat_link.string,
                'path': plugin.url_for('browse_images',
                                       cat=CAT_RE.match(cat_link['href']).group(1),
                                       page='1')
                }
        yield item
        
def image_response(img_id):
    for ext in ('tif', 'jpg'):
        for res in ('original', 'large'):
            href = urlparse.urljoin(BASE_URL, "/static/archives/images/{}/{}.{}".format(res, img_id, ext))
            try:
                resp = urllib2.urlopen(href)
            except urllib2.HTTPError:
                continue
            else:
                return resp
        
def image_item(title, href, size, thumbnail):
    return {'label': title,
            'path': href,
            'info': {'title': title,
                     'size': size
                    },
            'thumbnail': thumbnail,
            'is_playable': True}
        
def get_top100(url):
    soup = get_soup(url)
        
    for i, a in enumerate(soup('a', 'entry')):
        img_id = IMG_RE.match(a['href']).group(1)
        title = u"{}. {}".format(i+1, a.div.img['alt'])
        
        resp = image_response(img_id)
        if resp is not None:
            size = int(resp.headers.getheader('Content-Length'))
            href = resp.geturl()
            
            thumbnail = urlparse.urljoin(BASE_URL, a.div.img['src'])
    
            yield image_item(title, href, size, thumbnail)

def get_page_of_images(url, page, endpoint, **kwargs):
    page = int(page)
    soup = get_soup(url)
    if page > 1:
        previous_page = str(page - 1)
        item = {'label': "<< Page {} <<".format(previous_page),
                'path': plugin.url_for(endpoint, page=previous_page, **kwargs)
        }
        yield item

    if soup.find('span', 'paginator_next').a is not None:
        next_page = str(page + 1)
        item = {'label': ">> Page {} >>".format(next_page),
                'path': plugin.url_for(endpoint, page=next_page, **kwargs)
        }
        yield item
        
    for td in soup('td', 'imagerow'):
        img_id = IMG_RE.match(td.a['href']).group(1)
        title = td.a.img['alt']

        resp = image_response(img_id)
        if resp is not None:
            size = int(resp.headers.getheader('Content-Length'))
            href = resp.geturl()
            
            thumbnail = urlparse.urljoin(BASE_URL, td.a.img['src'])
    
            yield image_item(title, href, size, thumbnail)


@plugin.route('/')
def index():
    return [{'label': 'Top 100', 'path': plugin.url_for('top100')},
            {'label': 'Search', 'path': plugin.url_for('search')},
            {'label': 'Browse Categories', 'path': plugin.url_for('browse')}]
    
@plugin.cached_route('/top100')
def top100():
    url = urlparse.urljoin(BASE_URL, "/images/archive/top100")
    return plugin.finish(get_top100(url),
                         sort_methods=['unsorted', 'size', 'title'],
                         update_listing=True)
    
@plugin.route('/search')
def search():
    query = plugin.keyboard(heading="Search")
    if query:
        url = plugin.url_for('search_results', query=query, page=1)
        plugin.redirect(url)

@plugin.cached_route('/search/<query>/page/<page>')
def search_results(query, page):
    url = urlparse.urljoin(BASE_URL, "/images/page/{}/?search={}".format(page, query))
    items = get_page_of_images(url, page, 'search_results', query=query)
    return plugin.finish(items,
                         sort_methods=['unsorted', 'size', 'title'],
                         update_listing=True)
    
@plugin.cached_route('/browse')
def browse():
    return get_categories()

@plugin.cached_route('/browse/<cat>/page/<page>')
def browse_images(cat, page):
    url = urlparse.urljoin(BASE_URL, "/images/archive/category/{}/page/{}".format(cat, page))
    items = get_page_of_images(url, page, 'browse_images', cat=cat)
    return plugin.finish(items,
                         sort_methods=['unsorted', 'size', 'title'],
                         update_listing=True)

if __name__ == '__main__':
    plugin.run()
