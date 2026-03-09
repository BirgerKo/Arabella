# VentoFanSim — minimal image for one containerised simulated fan.
#
# Build:
#   docker build -t ventosim .
#
# Run standalone (fan index 0 → device ID SIMFAN0000000001):
#   docker run --rm -e FAN_INDEX=0 ventosim
#
# Normally started via docker-compose.yml.

FROM python:3.11-slim

WORKDIR /app

# Only the packages the simulator depends on (no PyQt6, no GUI code)
COPY blauberg_vento/            blauberg_vento/
COPY ventocontrol/__init__.py   ventocontrol/__init__.py
COPY ventocontrol/simulator.py  ventocontrol/simulator.py

# blauberg_vento has zero third-party runtime dependencies — no pip install needed

# Expose the Blauberg Vento protocol port (UDP)
EXPOSE 4000/udp

# FAN_INDEX is read by simulator.py via os.environ and maps to --start-index.
# Override with  -e FAN_INDEX=2  to produce device ID SIMFAN0000000003.
ENV FAN_INDEX=0

# Always run a single fan per container; the index distinguishes device IDs.
CMD ["python", "-m", "ventocontrol.simulator", "--count", "1"]
