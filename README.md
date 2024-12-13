## Guide d'utilisation rapide (Projet GL fait par MOUKTAR HOUSSEN Shams Ryan et Hayat MEGHLAT)

### Activation de l'environnement virtuel pour le développeur(warning : le venv est propre et unique a chaque machine)

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

### Lancement du serveur Flask (sans l'environnement virtuel et avoir installer les dépendances avant)

```
python run.py
```

### Enregistrer les dépendances actuelles (A faire en étant dans un venv uniquement)

```
pip freeze > requirements.txt
```

### Installer les dépendances à partir du fichier(obligatoire a faire si tu as clone le projet)

```
pip install -r requirements.txt
```

### Effectuer l'ensemble des tests unitaires

```
python -m unittest discover -s test
```

# Base de donnée MySQL

création de la base de donnée pour mysql dans init__.sql

Assurez vous d'avoir la dernière version de pip installer et une bdd mysql avec une configuration conforme aux informations stockées dans config.py !

```
python -m pip install --upgrade pip
```

## configuration par défaut entre MySQL et le serveur Flask et lancer le serveur

- le serveur flask et le serveur MySQL doivent etre sur la même machine en local (127.0.0.1)
- Le port MySQL utilisé : 3306
- le serveur flask se connecte en tant que root sur MySQL (config à avoir : user = root, password = root ou modifier config.py en conséquence)
- lancer toute la commande de init__.sql dans la base MySQL afin de creer la database serveur et toute ses tables
- ouvrir un terminal dans le dossier du serveur flask et executer la commande : pip install -r requirements.txt
- pour lancer les test serveur, lancer : python -m unittest discover -s test
- lancer le serveur Flask avec : python run.py