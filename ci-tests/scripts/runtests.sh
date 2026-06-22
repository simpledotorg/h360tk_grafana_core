## APK
apt-get update
apt-get upgrade
apt-get install -y --no-install-recommends libpq5 allure openjdk-21-jre-headless nodejs npm wget unzip 

wget -q https://github.com/allure-framework/allure2/releases/download/2.30.0/allure-2.30.0.zip -O /tmp/allure.zip
unzip -q /tmp/allure.zip -d /opt/
ln -sf /opt/allure-2.30.0/bin/allure /usr/bin/allure
rm /tmp/allure.zip



## Pip
pip install --upgrade pip
pip install -r /tests/requirements.txt

## Runs the tests
cd /tests/
behave --junit --junit-directory=/target -f allure_behave.formatter:AllureFormatter -o /target/allure-results

allure generate /target/allure-results --clean -o /target/html-report