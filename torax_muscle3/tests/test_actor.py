import imas
import libmuscle
import pytest
import ymmsl
from imas.ids_defs import CLOSEST_INTERP

import torax_muscle3
from torax_muscle3.torax_actor import main as torax_actor


def source_for_tests():
    """MUSCLE3 actor sending out imas data to test torax-m3 actor"""
    instance = libmuscle.Instance()
    ports = instance.list_ports()[ymmsl.Operator.O_F]
    imas_filepath = instance.get_setting("imas_source")
    with imas.DBEntry(uri=imas_filepath, mode="r") as db:
        while instance.reuse_instance():
            for port in ports:
                ids_name = port.replace("_out", "")
                ids_data = db.get(ids_name=ids_name)
                msg_out = libmuscle.Message(
                    0, data=ids_data.serialize(), next_timestamp=None
                )
                instance.send(port, msg_out)


def sink_for_tests():
    """MUSCLE3 actor receiving imas data to test torax-m3 actor"""
    instance = libmuscle.Instance()
    ports = instance.list_ports()[ymmsl.Operator.F_INIT]
    data_sink_path = instance.get_setting("imas_sink")
    with imas.DBEntry(uri=data_sink_path, mode="w") as db:
        while instance.reuse_instance():
            for port in ports:
                ids_name = port.replace("_in", "")
                msg_in = instance.receive(port)
                ids_data = getattr(imas.IDSFactory(), ids_name)()
                ids_data.deserialize(msg_in.data)
                db.put(ids_data)


def reply_for_tests():
    instance = libmuscle.Instance()
    imas_filepath = instance.get_setting("imas_source")
    with imas.DBEntry(uri=imas_filepath, mode="r") as db:
        equilibrium_data = db.get(ids_name="equilibrium")
        with imas.DBEntry("imas:memory?path=/", "w") as db2:
            db2.put(equilibrium_data)
            while instance.reuse_instance():
                msg_in = instance.receive("equilibrium_in")
                equilibrium_data = db2.get_slice(
                    ids_name="equilibrium",
                    time_requested=msg_in.timestamp,
                    interpolation_method=CLOSEST_INTERP,
                )
                msg_equilibrium_out = libmuscle.Message(
                    msg_in.timestamp,
                    data=equilibrium_data.serialize(),
                    next_timestamp=msg_in.next_timestamp,
                )
                instance.send("equilibrium_out", msg_equilibrium_out)


def mirror_for_tests():
    """MUSCLE3 actor receiving imas data to test torax-m3 actor"""
    instance = libmuscle.Instance()
    ports = instance.list_ports()[ymmsl.Operator.F_INIT]
    while instance.reuse_instance():
        for port in ports:
            msg_in = instance.receive(port)
            instance.send(port.replace("_in", "_out"), msg_in)


YMMSL_OUTPUT_TEMPLATE = """
ymmsl_version: v0.1
model:
  name: test_model
  components:
    sink:
      implementation: sink
      ports:
        f_init: [IDS_NAME_in]
    torax:
      implementation: torax
      ports:
        o_f: [IDS_NAME_o_f]
  conduits:
    torax.IDS_NAME_o_f: sink.IDS_NAME_in
settings:
  sink.imas_sink: {data_sink_path}
  torax.python_config_module: {config_path}
"""

YMMSL_INPUT_TEMPLATE = """
ymmsl_version: v0.1
model:
  name: test_model
  components:
    source:
      implementation: source
      ports:
        o_f: [IDS_NAME_out]
    torax:
      implementation: torax
      ports:
        f_init: [IDS_NAME_f_init]
  conduits:
    source.IDS_NAME_out: torax.IDS_NAME_f_init
settings:
  source.imas_source: {data_source_path}
  torax.python_config_module: {config_path}
"""

