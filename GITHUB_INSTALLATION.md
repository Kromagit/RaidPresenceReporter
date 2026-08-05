# Publication automatique sur GitHub

Ce dépôt compile automatiquement `RaidPresenceReporter.exe` sur un ordinateur Windows hébergé par GitHub Actions.

## Première mise en ligne

1. Crée un nouveau dépôt GitHub vide nommé `RaidPresenceReporter`.
2. Décompresse ce ZIP.
3. Dans GitHub, utilise **Add file > Upload files**.
4. Dépose tout le contenu du dossier, y compris le dossier caché `.github`.
5. Valide avec **Commit changes**.

## Télécharger un EXE de test

1. Ouvre l'onglet **Actions** du dépôt.
2. Sélectionne **Build Windows EXE**.
3. Clique sur **Run workflow**.
4. Quand le workflow est terminé, ouvre son résultat.
5. Télécharge l'artefact `RaidPresenceReporter-Windows`.

L'artefact contient l'EXE et un ZIP Windows. GitHub permet de stocker et télécharger ces artefacts depuis le résultat du workflow.

## Publier une version dans Releases

Dans le dépôt GitHub :

1. Ouvre **Releases**.
2. Clique sur **Draft a new release**.
3. Crée un nouveau tag, par exemple `v0.1.0`.
4. Publie la Release.

La création du tag déclenche automatiquement la compilation. Le workflow ajoute ensuite :

- `RaidPresenceReporter.exe`
- `RaidPresenceReporter-Windows.zip`

à la Release correspondant au tag.

## Mise à jour suivante

Pour une nouvelle version, modifie les fichiers puis publie un nouveau tag :

- `v0.1.1`
- `v0.2.0`
- `v1.0.0`

## Important

Windows peut afficher un avertissement SmartScreen car l'EXE n'est pas signé numériquement. Cela ne signifie pas nécessairement qu'il est dangereux ; la signature de code nécessite un certificat payant.
