import web
from web.contrib.template import render_mako
import sys
from math import ceil
sys.path.append("..")
from db import *

urls = (
    '/nodes/(\d+)', 'nodes',
)

app = web.application(urls, globals())
PAGE_NUM = 30

render = render_mako(
    directories=['templates'],
    input_encoding='utf-8',
    output_encoding='utf-8',
)

def get_paginate(object, page):
    count = object.select().count()
    content = object.select().order_by(object.id).paginate(page, PAGE_NUM)
    total = ceil(count/PAGE_NUM)
    if total < 5:
        page_list = [x for x in range(1,total)]

    return {"count": count, "content":content, "cur_page": page, "page_total": ceil(count/PAGE_NUM)}


class hello:
    def GET(self, name):
        return 'work'

class nodes:
    def GET(self, page=1):
        paginate = get_paginate(Asn(), int(page))
        return render.nodes(data=paginate["content"], paginate=paginate)

if __name__ == "__main__":
    app.run()
