
# LinkGuard Orchestrator – Installation Bundle (v2)

Installs:
- orchestrator (control plane)
- hub-agent (WireGuard privileged helper)
- orch-cli (administrator CLI)

## Install
```bash
unzip orchestrator-install-v2.zip
cd orchestrator-install-v2
sudo bash install.sh
```

## Verify
```bash
systemctl status orchestrator
systemctl status hub-agent
orch-cli health
```
