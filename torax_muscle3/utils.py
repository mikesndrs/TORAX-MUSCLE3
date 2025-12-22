"""
Utility functions for muscle3 and torax.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypeVar, cast

import numpy as np
from imas.ids_toplevel import IDSToplevel
from libmuscle import Instance
from torax._src.geometry.imas import IMASConfig
from torax._src.torax_pydantic import model_config
from ymmsl import SettingValue

logger = logging.getLogger()

TSetting = TypeVar("TSetting", bound=SettingValue)


@dataclass
class ExtraVarDir:
    """Temp code for extra vars"""

    name: str
    xs: List[float]
    ys: List


class ExtraVarCollection:
    """Temp code for extra vars"""

    extra_var_dirs: Dict[str, ExtraVarDir]

    def __init__(self, names: List[str] = []) -> None:
        self.extra_var_dirs = {
            name: ExtraVarDir(name=name, xs=[], ys=[]) for name in names
        }

    def add_val(self, name: str, x: float, y: Any) -> None:
        if name not in self.extra_var_dirs.keys():
            self.extra_var_dirs[name] = ExtraVarDir(name=name, xs=[], ys=[])
        self.extra_var_dirs[name].xs.append(x)
        self.extra_var_dirs[name].ys.append(y)

    def pad_extra_vars(self) -> None:
        for name in self.extra_var_dirs.keys():
            self.extra_var_dirs[name].xs = (
                [-np.inf] + self.extra_var_dirs[name].xs + [np.inf]
            )
            self.extra_var_dirs[name].ys = (
                [self.extra_var_dirs[name].ys[0]]
                + self.extra_var_dirs[name].ys
                + [self.extra_var_dirs[name].ys[-1]]
            )

    def get_val(self, name: str, x: float) -> Any:
        """Step interpolation"""
        var_dir = self.extra_var_dirs[name]
        idx = max(i for i in range(len(var_dir.xs)) if var_dir.xs[i] <= x)
        return var_dir.ys[idx]


def get_geometry_config_dict(config: model_config.ToraxConfig) -> dict:
    # only get overlapping keys from given config and IMASConfig
    imas_config_keys = IMASConfig.__annotations__
    # we can pick a random entry since all fields are time_invariant except hires_fac
    # (which we can ignore) and equilibrium_object (which we overwrite)
    if isinstance(config.geometry.geometry_configs, dict):
        config_dict = list(config.geometry.geometry_configs.values())[0].config.__dict__
    else:
        config_dict = config.geometry.geometry_configs.config.__dict__
    config_dict = {
        key: value for key, value in config_dict.items() if key in imas_config_keys
    }
    return config_dict


def get_setting_optional(
    instance: Instance, setting_name: str, default: Optional[TSetting] = None
) -> Optional[TSetting]:
    """Helper function to get optional settings from instance"""
    setting: Optional[TSetting]
    try:
        setting = cast(TSetting, instance.get_setting(setting_name))
    except KeyError:
        setting = default
    return setting


def merge_extra_vars(
    equilibrium_data: IDSToplevel, extra_var_col: ExtraVarCollection
) -> IDSToplevel:
    if "z_boundary_outline" in extra_var_col.extra_var_dirs.keys():
        equilibrium_data.time_slice[0].boundary.outline.z = extra_var_col.get_val(
            "z_boundary_outline", equilibrium_data.time[0]
        )
    if "r_boundary_outline" in extra_var_col.extra_var_dirs.keys():
        equilibrium_data.time_slice[0].boundary.outline.r = extra_var_col.get_val(
            "r_boundary_outline", equilibrium_data.time[0]
        )
    return equilibrium_data
