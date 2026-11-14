# Présentation SFO 16/11/2026

I. Introduction
- Sujet de thèse
- Usage généraliste
- Problématiques de recherche
- Inventaire global
- Introduction des zones d'études

II. Analyse critique et problématiques
- Fixité des plans
- Variabilités dans les états de sections
- Variabilité dans les matrices

III. Approaches de traitement automatique
- Ontologie
- Algorithme de peuplement
- Extraction auto

IV. Quelques examples développés

V. Conclusion cadastre-sfo

## Installation
```bash
uv venv .quartoenv --python 3.13
uv pip install -r requirements.txt
export QUARTO_PYTHON=$PWD/.quartoenv/bin/python
```

## Activate env
```
```

## Render slides
```bash
quarto preview slides/main.qmd  --port 9860 # live preview in the browser, reloads when you save
```


## Notes
J'ai allégé les images de la présentation sans toucher au contenu : les fichiers `.qmd` et les images d'origine restent tels quels. Sur un rendu de test de l'intro et de la partie I, le HTML est passé d'environ 66 Mo d'images intégrées à 29,7 Mo. Je n'ai pas pu rendre la présentation complète (voir plus bas).

**Ce qui ralentissait :** avec `embed-resources: true`, toutes les images sont copiées dans le fichier HTML, qui pesait 76 Mo. Les photos d'archives étaient en pleine résolution, par exemple 7,9 Mo pour le plan de Mont-Dauphin. Comme ce plan apparaît sur 3 slides, il était copié 3 fois, soit 31 Mo à lui seul. Le navigateur devait aussi décoder des images bien plus grandes que l'écran à chaque changement de slide.

**Ce que j'ai mis en place :**
- **[optimize_images.py](optimize_images.py)** : crée des copies allégées de `imgs/` dans `imgs_web/`. Les images sont limitées à 2400 px de côté, ce qui suffit pour des slides en 1600×900 et pour le zoom au clic. Les JPEG sont recompressés en qualité 85 et les PNG restent en PNG, pour que le texte et les schémas restent nets. Les originaux ne sont jamais modifiés.
  - Exemples : plan de Mont-Dauphin 7,9 → 0,4 Mo, image de fond de la page de titre 4,2 → 0,85 Mo, total 45,8 → 25,9 Mo.
- **[web-images.lua](web-images.lua)** : un filtre ajouté dans [main.qmd](main.qmd#L17). Au rendu, il remplace `imgs/...` par la copie de `imgs_web/...` si elle existe, sinon il garde l'image d'origine. Vous continuez à écrire `imgs/...` dans vos slides.
- J'ai installé la bibliothèque `pillow` dans votre Python 3.11 pour faire tourner le script.

Quand vous ajoutez ou modifiez une image, relancez `python optimize_images.py` depuis `slides/` avant le rendu. Seules les images nouvelles ou modifiées sont retraitées.

**Rendu complet non fait :** dans mon terminal, Quarto ne trouve pas de Python avec Jupyter, à cause de PyYAML. Le bloc plotly de `conclu.qmd` ne peut donc pas s'exécuter et l'ancien `main.html` est inchangé. Relancez votre rendu habituel pour obtenir la nouvelle version.

**À noter :**
- `imgs/p1/etat_de_section_marolles.png`, utilisé deux fois dans `p4.qmd`, n'existe pas dans le dossier.
- Les PNG pèsent encore 1,5 à 2,5 Mo chacun : `ex_*_org`, `pres_corpus_p2` et `ETS Mont-Dauphin`/`Ouessant` dans `p4`. On peut encore gagner environ 50 % en les convertissant en JPEG de haute qualité, au prix d'une légère perte de qualité. Je peux le faire si vous le souhaitez.
- Le gain le plus important viendrait de la suppression de `embed-resources: true` : les images seraient alors chargées au fil des slides et non toutes à l'ouverture. En contrepartie, il faudrait transporter le dossier avec le HTML. C'est à vous de choisir selon la façon dont vous présentez.

## Mermaid
J'ai ajouté une classe réutilisable `.mermaid-fit` dans [custom.scss:108-123](slides/custom.scss#L108-L123). Je n'ai pas relancé le rendu, donc c'est à vérifier dans vos slides.

**Utilisation** : entourez le bloc mermaid d'un div qui porte deux variables CSS.

````markdown
::: {.mermaid-fit style="--h: 500px; --zoom: 1.2"}
```{mermaid}
graph TD
    A --> B
```
:::
````

- **`--h`** fixe la hauteur. Le SVG est mis à l'échelle pour tenir dans cette hauteur, sans déformation. Sans `--h`, la hauteur maximale est de 600px.
- **`--zoom`** agrandit ou réduit en plus. `1` ne change rien, `0.8` réduit, `1.3` agrandit. La place prise sur la slide suit le zoom.

Vous pouvez donner des valeurs différentes à chaque diagramme. Par exemple `--h: 350px` pour le grand graphe de [p2.qmd:45](slides/p2.qmd#L45), et `--h: 750px` pour un diagramme seul sur sa slide.

**Pourquoi c'est nécessaire** : avec `mermaid-format: svg`, Mermaid ajoute dans le SVG un style `max-width: XXXpx` à sa taille d'origine. La CSS doit donc l'annuler avec `!important`, sinon il est impossible d'agrandir le diagramme.

**Deux autres réglages, dans le diagramme lui-même** (vous utilisez déjà le premier) :
- Pour resserrer ou aérer le graphe : `%%{init: {"flowchart": {"rankSpacing": 25, "nodeSpacing": 8}}}%%`
- Pour grossir le texte sans changer l'espacement : `%%{init: {"themeVariables": {"fontSize": "22px"}}}%%`

En pratique, réglez d'abord la densité avec `init`, puis la taille sur la slide avec `--h` et `--zoom`.