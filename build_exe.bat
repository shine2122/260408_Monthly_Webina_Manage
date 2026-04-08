@echo off
chcp 65001 > nul
echo ============================================
echo  크리AI티브 웨비나 자동화 EXE 빌드 시작
echo ============================================
echo.

pip install -r requirements.txt
if errorlevel 1 (
    echo [오류] pip install 실패. 종료합니다.
    pause
    exit /b 1
)

echo.
echo [빌드 중] PyInstaller 실행...
pyinstaller --onefile --windowed --name "웨비나자동화" ^
  --add-data "templates;templates" ^
  --add-data "config.json;." ^
  main.py

if errorlevel 1 (
    echo [오류] 빌드 실패. 위 오류 메시지를 확인하세요.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  빌드 완료!
echo ============================================
echo.
echo  실행 파일: dist\웨비나자동화.exe
echo.
echo  배포 시 아래 파일을 같은 폴더에 함께 전달하세요:
echo    - dist\웨비나자동화.exe
echo    - dashboard.html
echo    - templates\ 폴더 전체
echo    - config.json  (API 키 입력란 포함)
echo    - logs\        폴더 (없으면 자동 생성됨)
echo.
pause
