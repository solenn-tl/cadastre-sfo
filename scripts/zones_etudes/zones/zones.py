"""Cartes (folium / leaflet) et frises chronologiques (plotly) des zones d'études.

Données :
- data/zones.gpkg
    * couche "communes"          : limites actuelles (geo.api.gouv.fr), générée une fois
    * couche "zones_historiques" : à éditer dans QGIS (ex. partie de Gentilly annexée en 1860)
- data/registres.csv   : périodes de validité des registres, une ligne par registre
- data/evenements.csv  : dates repères affichées sur les frises (annexion, etc.)
"""
from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go

DATA = Path("data")
GPKG = DATA / "zones.gpkg"

ZONES = pd.DataFrame({
    "code": ["94038", "94037", "05082", "29155"],
    "nom":  ["L'Haÿ", "Gentilly", "Mont-Dauphin", "Ouessant"],
    "dep":  ["Val-de-Marne", "Val-de-Marne", "Hautes-Alpes", "Finistère"],
})

# Une couleur par département, partagée par les cartes et les frises
PAL = {"Val-de-Marne": "#1b6ca8", "Hautes-Alpes": "#c0392b", "Finistère": "#2e8b57"}
# Teinte par cadastre successif (1er, 2e, ...)
PAL_CADASTRE = {1: "#1b6ca8", 2: "#e08a1e", 3: "#7b4fa0"}

ANNEES = (1800, 1980)   # même axe pour toutes les frises -> comparables

# Cache CSS : n'afficher que l'échelle métrique de leaflet
CSS_ECHELLE = folium.Element(
    "<style>.leaflet-control-scale-line:not(:first-child){display:none}</style>"
)

# Fonds de la Géoplateforme IGN (WMTS) -- carte d'état-major utile pour le XIXe s.
def _wmts(layer, fmt="image/jpeg"):
    return ("https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0"
            f"&LAYER={layer}&STYLE=normal&TILEMATRIXSET=PM&FORMAT={fmt}"
            "&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}")

FONDS = {
    "Carte d'état-major (1820-1866)": _wmts("GEOGRAPHICALGRIDSYSTEMS.ETATMAJOR40"),
    "Photographies aériennes": _wmts("ORTHOIMAGERY.ORTHOPHOTOS"),
}


# --------------------------------------------------------------------------
# Données
# --------------------------------------------------------------------------
def init_gpkg(force=False):
    """Télécharge les limites communales et crée le gpkg (une seule fois)."""
    if GPKG.exists() and not force:
        return
    DATA.mkdir(exist_ok=True)
    url = "https://geo.api.gouv.fr/communes/{}?format=geojson&geometry=contour"
    communes = pd.concat(
        [gpd.read_file(url.format(c))[["code", "nom", "geometry"]] for c in ZONES.code]
    )
    communes = gpd.GeoDataFrame(communes, crs=4326).to_crs(2154)
    communes.to_file(GPKG, layer="communes", driver="GPKG")

    # Couche à éditer : on part des limites actuelles, à redécouper dans QGIS.
    hist = communes.copy()
    hist["zone"] = hist["nom"] + " (limites actuelles, à reprendre)"
    hist["debut"] = pd.NA
    hist["fin"] = pd.NA
    hist["commentaire"] = ""
    hist[["code", "zone", "debut", "fin", "commentaire", "geometry"]].to_file(
        GPKG, layer="zones_historiques", driver="GPKG"
    )


def communes():
    gdf = gpd.read_file(GPKG, layer="communes").to_crs(4326)
    gdf = gdf.drop(columns="nom").merge(ZONES, on="code")
    return gdf


def zones_historiques(code):
    gdf = gpd.read_file(GPKG, layer="zones_historiques").to_crs(4326)
    return gdf[gdf.code == code]


def _centre(gdf):
    c = gdf.to_crs(2154).geometry.union_all().centroid
    p = gpd.GeoSeries([c], crs=2154).to_crs(4326).iloc[0]
    return [p.y, p.x]


def _bornes(gdf):
    x0, y0, x1, y1 = gdf.total_bounds
    return [[y0, x0], [y1, x1]]


# --------------------------------------------------------------------------
# Cartes
# --------------------------------------------------------------------------
def _carte(location, zoom, width, height, interactive=True, fonds=False):
    m = folium.Map(
        location=location, zoom_start=zoom, width=width, height=height,
        tiles="CartoDB positron", control_scale=True,
        zoom_control=interactive, scrollWheelZoom=interactive,
        dragging=interactive, doubleClickZoom=interactive,
    )
    if fonds:
        for nom, url in FONDS.items():
            folium.TileLayer(url, name=nom, attr="IGN-F / Géoplateforme",
                             overlay=False, max_zoom=18).add_to(m)
    m.get_root().header.add_child(CSS_ECHELLE)
    return m


def carte_ensemble(width=480, height=520):
    """France entière, un point par commune, couleur par département."""
    gdf = communes()
    m = _carte([46.6, 2.5], 5, width, height)
    for _, r in gdf.iterrows():
        lat, lon = _centre(gdf[gdf.code == r.code])
        folium.CircleMarker(
            [lat, lon], radius=7, color="white", weight=1.5,
            fill=True, fill_color=PAL[r.dep], fill_opacity=1,
            tooltip=f"<b>{r.nom}</b><br>{r.dep}",
        ).add_to(m)
    return m


