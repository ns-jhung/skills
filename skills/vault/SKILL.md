---
name: vault
description: Read and write secrets in HashiCorp Vault. Use when the user wants to read a secret from Vault, write/store a secret to Vault, or work with Vault KV paths in Netskope services. Covers the Go (hashicorp/vault/api) and Python (hvac) patterns used across Netskope repos.
disable-model-invocation: false
allowed-tools: Read Write Edit Grep Glob Bash
---

# Vault read & write

Simple guidance for reading and writing secrets in HashiCorp Vault, matching the
patterns used across Netskope repos (`secretsclient`, `dlp-config-sync`,
`ns-python-ims`, `pki-identity-manager`).

## When to invoke

- User wants to **read** a secret from a Vault path.
- User wants to **write/store** a secret to a Vault path.
- User is wiring a Netskope service to Vault for secrets.

Do **not** invoke for Vault *Agent injection* via Helm annotations
(`vault.injectionEnabled`) — that injects secrets as files and needs no client code.

## Connect

You need a Vault **address** and a **token**. In Netskope services both usually
come from the environment (`VAULT_ADDR`, `VAULT_TOKEN`) or are injected by the
Vault Agent.

### Go (`github.com/hashicorp/vault/api`)

```go
import vault "github.com/hashicorp/vault/api"

config := &vault.Config{Address: vaultAddr}
client, err := vault.NewClient(config)
if err != nil {
    return err
}
client.SetToken(token)
```

### Python (`hvac`)

```python
from hvac import Client

client = Client(url=vault_addr, token=token)
assert client.is_authenticated()
```

## Read a secret

KV v2 stores data one level under `data/`, and the response nests it under
`.Data["data"]` (Go) / `["data"]["data"]` (Python).

### Go

```go
secret, err := client.KVv2("secret").Get(ctx, "myapp/db")
if err != nil {
    return err
}
password := secret.Data["password"].(string)
```

### Python

```python
resp = client.secrets.kv.v2.read_secret_version(
    mount_point="secret", path="myapp/db",
)
password = resp["data"]["data"]["password"]
```

## Write a secret

### Go

```go
data := map[string]interface{}{"password": "s3cr3t"}
_, err := client.KVv2("secret").Put(ctx, "myapp/db", data)
if err != nil {
    return err
}
```

### Python

```python
client.secrets.kv.v2.create_or_update_secret(
    mount_point="secret",
    path="myapp/db",
    secret={"password": "s3cr3t"},
)
```

## Known paths

| Service | Path | Notes |
|---------|------|-------|
| swg-lookup-svc (PDV) | `secrets/generic/global/modules/swg-lookup-svc-pdv/*` | Generic KV secrets for the swg-lookup-svc PDV module |

## Conventions (from Netskope repos)

- **Retry transient failures, not auth/CAS errors.** Use a Fibonacci/exponential
  backoff. Do **not** retry on `403` (permission), `404` (no such path), or
  `check-and-set parameter did not match` — those won't fix themselves.
- **403 = bad token *or* missing RBAC on the path.** On the first `403`, try
  re-authenticating once, then give up — looping on a policy misconfig wastes time.
- **Never log secret values.** Log the path and the operation, never the data.
- **Don't keep plaintext secrets in memory longer than needed.** Sensitive Go
  code (`secretsclient`) uses `memguard` locked buffers and destroys them after use.
- **Use the transit engine for encrypt/decrypt**, not for storing the key — KV is
  for storage, transit is for crypto-as-a-service.

## Reference implementations

| Repo | File | Notes |
|------|------|-------|
| `secretsclient` | `guardedclient.go` | Retry + re-auth wrapper, memguard buffers |
| `dlp-config-sync` | `server/secrets/vaultclientadapter.go` | KV v2 + transit adapter with retry |
| `ns-python-ims` | `nsims/vault/transit_vault.py` | Python transit client with TTL cache |
| `pki-identity-manager` | `src/internal/vault/vault_client.go` | Stale-token auth-error handling |
