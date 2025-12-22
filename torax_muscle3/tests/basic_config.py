"""Simplified config using mostly defaults for various simulation components."""

CONFIG = {
    "profile_conditions": {},  # use default profile conditions
    "plasma_composition": {},  # use default plasma composition
    "numerics": {
        "t_initial": 0,
        "t_final": 5,
        "fixed_dt": 0.1,
        "adaptive_dt": False,
    },
    # circular geometry is only for testing and prototyping
    "geometry": {
        "geometry_type": "chease",
        "geometry_file": "iterhybrid.mat2cols",
        "Ip_from_parameters": True,
        "R_major": 6.2,  # major radius (R) in meters
        "a_minor": 2.0,  # minor radius (a) in meters
        "B_0": 5.3,  # Toroidal magnetic field on axis [T]
    },
    "neoclassical": {
        "bootstrap_current": {},
    },
    "sources": {
        # Current sources (for psi equation)
        "generic_current": {},
        # Electron density sources/sink (for the n_e equation).
        "generic_particle": {},
        "gas_puff": {},
        "pellet": {},
        # Ion and electron heat sources (for the temp-ion and temp-el eqs).
        "generic_heat": {},
        "fusion": {},
        "ei_exchange": {},
        "ohmic": {},
    },
    "pedestal": {},
    "transport": {
        "model_name": "constant",
    },
    "solver": {
        "solver_type": "linear",
    },
    "time_step_calculator": {
        "calculator_type": "chi",
    },
}
