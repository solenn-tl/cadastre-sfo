#!/usr/bin/env python3
"""
Associe les dates d'utilisation du cadastre napoléonien (tableau des AD29)
à chaque commune (actuelle ou ancienne) récupérée dans Wikidata.

Usage :
    python associer_cadastre.py cadastre.csv wikidata.csv sortie.csv

Règles de rapprochement :
  1. Les noms sont normalisés (majuscules, sans accents ni apostrophes,
     tirets -> espaces, article "(LE)" replacé devant).
  2. Une table d'alias corrige les graphies différentes (BOTSHOREL / Botsorhel...).
  3. Les lignes "X (voir Y)" reprennent les dates de la commune Y.
  4. Si plusieurs éléments Wikidata portent le même nom (ex. Concarneau),
     on ne garde que ceux dont la période d'existence chevauche la période
     d'utilisation du cadastre.
  5. Les valeurs textuelles ("n'a pas servi", "Pas de cadastre"...) vont dans
     la colonne cadastre_remarque.
Un rapport des lignes non rapprochées est écrit à côté du fichier de sortie.
"""
import csv
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

# Graphie du tableau AD29 (normalisée) -> graphie Wikidata (normalisée)
ALIAS = {
    "BOTSHOREL": "BOTSORHEL",
    "BRASPART": "BRASPARTS",
    "KERFEUNTEN": "KERFEUNTEUN",
    "LANNEUFRET": "LANNEUFFRET",
    "LA FORET LANDERNEAU": "LA FOREST LANDERNEAU",
    "LOC EGUINER PLOUDIRY": "LOC EGUINER",
    "MEILARS": "CONFORT MEILARS",
    "PLOBANNALEC": "PLOBANNALEC LESCONIL",
    "PLOUEGAT GUERRAND": "PLOUEGAT GUERAND",
    "PLOUGERNEAU": "PLOUGUERNEAU",
    "PLOUGOUVERST": "PLOUGOURVEST",
    "PLOURIN PLOUDALMEZEAU": "PLOURIN",
    "SAINT PIERRE QUILBINON": "SAINT PIERRE QUILBIGNON",
}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).upper()
    s = re.sub(r"[’'`]", "", s)
    s = re.sub(r"[-\s]+", " ", s).strip()
    m = re.match(r"^(.*) \((LE|LA|LES|L)\)$", s)  # "CONQUET (LE)" -> "LE CONQUET"
    if m:
        s = f"{m[2]} {m[1]}"
    return s


def sans_article(s: str) -> str:
    return re.sub(r"^(LE|LA|LES|L) ", "", s)


def annee(v: str):
    m = re.match(r"^\s*(\d{4})", v or "")
    return int(m[1]) if m else None


def lire_cadastre(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f, delimiter=";"))
    data = []
    for r in rows[2:]:  # 2 lignes d'en-tête
        if not r or not r[0].strip():
            continue
        nom, deb, fin = (r + ["", "", ""])[:3]
        data.append({"nom": nom.strip(), "deb": deb.strip(), "fin": fin.strip()})
    return data


def main(cad_path, wd_path, out_path):
    cadastre = lire_cadastre(cad_path)

    # Index des communes du cadastre par nom normalisé
    index = {}
    renvois = {}
    for c in cadastre:
        m = re.match(r"^(.*?)\s*\(voir (.*)\)$", c["nom"], re.I)
        if m:  # "GUICQUELLEAU (voir Le Folgoët)"
            renvois[norm(m[1])] = (c, norm(m[2]))
            continue
        cle = norm(c["nom"])
        cle = ALIAS.get(cle, cle)
        index[cle] = c

    # Résolution des renvois vers les dates de la commune cible
    for cle, (c, cible) in renvois.items():
        t = index.get(cible) or index.get(sans_article(cible))
        if t is None:
            for k, v in index.items():
                if sans_article(k) == sans_article(cible):
                    t = v
                    break
        if t:
            index[cle] = {"nom": c["nom"], "deb": t["deb"], "fin": t["fin"], "renvoi": t["nom"]}
        else:
            index[cle] = {"nom": c["nom"], "deb": "", "fin": "", "renvoi": f"{cible} (introuvable)"}

    index_sa = defaultdict(list)
    for k in index:
        index_sa[sans_article(k)].append(k)

    with open(wd_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        wd = list(reader)
        champs = reader.fieldnames

    # Candidats : élément Wikidata -> ligne du cadastre
    candidats = defaultdict(list)  # clé cadastre -> [indices wikidata]
    for i, w in enumerate(wd):
        k = norm(w["label"])
        if k in index:
            candidats[k].append(i)
        else:
            ks = index_sa.get(sans_article(k), [])
            if len(ks) == 1:
                candidats[ks[0]].append(i)

    resultat = {}  # indice wikidata -> (ligne cadastre, méthode)
    for k, idxs in candidats.items():
        c = index[k]
        methode = "renvoi" if "renvoi" in c else ("alias" if k in ALIAS.values() else "nom")
        ids = {wd[i]["id"] for i in idxs}
        if len(ids) > 1:  # homonymes : départage par chevauchement de dates
            cd, cf = annee(c["deb"]), annee(c["fin"])
            gardes = []
            for i in idxs:
                wdd, wdf = annee(wd[i]["debut"]), annee(wd[i]["fin"])
                if (cf is None or wdd is None or wdd <= cf) and (cd is None or wdf is None or wdf >= cd):
                    gardes.append(i)
            idxs = gardes or idxs
            methode += "+dates"
        for i in idxs:
            resultat[i] = (c, methode)

    # Écriture
    nouveaux = ["cadastre_nom", "creation_cadastre", "fin_cadastre",
                "cadastre_remarque", "methode_rapprochement", "alerte"]
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=champs + nouveaux)
        w.writeheader()
        for i, row in enumerate(wd):
            out = dict(row)
            if i in resultat:
                c, methode = resultat[i]
                deb, fin = annee(c["deb"]), annee(c["fin"])
                rem = [v for v in (c["deb"], c["fin"]) if v and annee(v) is None]
                if "renvoi" in c:
                    rem.append(f"dates de {c['renvoi']}")
                alerte = ""
                wdd, wdf = annee(row["debut"]), annee(row["fin"])
                if wdf and deb and wdf < deb:
                    alerte = "commune disparue avant le début du cadastre"
                elif wdd and fin and wdd > fin:
                    alerte = "commune créée après la fin du cadastre"
                out.update(cadastre_nom=c["nom"], creation_cadastre=deb or "",
                           fin_cadastre=fin or "", cadastre_remarque=" ; ".join(rem),
                           methode_rapprochement=methode, alerte=alerte)
            w.writerow(out)

    # Rapport
    utilises = {id(c) for c, _ in resultat.values()}
    non_cad = [c["nom"] for c in index.values() if id(c) not in utilises]
    non_wd = sorted({wd[i]["label"] for i in range(len(wd)) if i not in resultat})
    rapport = Path(out_path).with_name(Path(out_path).stem + "_rapport.txt")
    with open(rapport, "w", encoding="utf-8") as f:
        f.write(f"Communes Wikidata : {len(wd)} lignes, {len(resultat)} avec dates cadastre\n\n")
        f.write(f"Lignes du cadastre sans élément Wikidata ({len(non_cad)}) :\n")
        f.writelines(f"  {n}\n" for n in sorted(non_cad))
        f.write(f"\nÉléments Wikidata sans ligne du cadastre ({len(non_wd)}) :\n")
        f.writelines(f"  {n}\n" for n in non_wd)
    print(open(rapport, encoding="utf-8").read())


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
