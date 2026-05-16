# Raspberry Pi setup

Raspberry Pi OS may reject direct `pip install` commands with an
`externally-managed-environment` error. Use a virtual environment instead.

The `--system-site-packages` option is important because camera and GPIO
packages are often installed by Raspberry Pi OS outside of `pip`.

```bash
cd /path/to/this/project

python3 -m venv --system-site-packages .venv
. .venv/bin/activate

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

Then run the scan from the same activated environment:

```bash
. .venv/bin/activate

python3 tray_scan_cycle.py \
  --tapo-host 192.168.1.50 \
  --tapo-username your_tapo_email \
  --tapo-password your_tapo_password \
  --collection-start-date 2026-05-16
```

If you already know what you are doing and want to install into system Python
anyway, `pip` also offers `--break-system-packages`, but the virtual
environment above is the safer option.
