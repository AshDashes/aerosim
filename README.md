# AeroSim - An Interactive 2-D Flight Simulator

> **Play Live in Browser (WebAssembly)**: [https://ashdashes.github.io/aerosim/](https://ashdashes.github.io/aerosim/)

<img width="800" alt="AeroSim Flight Simulator Demo" src="https://github.com/user-attachments/assets/320c9545-b194-4301-86e5-b50ae65da28e" />


**AeroSim** is a custom 2D flight simulator built from scratch in Python. It features custom-coded aerodynamics, real-time stall physics, and live FAA weather integration to model authentic flight conditions. It also includes an evolutionary neural network autopilot capable of learning flight control across Earth, Mars, and the Moon—fully playable in-browser or locally on desktop.

## Key Features:
### 1. First-Principles Flight Dynamics (`physics.py`)
* **4-Force Vector Resolution**: Computes real-time continuous vectors for Lift, Induced & Parasitic Drag, Engine Thrust, and Gravitational Weight.
* **Dynamic Control Surfaces**:
  * Wing Flaps deflection (`Clean`, `Takeoff 15°`, `Landing 30°`) with corresponding aerodynamic lift-to-drag trade-offs.
  * Retractable Landing Gear with parasitic drag penalties.
* **Flight Envelope & Stall Alarm**: Monitors critical angle-of-attack boundaries. Exceeding boundary limits triggers an aerodynamic stall with lift collapse and a warning alarm.
* **Ground Dynamics**: Simulates runway rolling friction, braking, and vertical touchdown descent velocity (distinguishing smooth landings from impact crashes).
* **Work-Energy Accounting**: Tracks continuous kinetic energy, gravitational potential, fuel burn, and total engine work done.
  
### 2. Multi-Planetary & Environmental Systems (`settings.py`)
* **Planetary Gravitational Profiles**:
  * **Earth**: $g = 9.81 \text{ m/s}^2$ 
  * **Mars**: $g = 3.71 \text{ m/s}^2$ 
  * **Moon**: $g = 1.62 \text{ m/s}^2$ 
* **Barometric Lapse Rate**: Calculates atmospheric density drop exponentially with altitude:
  $$\rho(y) = \rho_{\text{sea}} \cdot e^{-\frac{y}{8500}}$$
* **Turbulence & Sensor Noise**: Stochastic wind gusts and instrument jitter modeling real-world avionics disturbance.
  
### 3. Live Aviation Weather Integration (`weather.py`)
* Connects directly to the official **FAA/NOAA Aviation Weather API** (`aviationweather.gov`) using international ICAO station codes (e.g., CYYZ for Toronto Pearson, KJFK for New York).
* Uses regex to parse raw METAR strings for ambient temperature and altimeter / QNH barometric pressure.
* Dynamically calculates true real-world air density using the Ideal Gas Law:
  $$\rho = \frac{P}{R_{\text{specific}} \cdot T}$$
  Where $R_{\text{specific}} = 287.05 \text{ J/(kg}\cdot\text{K)}$.

### 4. Evolutionary Neural Autopilot (`brain.py`)
* **Hand-Built Neural Network**: 5-input, 6-hidden neuron, 2-output feed-forward network using hyperbolic tangent activation functions.
* **Genetic Algorithm**:
  * Evaluates population fitness based on pitch stability, runway distance, and altitude maintenance.
  * Implements elitism selection, uniform matrix crossover, and stochastic weight mutation to autonomously evolve stable flight controllers.

### 5. Avionics, Procedural Audio & UI (`main.py`)
* **Primary Flight Display (PFD)**:
  * Airspeed Indicator (knots)
  * Altimeter (feet)
  * Vertical Speed Indicator (VSI, ft/min)
  * Artificial Horizon (Attitude indicator showing live pitch and roll)
  * Dynamic FORCES Vector Diagram (live visual vectors for Lift, Drag, Thrust, and Weight)
* **Pre-Flight Startup Checklist**: Procedural startup sequence requiring Battery, Alternator, Fuel Pump, and Magnetos Ignition before engine turnover.
* **Procedural Sound Engine**: Mathematically synthesizes pure `.wav` audio files using mathematical sine waves and white noise decay envelopes (engine hum, stall alarm, switch clicks, and crash transients).

## Flight Controls
* **Throttle Up / Down**: `Up Arrow` / `Down Arrow`
* **Pitch Nose Up / Down**: `Right Arrow` / `Left Arrow`
* **Cycle Flaps**: `F` (`Retracted` -> `Takeoff 15°` -> `Landing 30°`)
* **Toggle Landing Gear**: `G` (`UP` / `DOWN`)
* **Reset Runway**: `R`
* **Return to Main Menu**: `M`
