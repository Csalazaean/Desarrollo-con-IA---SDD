# Script de arranque unificado para TaskControl (Principio de Restricciones Técnicas)
$env:FLASK_APP = "src.taskcontrol:create_app()"
$env:FLASK_ENV = "development"
$env:PYTHONPATH = "$PSScriptRoot;$PSScriptRoot\src"

if (Test-Path ".\.venv\Scripts\flask.exe") {
    & ".\.venv\Scripts\flask.exe" run --port 5000
} else {
    flask run --port 5000
}





