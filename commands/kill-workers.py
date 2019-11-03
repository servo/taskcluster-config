import sys
import taskcluster


def main(worker_pool):
    wm = taskcluster.WorkerManager(taskcluster.optionsFromEnvironment())
    result = wm.listWorkersForWorkerPool("proj-servo/" + worker_pool)
    workers = [w for w in result["workers"] if w["state"] != "stopped"]

    for w in workers:
        print(w["workerGroup"], w["workerId"], w["state"])
    print()

    if input("Remove all? y/n ") == "y":
        for w in workers:
            sys.stdout.write(".")
            sys.stdout.flush()
            wm.removeWorker("proj-servo/" + worker_pool, w["workerGroup"], w["workerId"])
        print()


if __name__ == "__main__":
    main(*sys.argv[1:])
