## APK
apt-get update
apt-get upgrade
apt-get install -y --no-install-recommends libpq5 allure 

## Pip
pip install --upgrade pip
pip install -r /tests/requirements.txt

## Runs the tests
cd /tests/
behave --junit --junit-directory=/target -f allure_behave.formatter:AllureFormatter -o /target/allure-results

allure generate /target/allure-results --clean -o /target/html-report

