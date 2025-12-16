r"""
MUSCLE3 actor wrapping TORAX.

Configuration can be specified as a path to a config file,.
and individual muscle3 config keys will be overwritten on that.

Start without inputs and outputs, and then add a static and
later dynamic equilibrium input.

Last (for sure) compatible torax commit: 4b76ef0566
"""

import logging
from typing import Optional, Tuple

import numpy as np
from imas import DBEntry, IDSFactory
from imas.ids_defs import CLOSEST_INTERP
from imas.ids_toplevel import IDSToplevel
from libmuscle import Instance, Message
from torax._src.config.build_runtime_params import (
    get_consistent_runtime_params_and_geometry,
)
from torax._src.config.config_loader import build_torax_config_from_file
from torax._src.core_profiles.profile_conditions import ProfileConditions
from torax._src.geometry import geometry
from torax._src.geometry.imas import IMASConfig
from torax._src.geometry.pydantic_model import Geometry, GeometryConfig
from torax._src.imas_tools.input.core_profiles import profile_conditions_from_IMAS
from torax._src.imas_tools.output.core_profiles import core_profiles_to_IMAS
from torax._src.imas_tools.output.equilibrium import torax_state_to_imas_equilibrium
from torax._src.orchestration import initial_state as initial_state_lib
from torax._src.orchestration.run_simulation import make_step_fn, prepare_simulation
from torax._src.state import SimError
from torax._src.torax_pydantic.model_config import ToraxConfig
from ymmsl import Operator

from torax_muscle3.utils import (
    ExtraVarCollection,
    get_geometry_config_dict,
    get_setting_optional,
    merge_extra_vars,
)

logger = logging.getLogger()


