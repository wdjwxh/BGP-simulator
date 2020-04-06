import networkx as nx
import matplotlib.pyplot as plt
from db import *
from bgp_message import *
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import cProfile
import pstats
from pstats import SortKey


def handle(msg: BGPUpdateMessage, queue):
    asn = AsnSmall.get(asn=msg.to_asn)
    asn.handle(msg, queue)
    

def start():
    queue = BGPUpdateMessageQueue()
    ori = AsnSmall.get(asn=393300)
    ori.build_init_message(queue,'102.112.1.0/22')
    executor = ThreadPoolExecutor(128)
    executor_list = []
    Doing = True
    pr = cProfile.Profile()
    pr.enable()
    i = 0
    while Doing:
        i = i + 1
        if i % 1000 == 0:
            p = pstats.Stats(pr)
            p.sort_stats(SortKey.TIME, SortKey.CUMULATIVE).print_stats(10)
        finish = True
        for future in executor_list:
            if not future.done():
                finish = False
                break
        
        if finish and queue.empty():
            #全部任务完成,同时队列里消息也为空
            #跳出While True循环
            Doing = False
            break

        batch_size = 0
        while not queue.empty() and batch_size < 256:
            batch_size += 1
            msg = queue.get()
            #print("=== Queue Len: " + str(queue.qsize()))
            # print("=====Message Receive=====")
            # print("From:   " + str(msg.from_asn) + "\t" + "To: " + str(msg.to_asn))
            # print("As Path: " + msg.as_path + "\t" + "LocalPerf: " + str(msg.local_perf))
            executor_list.append(executor.submit(handle, msg,queue))

if __name__ == "__main__":
    start()
