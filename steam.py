#! /usr/bin/env python2
# -*- coding: utf-8 -*-
import urllib2
import json
import codecs
import lxml.html
import re
import sys
import subprocess
import os
import pprint

pp = pprint.PrettyPrinter(indent=4)

SM_CARD   = 1
SM_BG     = 2
SM_SMILEY = 3
SM_SET    = 4
SM_CARD_M = 5

klass_map = [
    (SM_CARD_M, re.compile(u'Коллекционная карточка металлическая')),
    (SM_CARD, re.compile(u'Коллекционная карточка')),
    (SM_BG, re.compile(u'(Редкий |Необычный )?Фон профиля')),
    (SM_SMILEY, re.compile(u'(Редкий |Необычный )?Смайлик')),
    (SM_SET, re.compile(u'Набор карточек'))
]

with open('.steamrc') as f:
    hdrs = json.load(f)


class market_item:
    def __init__(self, a):
        self.href = a.attrib['href']
        self.name = a.xpath('div[1]/div[3]/span[1]')[0].text
        klass_txt = a.xpath('div[1]/div[3]/span[2]')[0].text
        self.klass = None
        for r in klass_map:
            if r[1].match(klass_txt):
                self.klass = r[0]
                break
        self.count = int(re.sub(',', '', a.xpath('div[1]/div[2]/span[1]/span[1]')[0].text))
        price_txt = a.xpath('div[1]/div[1]/span[1]/span[1]')[0].text
        self.price = float(re.sub(',', '.', re.match('([0-9,]+)', price_txt).group(1)))

def goo_value(appid):
    value = 0
    for i in (7, 10, 17):
        req = urllib2.Request("http://steamcommunity.com/auction/ajaxgetgoovalueforitemtype/?appid=%d&item_type=%d" % (appid, i), None, hdrs)
        ret = json.loads(urllib2.urlopen(req).read())
        if ret.has_key('goo_value'):
            val = int(ret['goo_value'])
            if val > value:
                value = val
            if val in (40, 60, 80, 100):
                break
    return value

def parse_item(a):
    return market_item(a)

def get_goods(appid, goo):
    if True:
        req = urllib2.Request('http://steamcommunity.com/market/search/render/?query=&start=0&count=100&search_descriptions=0&sort_column=price&sort_dir=asc&appid=753&category_753_Game%%5B%%5D=tag_app_%d' % (appid), None, hdrs)
        ret = json.loads(urllib2.urlopen(req).read())
        if not ret.has_key('success') or int(ret['success']) == 0 or not ret.has_key('results_html'):
            return None
        #with codecs.open('/tmp/dumps.html', 'w', 'utf-8') as f:
            #f.write(ret['results_html'])
        data = ret['results_html']
    else:
        with codecs.open('/tmp/dumps.html', 'r', 'utf-8') as f:
            data = f.read()
    data = "<root>" + data + "</root>"
    doc = lxml.html.fromstring(data)
    items = []
    for i in doc.xpath('a'):
        items.append(parse_item(i))
    cheapest = None
    cset = None
    count = 0
    cost = 0.0
    cost_s = ''
    for i in items:
        if i.klass == SM_CARD:
            count = count + 1
            if cost is not None and i.price > 0:
                cost = cost + i.price
                if len(cost_s) > 0:
                    cost_s = cost_s + ' + '
                cost_s = cost_s + ('%.2f' % i.price)
            else:
                cost = None
        if goo > 1:
            if i.klass in (SM_BG, SM_SMILEY) and i.price > 0:
                if i.price <= 2.15:
                    print('%.2f <= %s ==> \033[01;35m%s \033[01;37m(%.2f RUB per 1000 GEMS)\033[0m' % (i.price, i.name, i.href, 1000.0 * i.price / goo))
                    #if i.price <= 2:
                    subprocess.call(['firefox', i.href])
                if not cheapest or cheapest.price > i.price:
                    cheapest = i
        if i.klass == SM_SET:
            cset = i
    if cost is not None:
        if cost <= 18:
            hl = '\033[01;33m'
            print('  ! set cards: http://steamcommunity.com/market/search?category_753_Game%%5B%%5D=tag_app_%d&category_753_cardborder%%5B%%5D=tag_cardborder_0&category_753_item_class%%5B%%5D=tag_item_class_2&appid=753' % (appid))
        else:
            hl = ''
        print('  + %s%d cards in set; minimal set cost %.2f RUB (%s)\033[0m' % (hl, count, cost, cost_s))
    if cheapest:
        print('  * Cheapest item cost: %.2f @@ %s' % (cheapest.price, cheapest.href))
        print('                        %.2f RUB per 1000 gems' % (1000.0 * cheapest.price / goo))
    if cset:
        if cset.price >= 46:
            hl = '\033[01;36m'
        else:
            hl = ''
        print('  * Booster cost:       %.2f @@ %s%s\033[0m' % (cset.price, hl, cset.href))
    return items

