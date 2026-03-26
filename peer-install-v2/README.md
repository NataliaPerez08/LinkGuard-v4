
# LinkGuard Peer – Installation Bundle (v2)

Installs:
- wg-auto-register (peer agent)
- wg-auto-cli (local peer CLI)
- orch-cli (read-only orchestration CLI)

## Install
```bash
unzip peer-install-v2.zip
cd peer-install-v2
sudo bash install.sh
```

## Verify
```bash
systemctl status wg-auto-register
wg-auto-cli status
orch-cli health
```


https://linkguard-release.s3.us-east-2.amazonaws.com/Releasev4.zip