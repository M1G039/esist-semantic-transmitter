Setting up Mosquitto directly on a Raspberry Pi is very straightforward because it is natively available in the standard Raspberry Pi OS (Debian) repositories. [sunfounder](https://www.sunfounder.com/blogs/news/how-to-set-up-a-raspberry-pi-mqtt-broker-a-complete-guide)

Here are the exact steps to install, configure, and run it.

### 1. Update your system
Before installing anything, open the Raspberry Pi terminal (or connect via SSH) and update the package list: [tech-sparks](https://www.tech-sparks.com/install-mosquitto-on-raspberry-pi/)
```bash
sudo apt update
sudo apt upgrade -y
```

### 2. Install Mosquitto and Client Tools
Install the Mosquitto broker and the command-line clients (which you will need for testing): [sunfounder](https://www.sunfounder.com/blogs/news/how-to-set-up-a-raspberry-pi-mqtt-broker-a-complete-guide)
```bash
sudo apt install -y mosquitto mosquitto-clients
```

### 3. Ensure the service runs on boot
By default, the installation will start the service and enable it to run on boot. You can verify that it is running with: [pimylifeup](https://pimylifeup.com/raspberry-pi-mosquitto-mqtt-server/)
```bash
sudo systemctl status mosquitto
```
If it is not running, start and enable it manually: [sunfounder](https://www.sunfounder.com/blogs/news/how-to-set-up-a-raspberry-pi-mqtt-broker-a-complete-guide)
```bash
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

### 4. Configure Mosquitto for external access
By default, newer versions of Mosquitto (v2.0+) only allow connections from `localhost` and require authentication. Since you want to connect to it from other devices (like your semantic transmitter), you need to change this. [randomnerdtutorials](https://randomnerdtutorials.com/how-to-install-mosquitto-broker-on-raspberry-pi/)

Open the configuration file using the `nano` text editor:
```bash
sudo nano /etc/mosquitto/mosquitto.conf
```
Scroll to the bottom of the file and add these two lines: [randomnerdtutorials](https://randomnerdtutorials.com/how-to-install-mosquitto-broker-on-raspberry-pi/)
```text
listener 1883 0.0.0.0
allow_anonymous true
```
*(Note: `allow_anonymous true` is fine for testing or private Tailscale networks. If this Pi will be exposed to the public internet, you should set up password authentication instead.)*

Save the file (`Ctrl+O`, then `Enter`) and exit (`Ctrl+X`).

Restart Mosquitto to apply the changes:
```bash
sudo systemctl restart mosquitto
```

### 5. Test the Broker locally
You can use the client tools you installed to ensure the broker is working. [sunfounder](https://www.sunfounder.com/blogs/news/how-to-set-up-a-raspberry-pi-mqtt-broker-a-complete-guide)

Open two separate terminal windows on the Pi (or use two SSH sessions).
**In Terminal 1 (Subscriber):**
```bash
mosquitto_sub -h localhost -t "test/topic"
```
**In Terminal 2 (Publisher):**
```bash
mosquitto_pub -h localhost -t "test/topic" -m "Hello from Raspberry Pi!"
```
If everything is working, you will see the "Hello from Raspberry Pi!" message appear in Terminal 1. [stevessmarthomeguide](https://stevessmarthomeguide.com/install-mosquitto-raspberry-pi/)

### Connecting from your project
Once this is done, you can point your Python code (`MQTT_BROKER_ADDRESS`) to the Raspberry Pi's IP address or its Tailscale MagicDNS name (if you install Tailscale on the Pi) just as we discussed previously!


---

## This is just a code snippet for the `main()` in `app.py`

```
if st.session_state.transport_mode == TRANSPORT_MQTT:
        col_host, col_port = st.columns([3, 1])

        with col_host:
            st.session_state.mqtt_broker_host = st.text_input(
                "MQTT Broker Address",
                value=st.session_state.get("mqtt_broker_host", ""),
                placeholder="home-llms.tailnet-name.ts.net",
                help="Use the Tailscale IP or MagicDNS name of the machine running Mosquitto.",
            )

        with col_port:
            st.session_state.mqtt_broker_port = st.number_input(
                "Port",
                min_value=1,
                max_value=65535,
                value=int(st.session_state.get("mqtt_broker_port", 1883)),
                step=1,
            )

        col_connect, col_disconnect = st.columns(2)

        with col_connect:
            if st.button("Connect", use_container_width=True):
                broker_host = st.session_state.mqtt_broker_host.strip()
                broker_port = int(st.session_state.mqtt_broker_port)

                if not broker_host:
                    st.error("Please enter an MQTT broker address.")
                else:
                    try:
                        st.session_state.mqtt_client = MQTT_ClientWrapper(
                            broker_host=broker_host,
                            broker_port=broker_port,
                        )
                        st.session_state.mqtt_client.connect()
                        add_event(
                            "MQTT",
                            f"Connecting to broker at {broker_host}:{broker_port}...",
                            "info",
                        )
                    except Exception as exc:
                        st.session_state.mqtt_client = None
                        add_event("MQTT", str(exc), "error")
                        st.error(str(exc))

        with col_disconnect:
            if st.button("Disconnect", use_container_width=True):
                if st.session_state.mqtt_client is not None:
                    try:
                        st.session_state.mqtt_client.disconnect()
                        add_event("MQTT", "Disconnected from broker.", "info")
                    except Exception as exc:
                        add_event("MQTT", str(exc), "error")
                        st.error(str(exc))
                    finally:
                        st.session_state.mqtt_client = None

        if st.session_state.mqtt_client is not None:
            state = st.session_state.mqtt_client.connection_state
            if state == ConnectionState.CONNECTED:
                st.success(
                    f"Connected to MQTT broker at "
                    f"{st.session_state.mqtt_broker_host}:{st.session_state.mqtt_broker_port}"
                )
            elif state == ConnectionState.CONNECTING:
                st.info("Connecting to broker...")
            else:
                error_msg = getattr(st.session_state.mqtt_client, "last_error", None)
                if error_msg:
                    st.error(f"Not connected: {error_msg}")
                else:
                    st.error("Not connected")
        else:
            st.warning("Enter broker address and press Connect.")
```
