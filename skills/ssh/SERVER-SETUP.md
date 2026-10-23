# Server setup

`SKILL.md` rules are the soft layer. The **boundary** is the server account the
wrapper logs in as: size it so a run that ignored every rule could still only
read. Every step below needs root, so each one is a privilege handoff: give the
user the exact command, ask for output and exit status, and check it against
the expected result before moving on.

Done when every **Verify** line has user-returned output matching its expected
result.

## Account

Create one dedicated account per agent and project, e.g. `agent`:

```sh
useradd --create-home --shell /bin/bash agent
```

Grant read access narrowly: `adm` or `systemd-journal` group for logs, and
`setfacl -R -m u:agent:rX <app-dir>` for application files. Keep secrets
(`.env`, keys, credentials) owner-only so the account cannot read them.

**Verify:**

- `sudo -l -U agent` → `User agent is not allowed to run sudo`.
- `id agent` → no `sudo`, `wheel`, `admin`, `docker`, `lxd`, `libvirt`, or
  `disk` group (each is root-equivalent).

## Key

Generate a fresh key for this account only, on the user's machine:

```sh
ssh-keygen -t ed25519 -f ~/.ssh/agent_<project> -C agent@<project>
```

Install its public key in `~agent/.ssh/authorized_keys` with options:

```
restrict,from="<user public IP or CIDR>" ssh-ed25519 AAAA... agent@<project>
```

`restrict` disables forwarding, PTY, X11, and `~/.ssh/rc`; `from=` limits
source addresses. Point `.env` `SSH_USERNAME` and `SSH_PRIVATE_KEY_PATH` at this
account and key.

**Verify:** `ssh -i ~/.ssh/agent_<project> -t agent@<host> true` →
`PTY allocation request failed`.

## Host key pin

The wrapper connects only to pinned hosts. Fetch the fingerprint over a trusted
channel (provider console, or on the server):

```sh
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Then on the user's machine, scan and compare:

```sh
ssh-keyscan -t ed25519 -p <port> <host> > /tmp/hostkey && ssh-keygen -lf /tmp/hostkey
```

Matching fingerprints → append `/tmp/hostkey` to `~/.ssh/known_hosts`, or to a
project file named by `.env` `SSH_KNOWN_HOSTS_PATH` (host keys are public; the
file can be committed so the whole team shares the pin).

**Verify:** wrapper smoke exits 0.

## Stronger options

Offer these when the user wants more than the baseline:

- **Short-lived certificates** (Vault SSH CA, Smallstep, Teleport, Tailscale
  SSH) replace the static key with credentials that expire within hours.
- **Forced-command allowlist**: `command="/usr/local/bin/agent-shell"` in
  `authorized_keys`, dispatching `$SSH_ORIGINAL_COMMAND` against fixed
  operations. Strongest boundary, but it narrows Browse and Debug to the
  allowlist.
- **Audit**: record every command the account runs:

  ```sh
  echo "-a always,exit -F arch=b64 -S execve -F auid=$(id -u agent) -k agent" \
    > /etc/audit/rules.d/agent.rules && augenrules --load
  ```
