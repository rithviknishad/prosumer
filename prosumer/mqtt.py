import paho.mqtt.client as mqtt


def on_connect(client, userdata, rc) -> None:
    pass


def on_message(client, userdata, msg) -> None:
    pass


client = mqtt.Client()

client.on_connect = on_connect
client.on_message = on_message
