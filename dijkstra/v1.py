"""Exécution académique autonome : une LSDB et un SPF par routeur."""
from .examples import reference_graph
from .core.lsdb import build_lsdbs
from .core.spf import run_all
from .display import show_result

def main() -> None:
    databases = build_lsdbs(reference_graph())
    for source, result in run_all(databases).items():
        show_result(databases[source], result)

if __name__ == "__main__":
    main()
