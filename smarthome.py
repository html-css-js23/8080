from flask import Flask, render_template, request, jsonify
import paho.mqtt.client as mqtt
import json

# Flask app setup
app = Flask(__name__)

# MQTT settings
MQTT_BROKER = "192.168.1.207"  # Replace with your broker's IP
MQTT_PORT = 1883
MQTT_USERNAME = "pcalex"
MQTT_PASSWORD = "pcalex"

# Topics for the two lights
LIGHTS = {
    "bedside_lamp": "zigbee2mqtt/Alex's Bedside Lamp/set",
    "desk_lamp": "zigbee2mqtt/Alex's Desk Lamp/set",
    "kbr_light": "zigbee2mqtt/Kid's Bedroom Light Switch/set",
    "hlw_light": "zigbee2mqtt/Hallway Light Switch/set",
}

# Zigbee button topic
BUTTON_TOPIC = "zigbee2mqtt/0x54ef441000d32500"


# MQTT client setup
mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
except Exception as e:
    print(f"Failed to connect to MQTT broker: {e}")
    exit(1)

# Light state tracker
light_states = {
    "bedside_lamp": "OFF",
    "desk_lamp": "OFF",
}

# Function to toggle light state
def toggle_light(light):
    global light_states
    current_state = light_states.get(light, "OFF")
    new_state = "OFF" if current_state == "ON" else "ON"
    topic = LIGHTS.get(light)
    if topic:
        mqtt_client.publish(topic, json.dumps({"state": new_state}))
        light_states[light] = new_state
        print(f"Toggled {light} to {new_state}")


# MQTT message callback
def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode())
        
        # Check if the message is from the button
        if topic == BUTTON_TOPIC:
            action = payload.get("action")
            
            if action == "single":
                toggle_light("desk_lamp")  # Toggle Alex's Desk Lamp
            elif action == "double":
                toggle_light("bedside_lamp")  # Toggle Alex's Bedside Lamp
            elif action == "hold":
                toggle_light("desk_lamp")  # Toggle Alex's Desk Lamp
                toggle_light("bedside_lamp")  # Toggle Alex's Bedside Lamp
    except Exception as e:
        print(f"Error processing message: {e}")


# Attach the MQTT message callback
mqtt_client.on_message = on_message

# Subscribe to the button topic
mqtt_client.subscribe(BUTTON_TOPIC)


# Flask Routes
@app.route("/")
def index():
    return render_template("index.html")  # HTML page with control UI

@app.route("/control", methods=["POST"])
def control():
    try:
        data = request.json
        light = data["light"]  # "bedside_lamp", "desk_lamp", or "kbr_light"
        command = data["command"]  # Command payload
        
        if light in LIGHTS:
            topic = LIGHTS[light]

            if "color" in command:
                color = command["color"]
                if color.get("r") == 255 and color.get("g") == 255 and color.get("b") == 255:
                    mqtt_client.publish(topic, json.dumps({"color_temp": 1000}))
                    return jsonify({"status": "success"}), 200
                else:
                    mqtt_client.publish(topic, json.dumps(command))
                    return jsonify({"status": "success"}), 200
            
            # Handle color changes
            if "color" in command:
                mqtt_client.publish(topic, json.dumps(command))
                return jsonify({"status": "success"}), 200

            # Handle brightness changes
            if "brightness" in command:
                mqtt_client.publish(topic, json.dumps({"brightness": command["brightness"]}))
                return jsonify({"status": "success"}), 200

            # Handle turning light ON or OFF
            if "state" in command:
                mqtt_client.publish(topic, json.dumps({"state": command["state"]}))
                return jsonify({"status": "success"}), 200
            
            if "state_left" in command or "state_right" in command:
                mqtt_client.publish(topic, json.dumps(command))
                print(f"MQTT Publish: Topic={topic}, Payload={command}")  # Debugging log
                return jsonify({"status": "success"}), 200

            return jsonify({"status": "success"}), 200

        else:
            return jsonify({"status": "error", "message": "Invalid light"}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
