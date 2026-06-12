#!/usr/bin/env bash
# build.sh — script exécuté par Render à chaque déploiement

set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

python manage.py creer_admin admin@isj.cm "Admin1234!" --prenom Hermann --nom Ekotto