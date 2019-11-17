import datetime
import sys
import taskcluster


def main(*task_group_ids):
    for task_group_id in task_group_ids:
        print("https://community-tc.services.mozilla.com/tasks/groups/" + task_group_id)
        timings = {}
        def handler(result):
            for task in result["tasks"]:
                name = task["task"]["metadata"]["name"]
                for run in task["status"]["runs"]:
                    resolved = run.get("resolved")
                    if not resolved:
                        print("Not resolved yet:", name)
                        continue
                    key = task["task"]["workerType"]
                    if "WPT" in name:
                        key += " WPT"
                    # fromisoformat doesn’t like the "Z" timezone, [:-1] to remove it
                    timings.setdefault(key, []).append(
                        datetime.datetime.fromisoformat(resolved[:-1]) -
                        datetime.datetime.fromisoformat(run["started"][:-1])
                    )

        queue = taskcluster.Queue(taskcluster.optionsFromEnvironment())
        queue.listTaskGroup(task_group_id, paginationHandler=handler)

        r = lambda d: datetime.timedelta(seconds=round(d.total_seconds()))
        for worker_type, t in sorted(timings.items()):
            print("count {}, total {}, max: {}\t{}\t{}".format(
                len(t),
                r(sum(t[1:], start=t[0])),
                r(max(t)),
                worker_type,
                ' '.join(str(r(s)) for s in t),
            ))


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
