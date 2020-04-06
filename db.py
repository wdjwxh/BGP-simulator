from peewee import *
from bgp_message import BGPUpdateMessage, BGPUpdateMessageType
#from methodtools import lru_cache
from functools import lru_cache
import config

database = MySQLDatabase(config.DB_DATABASE, **{'charset': 'utf8', 'sql_mode': 'PIPES_AS_CONCAT',
                                   'use_unicode': True, 'host': config.DB_HOST, 'user': config.DB_USER, 'password': config.DB_PASSWORD})


class UnknownField(object):
    def __init__(self, *_, **__): pass


class BaseModel(Model):
    class Meta:
        database = database

class Relation(BaseModel):
    asn_1 = IntegerField(index=True)
    asn_2 = IntegerField(index=True)
    relation = IntegerField()

    class Meta:
        table_name = 'relation'

class RelationSmall(BaseModel):
    asn_1 = IntegerField(index=True)
    asn_2 = IntegerField(index=True)
    relation = IntegerField()

    class Meta:
        table_name = 'relation_small'

class Route(BaseModel):
    as_len = IntegerField(null=True)
    asn = IntegerField(index=True)
    aspath = CharField(constraints=[SQL("DEFAULT ''")])
    local_perf = IntegerField()
    origin = IntegerField()
    prefix = CharField(constraints=[SQL("DEFAULT ''")])

    class Meta:
        table_name = 'route'

class RouteSmall(Route):
    as_len = IntegerField(null=True)
    asn = IntegerField(index=True)
    aspath = CharField(constraints=[SQL("DEFAULT ''")])
    local_perf = IntegerField()
    origin = IntegerField()
    prefix = CharField(constraints=[SQL("DEFAULT ''")])

    class Meta:
        table_name = 'route_small'

