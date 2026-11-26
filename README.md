# image2saw ╝║╝║╝║

**Pixels to soundscape patterns.**

Version A. Transforme une image en boucle sonore. Chaque pixel de la zone sélectionnée est une voix ; une gaussienne parcourt l'image et fait chanter les pixels qu'elle recouvre.

**Essayer en ligne :** https://pierrepomiers.github.io/image2saw/

## Principe

- **Teinte → note** (rouge grave, violet aigu). En noir et blanc, c'est la luminosité qui donne la note.
- **Luminosité → volume**, **saturation → résonance**.
- La gaussienne passe par tous les pixels de la sélection. Au-delà des bords, l'image est repliée en miroir pour que le chœur reste complet.
- Les parcours sont fermés et chaque voix fait un nombre entier de cycles : la boucle se referme sans clic.
- La durée se cale sur un tempo et une mesure (3/4, 4/4, 5/4, 6/8, 7/8) pour que les samples tombent sur les temps.

## Utilisation

1. Charger une image (ou choisir un des trois exemples).
2. Glisser sur l'image pour sélectionner la zone à jouer.
3. Régler le parcours, la gaussienne, le son et le temps avec les sliders ou en tapant les valeurs.
4. Écouter, puis exporter la boucle en WAV 16 bits stéréo, ou en vidéo (l'image qui ondule avec le son).
5. Sauver les réglages dans un fichier `.json` pour les retrouver ou les partager.

Tout tient dans un seul fichier, `index.html`, sans dépendance ni serveur : le son est calculé dans le navigateur.

## État du projet

Prototype. Restent à faire : l'enchaînement des samples avec fondus, puis le portage en plugin audio.

Cette version A repart de zéro : le code n'a plus rien de commun avec les versions Python précédentes (v2.x), qui généraient un WAV en ligne de commande à partir d'oscillateurs séquencés.

## Auteur

Pierre Pomiers — projet *Image to Sound*, exploration des liens entre vision, vibration et matière sonore.

Licence MIT.