def vignette(code, zoom=11, width=230, height=230):
    """Commune seule, zoom FIXE -> toutes les vignettes à la même échelle.

    NB : en Web Mercator l'échelle varie avec la latitude (~8 % d'écart entre
    les Hautes-Alpes et Ouessant) ; la barre d'échelle de chaque vignette
    reste exacte.
    """
    g = communes().query("code == @code")
    m = _carte(_centre(g), zoom, width, height, interactive=False)
    folium.GeoJson(
        g, style_function=lambda f, c=PAL[g.dep.iloc[0]]: {
            "color": c, "weight": 1.5, "fillColor": c, "fillOpacity": 0.45},
    ).add_to(m)
    return m


def carte_detail(code, width=430, height=480):
    """Limites actuelles en pointillé + zones historiques du gpkg."""
    g = communes().query("code == @code")
    couleur = PAL[g.dep.iloc[0]]
    m = _carte(_centre(g), 13, width, height, fonds=True)

    folium.GeoJson(
        g, name="Limites actuelles",
        style_function=lambda f: {"color": "#333", "weight": 2,
                                  "dashArray": "6 4", "fillOpacity": 0},
    ).add_to(m)

    h = zones_historiques(code)
    if len(h):
        h = h.assign(periode=h.apply(
            lambda r: f"{_annee(r.debut)} – {_annee(r.fin)}", axis=1))
        folium.GeoJson(
            h, name="Zones historiques",
            style_function=lambda f: {"color": couleur, "weight": 1,
                                      "fillColor": couleur, "fillOpacity": 0.3},
            tooltip=folium.GeoJsonTooltip(["zone", "periode", "commentaire"],
                                          aliases=["", "Période", ""]),
        ).add_to(m)

    m.fit_bounds(_bornes(g), padding=(10, 10))
    folium.LayerControl(collapsed=True).add_to(m)
    return m


def _annee(v):
    return "?" if pd.isna(v) else str(int(v))


# --------------------------------------------------------------------------
# Frise chronologique
# --------------------------------------------------------------------------
def frise(code, height=None):
    """Barres horizontales : une ligne par registre, une couleur par cadastre.

    - début ou fin vide dans le CSV  -> barre prolongée jusqu'au bord, hachurée
    - numerise = non / partiel       -> barre pâle / hachurée et libellé
    """
    reg = pd.read_csv(DATA / "registres.csv", dtype={"code": str})
    reg = reg[reg.code == code].copy()
    evt = pd.read_csv(DATA / "evenements.csv", dtype={"code": str})
    evt = evt[evt.code == code]

    reg["debut_inc"] = reg.debut.isna()
    reg["fin_inc"] = reg.fin.isna()
    reg["d"] = reg.debut.fillna(ANNEES[0])
    reg["f"] = reg.fin.fillna(ANNEES[1])

    lignes = list(dict.fromkeys(reg.registre))       # ordre du CSV
    fig = go.Figure()

    for _, r in reg.iterrows():
        incertain = r.debut_inc or r.fin_inc
        num = str(r.numerise).strip().lower()
        couleur = PAL_CADASTRE.get(int(r.cadastre), "#888")
        motif = "/" if (incertain or num == "partiel") else ""
        hover = (f"<b>{r.registre}</b> – cadastre n°{int(r.cadastre)}<br>"
                 f"{_annee(r.debut)} – {_annee(r.fin)}<br>"
                 f"Numérisé : {r.numerise}"
                 + (f"<br>{r.note}" if isinstance(r.note, str) else ""))
        fig.add_trace(go.Bar(
            y=[r.registre], x=[r.f - r.d], base=[r.d], orientation="h",
            marker=dict(color=couleur, opacity=1 if num == "oui" else 0.35,
                        pattern=dict(shape=motif, fgcolor="white", size=6),
                        line=dict(color=couleur, width=1)),
            text=[f"{_annee(r.debut)} – {_annee(r.fin)}"
                  + ("" if num == "oui" else f" · {r.numerise}")],
            textposition="inside", insidetextanchor="middle",
            hovertemplate=hover + "<extra></extra>",
            name=f"Cadastre n°{int(r.cadastre)}",
            legendgroup=str(r.cadastre), showlegend=False,
        ))

    # Légende : un item par cadastre seulement
    for n in sorted(reg.cadastre.unique()):
        fig.add_trace(go.Bar(y=[None], x=[None], orientation="h",
                             marker_color=PAL_CADASTRE.get(int(n), "#888"),
                             name=f"Cadastre n°{int(n)}"))

    for _, e in evt.iterrows():
        fig.add_vline(x=e.annee, line=dict(color="#555", width=1, dash="dot"))
        fig.add_annotation(x=e.annee, y=1.02, yref="paper", text=e.libelle,
                           showarrow=False, font=dict(size=11, color="#555"),
                           xanchor="left", yanchor="bottom")

    fig.update_layout(
        barmode="overlay", bargap=0.35,
        height=height or 90 + 42 * len(lignes),
        margin=dict(l=10, r=10, t=30, b=25),
        plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13),
        legend=dict(orientation="h", y=-0.25, x=0),
        uniformtext=dict(minsize=9, mode="hide"),
    )
    fig.update_xaxes(range=ANNEES, dtick=20, showgrid=True, gridcolor="#eee")
    fig.update_yaxes(categoryorder="array", categoryarray=lignes[::-1])
    return fig
