@echo off
echo ========================================
echo   INSTALL CHROMEDRIVER - WINDOWS
echo ========================================
echo.

REM Get Chrome version
for /f "tokens=2 delims==" %%i in ('wmic datafile where name^="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" get Version /value') do set CHROME_VERSION=%%i

echo Chrome version: %CHROME_VERSION%

REM Create drivers folder
if not exist "drivers" mkdir drivers

echo.
echo Đang tải ChromeDriver phù hợp...
echo.

REM Download using Python
python -c "import urllib.request, zipfile, os, re; ver = '%CHROME_VERSION%'.split('.')[0]; url = f'https://storage.googleapis.com/chrome-for-testing-public/{ver}.0.6723.92/win64/chromedriver-win64.zip' if int(ver) ^>= 115 else f'https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{ver}'; print(f'Downloading ChromeDriver for Chrome {ver}...'); response = urllib.request.urlopen('https://googlechromelabs.github.io/chrome-for-testing/latest-versions-per-milestone.json'); import json; data = json.loads(response.read()); download_url = data['milestones'][ver]['downloads']['chromedriver'][2]['url']; urllib.request.urlretrieve(download_url, 'drivers/chromedriver.zip'); zip_ref = zipfile.ZipFile('drivers/chromedriver.zip', 'r'); zip_ref.extractall('drivers/'); zip_ref.close(); os.remove('drivers/chromedriver.zip'); print('ChromeDriver installed successfully!')"

echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
pause
