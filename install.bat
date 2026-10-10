@echo off
echo ============================================
echo   ARIA - Installing Dependencies
echo ============================================
echo.

pip install customtkinter==5.2.2
pip install requests==2.31.0
pip install SpeechRecognition==3.10.0
pip install pyttsx3==2.90
pip install psutil==5.9.8
pip install Pillow==10.3.0

echo.
echo Trying to install PyAudio (for voice input)...
pip install pyaudio==0.2.14
IF ERRORLEVEL 1 (
    echo PyAudio failed. Trying pipwin fallback...
    pip install pipwin
    pipwin install pyaudio
)

echo.
echo ============================================
echo   All dependencies installed!
echo   Run: python main.py
echo ============================================
pause
