import networkx as nx
import matplotlib.pyplot as plt
from db import Asn, Relation, Route
from bgp_message import *
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


def handle(msg: BGPUpdateMessage, queue):
    asn = Asn.get(asn=msg.to_asn)
    asn.handle(msg, queue)
    

def start():
    queue = BGPUpdateMessageQueue()
    ori = Asn.get(asn=268200)
    ori.build_init_message(queue,'202.112.1.0/22')
    executor = ThreadPoolExecutor(100)
    executor_list = []
    Doing = True
    while Doing:
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

        if not queue.empty():
            msg = queue.get()
            obj_list = []
            print("=== Queue Len: " + str(queue.qsize()))
            # print("=====Message Receive=====")
            # print("From:   " + str(msg.from_asn) + "\t" + "To: " + str(msg.to_asn))
            # print("As Path: " + msg.as_path + "\t" + "LocalPerf: " + str(msg.local_perf))
            executor_list.append(executor.submit(handle, msg,queue))

if __name__ == "__main__":
    start()