YMMSL_REPLY_TEMPLATE = """
ymmsl_version: v0.1
model:
  name: test_model
  components:
    reply:
      implementation: reply
      ports:
        f_init: [IDS_NAME_in]
        o_f: [IDS_NAME_out]
    torax:
      implementation: torax
      ports:
        s: [IDS_NAME_s]
        o_i: [IDS_NAME_o_i]
  conduits:
    torax.IDS_NAME_o_i: reply.IDS_NAME_in
    reply.IDS_NAME_out: torax.IDS_NAME_s
settings:
  reply.imas_source: {data_source_path}
  torax.python_config_module: {config_path}
"""

YMMSL_INNER_TEMPLATE = """
ymmsl_version: v0.1
model:
  name: test_model
  components:
    mirror:
      implementation: mirror
      ports:
        f_init: [IDS_NAME_in]
        o_f: [IDS_NAME_out]
    torax:
      implementation: torax
      ports:
        s: [IDS_NAME_s]
        o_i: [IDS_NAME_o_i]
  conduits:
    torax.IDS_NAME_o_i: mirror.IDS_NAME_in
    mirror.IDS_NAME_out: torax.IDS_NAME_s
settings:
  torax.python_config_module: {config_path}
"""

YMMSL_INPUT_EQUILIBRIUM = YMMSL_INPUT_TEMPLATE.replace("IDS_NAME", "equilibrium")
YMMSL_INPUT_CORE_PROFILES = YMMSL_INPUT_TEMPLATE.replace("IDS_NAME", "core_profiles")
YMMSL_OUTPUT_EQUILIBRIUM = YMMSL_OUTPUT_TEMPLATE.replace("IDS_NAME", "equilibrium")
YMMSL_OUTPUT_CORE_PROFILES = YMMSL_OUTPUT_TEMPLATE.replace("IDS_NAME", "core_profiles")
YMMSL_REPLY_EQUILIBRIUM = YMMSL_REPLY_TEMPLATE.replace("IDS_NAME", "equilibrium")
YMMSL_REPLY_CORE_PROFILES = YMMSL_REPLY_TEMPLATE.replace("IDS_NAME", "core_profiles")
YMMSL_INNER_EQUILIBRIUM = YMMSL_INNER_TEMPLATE.replace("IDS_NAME", "equilibrium")
YMMSL_INNER_CORE_PROFILES = YMMSL_INNER_TEMPLATE.replace("IDS_NAME", "core_profiles")


@pytest.mark.parametrize(
    "ymmsl_text",
    [
        pytest.param(YMMSL_INPUT_EQUILIBRIUM, id="input equilibrium"),
        pytest.param(YMMSL_OUTPUT_EQUILIBRIUM, id="output equilibrium"),
        pytest.param(YMMSL_OUTPUT_CORE_PROFILES, id="output core_profiles"),
        pytest.param(YMMSL_REPLY_EQUILIBRIUM, id="reply equilibrium"),
        pytest.param(YMMSL_INNER_CORE_PROFILES, id="inner core_profiles"),
        # # no core_profiles in input_data
        # pytest.param(YMMSL_INPUT_CORE_PROFILES, id='input core_profiles'),
        # # equilibrium_output not sufficient for equilibrium input
        # pytest.param(YMMSL_INNER_EQUILIBRIUM, id='inner equilibrium'),
    ],
)
@pytest.mark.filterwarnings("ignore:.*use of fork():DeprecationWarning")
def test_actor(tmp_path, monkeypatch, ymmsl_text):
    monkeypatch.chdir(tmp_path)
    filename = "ITERhybrid_COCOS17_IDS_ddv4.nc"
    data_source_path = f"{torax_muscle3.__path__[0]}/tests/data/{filename}"
    data_sink_path = f"imas:hdf5?path={(tmp_path / 'sink_dir').absolute()}"
    config_path = f"{torax_muscle3.__path__[0]}/tests/basic_config.py"
    configuration = ymmsl.load(
        ymmsl_text.format(
            data_source_path=data_source_path,
            data_sink_path=data_sink_path,
            config_path=config_path,
        )
    )
    implementations = {
        "reply": reply_for_tests,
        "mirror": mirror_for_tests,
        "sink": sink_for_tests,
        "source": source_for_tests,
        "torax": torax_actor,
    }
    libmuscle.runner.run_simulation(configuration, implementations)