class Asn(BaseModel):
    asn = IntegerField(null=True)
    msg = None
    queue = None
    use_relation = Relation()
    use_route = Route()

    class Meta:
        table_name = 'asn'

    def set_relation_model(self, model: Relation):
        self.use_relation = model

    def set_route_model(self, model: Route):
        self.use_route = model

    def use_small_dataset(self):
        self.set_relation_model(RelationSmall)
        self.set_route_model(RouteSmall)

    @lru_cache(maxsize=65536)
    def get_peers(self):
        nodes = []
        for r in self.use_relation.select().where(((self.use_relation.asn_1 == self.asn) | (self.use_relation.asn_2 == self.asn)) & (self.use_relation.relation == 0)):
            if r.asn_1 == self.asn:
                nodes.append(r.asn_2)
            else:
                nodes.append(r.asn_1)
        return nodes

    @lru_cache(maxsize=65536)
    def get_customers(self):
        nodes = []
        for r in self.use_relation.select(self.use_relation.asn_2).where((self.use_relation.asn_1 == self.asn) & (self.use_relation.relation == 1)):
            nodes.append(r.asn_2)
        return nodes

    @lru_cache(maxsize=65536)
    def get_providers(self):
        nodes = []
        for r in self.use_relation.select(self.use_relation.asn_1).where((self.use_relation.asn_2 == self.asn) & (self.use_relation.relation == 1)):
            nodes.append(r.asn_1)
        return nodes

    def build_init_message(self, queue, prefix='10.0.0.0/8'):
        msg = BGPUpdateMessage(as_path=str(self.asn), from_asn=self.asn, local_perf=10,
                                    as_len=1, origin_asn=self.asn, prefix=prefix)
        # 初始报文广播给所有的邻居
        for peer in self.get_peers():
            # 修改报文或重新构造报文
            msg.local_perf = BGPUpdateMessageType.FROM_PEER
            msg.to_asn = peer
            msg.send(queue)
        for customer in self.get_customers():
            msg.local_perf = BGPUpdateMessageType.FROM_PROVIDER
            msg.to_asn = customer
            msg.send(queue)
        for provider in self.get_providers():
            msg.local_perf = BGPUpdateMessageType.FROM_CUSTOMER
            msg.to_asn = provider
            msg.send(queue)
        self.msg = None

    def handle(self, msg, queue):
        self.queue = queue
        #print("---Check-" + str(self.asn) + '--')
        if msg.from_asn == self.asn:
            print("错误消息")
            return
        as_paths = msg.as_path.split(',')
        if str(self.asn) in as_paths:
            print("环路")
            return

        self.msg = msg
        (should, route) = self.should_update()
        if should:
            if route == None:
                #print("---Insert---")
                self.insert_route()
            else:
                self.update_route(route)
            self.seed_peers()
        #print("---Check End-" + str(self.asn) + '--')
        self.msg = None

    # 判断self.msg是否会更新本地的路由表
    def should_update(self):
        route = self.find_route(self.msg.prefix)
        if route == None:
            return (True, None)
        # 看local_perf,高的采用
        if int(self.msg.local_perf) > route.local_perf:
            return (True, route)
        # as长度,采用越短
        if int(self.msg.as_len) < route.as_len:
            return (True, route)
        return (False, None)

    def insert_route(self):
        route = self.use_route(asn=self.asn, prefix=self.msg.prefix, aspath=self.msg.as_path,
                      origin=self.msg.origin_asn, local_perf=self.msg.local_perf, as_len=self.msg.as_len)
        route.save()

    # 用self.msg更新本地的路由表
    def update_route(self, route: Route):
        route.aspath = self.msg.as_path
        route.origin = self.msg.origin_asn
        route.local_perf = self.msg.local_perf
        route.as_len = self.msg.as_len
        route.save()

    def build_new_message(self, *, to_asn, msg_type):
        new_msg = BGPUpdateMessage(as_path=str(self.asn) + ',' + self.msg.as_path, from_asn=self.asn,
                                   local_perf=msg_type, as_len=self.msg.as_len + 1, origin_asn=self.msg.origin_asn, prefix=self.msg.prefix, to_asn=to_asn)
        return new_msg

    def seed_peers(self):
        # 发送给其它人
        if self.msg.is_from_customer():
            #发给provider, 来自customer ,30,允许传递给所有人
            for peer in self.get_peers():
                # 修改报文或重新构造报文
                new_msg = self.build_new_message(
                    to_asn=peer, msg_type=BGPUpdateMessageType.FROM_PEER)
                new_msg.send(self.queue)
            for customer in self.get_customers():
                if customer == self.msg.from_asn:
                    continue
                new_msg = self.build_new_message(
                    to_asn=customer, msg_type=BGPUpdateMessageType.FROM_PROVIDER)
                new_msg.send(self.queue)
            for provider in self.get_providers():
                new_msg = self.build_new_message(
                    to_asn=provider, msg_type=BGPUpdateMessageType.FROM_CUSTOMER)
                new_msg.send(self.queue)
        elif self.msg.is_from_peer():
            # 来自peers, 20 的只传递给自己的customer
            for customer in self.get_customers():
                new_msg = self.build_new_message(
                    to_asn=customer, msg_type=BGPUpdateMessageType.FROM_PROVIDER)
                new_msg.send(self.queue)
        elif self.msg.is_from_provider():
            #发给customer,来自providers, 10,只允许传递给customer
            for customer in self.get_customers():
                new_msg = self.build_new_message(
                    to_asn=customer, msg_type=BGPUpdateMessageType.FROM_PROVIDER)
                new_msg.send(self.queue)

    def find_route(self, prefix):
        routes = []
        for i in self.use_route.select().where((self.use_route.asn == self.asn) & (self.use_route.prefix == prefix)):
            routes.append(i)
        return routes[0] if len(routes) > 0 else None


class AsnSmall(Asn):
    asn = IntegerField(null=True)
    msg = None
    queue = None
    use_relation = RelationSmall()
    use_route = RouteSmall()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_small_dataset()

    class Meta:
        table_name = 'asn_small'