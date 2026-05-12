---
title: Spaceship Game
emoji: 🚀
colorFrom: red
colorTo: blue
sdk: static
pinned: false
short_description: A 3D space shooter controlled by Reachy Mini's head !
tags:
 - reachy_mini
 - reachy_mini_python_app
---

# Spaceship Game

A 3D space shooter game for Reachy Mini where you control a spaceship using the robot's head movements and fire weapons by pulling the antennas. Features wave-based gameplay with increasing difficulty.

![Spaceship Game Screenshot](spaceship_game/assets/screenshot.png)

## Features

- **Physical Controls**: Move Reachy Mini's head to aim the spaceship in 3D space
- **Dual Weapons**: Pull left and right antennas independently to fire guns
- **Wave System**: Face increasingly difficult waves of enemy ships
- **Three Enemy Types**: Red (basic), Orange (fast/aimed), Purple (heavy/spread)

## Setup

### 1. Install Dependencies

```bash
pip install -e .
```

### 2. Run the Game

Run the app through the Reachy Mini app manager or directly:

```bash
python -m spaceship_game.main
```

## How to Play

1. **Start**: Aim at the glowing button and pull an antenna to start
2. **Aim**: Tilt head up/down and turn left/right to aim the spaceship
3. **Fire**: Pull the left or right antenna down to shoot the respective gun
4. **Survive**: Destroy enemies and dodge their bullets
5. **Score**: Each enemy type gives different points (Red: 100, Orange: 150, Purple: 300)

## Game Over

When your health reaches zero, shoot the restart button to play again!