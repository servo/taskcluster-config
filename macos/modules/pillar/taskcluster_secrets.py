# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import taskcluster


def ext_pillar(_minion_id, _pillar, *_args):
    secrets = taskcluster.Secrets(taskcluster.optionsFromEnvironment())
    result = secrets.get("project/servo/tc-client/worker/macos/1")
    return result["secret"]
