"""Dessin SVG facultatif, uniquement à partir des résultats déjà calculés."""
import math
from html import escape
from pathlib import Path
from ..core.graph import NetworkGraph
from ..core.models import SPFResult
from ..core.spf import reconstruct_path

def text_topology(graph: NetworkGraph) -> str:
    lines = [f"{a} --{cost}-- {b}" for a, b, cost in graph.get_links()]
    lines += [f"{r} (isolé)" for r in graph.get_routers() if not graph.get_neighbors(r)]
    return "\n".join(lines) or "Réseau vide."

def write_svg(graph: NetworkGraph, path: str | Path, result: SPFResult | None = None,
              destination: str | None = None) -> None:
    routers = graph.get_routers()
    positions = {r: (360 + 255 * math.cos(2 * math.pi * i / max(1, len(routers))),
                     330 + 255 * math.sin(2 * math.pi * i / max(1, len(routers))))
                 for i, r in enumerate(routers)}
    tree = {frozenset(edge) for edge in result.tree_edges} if result else set()
    selected = reconstruct_path(result.predecessors, result.source, destination) if result and destination else []
    highlighted = {frozenset(edge) for edge in zip(selected, selected[1:])}
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="720" height="710" viewBox="0 0 720 710">',
           '<rect width="720" height="710" fill="#f4f6fa"/>',
           '<text x="20" y="30" font-family="sans-serif">Topologie : gris / arbre SPF : bleu / chemin : orange</text>']
    for a, b, cost in graph.get_links():
        x1, y1 = positions[a]
        x2, y2 = positions[b]
        edge = frozenset((a, b))
        color = "#d35400" if edge in highlighted else "#2563eb" if edge in tree else "#a1a1aa"
        width = 5 if edge in highlighted else 3 if edge in tree else 1
        svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>')
        svg.append(f'<text x="{(x1+x2)/2}" y="{(y1+y2)/2-5}" font-family="sans-serif" fill="#111">{escape(str(cost))}</text>')
    for router, (x, y) in positions.items():
        fill = "#fde68a" if result and router == result.source else "white"
        svg.append(f'<circle cx="{x}" cy="{y}" r="25" fill="{fill}" stroke="#172554" stroke-width="2"/>')
        svg.append(f'<text x="{x}" y="{y+5}" text-anchor="middle" font-family="sans-serif">{escape(router)}</text>')
    svg.append('</svg>')
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(svg), encoding="utf-8")
    except OSError as error:
        raise ValueError(f"Dessin SVG impossible : {error}") from error
