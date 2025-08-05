@echo off
echo Setting permissions for uploads directory...
icacls "static\uploads" /grant "IUSR":(OI)(CI)M
icacls "static\uploads" /grant "IIS_IUSRS":(OI)(CI)M
icacls "static\uploads" /grant "NETWORK SERVICE":(OI)(CI)M
echo Done!
pause
