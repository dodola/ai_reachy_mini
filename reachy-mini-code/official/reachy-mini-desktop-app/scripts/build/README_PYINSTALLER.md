# PyInstaller Build Script for Linux

Ce script compile le daemon reachy-mini en un exécutable standalone pour Linux, résolvant les problèmes de bundling AppImage avec les environnements virtuels Python.

## 🎯 Objectif

Remplacer le bundling complexe de venv Python (500+ fichiers) par un seul exécutable autonome compatible avec `linuxdeploy` et le système d'empaquetage AppImage de Tauri.

## 📋 Prérequis

### Système
```bash
sudo apt install python3-dev python3-pip libportaudio2 portaudio19-dev
```

### Repository reachy_mini
Le script attend que le repository `reachy_mini` soit cloné dans `../reachy_mini` (à côté de ce repository).

## 🚀 Usage

### Build Standard (PyPI)
```bash
bash scripts/build/build-daemon-pyinstaller.sh
```

### Build avec Branche GitHub
```bash
REACHY_MINI_SOURCE=develop bash scripts/build/build-daemon-pyinstaller.sh
REACHY_MINI_SOURCE=main bash scripts/build/build-daemon-pyinstaller.sh
```

### Build avec Source Locale
```bash
REACHY_MINI_SOURCE=/path/to/reachy_mini bash scripts/build/build-daemon-pyinstaller.sh
```

### Avec NPM/Yarn
```bash
yarn build:sidecar-linux              # PyPI
yarn build:sidecar-linux:develop      # Branch develop
yarn build:sidecar-linux:main         # Branch main
```

## 🔧 Fonctionnement

### 1. Création d'un venv temporaire
```bash
python3 -m venv /tmp/build-venv
```

### 2. Installation des dépendances
- PyInstaller
- reachy-mini (depuis PyPI, GitHub, ou local)

### 3. Compilation avec PyInstaller
Crée un exécutable standalone qui inclut :
- Python 3.12 embarqué
- Toutes les bibliothèques Python
- Les bibliothèques natives (.so)
- Les fichiers de données nécessaires

### 4. Output
```
src-tauri/binaries/reachy-mini-daemon-x86_64-unknown-linux-gnu
```

Exécutable de ~50-100MB, prêt à être bundlé par Tauri.

## 📦 Comparaison avec l'Ancienne Méthode

| Aspect | Venv (Ancien) | PyInstaller (Nouveau) |
|--------|---------------|----------------------|
| Fichiers créés | 500+ | 1 |
| Taille | ~500MB | ~100MB |
| Chemins hardcodés | ❌ Oui | ✅ Non |
| Compatible linuxdeploy | ❌ Non | ✅ Oui |
| Compatible AppImage | ❌ Non | ✅ Oui |

## 🐛 Troubleshooting

### Erreur : `reachy_mini repository not found`
```bash
# Le script attend ../reachy_mini
cd ..
git clone https://github.com/pollen-robotics/reachy_mini.git
cd reachy_mini_desktop_app
```

### Erreur : `PyInstaller build failed`
```bash
# Vérifier les dépendances système
sudo apt install python3-dev libportaudio2 portaudio19-dev

# Vérifier que Python 3.12 est disponible
python3 --version
```

### Erreur : `Executable test failed`
C'est normal si exécuté hors de l'environnement Tauri. L'exécutable nécessite certaines bibliothèques système qui seront disponibles dans l'AppImage final.

## 🔍 Debugging

### Verbose Mode
```bash
DEBUG=1 bash scripts/build/build-daemon-pyinstaller.sh
```

### Tester l'exécutable
```bash
./src-tauri/binaries/reachy-mini-daemon-* --help
```

### Inspecter les dépendances
```bash
ldd src-tauri/binaries/reachy-mini-daemon-*
```

## 📚 Ressources

- [PyInstaller Documentation](https://pyinstaller.org/)
- [Tauri Sidecar Guide](https://v2.tauri.app/develop/sidecar/)
- [Linux Packaging Strategy](../../docs/LINUX_PACKAGING_STRATEGY.md)

## ✅ Avantages de Cette Approche

1. **Simplicité** : Un seul fichier vs 500+ fichiers
2. **Compatibilité** : linuxdeploy comprend les exécutables standards
3. **Portabilité** : Fonctionne sur toutes les distributions Linux
4. **Maintenabilité** : Configuration Tauri simplifiée (3 lignes vs 10)
5. **Performance** : Build plus rapide, AppImage plus léger

## 🚧 Limitations Connues

- **Taille** : Exécutable plus gros qu'un simple script Python
- **Startup** : Légèrement plus lent (extraction à l'exécution)
- **Build Time** : PyInstaller prend quelques minutes

Ces limitations sont largement compensées par la résolution du problème AppImage et la simplification du workflow de build.
