Exact : **voices** et **step_ms** ne peuvent PAS être complètement indépendants *si on veut garantir la durée exacte* définie par `--duration-s`.

Mais attention :
👉 Le modèle actuel fait un choix très clair :
**on considère que `voices` et `step_ms` SONT des paramètres artistiques fixes, et que c’est la TAILLE de l’image audio qui s’ajuste pour obtenir la durée.**

C’est cohérent, mais ça a des implications.

Je t’explique précisément.

---

# 🧠 1. La formule “vraie” de la durée dans Image2Saw

La durée totale est (simplifiée) :

[
\text{duration} = \frac{N_columns}{\text{voices}} \times \text{step_ms} ; + ; \text{sustain_s}
]

Donc :

* Si **voices ↑**, durée ↓ (à taille fixe)
* Si **step_ms ↑**, durée ↑ (à taille fixe)
* Et inversement.

Donc **si tu fixes voices et step_ms**, alors la seule variable qui peut être ajustée pour atteindre une durée donnée est **N_columns**, c’est-à-dire la **largeur de l’image audio**.

Ce que fait déjà le moteur v3.2.

---

# 🎯 2. Trois stratégies possibles dans un système comme le tien

Il existe **3 philosophies** pour gérer “duration_s”.

## **Stratégie A — actuelle**

👉 *Duration définit la taille de l'image, et `voices` + `step_ms` sont stables (artistiques).*
C’est ce que fait **v3.2**.

* **Avantages :**

  * Le mood reste stable (step / voices = caractère sonore constant).
  * Très prévisible en live.
  * La vidéo garde la même “vitesse de balayage” d’un preset à l’autre.

* **Inconvénient :**

  * La taille de l’image audio change → résolution sonore variable selon duration.

C’est américain et simple : *“Duration means how long you want. I’ll stretch the image for you.”*

---

## **Stratégie B — duration fixe la vitesse (step_ms)**

Ici :

* **N_columns** reste = taille de l’image choisie par l’artiste
* `voices` reste fixe
* **step_ms = calculé automatiquement** pour respecter la durée

Ça donnerait :

[
\text{step_ms} = \frac{(\text{duration} - \text{sustain}) \times \text{voices}}{N_columns}
]

### Mood impacté :

* step_ms devient entièrement dépendant de la durée.
* Donc ton preset “movement” devient **inutile**, car `movement` n’a plus le droit de modifier step_ms (sinon tu casses la durée).

---

## **Stratégie C — duration fixe les voices**

Symétrique de B :

* step_ms stable (ton mood)
* N_columns fixe
* voices recalculées automatiquement

Mais ce serait très étrange artistiquement :
→ nombre de voices = proportionnel à la durée.

Ça casse la cohérence sonore.

---

# ⭐ Conclusion : le meilleur choix artistique = **Stratégie A**

C’est exactement ce que fait v3.2 :
👉 **voices** et **step_ms** sont des potards artistiques **100% libres**
👉 et c’est **N_columns** (la taille audio) qui s’ajuste automatiquement pour atteindre la durée.

Ça veut dire :

> “Tu choisis l'intensité (voices) et la vitesse (step_ms),
> je m’occupe d’étirer ou compacter l’image pour que ça fasse la durée que tu veux.”

C’est exactement le workflow d’un synthétiseur granulaire ou spectral moderne.

---

# 🧪 Test : valeur extrême

Si tu veux une durée longue avec :

* `step_ms = 10`
* `voices = 5`

→ l’image audio deviendra *très large*.
→ Ce n’est pas un bug : c’est logique dans ce modèle.

---

# 🧩 Donc pour répondre à ta question :

> **“Voices et step_ms ne peuvent pas être complètement indépendants si je veux garantir une durée fixe, si ?”**

### ✔️ Réponse exacte :

* **Dans la logique v3.2 (actuelle) :
  SI. Ils le sont complètement indépendants.**

* Mais pour que cela reste vrai, la durée demandée doit être obtenue en ajustant **uniquement la taille de l’image audio**.

C’est le compromis qui rend l’outil **artist-friendly** ET stable.

---

# 🎨 Bonus : ce modèle est parfait pour le mode artiste

Car tu peux mapper :

* `movement` → step_ms
* `density` → voices
* `resolution` → size initiale
* `duration` → stretch automatique (N_columns)

Et tout reste cohérent et musical.

---

Si tu veux, je peux maintenant te proposer :

### ✔️ un mapping artistique **propre** pour step_ms/density

### ✔️ ou un schéma ASCII pour documenter cette logique dans ton README

### ✔️ ou une version améliorée de compute_audio_image_shape_from_duration

À toi de choisir !

