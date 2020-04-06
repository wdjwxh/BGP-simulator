import networkx as nx
import matplotlib.pyplot as plt
from db import *
import peewee
import random

def create_topo():
    G = nx.Graph()
    G.add_node(1) 
    G.add_node('A') 
    G.add_nodes_from([2, 3]) 
    G.add_edges_from([(1,2),(1,3),(2,4),(2,5),(3,6),(4,8),(5,8),(3,7)]) 
    H = nx.path_graph(10) 
    G.add_nodes_from(H)
    G.add_node(H)
    G.add_node('a')#添加点a
    G.add_edge('x','y')#添加边,起点为x，终点为y
    nx.draw(G, with_labels=True)

    plt.show()

def get_data():
    a = Asn.get(Asn.asn == 123)
    print(a.asn)

def clean_database():
    Asn.truncate_table()
    Relation.truncate_table()
    Route.truncate_table()
    pass

def init_database(graph:nx.DiGraph):
    clean_database()
    for node in graph.nodes():
        asn = Asn.create(asn=node)

    exists = []
    for edge in graph.edges():
        if (edge[0], edge[1]) in exists:
            continue
        if (edge[1], edge[0]) in graph.edges():
            Relation.create(asn_1=edge[0], asn_2=edge[1], relation=0)
            exists.append((edge[0], edge[1]))
            exists.append((edge[1], edge[0]))
        else:
            Relation.create(asn_1=edge[0], asn_2=edge[1], relation=1)


def init_data():
    # G = nx.DiGraph()
    # G.add_nodes_from([x for x in range(1,9)])
    # G.add_edges_from([[1,2],[2,1],[1,5], [1,4],[4,1],  [2,4],[4,2], [2,3], [4,3], [4,7], [5,6], [7,8]])
    G = nx.read_gpickle('data/as-caida20200301.gpickle')

    init_database(G)

def make_data_small():
    #1.找出所有没有providers的asn
    PROBABILITY = 0.2
    new_nodes = set()
    set_A = set()
    for asn in Asn.select().where(Asn.asn.not_in(Relation.select(Relation.asn_2).where(Relation.relation == 1).group_by(Relation.asn_2))):
        set_A.add(asn.asn)
        new_nodes.add(asn.asn)
    
    #2.1 得到所有的customer
    iter_times = 0
    while True:
        iter_times = iter_times + 1
        print("iter {} times".format(iter_times))
        set_customer = set()
        asn_customer = {}
        for r in Relation.select(Relation.asn_1,Relation.asn_2).where((Relation.asn_1 << set_A) & (Relation.relation == 1)).order_by(Relation.asn_1):
            if str(r.asn_1) not in asn_customer:
                asn_customer[str(r.asn_1)] = []
            asn_customer[str(r.asn_1)].append(r.asn_2)
        
        #2.2 随机选择
        for (key_asn, item_customer) in asn_customer.items():
            random_customer = [x for x in item_customer if random.random() <= PROBABILITY]
            new_nodes |= set(random_customer)
            set_customer |= set(random_customer)

        set_A = set_customer
        print('A.length: {}'.format(len(set_A)))
        print('NewNode.length: {}'.format(len(new_nodes)))
        if len(set_A) == 0:
            break
    
    #2.3 保存所有的点
    print("insert into database")
    new_nodes = [{'asn': x} for x in new_nodes]
    AsnSmall.truncate_table()
    with database.atomic():
        for batch in chunked(new_nodes, 500):
            AsnSmall.insert_many(batch, fields=[AsnSmall.asn]).execute()
    #3 通过新的点集合，所到其原来的边
    RelationSmall.truncate_table()
    database.execute_sql(
        'insert into relation_small select * from relation where relation.asn_1 in (select asn from asn_small) and relation.asn_2 in (select asn from asn_small)')

    print("end")
        
if __name__ == "__main__":
    # init_data()
    # make_data_small()
    pass
