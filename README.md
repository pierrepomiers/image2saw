# image2saw ╝║╝║╝║

**Creative pixels to soundscape generator.**

Version A. Transforme une image en boucle sonore. Chaque pixel de la zone sélectionnée est une voix ; une fenêtre (une gaussienne) parcourt l'image et fait chanter les pixels qu'elle recouvre.

**Essayer en ligne :** https://pierrepomiers.github.io/image2saw/

*English speakers: the page and its built-in help `[ ? ]` are available in English. It follows your device language; you can switch under settings → language.*

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
3. Les trois signes dans le coin bas gauche de l'image : `[ ▶ ]` lance l'écoute (il devient `[ ▮▮ ]` pour mettre en pause ; la barre d'espace fait de même), `[ .wav ]` exporte, `[ ● ]` filme, `[ 1:1 ]` filme au format carré.
4. Changer les réglages : le son est recalculé à chaque changement, et la ligne sous l'image montre l'avancement. Quand le calcul est long, un aperçu est joué d'abord, puis remplacé par le son complet.
5. `[ .wav ]` exporte la boucle en WAV 16 bits stéréo. `[ ● ]` filme un tour de boucle, l'image qui ondule avec le son ; il passe au rouge pendant l'enregistrement, et un nouvel appui annule. `[ 1:1 ]` fait de même dans un carré de 1080 × 1080, pour les réseaux qui l'attendent. Si la sélection n'est pas carrée, elle est d'abord ramenée au carré de son petit côté, centré ; le son est recalculé pour elle, puis l'enregistrement démarre tout seul.

## Réglages

Sur un téléphone tenu debout, les sections de réglages sont des pages côte à côte : on les feuillette en glissant de côté, ou en touchant leur nom sous l'image.

**source**
- `[ caméra ]` : joue en direct l'image de la caméra du téléphone ou de l'ordinateur à la place d'une image fixe. On bouge la caméra, le son suit aussitôt. `[ retourner ]` passe de la caméra arrière à la caméra avant. `[ figer ]` garde l'image du moment et revient au mode normal, où les boucles s'exportent. Tant que la caméra tourne, ce qui demande une boucle figée est grisé : toute la section drum (`rythme`, `doom`) et les signes d'export ; tous les autres réglages agissent de la même façon. Choisir une image d'exemple ou en charger une quitte aussi la caméra. Le son en direct est tenu au même niveau que la boucle figée. La caméra ne fonctionne que si la page est ouverte dans un navigateur (Safari, Chrome), pas à l'intérieur de Claude.
- `zoom` : avec la caméra, grossit jusqu'à 8×. Le zoom de l'objectif est utilisé quand le navigateur y donne accès ; au-delà, ou sans lui, l'image est recadrée autour de son centre.
- `images/s` : avec la caméra, nombre de rafraîchissements du son et de l'image par seconde, de 1 à 30. Une valeur basse donne un résultat saccadé, stroboscopique.
- `résolution` : nombre de pixels sur le grand côté de la zone, de 1 à 64. Tous sont parcourus : plus il y en a, plus la fenêtre va vite et plus le calcul est long. Avec la caméra, elle est plafonnée à 32.
- `parcours` : trajet de la fenêtre, choisi avec `<` et `>`.
  - `h-snake`, `v-snake` : serpentin qui passe une fois par chaque pixel, par lignes ou par colonnes.
  - `aller-retour` : serpentin à l'aller, même chemin au retour.
  - `spirale` : vers le centre, puis retour.
  - `chaos` : chemin tiré au hasard, de voisin en voisin, qui passe quand même une fois par chaque pixel avant de boucler. `[ autre ]` tire un autre chemin.

**fonction**
- `largeur` : taille de la fenêtre, en proportion de la zone. Vers 50 %, presque tous les pixels chantent en même temps.
- `résonance` : temps pendant lequel une voix sonne encore après le passage de la fenêtre.
- `influence` : poids de l'image sur la largeur et la résonance. Zone unie : fenêtre plus large. Zone chargée : plus étroite. Couleur vive : résonance plus longue.
- `relief` : casse le défilement régulier. La fenêtre roule sur l'image comme une bille sur des montagnes russes, où la hauteur du terrain est la hauteur de note des pixels : monter vers les notes aiguës lui coûte de la vitesse, en descente elle accélère. Deux choses suivent sa vitesse. La fenêtre respire : lente sur un point haut, elle se resserre sur quelques pixels et des notes isolées ressortent ; lancée, elle s'ouvre en nappe. Les notes glissent : elles montent quand la bille accélère et redescendent quand elle ralentit. À 0 elle avance à pas régulier ; à 100 % elle est cent fois plus lente sur la note la plus haute que sur la plus basse. La boucle garde sa durée et se referme sans clic. Avec la caméra, le terrain suit l'image en direct.
- `silence` : part de la boucle, de 0 à 90 %, pendant laquelle la fenêtre ne touche plus rien : cela tombe sur les notes les plus graves de son trajet, là où la bille du `relief` va le plus vite. Seules les résonances restent : c'est `résonance` qui décide si ces trous sont nets ou habités. Agit avec ou sans relief.

**son**
- `onde` : sinus, triangle, scie ou carré. La pointe de la scie est légèrement arrondie, pour garder son mordant sans les aigus stridents.
- `grave`, `aigu` : note la plus basse et la plus haute. Les curseurs avancent par demi-tons de C0 à B6 et affichent le nom de la note. Une valeur en hertz tapée à la main reste libre (par exemple 5 pour des grondements).
- `échelle` : répartition des notes entre ces deux limites, linéaire (plus claire) ou log (régulière en octaves, plus sombre).
- `accord` : notes libres, ou ramenées sur la gamme chromatique ou pentatonique.
- `stéréo` : largeur de la scène. La gauche de l'image sonne à gauche.

**death**
- `death` : distorsion du son des pixels, de 0 (coupée) à 12. Le rythme a la sienne, `doom`. Le grave profond reste propre ; tout le reste passe par une saturation « à lampe », puis à partir de 6 par un étage qui replie l'onde sur elle-même, puis par un filtre de baffle et un compresseur lourd. Plus la valeur monte, plus le son est épais et déchiré.
- Elle agit avant l'égaliseur, et le niveau d'ensemble reste maîtrisé. La ligne rougit et tremble en approchant de 12.

**drum**
- `rythme` : ligne de basse optionnelle, coupée à 0. Le réglage est son volume, ajouté par-dessus le son principal ; quand le total saturerait, l'ensemble est baissé d'un bloc, si bien qu'aux valeurs hautes la basse passe devant. Un motif rythmique est lu dans l'image : on suit une ligne de pixels, un pixel par double croche ; les pas où l'image change le plus sont frappés, et la couleur du pixel choisit la note, comparée aux autres pixels de cette ligne : même une image d'une seule teinte donne une petite mélodie. C'est une basse « sub » accordée d'après `grave`, qui boucle exactement avec le son principal et part dans les exports. Ses harmoniques nourrissent `doom`. Pendant la lecture, chaque pixel frappé s'allume sur l'image et reste marqué jusqu'à la fin de la mesure. Dans l'image animée, donc dans la vidéo exportée, chaque pixel frappé gonfle aussi le temps de sa frappe, par-dessus l'onde (il suit `wobble`). `[ autre rythme ]` lit l'image autrement et donne un autre motif. Grisé en mode caméra, où elle ne joue pas.
- `doom` : distorsion du rythme seul, de 0 à 12. Une cousine de `death` faite pour la basse : chaque note est saturée à la source, à force constante, si bien que son grain reste le même du début à la fin pendant qu'elle s'éteint naturellement. Les deux sont indépendantes.

**EQ** (égaliseur)
- Sept curseurs verticaux, un par octave, de −12 à +12 dB avec une graduation tous les 6 dB : sous 30 Hz, puis 60, 120, 250, 500 Hz et 1 kHz, enfin tout ce qui est au-dessus de 2 kHz.
- Avec les curseurs, les notes s'arrêtent à B6, un peu moins de 2 kHz ; seule une valeur tapée à la main peut monter plus haut. Le dernier curseur règle donc surtout les harmoniques, qui donnent leur brillance à la scie et au carré ; il est presque sans effet sur le sinus.
- Le niveau d'ensemble est maintenu et ne sature jamais. `[ plat ]` remet tout à 0 dB.
- L'export WAV et la vidéo reçoivent les mêmes filtres que l'écoute.

**temps**
- `mesure`, `mesures`, `tempo` : durée de la boucle en mesures (3/4, 4/4, 5/4, 6/8, 7/8). Un tempo plus lent donne une boucle plus longue.
- `durée` : durée en secondes, quand la mesure est sur `libre`. D'une demi-seconde à 60 s, la durée d'une story Instagram ; une longue boucle demande plus de temps de calcul et d'export.

**animation**
- `wobble` : force de l'ondulation de l'image pendant la lecture, jusqu'à 200 %. Elle suit le volume et la hauteur réels du son.

**réglages**
- `[ sauver ]`, `[ ouvrir ]`, `[ défauts ]` : enregistrer les réglages dans un fichier `.json`, en recharger un, ou revenir aux valeurs de départ.
- `langue` : affiche la page et son aide `[ ? ]` en français ou en anglais (`english`). Par défaut, la page suit la langue de l'appareil.

## Technique

Tout tient dans un seul fichier, `index.html`, sans dépendance ni serveur : le son est calculé dans le navigateur, réparti sur plusieurs fils de calcul. Avec la caméra, un second moteur fabrique le son en direct, voix par voix, sans passer par une boucle calculée. La vidéo est enregistrée en temps réel, il faut garder la page affichée.

## État du projet

Prototype. Restent à faire : l'enchaînement des samples avec fondus, puis le portage en plugin audio.

Cette version A repart de zéro : le code n'a plus rien de commun avec les versions Python précédentes (v2.x), qui généraient un WAV en ligne de commande à partir d'oscillateurs séquencés.

## Auteur

Pierre Pomiers — projet *Image to Sound*, exploration des liens entre vision, vibration et matière sonore.

© 2026 Pierre Pomiers. Licence MIT : voir le fichier `LICENSE`.
