{% set bin = "/opt/local/bin" %}
{% set etc = "/etc/generic-worker" %}
{% set user = "worker" %}
{% set home = "/Users/" + user %}
{% set git_repo_cache = "/var/cache/servo.git" %}

GMT:
  timezone.system

sshkeys:
  ssh_auth.present:
    - user: root
    - names:
    {% for key in pillar.ssh_keys %}
      - {{ key | yaml_encode }}
    {% endfor %}

/etc/sysctl.conf:
  file.managed:
    - source: salt://{{ tpldir }}/etc/sysctl.conf

/etc/profile:
  file.managed:
    - source: salt://{{ tpldir }}/etc/profile

{{ bin }}/generic-worker:
  file.managed:
    - name:
    - source: https://github.com/taskcluster/generic-worker/releases/download/v16.5.5/generic-worker-simple-darwin-amd64
    - source_hash: sha256=d67093e9edd6aa6d868562c761a8e8497a280b1be4ee7a881906f342857ed6d7
    - mode: 755
    - makedirs: True

{{ bin }}/livelog:
  file.managed:
    - source: https://github.com/taskcluster/livelog/releases/download/v1.1.0/livelog-darwin-amd64
    - source_hash: sha256=be5d4b998b208afd802ac6ce6c4d4bbf0fb3816bb039a300626abbc999dfe163
    - mode: 755
    - makedirs: True

{{ bin }}/taskcluster-proxy:
  file.managed:
    - source: https://github.com/taskcluster/taskcluster-proxy/releases/download/v5.1.0/taskcluster-proxy-darwin-amd64
    - source_hash: sha256=3faf524b9c6b9611339510797bf1013d4274e9f03e7c4bd47e9ab5ec8813d3ae
    - mode: 755
    - makedirs: True

{{ user }} group:
  group.present:
    - name: {{ user }}

{{ user }}:
  user.present:
    - home: {{ home }}
    - gid_from_name: True

# `user.present`’s `createhome` is apparently not supported on macOS
{{ home }}:
  file.directory:
    - user: {{ user }}

{{ etc }}/config.json:
  file.serialize:
    - makedirs: True
    - group: {{ user }}
    - mode: 640
    - show_changes: False
    - formatter: json
    - dataset:
        provisionerId: proj-servo
        workerType: {{ pillar.worker_type }}{{ "-disabled-" + grains.id if pillar.disabled else "" }}
        workerGroup: proj-servo
        workerId: {{ grains.id }}
        tasksDir: {{ home }}/tasks
        publicIP: {{ salt.network.ip_addrs()[0] }}
        ed25519SigningKeyLocation: {{ home }}/keypair
        clientId: {{ pillar.credentials.client_id }}
        accessToken: {{ pillar.credentials.access_token }}
        taskclusterProxyExecutable: {{ bin }}/taskcluster-proxy
        taskclusterProxyPort: 8080
        livelogExecutable: {{ bin }}/livelog
        wstAudience: communitytc
        wstServerURL: https://community-websocktunnel.services.mozilla.com
        rootURL: https://community-tc.services.mozilla.com

{{ bin }}/generic-worker new-ed25519-keypair --file {{ home }}/keypair:
  cmd.run:
    - creates: {{ home }}/keypair
    - runas: {{ user }}

/Library/LaunchAgents/net.generic.worker.plist:
  file.absent: []

net.generic.worker:
  file.managed:
    - name: /Library/LaunchDaemons/net.generic.worker.plist
    - mode: 600
    - user: root
    - template: jinja
    - source: salt://generic-worker.plist.jinja
    - context:
      bin: {{ bin }}
      etc: {{ etc }}
      home: {{ home }}
      username: {{ user }}
  service.running:
    - enable: True
    - watch:
      - file: /Library/LaunchDaemons/net.generic.worker.plist

# generic-worker responds to an 'interrupt' signal by gracefully exiting
# after the currently-running task is resolved, if any
pkill -INT generic-worker:
  cmd.wait:
    - require:
      - net.generic.worker
    - watch:
      - file: {{ bin }}/generic-worker
      - file: {{ bin }}/livelog
      - file: {{ bin }}/taskcluster-proxy
      - file: {{ etc }}/config.json

{{ git_repo_cache }}:
  cmd.run:
    - creates: {{ git_repo_cache }}
    - name: >-
        mkdir -p /var/cache &&
        git init --bare {{ git_repo_cache }}

cron_git_fetch:
  cron.present:
    - identifier: cron git fetch
    - minute: 12
    - hour: 8
    - name: >-
        cd {{ git_repo_cache }} &&
        git fetch --no-tags https://github.com/servo/servo master:master &&
        touch cron-fetch-stamp

/usr/local:
  file.directory:
    - user: {{ user }}
    - mode: 755

Homebrew:
  cmd.run:
    - runas: {{ user }}
    - creates: /usr/local/bin/brew
    - require:
        - /usr/local
    - name: >-
        curl -L https://github.com/Homebrew/brew/tarball/master |
            tar xz --strip 1 -C /usr/local &&
        brew update &&
        brew analytics off
