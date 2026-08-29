# Incident Report: incident01

## Assessment
The evidence supports a high-severity malicious compromise of `web01` (`10.10.10.15`). An external source, `185.199.110.47`, conducted SSH password guessing against invalid `admin`, `root`, and `deploy` accounts, then successfully authenticated as `deploy` at 09:41:31Z. The same source performed web reconnaissance against administrative and common application paths.

After the successful login, `deploy` opened a session and used `sudo` to execute reconnaissance commands including `id`, `uname -a`, and `cat /etc/passwd`. The account then ran Python socket code, downloaded an update-looking payload with curl, made `/tmp/.cache_update` executable, and executed it. The payload subsequently ran as `root` and used `--connect`. DNS and firewall records correlate outbound connections from the host to `203.0.113.77` and `198.51.100.24` over HTTPS. A later root-owned `nc` attempted to connect to `192.0.2.55:4444`; both recorded attempts were denied by the firewall. These events are consistent with credential compromise, payload execution, privilege escalation through sudo, and attempted command-and-control or reverse-shell activity.

The later accepted public-key login for `deploy` from internal address `10.10.10.15` is consistent with local access or an administrative session, but it does not explain the preceding external login and payload chain. The evidence does not establish persistence or whether the HTTPS destinations delivered additional content. The external addresses shown are documentation/test-range addresses in this evidence, so their maliciousness is based on observed behavior rather than reputation.

## Response actions
- Blocked `185.199.110.47` through CyberBroker: **executed**.
- Blocked process `/tmp/.cache_update` on `web01` through CyberBroker: **executed**.
- Blocked TCP port `4444` through CyberBroker: **executed**.
- Blocked account `deploy` through CyberBroker: **executed**.
- Requested quarantine of `/tmp/.cache_update`: **denied** by CyberBroker because the path was outside the allowed scope. No alternative execution path was used.

## Recommended follow-up
Preserve and examine host, shell, sudo, SSH-key, and application evidence; rotate or replace the `deploy` credentials and keys; inspect root authorization and persistence locations; determine what was retrieved from the HTTPS destinations; and perform a full host rebuild or trusted reimage if integrity cannot be established. Validate that the malicious process has terminated and review adjacent systems for reuse of the compromised credentials.
