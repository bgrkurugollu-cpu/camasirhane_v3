from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from ... import models

RACK_LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
RACK_FLOORS = 7
RACK_COMPARTMENTS = 5

def get_compartment_capacity(floor: int) -> int:
    return 1 if floor == 7 else 3

def assign_shelf(db: Session, cinsiyet: Optional[str] = None) -> Optional[str]:
    occupancy = db.query(
        models.Temiz_Kiyafet.raf_id,
        func.count(models.Temiz_Kiyafet.islem_id)
    ).filter(models.Temiz_Kiyafet.raf_id != None).group_by(models.Temiz_Kiyafet.raf_id).all()

    occupancy_dict = {raf_id: count for raf_id, count in occupancy}

    if cinsiyet == 'K':
        letters = ['E']
    else:
        letters = [l for l in RACK_LETTERS if l != 'E']

    for letter in letters:
        for floor in range(1, RACK_FLOORS + 1):
            cap = get_compartment_capacity(floor)
            for comp in range(1, RACK_COMPARTMENTS + 1):
                raf_id = f"{letter}{floor}{comp}"
                if occupancy_dict.get(raf_id, 0) < cap:
                    return raf_id
    return None
