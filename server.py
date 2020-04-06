import web
from web.contrib.template import render_mako
import sys
from math import ceil
from db import *
from urllib.parse import urlencode
import json

urls = (
    '/', 'nodes',
    '/favicon.ico', 'hello',
    '/nodes', 'nodes',
    '/relations', 'relations',
    '/routes', 'routes',
    '/topo', 'topo',
    '/topo-json', 'topojson',
)

app = web.application(urls, globals())
PAGE_NUM = 30


render = render_mako(
    directories=['templates'],
    input_encoding='utf-8',
    output_encoding='utf-8',
)


def get_paginate(object, condition, page):
    count = object.select().where(condition).count()
    print(object.select().where(condition).sql())
    content = object.select().where(condition).order_by(
        object.id).paginate(page, PAGE_NUM)
    total = max(1, ceil(count/PAGE_NUM))
    if total < 5:
        page_list = [x for x in range(1, total + 1)]
    else:
        if page <= 3:
            page_list = [x for x in range(1, max(page, 4))]
        elif page >= total - 2:
            page_list = [x for x in range(total - 2, total + 1)]
        else:
            page_list = [page-1, page, page+1]
    if page_list[0] != 1:
        page_list = [1, '...'] + page_list
    if page_list[-1] != total:
        page_list = page_list + ['...', total]

    return {"count": count, "content": content, "cur_page": page, "page_total": ceil(count/PAGE_NUM), "page_list": page_list}


class hello:
    def GET(self):
        return ''

class nodes:
    def GET(self):
        request = web.input()
        params = {
            'asn' : -1,
            'page': 1,
        }
        params.update(request)
        condition = True
        asn = int(params['asn'] or -1)
        if asn != -1:
            condition = (AsnSmall.asn == asn) & (condition)
        paginate = get_paginate(AsnSmall(), condition, max(0, int(params['page'])))
        return render.nodes(data=paginate["content"], paginate=paginate)


class relations:
    def GET(self):
        request = web.input()
        params = {
            'asn': -1,
            'relation_type': 'alls',
            'page': 1
        }
        params.update(request)
        condition = True
        asn = int(params['asn'] or -1)
        relation_type = params['relation_type']
        if asn != -1:
            if relation_type == 'alls':
                condition = (RelationSmall.asn_1 == asn) | (
                    RelationSmall.asn_2 == asn)
            elif relation_type == 'peers':
                condition = ((RelationSmall.asn_1 == asn) | (
                    RelationSmall.asn_2 == asn)) & (RelationSmall.relation == 0)
            elif relation_type == 'customers':
                condition = (RelationSmall.asn_1 == asn) & (
                    RelationSmall.relation == 1)
            elif relation_type == 'providers':
                condition = (RelationSmall.asn_2 == asn) & (
                    RelationSmall.relation == 1)
        paginate = get_paginate(
            RelationSmall(), condition, max(0, int(params['page'])))
        return render.relations(asn=asn, relation_type=relation_type, data=paginate["content"], paginate=paginate)

class routes:
    def GET(self):
        request = web.input()
        params = {
            'asn': -1,
            'prefix' : '',
            'origin': -1,
            'aspath' : '',
            'page': 1
        }
        params.update(request)
        condition = True
        asn = int(params['asn'] or -1)
        origin = int(params['origin'] or -1)
        if asn != -1:
            condition = (RouteSmall.asn == asn) & (condition)
        if params['prefix'] != '':
            condition = (RouteSmall.prefix == params['prefix']) & (condition)
        if origin != -1:
            condition = (RouteSmall.origin == origin) & (condition)
        if params['aspath'] != '':
            condition = (RouteSmall.aspath.contains(params['aspath'])) & (condition)

        paginate = get_paginate(
            RouteSmall(), condition, max(0, int(params['page'])))
        params.pop('page')
        return render.routes(qs=urlencode(params), data=paginate["content"], paginate=paginate)
class topo:
    def GET(self):
        request = web.input()
        params = {
            'asn': -1,
        }
        params.update(request)
        return render.topo(asn=params['asn'])

class topojson:
    def GET(self):
        request = web.input()
        params = {
            'asn': -1,
        }
        params.update(request)
        condition = True
        asn = int(params['asn'] or -1)
        if asn == -1:
            nodes = []
            edges = []

        else:
            asn = AsnSmall.get(asn=asn)
            peers = asn.get_peers()
            customers = asn.get_customers()
            providers = asn.get_providers()
            print(asn.id)
            node_list = peers + customers + providers + [asn.asn]
            relations = RelationSmall.select().where((RelationSmall.asn_1 << node_list) & (RelationSmall.asn_2 << node_list))
            nodes = []
            edges = []
            
            nodes_value = {}
            for rel in relations:
                if rel.asn_1 not in nodes_value:
                    nodes_value[rel.asn_1] = 0
                if rel.asn_2 not in nodes_value:
                    nodes_value[rel.asn_2] = 0
                nodes_value[rel.asn_1] += 1
                nodes_value[rel.asn_2] += 1

                if rel.relation == 0:
                    edges.append({'from': rel.asn_1, 'to': rel.asn_2,
                                  'relation': 'p2p', 'color': {'color': 'blue'}})
                else:
                    edges.append({'from': rel.asn_1, 'to': rel.asn_2,
                                  'arrows': 'to', 'relation': 'p2c', 'color': {'color': 'green'}})
            
            for asn, count in nodes_value.items():
                nodes.append({'id': asn, 'label': str(asn), 'value': count})
            
        data = {
            'nodes': nodes,
            'edges': edges,
        }
        web.header('Content-Type', 'application/json')
        return json.dumps(data)


if __name__ == "__main__":
    app.run()