def load_apps():
    res = '.apps.json'
    if os.path.isfile(res):
        with open(res) as f:
            apps = json.load(f)
    else:
        apps = {}
    return apps

def load_app_ids():
    ids = set()
    for k, v in load_apps().items():
        ids.update(v)
    return ids

def save_app_id(appid, goo):
    res = '.apps.json'
    if os.path.isfile(res):
        with open(res) as f:
            apps = json.load(f)
    else:
        apps = {}
    key = str(goo)
    if apps.has_key(key):
        if appid not in apps[key]:
            apps[key].append(appid)
    else:
        apps[key] = [appid]

    with open(res, 'w') as f:
        json.dump(apps, f, indent=2)

def process_app(appid, goo_cost):
    if appid in load_app_ids():
        hl = '\033[01;30m'
    else:
        hl = ''
    print('%sappid = %d => http://store.steampowered.com/app/%d/\033[0m' % (hl, appid, appid))
    goo = goo_cost or goo_value(appid)
    print('Goo value is %d' % (goo))
    print('\033[92m===> http://steamcommunity.com/market/search?appid=753&category_753_Game%%5B%%5D=tag_app_%d&q=#p1_price_asc <==\033[0m' % (appid))
    if goo >= 80:
        save_app_id(appid, goo)
        get_goods(appid, goo)
    elif goo > 0:
        get_goods(appid, 0)

if len(sys.argv) > 1:
    appsrc = sys.argv[1]
else:
    appsrc = subprocess.check_output(['/usr/bin/xclip', '-o', '-selection', 'clipboard'])

if re.search('/app/[0-9]+', appsrc):
    appid = int(re.search('/app/([0-9]+)', appsrc).group(1))
elif re.search('=tag_app_[0-9]+', appsrc):
    appid = int(re.search('=tag_app_([0-9]+)', appsrc).group(1))
elif re.search('/market/listings/753/[0-9]+', appsrc):
    appid = int(re.search('/market/listings/753/([0-9]+)', appsrc).group(1))
elif re.search('gamepage-appid-[0-9]+', appsrc):
    appid = int(re.search('gamepage-appid-([0-9]+)', appsrc).group(1))
elif len(sys.argv) > 1 and sys.argv[1] == '-a':
    with open('.apps.json') as f:
        apps = json.load(f)
    for k, v in apps.items():
        for a in v:
            process_app(a, int(k))
    sys.exit(0)
elif len(sys.argv) > 1 and sys.argv[1] == '-c':
    with open('.apps.json') as f:
        apps = json.load(f)
    out = dict()
    for k, v in apps.items():
        for a in v:
            goo = goo_value(a)
            if goo == int(k):
                print('app[%d] => %d goo' % (a, goo))
            elif goo < int(k):
                print('\033[01;31mapp[%d] => %d goo\033[0m' % (a, goo))
            else:
                print('\033[01;32mapp[%d] => %d goo\033[0m' % (a, goo))
            if goo >= 80:
                if out.has_key(goo):
                    out[goo].append(a)
                else:
                    out[goo] = [a]
    os.rename('.apps.json', '.apps.json.bak')
    with open('.apps.json', 'w') as f:
        json.dump(out, f, indent=2)
    sys.exit(0)
else:
    print('Failed to parse appid from «%s»' % (appsrc))
    sys.exit(1)

process_app(appid, None)
