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
                workers.append(w)
    wm.listWorkersForWorkerPool("proj-servo/" + worker_pool, paginationHandler=handle)

    workers.sort(key=lambda w: w["created"])
    print("Created                  ID                  State")
    for w in workers:
        print(w["created"], w["workerId"], w["state"])
    print("… and %s stopped" % stopped)

    if input("Remove all? [y/n] ") != "y":
        return 1

    for w in workers:
        sys.stdout.write(".")
        sys.stdout.flush()
        wm.removeWorker("proj-servo/" + worker_pool, w["workerGroup"], w["workerId"])
    print()


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
