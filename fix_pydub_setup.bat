@echo off
REM Fix pydub installation and verify in virtual environment

echo [1/3] Activating virtual environment...
call venv\Scripts\activate

echo [2/3] Installing pydub and upgrading pip...
pip install --upgrade pip
pip install pydub

echo [3/3] Verifying pydub installation...
python -c "from pydub import AudioSegment; print('✅ pydub is working!')"

echo All done! If you see 'pydub is working', you're good to go.
pause
