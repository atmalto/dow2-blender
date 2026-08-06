from __future__ import annotations

from typing import Tuple


BADGE_SLOTS = (
    ("badge1", "Badge 1", "badge1Tex", "badge1MatrixRow1Row2", "badge1Translate"),
    ("badge2", "Badge 2", "badge2Tex", "badge2MatrixRow1Row2", "badge2Translate"),
)

BADGE_NODE_LABELS = {
    "badge1": {
        "matrix_u_x": "Badge 1 Matrix U.X",
        "matrix_u_y": "Badge 1 Matrix U.Y",
        "translate_u": "Badge 1 Translate U",
        "matrix_v_x": "Badge 1 Matrix V.X",
        "matrix_v_y": "Badge 1 Matrix V.Y",
        "translate_v": "Badge 1 Translate V",
    },
    "badge2": {
        "matrix_u_x": "Badge 2 Matrix U.X",
        "matrix_u_y": "Badge 2 Matrix U.Y",
        "translate_u": "Badge 2 Translate U",
        "matrix_v_x": "Badge 2 Matrix V.X",
        "matrix_v_y": "Badge 2 Matrix V.Y",
        "translate_v": "Badge 2 Translate V",
    },
}


def badge_control(slot_name: str) -> Tuple[str, str, str, str, str]:
    for control in BADGE_SLOTS:
        if control[0] == slot_name:
            return control
    raise KeyError(f"Unknown badge slot {slot_name}")


__all__ = [
    "BADGE_NODE_LABELS",
    "BADGE_SLOTS",
    "badge_control",
]