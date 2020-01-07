#!/usr/bin/env python

import os
import datetime
import signal
import subprocess
import sys
import time


def main(argv0, sig=None):
    if sig:
        sig = {"sigterm": signal.SIGTERM, "sigkill": signal.SIGKILL}[sig.lower()]
    count = 0
    for line in subprocess.check_output(["ps", "-eo", "pid,comm"]).splitlines():
        pid, path = line.split(None, 1)
        if path.startswith("/Users/worker/tasks/") and not os.path.exists(path):
            count += 1
            line = subprocess.check_output(["ps", "-o", "%cpu,lstart", "-p", pid]).splitlines()[1]
            cpu, start_date = line.split(None, 1)
            duration = time.time() - time.mktime(time.strptime(start_date.strip(), "%c"))
            duration = datetime.timedelta(seconds=int(duration))
            print("pid {} {}, {}% CPU, running for {}".format(pid, path, cpu, duration))
            if sig:
                os.kill(int(pid), sig)
    if sig:
        print("Killed {} processes".format(count))
    elif count:
        print("Use `{0} sigterm` or `{0} sigkill` to kill these {1} processes".format(argv0, count))


if __name__ == "__main__":
    main(*sys.argv)
