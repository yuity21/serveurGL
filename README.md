## Guide d'utilisation rapide

### Activation de l'environnement virtuel (toujours l'activer avant de lancer le code ou les test)

**Windows:**
```
venv\Scripts\activate
```

**macOS/Linux**
```
source venv/bin/activate
```

### Désactivation de l'environnement virtuel

```
deactivate
```

### Lancement du serveur Flask

```
python run.py
```

### Enregistrer les dépendances actuelles

```
pip freeze > requirements.txt
```

### Installer les dépendances à partir du fichier

```
pip install -r requirements.txt
```

### Effectuer l'ensemble des tests unitaires

```
python -m unittest discover -s test
```

# Base de donnée

création de la base de donnée pour mysql dans init__.sql

Assurez vous d'avoir la dernière version de pip installer et une bdd mysql avec une configuration conforme aux informations stockées dans config.py !

```
python -m pip install --upgrade pip
```
