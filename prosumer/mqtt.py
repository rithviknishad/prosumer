from typing import Final

from django.conf import settings
from paho.mqtt.client import Client


def _state_to_mqtt_payload(key: str, value: any):
    return {
        "topic": f"prosumers/{SHORT_VP_ADDRESS}/{key}",
        "payload": str(value),
        "retain": True,
    }


def prosumer_state_key_to_topic(state_key: str) -> str:
    return f"prosumers/{SHORT_VP_ADDRESS}/{state_key}"


def _on_connect(_client, _userdata, _flags, return_code) -> None:
    print(f"mqtt_client::connected with rc=${return_code}")


def _on_message(_client, _userdata, msg) -> None:
    print(f"mqtt_client::new_msg: {msg}")


def _on_connect_fail(_userdata):
    print("mqtt_client::connect fail")


def _on_disconnect(*args, **kwargs) -> None:
    print(f"mqtt_client::disconnected {args}   {kwargs}")


PROSUMER_SETTINGS: Final = settings.PROSUMER_CONFIG["settings"]
SERVER: Final[str] = PROSUMER_SETTINGS["server"]
PORT: Final[int] = PROSUMER_SETTINGS["mqttPort"]
VP_ADDRESS: Final[str] = PROSUMER_SETTINGS["vpAddress"]
SHORT_VP_ADDRESS: Final = VP_ADDRESS.split(":")[-1]

client: Final[Client] = Client(client_id=SHORT_VP_ADDRESS)

client.on_connect = _on_connect
client.on_message = _on_message
client.on_connect_fail = _on_connect_fail
client.on_disconnect = _on_disconnect

client.will_set(**_state_to_mqtt_payload(*("isOnline", False)))

client.connect(SERVER, PORT)
client.loop_start()


def set_state(state: str, value: any, parent_state: str | None = None) -> None:
    state = "/".join([parent_state, state]) if parent_state else state
    if isinstance(value, list):
        return set_states({str(k): v for k, v in dict(enumerate(value)).items()}, state)
    if isinstance(value, dict):
        return set_states(states=value, parent_state=state)
    client.publish(**_state_to_mqtt_payload(state, value))


def set_states(states: dict[str, any], parent_state: str | None = None) -> None:
    for item in states.items():
        set_state(*item, parent_state=parent_state)
