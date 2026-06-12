#!/usr/bin/env bash
# build.sh â€” script exÃ©cutÃ© par Render Ã  chaque dÃ©ploiement

set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# python manage.py creer_admin admin@isj.cm "Admin1234!" --prenom Hermann --nom Ekotto