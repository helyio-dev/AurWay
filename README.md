# 🛡️ AurWay : Anonymous Peer-to-Peer Node

## 🧭 Introduction

**AurWay** est une solution de communication *Peer-to-Peer (P2P)* axée sur l'anonymat et la sécurité.  
Le projet utilise le réseau **T.O.R (The Onion Router)** pour masquer les adresses IP et localisations des participants, garantissant un routage des messages chiffré et anonyme.

Chaque nœud **AurWay** fonctionne comme un **service caché T.O.R**, assurant le chiffrement de bout en bout et la diffusion des messages entre pairs connectés, créant ainsi des salons de discussion décentralisés.

---

## ⚙️ Prérequis

Ce projet est développé en **Python** et nécessite l’exécutable **T.O.R** pour lancer et gérer le service caché.

### 1. Environnement Python et dépendances

AurWay requiert **Python 3.8+**.  
Installez toutes les dépendances via :


> pip install -r requirements.txt


| Librairie | Fonction |
| :--- | :--- |
| **cryptography** | Chiffrement symétrique Fernet des messages de bout en bout. |
| **pysocks** | Routage des connexions via le proxy SOCKS de Tor. |
| **requests** | Gestion des requêtes externes (découverte de salons) via Tor. |
| **stem** | Contrôle et configuration du processus Tor et des Services Cachés. |

### 2. Binaire T.O.R

L’exécutable **T.O.R** est indispensable au fonctionnement d’AurWay.

Il doit être présent dans le répertoire du projet pour être invoqué automatiquement.

#### Structure du projet :
```
AurWay
├── src
│   └── core
│       ├── __init__.py
│       └── peer.py
├── tor
│   ├── pluggable_transport
│   │   ├── conjure-client.exe
│   │   ├── lyrebird.exe
│   │   ├── pt_config.json
│   │   └── README.CONJURE.md
│   ├── geoip
│   ├── geoip6
│   ├── tor-gencert.exe
│   ├── tor.exe
│   └── torrc-defaults
├── LICENSE
├── main.py
├── README.md
└── requirements.txt
```

> 💡 Le script principal est configuré pour rechercher le binaire dans le dossier `tor/`.

---

## 🚀 Démarrage et Connexion

_Le script `main.py` peut fonctionner en plusieurs modes selon l’usage souhaité._

### 1. Créer un salon (mode écoute)

Cette commande démarre votre nœud en mode écoute, crée un service caché T.O.R (adresse `.onion`) et attend les connexions entrantes.

```bash
python main.py <PORT_LOCAL>
```

Une fois lancé, le programme affiche une adresse .onion, par exemple : [+] Peer anonyme prêt. Adresse .onion : abcd1234.onion:6000

Cette adresse peut être partagée à d'autres utilisateurs pour rejoindre votre salon.

### 2. Rejoindre un salon existant
Pour rejoindre un autre nœud, utilisez le mode connexion ciblée en précisant son adresse .onion.

```bash
python main.py <PORT_LOCAL_CLIENT> --target <ADRESSE_ONION_CIBLE>:<PORT_CIBLE>
```


## 🌐 Installation rapide

```
git clone https://github.com/helyio-dev/AurWay.git
cd AurWay
pip install -r requirements.txt
python main.py 9050
```