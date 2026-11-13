
@echo off
echo Eliminando carpetas __pycache__...

for /d /r "%~dp0.." %%d in (__pycache__) do (
    if exist "%%d" (
        rmdir /s /q "%%d"
        echo Eliminada: %%d
    )
)

echo.
echo Limpieza completada.
pause