class ToraxMuscleRunner:
    from torax._src.orchestration.sim_state import SimState
    from torax._src.orchestration.step_function import SimulationStepFn

    # first_run
    first_run: bool = True
    output_all_timeslices: Optional[bool] = False
    db_out: DBEntry
    torax_config: ToraxConfig
    step_fn: SimulationStepFn
    time_step_calculator_dynamic_params = None
    equilibrium_interval = None

    # state
    sim_state: SimState
    post_processed_outputs = None
    extra_var_col: ExtraVarCollection
    t_cur: float
    t_next_inner: Optional[float] = None
    t_next_outer: Optional[float] = None
    finished: bool = False
    last_equilibrium_call = -np.inf

    def __init__(self) -> None:
        self.get_instance()
        self.extra_var_col = ExtraVarCollection()

    def run_sim(self) -> None:
        if self.finished:
            raise Warning("Already finished")

        while self.instance.reuse_instance():
            if self.first_run:
                self.run_prep()
            self.run_f_init()
            while not self.step_fn.is_done(
                self.t_cur,
            ):
                self.run_o_i()
                self.run_s()
                self.run_timestep()
            self.run_o_f()

        self.finished = True

    def run_prep(self) -> None:
        self.equilibrium_interval = get_setting_optional(
            self.instance, "equilibrium_interval", 1e-6
        )
        self.output_all_timeslices = get_setting_optional(
            self.instance, "output_all_timeslices", False
        )
        if self.output_all_timeslices:
            self.db_out = DBEntry("imas:memory?path=/db_out/", "w")
        # load config file from path
        config_module_str = self.instance.get_setting("python_config_module")
        self.torax_config = build_torax_config_from_file(
            path=config_module_str,
        )
        (
            self.sim_state,
            self.post_processed_outputs,
            self.step_fn,
        ) = prepare_simulation(self.torax_config)

        self.time_step_calculator_dynamic_params = self.step_fn.runtime_params_provider(
            self.sim_state.t
        ).time_step_calculator

    def run_f_init(self) -> None:
        self.receive_equilibrium(port_name="f_init")
        self.receive_core_profiles(port_name="f_init")
        # self.sim_state.t = self.t_cur
        self.t_cur = self.sim_state.t
        if self.first_run or self.instance.is_connected("equilibrium_f_init"):
            self.step_fn = make_step_fn(self.torax_config)
            self.sim_state, self.post_processed_outputs = (
                initial_state_lib.get_initial_state_and_post_processed_outputs(
                    step_fn=self.step_fn,
                )
            )
            self.t_final = self.step_fn.runtime_params_provider.numerics.t_final
        self.first_run = False

        if self.output_all_timeslices:
            equilibrium_data = self.get_equilibrium_ids()
            core_profiles_data = self.get_core_profiles_ids()
            self.db_out.put_slice(equilibrium_data)
            self.db_out.put_slice(core_profiles_data)

    def run_o_i(self) -> None:
        self.t_next_inner = self.get_t_next()
        if self.t_cur >= self.last_equilibrium_call + self.equilibrium_interval:
            if self.instance.is_connected("equilibrium_o_i"):
                equilibrium_data = self.get_equilibrium_ids()
                self.send_ids(equilibrium_data, "equilibrium", "o_i")
            if self.instance.is_connected("equilibrium_o_i"):
                core_profiles_data = self.get_core_profiles_ids()
                self.send_ids(core_profiles_data, "core_profiles", "o_i")

    def run_s(self) -> None:
        if self.t_cur >= self.last_equilibrium_call + self.equilibrium_interval:
            self.receive_equilibrium(port_name="s")
            self.receive_core_profiles(port_name="s")

    def run_timestep(self) -> None:
        self.sim_state, self.post_processed_outputs = self.step_fn(
            self.sim_state,
            self.post_processed_outputs,
        )
        sim_error = self.step_fn.check_for_errors(
            self.sim_state,
            self.post_processed_outputs,
        )
        self.t_cur = self.sim_state.t

        if self.output_all_timeslices:
            equilibrium_data = self.get_equilibrium_ids()
            core_profiles_data = self.get_core_profiles_ids()
            self.db_out.put_slice(equilibrium_data)
            self.db_out.put_slice(core_profiles_data)

        if sim_error != SimError.NO_ERROR:
            raise Exception(sim_error)

    def run_o_f(self) -> None:
        if self.output_all_timeslices:
            equilibrium_data = self.db_out.get("equilibrium")
            core_profiles_data = self.db_out.get("core_profiles")
            self.db_out.close()
        else:
            equilibrium_data = self.get_equilibrium_ids()
            core_profiles_data = self.get_core_profiles_ids()
        self.send_ids(equilibrium_data, "equilibrium", "o_f")
        self.send_ids(core_profiles_data, "core_profiles", "o_f")

    def get_instance(self) -> None:
        coupled_ids_names = ["equilibrium", "core_profiles"]
        self.instance = Instance(
            {
                Operator.F_INIT: [
                    f"{ids_name}_f_init" for ids_name in coupled_ids_names
                ],
                Operator.O_I: [f"{ids_name}_o_i" for ids_name in coupled_ids_names],
                Operator.S: [f"{ids_name}_s" for ids_name in coupled_ids_names],
                Operator.O_F: [f"{ids_name}_o_f" for ids_name in coupled_ids_names],
            }
        )

    def get_equilibrium_ids(self) -> IDSToplevel:
        equilibrium_data = torax_state_to_imas_equilibrium(
            self.sim_state, self.post_processed_outputs
        )
        if self.extra_var_col is not None:
            equilibrium_data = merge_extra_vars(equilibrium_data, self.extra_var_col)
        return equilibrium_data

    def get_core_profiles_ids(self) -> IDSToplevel:
        core_profiles_data = core_profiles_to_IMAS(
            self.step_fn.runtime_params_provider,
            self.torax_config,
            [self.post_processed_outputs],
            [self.sim_state.core_profiles],
            [self.sim_state.core_sources],
            [self.sim_state.geometry],
            [self.sim_state.t],
        )
        return core_profiles_data

    def receive_equilibrium(self, port_name: str) -> None:
        if not self.instance.is_connected(f"equilibrium_{port_name}"):
            return
        equilibrium_data, self.t_cur, t_next = self.receive_ids(
            "equilibrium", port_name
        )
        if port_name == "f_init":
            self.t_next_outer = t_next
        elif port_name == "s":
            self.t_next_inner = t_next

        if (
            equilibrium_data.code.output_flag
            and equilibrium_data.code.output_flag[0] == -1
        ):
            return

        geometry_configs = {}
        torax_config_dict = get_geometry_config_dict(self.torax_config)
        torax_config_dict["geometry_type"] = "imas"

        with DBEntry("imas:memory?path=/", "w") as db:
            db.put(equilibrium_data)
            for t in equilibrium_data.time:
                my_slice = db.get_slice(
                    ids_name="equilibrium",
                    time_requested=t,
                    interpolation_method=CLOSEST_INTERP,
                )
                config_kwargs = {
                    **torax_config_dict,
                    "equilibrium_object": my_slice,
                    "imas_uri": None,
                    "imas_filepath": None,
                    "Ip_from_parameters": False,
                }
                imas_cfg = IMASConfig(**config_kwargs)
                cfg = GeometryConfig(config=imas_cfg)
                geometry_configs[str(t)] = cfg
                # temp extra vars code
                self.extra_var_col.add_val(
                    "z_boundary_outline",
                    t,
                    np.asarray(my_slice.time_slice[0].boundary.outline.z),
                )
                self.extra_var_col.add_val(
                    "r_boundary_outline",
                    t,
                    np.asarray(my_slice.time_slice[0].boundary.outline.r),
                )
        # temp extra vars code
        self.extra_var_col.pad_extra_vars()
        self.last_equilibrium_call = self.t_cur
        self.torax_config.update_fields(
            {
                "geometry": {
                    'geometry_type': geometry.GeometryType.IMAS,
                    'geometry_configs': geometry_configs,
                }
            }
        )
        self.step_fn = make_step_fn(self.torax_config)

    def receive_core_profiles(self, port_name: str) -> None:
        if not self.instance.is_connected(f"core_profiles_{port_name}"):
            return
        core_profiles_data, self.t_cur, t_next = self.receive_ids(
            "core_profiles", port_name
        )
        if port_name == "f_init":
            self.t_next_outer = t_next
        elif port_name == "s":
            self.t_next_inner = t_next

        if (
            core_profiles_data.code.output_flag
            and core_profiles_data.code.output_flag[0] == -1
        ):
            return

        core_profiles_conditions = profile_conditions_from_IMAS(core_profiles_data)
        self.torax_config.update_fields(
            {"profile_conditions": core_profiles_conditions}
        )
        self.step_fn = make_step_fn(self.torax_config)

    def receive_ids(
        self, ids_name: str, port_name: str
    ) -> Tuple[IDSToplevel, float, Optional[float]]:
        if not self.instance.is_connected(f"{ids_name}_{port_name}"):
            raise Warning("Calling receive while not connected")
        msg = self.instance.receive(f"{ids_name}_{port_name}")
        t_cur = msg.timestamp
        t_next = msg.next_timestamp
        ids_data = getattr(IDSFactory(), ids_name)()
        ids_data.deserialize(msg.data)
        return ids_data, t_cur, t_next

    def send_ids(self, ids: IDSToplevel, ids_name: str, port_name: str) -> None:
        if not self.instance.is_connected(f"{ids_name}_{port_name}"):
            return
        if port_name == "o_i":
            t_next = self.t_next_inner
        elif port_name == "o_f":
            t_next = self.t_next_outer
        msg = Message(self.t_cur, data=ids.serialize(), next_timestamp=t_next)
        self.instance.send(f"{ids_name}_{port_name}", msg)

    def get_t_next(self) -> Optional[float]:
        runtime_params_t, geo_t = get_consistent_runtime_params_and_geometry(
            t=self.sim_state.t,
            runtime_params_provider=self.step_fn.runtime_params_provider,
            geometry_provider=self.step_fn._geometry_provider,
        )
        dt = self.step_fn.time_step_calculator.next_dt(
            self.sim_state.t,
            runtime_params_t,
            geo_t,
            self.sim_state.core_profiles,
            self.sim_state.core_transport,
        )
        t_next = self.sim_state.t + dt
        if t_next >= self.t_final:
            t_next = None
        return t_next


def main() -> None:
    """Create TORAX instance and enter submodel execution loop"""
    logger.info("Starting TORAX actor")
    tmr = ToraxMuscleRunner()
    tmr.run_sim()


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    main()
