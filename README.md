# RaidPresence Reporter v0.1.1

Application Windows/Python qui :

1. lit le fichier `RaidPresence.lua` de l'addon ;
2. filtre une période mensuelle, une quinzaine ou des dates libres ;
3. exclut les sessions temporaires de donjon par défaut ;
4. calcule la présence par main et par boss ;
5. récupère expérimentalement les données publiques UwULogs ;
6. détermine le personnage ayant les meilleurs points/parses pour chaque main ;
7. génère un fichier Excel avec les feuilles :
   - Tableau de bord
   - Présences
   - Boss
   - Historique
   - Parses UwULogs
   - Personnages

## Installation

Windows 10/11, Python 3.10 ou plus récent.

```bat
install.bat
run.bat
```

## Utilisation

1. Sélectionner `WTF\Account\<COMPTE>\SavedVariables\RaidPresence.lua`.
2. Choisir le serveur UwULogs, par exemple `Lordaeron`, `Icecrown` ou le nom exact affiché par UwULogs.
3. Choisir la période.
4. Cliquer sur **Générer Excel**.

Le connecteur UwULogs utilise l'endpoint public de données de personnage. Comme ce service n'est pas documenté comme une API stable, l'application continue à générer le rapport si UwULogs est indisponible.

## Import manuel UwULogs

Le fichier CSV facultatif doit contenir :

```csv
main,character,spec,overall_points,overall_rank,best_parse,source_url
Kromautisme,Kromallumer,Fire,94.8,12,99,https://uwu-logs.xyz/character?...
```

Le CSV manuel est prioritaire sur les données téléchargées.

## Création d'un EXE

```bat
build_exe.bat
```

Le programme sera placé dans `dist\RaidPresenceReporter.exe`.


## EXE automatique par GitHub

Consulte `GITHUB_INSTALLATION.md`. Le workflow `.github/workflows/build-windows.yml` compile l'EXE sur `windows-latest` et le joint automatiquement aux Releases créées avec un tag `v*`.


## Modifications v0.1.1

- Normalisation des valeurs UwULogs : `8934.187...` devient `89.3`.
- Affichage des parses avec une décimale dans Excel.
- Les statistiques de présence utilisent désormais les NPC ID uniques.
- Un joueur présent plusieurs fois sur le même NPC ID n'est compté qu'une fois pour cet ID.
- La feuille `Boss` est remplacée par `NPC ID`, avec une ligne par identifiant unique.
- La feuille `Historique` conserve toujours le détail de tous les kills et présences.


## Règles v0.1.2

- La présence est calculée par ID ICC complète, pas par boss.
- Toravon, Halion, Anub’arak et Valithria sont toujours ignorés pour le calcul du meilleur personnage UwULogs.
