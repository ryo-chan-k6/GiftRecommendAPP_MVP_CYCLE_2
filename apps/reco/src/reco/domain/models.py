from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ResolvedParams:
    mode: str
    algorithm: str
    k: int
    w_vec: float
    w_pop: float
    w_rev: float
    mmr_lambda: float
    n_in: int = 50
    n_out: int = 20
    resolved_by: str = "mode"

    def to_response_params(self) -> Dict[str, float | int]:
        return {
            "k": self.k,
            "w_vec": self.w_vec,
            "w_pop": self.w_pop,
            "w_rev": self.w_rev,
            "mmr_lambda": self.mmr_lambda,
            "n_in": self.n_in,
            "n_out": self.n_out,
        }
