# -*- coding: utf-8 -*-
import scrapy
from urllib.parse import urlencode, unquote
from urllib.parse import urlparse
import json
import time
from datetime import datetime


API_KEY = ''
def get_url(url):
    payload = {'api_key': API_KEY, 'url': url}
    proxy_url = 'http://api.scraperapi.com/?' + urlencode(payload)
    return proxy_url
query_paper = ''

class ExampleSpider(scrapy.Spider):
    name = 'scholar'
    allowed_domains = ['api.scraperapi.com']

    def start_requests(self):
        queries = ['paper name']
        for query in queries:
            url = 'https://scholar.google.com/scholar?' + urlencode({'hl': 'en', 'q': query})
            yield scrapy.Request(get_url(url), callback=self.cite_link_parse, meta={'position': 0, 'query':query})
    def cite_link_parse(self, response):

        query = response.meta['query']
        res = response.xpath('//*[@data-rp]')[0] 
        print('query {} and find the parper'.format(query))
        cited_link = res.xpath('.//a[starts-with(text(),"Cited")]/@href').extract_first()
        cited_link = "https://scholar.google.com" + cited_link if cited_link else ""
        yield scrapy.Request(get_url(cited_link), callback=self.find_author_scholar, meta={'position': 0, 'query':query, 'error_num':0})
        

    def find_author_scholar(self, response):
        query = response.meta['query']
        position = response.meta['position']
        try_num = response.meta['error_num']
        url_string = unquote(response.url)
        print('author data list url is {}'.format(url_string))
        if try_num > 0:
            print('this is the try again request,url {}'.format(url_string))
        next_page = response.xpath('//td[@align="left"]/a/@href').extract_first()
        data_rp = response.xpath('//*[@data-rp]')
        #judge web has normal page and data information, if not, crawl it again
        if (not data_rp) and try_num < 10:
            #crawl again
            print('error query times {} {}!!!!try again!!!!cite list url{}'.format(try_num, query, url_string))
            try_num += 1
            yield scrapy.Request(url_string, callback=self.find_author_scholar, meta={'position': position, 'query':query, 'error_num':try_num})
            print('all hred',response.xpath('//td[@align="left"]/a/@href').extract())
        elif try_num >= 10:
            print('query {} try too times, give up!!!!!!!!'.format(query))
        else:
            if next_page and 'start=' in next_page:
                print('url',url_string)
                page_url = next_page
                print('next page link is {}'.format(page_url))
                page_index = page_url.index('start=') + len('start=')
                next_page_num = page_url[page_index]
                if page_url[page_index+2] >='0' and page_url[page_index+2] <='9':
                    next_page_num += page_url[page_index+1]
                print('get the next({}) page url'.format(next_page_num))
            elif 'start=' in url_string:
                page_url = url_string
                page_index = page_url.index('start=') + len('start=')
                this_page = page_url[page_index]
                if page_url[page_index+1] >='0' and page_url[page_index+1] <='9':
                    this_page += page_url[page_index+1]
                print('not next page information after page {} !!!!!!!'.format(this_page))
            else:
                this_page = 0
                print('only one cited page')

            find_flag = False
            res_data = response.xpath('//*[@data-rp]')
            print('the data item num, which contained in this page is {}'.format(len(res_data)))
            author_list_num = 0
            for res in res_data:
                find_flag = True
                temp = res.xpath('.//h3/a//text()').extract()
                if not temp:
                    title = "[C] " + "".join(res.xpath('.//h3/span[@id]//text()').extract())
                else:
                    title = "".join(temp)
                author_name_list_url_list = res.xpath('.//*[@class="gs_a"]/a/@href').extract()
                author_list_num += 1
                position = (position // 10 + 1 ) * 10 
                for author_url in author_name_list_url_list:
                    author_url = "https://scholar.google.com" + author_url
                    position += 1
                    yield scrapy.Request(get_url(author_url), callback=self.find_cited_value, meta={'title': title,'position': position, 'query':query, 'h_error_num':0})

            if not find_flag:
                print('not find the paper list information!!!!!')
                #crawl again
                print('error query {}!!!!try again!!!!cite list url{}'.format(query, url_string))
                try_num += 1
                yield scrapy.Request(url_string, callback=self.find_author_scholar, meta={'position': position, 'query':query, 'error_num':try_num})
            if next_page:
                url = "https://scholar.google.com" + next_page
                yield scrapy.Request(get_url(url), callback=self.find_author_scholar, meta={'position': position, 'query':query, 'error_num':0})
            else:
                print('not find the next ({}) page number!!!!!!'.format(int(this_page)//10+1))


    def find_cited_value(self, response):
        url_string = unquote(response.url)
        query = response.meta['query']
        title = response.meta['title']
        position = response.meta['position']
        try_num = response.meta['h_error_num']
        if try_num > 0:
            print('this is the author try again request,url {}'.format(url_string))
        res = response.xpath('//*[@id="gs_bdy"]')
        author_name = res.xpath('//*[@id="gsc_prf_in"]//text()').extract()
        h_value = res.xpath('//*[@class="gsc_rsb_std"]//text()').extract()
        if len(h_value)<4 and try_num < 5:
            print('find h_value error,h_value is {}'.format(h_value))
            try_num += 1
            yield scrapy.Request(url_string, callback=self.find_cited_value, meta={'title': title,'position': position, 'query':query, 'h_error_num':try_num})
        elif try_num >=5:
            print("query author scholar {} error, give up!!!!!!!".format(author_name))
        else:
            item = {'query': query, 'position': position, 'title': title ,'name': author_name, 'cited_all': h_value[0],'cited_after_2015': h_value[1],'h_vakue_all': h_value[2], 'h_vakue_after_2015': h_value[3], 'i10_vakue_all': h_value[4], 'i10_vakue_after_2015': h_value[5]}
            yield item