import sys
import taskcluster


def main(worker_pool):
    wm = taskcluster.WorkerManager(taskcluster.optionsFromEnvironment())
    workers = []
    stopped = 0
    def handle(result):
        nonlocal stopped
        for w in result["workers"]:
            if w["state"] == "stopped":
                stopped += 1
            else:
                print(w["workerGroup"], w["workerId"], w["state"])
                workers.append(w)
    wm.listWorkersForWorkerPool("proj-servo/" + worker_pool, paginationHandler=handle)
    print("… and %s stopped" % stopped)

    if input("Remove all? y/n ") == "y":
        for w in workers:
            sys.stdout.write(".")
            sys.stdout.flush()
            wm.removeWorker("proj-servo/" + worker_pool, w["workerGroup"], w["workerId"])
        print()


if __name__ == "__main__":
    main(*sys.argv[1:])
