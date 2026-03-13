from pydantic import BaseModel
from typing import Optional

class Stat(BaseModel):
    distribution_type: Optional[str] = None
    mean: Optional[float] = None
    std: Optional[float] = None

    range: Optional[float] = None
    p95: Optional[float] = None
    mad: Optional[float] = None
    n_slope: Optional[float] = None
    autocorr: Optional[float] = None
    fano_factor: Optional[float] = None

    min: Optional[float] = None
    max: Optional[float] = None
    sum: Optional[float] = None
    population: Optional[float] = None