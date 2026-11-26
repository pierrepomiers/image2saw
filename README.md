# image2saw ╝║╝║╝║

**Creative pixels to soundscape generator.**

Version A. Transforme une image en boucle sonore. Chaque pixel de la zone sélectionnée est une voix ; une fenêtre (une gaussienne) parcourt l'image et fait chanter les pixels qu'elle recouvre.

**Essayer en ligne :** https://pierrepomiers.github.io/image2saw/

La version exacte est affichée en bas de la page (`A · numéro de commit`). L'aide intégrée s'ouvre avec `[ ? ]`, en anglais.

## Principe

- **Teinte → note** : rouge grave, violet aigu. En noir et blanc, c'est la luminosité qui donne la note.
- **Luminosité → volume**, **saturation → durée de résonance**.
- La fenêtre passe par tous les pixels de la sélection. Au-delà des bords, l'image est repliée en miroir pour que le chœur reste complet.
- Les parcours sont fermés et chaque voix fait un nombre entier de cycles : la boucle se referme sans clic.
- La durée se cale sur un tempo et une mesure, pour que les samples tombent sur les temps.

## Utilisation

1. Charger une image avec `[ charger ]`, ou choisir un des trois exemples.
2. Glisser sur l'image pour sélectionner la zone à jouer. Glisser à l'intérieur du cadre le déplace, tirer un coin le redimensionne.
3. `[ lecture ]` pour écouter (la barre d'espace fait de même).
4. Changer les réglages : le son est recalculé à chaque changement, et la ligne sous l'image montre l'avancement. Quand le calcul est long, un aperçu est joué d'abord, puis remplacé par le son complet.
5. `[ wav ]` exporte la boucle en WAV 16 bits stéréo. `[ vidéo ]` filme un tour de boucle : l'image qui ondule, avec le son.

## Réglages

**image**
- `résolution` : nombre de pixels sur le grand côté de la zone, de 1 à 64. Tous sont parcourus : plus il y en a, plus la fenêtre va vite et plus le calcul est long.
- `parcours` : trajet de la fenêtre, choisi avec `<` et `>`.
  - `h-snake`, `v-snake` : serpentin qui passe une fois par chaque pixel, par lignes ou par colonnes.
  - `aller-retour` : serpentin à l'aller, même chemin au retour.
  - `spirale` : vers le centre, puis retour.
  - `chaos` : chemin tiré au hasard, de voisin en voisin, qui passe quand même une fois par chaque pixel avant de boucler. `[ autre ]` tire un autre chemin.

**gaussienne**
- `largeur` : taille de la fenêtre, en proportion de la zone. Vers 50 %, presque tous les pixels chantent en même temps.
- `résonance` : temps pendant lequel une voix sonne encore après le passage de la fenêtre.
- `influence` : poids de l'image sur la largeur et la résonance. Zone unie : fenêtre plus large. Zone chargée : plus étroite. Couleur vive : résonance plus longue.

**son**
- `onde` : sinus, triangle, scie ou carré.
- `grave`, `aigu` : note la plus basse et la plus haute. Les curseurs avancent par demi-tons de C0 à B6 et affichent le nom de la note. Une valeur en hertz tapée à la main reste libre (par exemple 5 pour des grondements).
- `échelle` : répartition des notes entre ces deux limites, linéaire (plus claire) ou log (régulière en octaves, plus sombre).
- `accord` : notes libres, ou ramenées sur la gamme chromatique ou pentatonique.
- `stéréo` : largeur de la scène. La gauche de l'image sonne à gauche.

**égaliseur**
- Sept curseurs verticaux de −15 à +15 dB, resserrés dans le grave : sous 30 Hz, 60, 120, 250, 500 Hz, 2 kHz, au-dessus de 8 kHz.
- Le niveau d'ensemble est maintenu et ne sature jamais. `[ plat ]` remet tout à 0 dB.
- L'export WAV et la vidéo reçoivent les mêmes filtres que l'écoute.

**temps**
- `mesure`, `mesures`, `tempo` : durée de la boucle en mesures (3/4, 4/4, 5/4, 6/8, 7/8). Un tempo plus lent donne une boucle plus longue.
- `durée` : durée en secondes, quand la mesure est sur `libre`.

**image animée**
- `wobble` : force de l'ondulation de l'image pendant la lecture, jusqu'à 200 %. Elle suit le volume et la hauteur réels du son.

**réglages**
- `[ sauver ]`, `[ ouvrir ]`, `[ défauts ]` : enregistrer les réglages dans un fichier `.json`, en recharger un, ou revenir aux valeurs de départ.

## Technique

Tout tient dans un seul fichier, `index.html`, sans dépendance ni serveur : le son est calculé dans le navigateur, réparti sur plusieurs fils de calcul. La vidéo est enregistrée en temps réel, il faut garder la page affichée.

## État du projet

Prototype. Restent à faire : l'enchaînement des samples avec fondus, puis le portage en plugin audio.

Cette version A repart de zéro : le code n'a plus rien de commun avec les versions Python précédentes (v2.x), qui généraient un WAV en ligne de commande à partir d'oscillateurs séquencés.

## Auteur

Pierre Pomiers — projet *Image to Sound*, exploration des liens entre vision, vibration et matière sonore.

Licence MIT.
