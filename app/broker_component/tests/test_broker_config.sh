mosquitto -c /mosquitto/config/mosquitto.conf -v
mosquitto_pub -h mqtt-broker -t "test/topic" -m "hello"
mosquitto_sub -h mqtt-broker -t "test/topic" -C 1
