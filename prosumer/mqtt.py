import base64
from typing import Final

from django.conf import settings
from paho.mqtt.client import Client


def _state_to_mqtt_payload(key: str, value: any):
    return {
        "topic": f"prosumers/{SHORT_VP_ADDRESS}/{key}",
        "payload": value,
        "retain": True,
    }


def prosumer_state_key_to_topic(state_key: str) -> str:
    return f"prosumers/{SHORT_VP_ADDRESS}/{state_key}"


def _on_connect(client, userdata, flags, rc) -> None:
    print(f"mqtt_client::connected with rc=${rc}")


def _on_message(client, userdata, msg) -> None:
    print(f"mqtt_client::new_msg: {msg}")


def _on_connect_fail(userdata):
    print("mqtt_client::connect fail")


def _on_disconnect(*args, **kwargs) -> None:
    print(f"mqtt_client::disconnected {args}   {kwargs}")


CONFIG: Final = settings.PROSUMER_CONFIG
SERVER: Final[str] = CONFIG["server"]
PORT: Final[int] = CONFIG["mqtt_port"]
VP_ADDRESS: Final[str] = CONFIG["vp_address"]
SHORT_VP_ADDRESS: Final = VP_ADDRESS.split(":")[-1]

_client: Final[Client] = Client(
    client_id=base64.b64encode(VP_ADDRESS.encode("ascii")).decode("ascii")
)

_client.on_connect = _on_connect
_client.on_message = _on_message
_client.on_connect_fail = _on_connect_fail
_client.on_disconnect = _on_disconnect

_client.will_set(**_state_to_mqtt_payload(*("isOnline", False)))

_client.connect(SERVER, PORT)
_client.loop_start()


def update_state(state: str, value: any) -> None:
    _client.publish(**_state_to_mqtt_payload(state, value))


def update_states(states: dict[str, any]) -> None:
    for item in states.items():
        _client.publish(**_state_to_mqtt_payload(*item))
