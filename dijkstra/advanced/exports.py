"""Exports JSON stricts (INF = null) et CSV lisibles sous Windows."""
import csv
import json
import math
from fractions import Fraction
from pathlib import Path
from ..display import format_cost
from ..core.models import SPFResult, RoutingEntry
from ..core.spf import reconstruct_path
from .topology_io import topology_dict
from .service import NetworkAnalyzer

def json_value(value: object) -> object:
    if isinstance(value, Fraction):
        if value.denominator == 1:
            return value.numerator
        try:
            numeric = float(value)
        except OverflowError:
            return format_cost(value)
        if math.isfinite(numeric) and Fraction(str(numeric)) == value:
            return numeric
        return format_cost(value)  # Valeur décimale exacte si un float la perdrait.
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return value

def write_json(path: str | Path, data: object) -> None:
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(json_value(data), ensure_ascii=False, indent=2,
                                   allow_nan=False) + "\n", encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValueError(f"Écriture impossible : {path} : {error}") from error

def table_dict(table: list[RoutingEntry]) -> list[dict]:
    return [{"destination": e.destination, "next_hop": e.next_hop,
             "next_hops": list(e.next_hops), "cost": e.cost, "path": list(e.path)} for e in table]

def result_dict(result: SPFResult) -> dict:
    return {"source": result.source, "distances": result.distances,
            "predecessors": result.predecessors, "tree_edges": result.tree_edges,
            "paths": {r: reconstruct_path(result.predecessors, result.source, r)
                      for r in result.distances}, "elapsed_seconds": result.elapsed_seconds}

def export_analysis(analyzer: NetworkAnalyzer, directory: str | Path = "outputs") -> list[Path]:
    directory = Path(directory)
    data = {"topology.json": topology_dict(analyzer.graph),
            "lsdb.json": {r: db.to_dict() for r, db in analyzer.lsdbs.items()},
            "distances.json": {r: result.distances for r, result in analyzer.results.items()},
            "spf.json": {r: result_dict(result) for r, result in analyzer.results.items()}}
    paths = []
    for name, payload in data.items():
        path = directory / name
        write_json(path, payload)
        paths.append(path)
    csv_path = directory / "routing.csv"
    try:
        with csv_path.open("w", encoding="utf-8-sig", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(["Source", "Destination", "Next Hop", "Coût", "Chemin"])
            for source, table in sorted(analyzer.tables.items()):
                for entry in table:
                    writer.writerow([source, entry.destination, entry.next_hop or "-",
                                     format_cost(entry.cost), " -> ".join(entry.path) or "Inaccessible"])
    except OSError as error:
        raise ValueError(f"Export CSV impossible : {error}") from error
    return paths + [csv_path]
