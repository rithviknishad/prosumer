from typing import Optional

from paho.mqtt.client import Client


def _on_connect(_client, _userdata, _flags, return_code) -> None:
    print(f"mqtt_client::connected with rc=${return_code}")


def _on_message(_client, _userdata, msg) -> None:
    print(f"mqtt_client::new_msg: {msg}")


def _on_connect_fail(_userdata):
    print("mqtt_client::connect fail")


def _on_disconnect(*args, **kwargs) -> None:
    print(f"mqtt_client::disconnected {args}   {kwargs}")


class ProsumerMqttClient(Client):
    "Custom MQTT client for prosumer."

    def __init__(self, vp_address: str, server: str, port: int, *args, **kwargs):
        self.short_vp_addr = vp_address.split(":")[-1]
        super().__init__(client_id=self.short_vp_addr, *args, **kwargs)
        self.on_connect = _on_connect
        self.on_disconnect = _on_disconnect
        self.on_message = _on_message
        self.on_connect_fail = _on_connect_fail
        self.will_set(**self._state_to_mqtt_payload(*("isOnline", False)))
        self.connect(server, port)
        self.loop_start()

    def _state_to_mqtt_payload(self, state: str, value: any):
        return {
            "topic": f"prosumers/{self.short_vp_addr}/{state}",
            "payload": str(value),
            "retain": True,
        }

    def set_state(
        self, state: str, value: any, parent_state: Optional[str] = None
    ) -> None:
        if state.startswith("$"):
            return
        state = "/".join([parent_state, state]) if parent_state else state
        if isinstance(value, list):
            return self.set_states(
                {str(k): v for k, v in dict(enumerate(value)).items()}, state
            )
        if isinstance(value, dict):
            return self.set_states(states=value, parent_state=state)
        self.publish(**self._state_to_mqtt_payload(state, value))

    def set_states(
        self, states: dict[str, any], parent_state: str | None = None
    ) -> None:
        for item in states.items():
            self.set_state(*item, parent_state=parent_state)
