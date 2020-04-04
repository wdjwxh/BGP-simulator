import networkx as nx


g = nx.read_gpickle('data/as-caida20200301.gpickle')

print(list(g.nodes())[:100])