## APK
apt-get update
apt-get upgrade
apt-get install -y --no-install-recommends libpq5

## Pip
pip install -r /tests/requirements.txt

## Runs the tests
cd /tests/
behave
