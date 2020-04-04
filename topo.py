import networkx as nx
import matplotlib.pyplot as plt
from db import Asn, Relation, Route

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

if __name__ == "__main__":
    init_data()
    pass
