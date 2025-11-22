Oui, **dans la logique actuelle c’est normal** – et même volontaire 🙂

Je réexplique la philosophie de `--duration-s` telle qu’on l’a conçue pour v3.2 :

---

## 🧠 Idée de base

On considère que :

* `step_ms` = **vitesse de balayage** (caractère rythmique / densité temporelle),
* `voices` = **nombre de voix simultanées max** (épaisseur / complexité),
* `duration_s` = **durée globale cible**.

Pour ne pas casser le “timbre” ni le caractère du moteur, on a choisi la stratégie suivante :

> 👉 Quand tu donnes `--duration-s`, on **ne touche pas** à `step_ms` ni `voices`.
> On ajuste **uniquement la taille de l’image audio** (la largeur surtout) pour que,
> avec *ces* `step_ms` et `voices`, on retombe sur la durée demandée.

En gros :

```text
durée ≈ (nb_colonnes / voices) * step_ms  + sustain_s
         ↑
       c'est là qu'on joue : on adapte nb_colonnes ⇒ donc la size de l'image audio
```

Donc :

* si tu ne précises pas `--step-ms` ni `--voices`, ils restent à leurs valeurs par défaut (50 ms et 20 voix),
* `--duration-s` se contente de calculer la **largeur logique** de l’image audio pour que le défilement prenne à peu près cette durée.

---

## Donc pour répondre à ta question

> “dans image_proc.py, dans le calcul lié au paramètre 'duration' seule la size de l'image qui sert pour l'audio change et les paramètres voices et step reste toujours à 20 voix et 50ms c'est normal ?”

🟢 **Oui, c’est normal dans la conception actuelle** :

* `duration_s` **ne modifie pas** `step_ms` ni `voices`
* il **modifie seulement** la taille de l’image (surtout la largeur) pour atteindre la durée cible.

Si tu veux une autre logique (par ex. “je fixe la taille de l’image, `duration` doit alors ajuster `step_ms` ou `voices`”), on peut tout à fait définir :

* un **mode A** : durée → redimensionnement de l’image (ce qu’on a aujourd’hui)
* un **mode B** : durée → recalcul de `step_ms` (et éventuellement de `voices`)

et décider comment les exposer proprement dans la CLI.

