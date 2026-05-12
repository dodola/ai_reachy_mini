import * as THREE from 'three';

async function startMusic() {
    try {
        await fetch('/start_music', { method: 'POST' });
    } catch (e) {
        console.error('Error starting music:', e);
    }
}

// Game state
let scene, camera, renderer;
let spaceship, spaceshipParts = {};
let stars = [];
let asteroids = [];
let enemies = [];
let projectiles = [];
let enemyBullets = [];
let explosions = [];
let sensorData = { roll: 0, pitch: 0, yaw: 0, antennas: { right: 0, left: 0 }, fire_left: false, fire_right: false, score: 0, health: 100 };
let lastFireLeftState = false;
let lastFireRightState = false;
let gameStarted = false;
let startButton = null;
let gameOver = false;
let finalScore = 0;

// Wave system
let currentWave = 0;
let enemiesSpawnedThisWave = 0;
let enemiesToSpawnThisWave = 0;
let waveInProgress = false;
let timeBetweenWaves = 5000; // 5 seconds between waves
let nextWaveTime = 0;

// Game settings
const SMOOTHING = 0.15;
const MOVEMENT_SCALE = 1.8;
const YAW_MOVEMENT_SCALE = 0.3;
const SPEED = 0.5;
const FORWARD_SPEED = 1.5; // Speed moving through space
const MAX_ASTEROIDS = 10;
const ASTEROID_SPAWN_INTERVAL = 3000;
const ENEMY_SPAWN_INTERVAL = 2500;
const MAX_ENEMIES = 8;

// Initialize the scene
function init() {
    // Scene setup
    scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x000000, 0.0008);

    // Camera setup - positioned behind the spaceship
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(0, 2, 8);
    camera.lookAt(0, 2, 0);

    // Renderer setup
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    document.getElementById('game-canvas').appendChild(renderer.domElement);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0x404040, 1);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
    directionalLight.position.set(5, 10, 7.5);
    scene.add(directionalLight);

    // Create starfield
    createStarfield();

    // Create spaceship
    createSpaceship();

    // Create initial asteroids
    for (let i = 0; i < 5; i++) {
        createAsteroid();
    }

    // Handle window resize
    window.addEventListener('resize', onWindowResize, false);

    // Start game loop
    animate();

    // Create start button
    createStartButton();

    // Start fetching sensor data
    fetchSensorData();

    // Spawn asteroids periodically (only when game started)
    setInterval(() => {
        if (gameStarted && !gameOver) createAsteroid();
    }, ASTEROID_SPAWN_INTERVAL);

    // Wave-based enemy spawning handled in animate loop

}

function createStartButton() {
    const buttonGroup = new THREE.Group();

    // Create a large glowing target
    const buttonGeometry = new THREE.CylinderGeometry(4, 4, 1, 32);
    const buttonMaterial = new THREE.MeshPhongMaterial({
        color: 0x00ff00,
        emissive: 0x00ff00,
        emissiveIntensity: 0.5
    });
    const button = new THREE.Mesh(buttonGeometry, buttonMaterial);
    button.rotation.x = Math.PI / 2;
    buttonGroup.add(button);

    // Outer ring
    const ringGeometry = new THREE.TorusGeometry(5, 0.3, 16, 32);
    const ringMaterial = new THREE.MeshBasicMaterial({
        color: 0x00ff00,
        transparent: true,
        opacity: 0.7
    });
    const ring = new THREE.Mesh(ringGeometry, ringMaterial);
    ring.rotation.x = Math.PI / 2;
    buttonGroup.add(ring);

    // Inner glow
    const glowGeometry = new THREE.SphereGeometry(3, 32, 32);
    const glowMaterial = new THREE.MeshBasicMaterial({
        color: 0x00ff00,
        transparent: true,
        opacity: 0.3
    });
    const glow = new THREE.Mesh(glowGeometry, glowMaterial);
    buttonGroup.add(glow);

    // Position in front of player
    buttonGroup.position.set(0, 0, -40);

    buttonGroup.userData = {
        button: button,
        ring: ring,
        glow: glow
    };

    scene.add(buttonGroup);
    startButton = buttonGroup;
}

function removeStartButton() {
    if (startButton) {
        scene.remove(startButton);
        startButton = null;
    }
}

function triggerGameOver() {
    gameOver = true;
    gameStarted = false;
    finalScore = sensorData.score;

    // Clear all game objects
    clearGameObjects();

    // Show name entry overlay (will show game over screen after submission)
    showNameOverlay(finalScore);

    console.log('Game Over! Final Score:', finalScore);
}

function clearGameObjects() {
    // Remove all enemies
    for (let i = enemies.length - 1; i >= 0; i--) {
        scene.remove(enemies[i]);
    }
    enemies = [];

    // Remove all asteroids
    for (let i = asteroids.length - 1; i >= 0; i--) {
        scene.remove(asteroids[i]);
    }
    asteroids = [];

    // Remove all enemy bullets
    for (let i = enemyBullets.length - 1; i >= 0; i--) {
        scene.remove(enemyBullets[i]);
    }
    enemyBullets = [];

    // Remove all projectiles
    for (let i = projectiles.length - 1; i >= 0; i--) {
        scene.remove(projectiles[i]);
    }
    projectiles = [];
}

function showGameOverScreen() {
    // Update start message to show game over
    const startMsg = document.getElementById('start-message');
    if (startMsg) {
        startMsg.innerHTML = `
            <div style="color: #f00; font-size: 64px; text-shadow: 0 0 30px #f00;">GAME OVER</div>
            <div style="color: #0ff; font-size: 48px; margin-top: 20px; text-shadow: 0 0 20px #0ff;">SCORE: ${finalScore}</div>
            <div style="font-size: 32px; margin-top: 30px; color: #0f0; text-shadow: 0 0 20px #0f0;">SHOOT TO RESTART</div>
            <div style="font-size: 20px; margin-top: 15px; opacity: 0.7;">AIM AND FIRE AT THE TARGET</div>
        `;
        startMsg.style.display = 'block';
    }

    // Create restart button
    createStartButton();
}

async function resetGame() {
    gameOver = false;
    gameStarted = true;
    finalScore = 0;

    // Reset local sensorData immediately to avoid triggering game over on the next poll
    // before the backend /reset_game response arrives
    sensorData.health = 100;
    sensorData.score = 0;

    // Reset wave system
    currentWave = 0;
    enemiesSpawnedThisWave = 0;
    enemiesToSpawnThisWave = 0;
    waveInProgress = false;
    nextWaveTime = Date.now() + 1000; // Start first wave after 1 second

    // Reset backend score and health
    try {
        await fetch('/reset_game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
    } catch (e) {
        console.error('Error resetting game:', e);
    }

    // Hide start/game over message
    const startMsg = document.getElementById('start-message');
    if (startMsg) {
        startMsg.style.display = 'none';
    }

    // Hide wave announcement
    const waveMsg = document.getElementById('wave-message');
    if (waveMsg) {
        waveMsg.style.display = 'none';
    }

    // Hide leaderboard panel
    const lbPanel = document.getElementById('leaderboard-panel');
    if (lbPanel) lbPanel.style.display = 'none';

    console.log('Game restarted!');
}

function startNewWave() {
    currentWave++;
    waveInProgress = true;
    enemiesSpawnedThisWave = 0;

    // Calculate enemies for this wave — steeper curve
    // Wave 1: 4, Wave 2: 6, Wave 3: 7, Wave 5: 10, Wave 8: 15...
    enemiesToSpawnThisWave = 3 + currentWave + Math.floor(currentWave / 2);

    // Show wave announcement
    showWaveAnnouncement();

    console.log(`Wave ${currentWave} started! Enemies: ${enemiesToSpawnThisWave}`);
}

function showWaveAnnouncement() {
    const waveMsg = document.getElementById('wave-message');
    if (waveMsg) {
        waveMsg.innerHTML = `
            <div style="font-size: 72px; animation: pulse 0.5s;">WAVE ${currentWave}</div>
            <div style="font-size: 32px; margin-top: 10px;">${enemiesToSpawnThisWave} ENEMIES</div>
        `;
        waveMsg.style.display = 'block';

        // Hide after 2 seconds
        setTimeout(() => {
            waveMsg.style.display = 'none';
        }, 2000);
    }
}

function spawnWaveEnemy() {
    if (!waveInProgress || enemiesSpawnedThisWave >= enemiesToSpawnThisWave) return;

    // Spawn with variety based on wave
    let enemyType = null;

    // Special wave compositions
    if (currentWave % 5 === 0) {
        // Boss wave - all heavy enemies
        enemyType = 2;
    } else if (currentWave % 3 === 0) {
        // Fast wave - mostly fast enemies
        enemyType = Math.random() < 0.8 ? 1 : 2;
    }

    createEnemy(enemyType);
    enemiesSpawnedThisWave++;
}

function checkWaveComplete() {
    if (waveInProgress && enemiesSpawnedThisWave >= enemiesToSpawnThisWave && enemies.length === 0) {
        // Wave complete!
        waveInProgress = false;
        nextWaveTime = Date.now() + Math.max(3000, timeBetweenWaves - currentWave * 200);

        // Show wave clear message
        const waveMsg = document.getElementById('wave-message');
        if (waveMsg) {
            waveMsg.innerHTML = `
                <div style="color: #0f0; font-size: 64px;">WAVE CLEAR!</div>
                <div style="font-size: 32px; margin-top: 10px;">Next wave in 3 seconds...</div>
            `;
            waveMsg.style.display = 'block';

            setTimeout(() => {
                waveMsg.style.display = 'none';
            }, 2500);
        }

        console.log(`Wave ${currentWave} complete!`);
    }
}

function createSpaceship() {
    spaceship = new THREE.Group();

    // Main body - fuselage
    const bodyGeometry = new THREE.ConeGeometry(0.5, 2, 8);
    const bodyMaterial = new THREE.MeshPhongMaterial({
        color: 0x00ccff,
        emissive: 0x004466,
        shininess: 100
    });
    const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
    body.rotation.x = Math.PI / 2;
    spaceship.add(body);
    spaceshipParts.body = body;

    // Wings
    const wingGeometry = new THREE.BoxGeometry(3, 0.1, 0.8);
    const wingMaterial = new THREE.MeshPhongMaterial({
        color: 0x0099cc,
        emissive: 0x003344
    });
    const wings = new THREE.Mesh(wingGeometry, wingMaterial);
    wings.position.z = 0.3;
    spaceship.add(wings);
    spaceshipParts.wings = wings;

    // Cockpit
    const cockpitGeometry = new THREE.SphereGeometry(0.3, 16, 16);
    const cockpitMaterial = new THREE.MeshPhongMaterial({
        color: 0x88ffff,
        emissive: 0x004466,
        transparent: true,
        opacity: 0.8
    });
    const cockpit = new THREE.Mesh(cockpitGeometry, cockpitMaterial);
    cockpit.position.z = -0.5;
    cockpit.scale.z = 0.7;
    spaceship.add(cockpit);
    spaceshipParts.cockpit = cockpit;

    // Engine glow
    const engineGeometry = new THREE.CylinderGeometry(0.2, 0.3, 0.5, 8);
    const engineMaterial = new THREE.MeshBasicMaterial({
        color: 0xff6600,
        transparent: true,
        opacity: 0.8
    });
    const engineGlow = new THREE.Mesh(engineGeometry, engineMaterial);
    engineGlow.rotation.x = Math.PI / 2;
    engineGlow.position.z = 1.2;
    spaceship.add(engineGlow);
    spaceshipParts.engine = engineGlow;

    // Add point light for engine
    const engineLight = new THREE.PointLight(0xff6600, 2, 10);
    engineLight.position.z = 1.5;
    spaceship.add(engineLight);
    spaceshipParts.engineLight = engineLight;

    scene.add(spaceship);
}

function createStarfield() {
    const starGeometry = new THREE.BufferGeometry();
    const starPositions = [];

    for (let i = 0; i < 2000; i++) {
        const x = (Math.random() - 0.5) * 2000;
        const y = (Math.random() - 0.5) * 2000;
        const z = Math.random() * -2000; // Stars in front of us
        starPositions.push(x, y, z);
    }

    starGeometry.setAttribute('position', new THREE.Float32BufferAttribute(starPositions, 3));

    const starMaterial = new THREE.PointsMaterial({
        color: 0xffffff,
        size: 2,
        transparent: true
    });

    const starField = new THREE.Points(starGeometry, starMaterial);
    scene.add(starField);
    stars.push(starField);
}

function createAsteroid() {
    if (asteroids.length >= MAX_ASTEROIDS) return;

    const size = Math.random() * 2 + 1;
    const geometry = new THREE.DodecahedronGeometry(size, 0);
    const material = new THREE.MeshPhongMaterial({
        color: 0x888888,
        flatShading: true
    });
    const asteroid = new THREE.Mesh(geometry, material);

    // Random position in front of spaceship
    asteroid.position.x = (Math.random() - 0.5) * 50;
    asteroid.position.y = (Math.random() - 0.5) * 50;
    asteroid.position.z = -100 - Math.random() * 50;

    // Random rotation
    asteroid.rotation.x = Math.random() * Math.PI;
    asteroid.rotation.y = Math.random() * Math.PI;

    // Random velocity (z is relative to forward speed)
    asteroid.userData.velocity = {
        x: (Math.random() - 0.5) * 0.1,
        y: (Math.random() - 0.5) * 0.1,
        z: Math.random() * 0.5
    };

    asteroid.userData.rotationSpeed = {
        x: (Math.random() - 0.5) * 0.02,
        y: (Math.random() - 0.5) * 0.02,
        z: (Math.random() - 0.5) * 0.02
    };

    scene.add(asteroid);
    asteroids.push(asteroid);
}

function createEnemy(forceType = null) {
    if (enemies.length >= MAX_ENEMIES) return;

    const enemyGroup = new THREE.Group();

    // Enemy type (0: basic, 1: fast, 2: heavy)
    // Can be forced by wave system, or random
    let type;
    if (forceType !== null) {
        type = forceType;
    } else {
        // Higher waves have higher chance of tough enemies
        const rand = Math.random();
        if (currentWave < 3) {
            type = rand < 0.7 ? 0 : (rand < 0.9 ? 1 : 2);
        } else if (currentWave < 6) {
            type = rand < 0.5 ? 0 : (rand < 0.8 ? 1 : 2);
        } else {
            type = rand < 0.3 ? 0 : (rand < 0.6 ? 1 : 2);
        }
    }

    let color, size, health, points, shootPattern;

    // Scale health with wave number
    const healthMultiplier = 1 + Math.floor(currentWave / 3) * 0.5;

    switch(type) {
        case 0: // Basic enemy
            color = 0xff3333;
            size = 1;
            health = Math.ceil(2 * healthMultiplier);
            points = 100;
            shootPattern = 'straight';
            break;
        case 1: // Fast enemy
            color = 0xffaa00;
            size = 0.7;
            health = Math.ceil(1 * healthMultiplier);
            points = 150;
            shootPattern = 'aimed';
            break;
        case 2: // Heavy enemy
            color = 0xff00ff;
            size = 1.5;
            health = Math.ceil(5 * healthMultiplier);
            points = 300;
            shootPattern = 'spread';
            break;
    }

    // Create enemy ship model
    // Main body - inverted cone (pointy end forward)
    const bodyGeometry = new THREE.ConeGeometry(size * 0.5, size * 1.5, 6);
    const bodyMaterial = new THREE.MeshPhongMaterial({
        color: color,
        emissive: color,
        emissiveIntensity: 0.3,
        flatShading: true
    });
    const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
    body.rotation.x = -Math.PI / 2; // Point forward (toward player)
    enemyGroup.add(body);

    // Wings
    const wingGeometry = new THREE.BoxGeometry(size * 2.5, size * 0.1, size * 0.6);
    const wingMaterial = new THREE.MeshPhongMaterial({
        color: color,
        emissive: color,
        emissiveIntensity: 0.2
    });
    const wings = new THREE.Mesh(wingGeometry, wingMaterial);
    wings.position.z = size * 0.3;
    enemyGroup.add(wings);

    // Cockpit/core
    const cockpitGeometry = new THREE.SphereGeometry(size * 0.3, 8, 8);
    const cockpitMaterial = new THREE.MeshPhongMaterial({
        color: 0xffffff,
        emissive: color,
        emissiveIntensity: 0.8
    });
    const cockpit = new THREE.Mesh(cockpitGeometry, cockpitMaterial);
    cockpit.position.z = -size * 0.3;
    enemyGroup.add(cockpit);

    // Engine glow at back
    const engineGeometry = new THREE.CylinderGeometry(size * 0.15, size * 0.25, size * 0.4, 6);
    const engineMaterial = new THREE.MeshBasicMaterial({
        color: 0xff0000,
        transparent: true,
        opacity: 0.8
    });
    const engine = new THREE.Mesh(engineGeometry, engineMaterial);
    engine.rotation.x = Math.PI / 2;
    engine.position.z = size * 0.8;
    enemyGroup.add(engine);

    // Outer glow
    const glowGeometry = new THREE.SphereGeometry(size * 1.5, 8, 8);
    const glowMaterial = new THREE.MeshBasicMaterial({
        color: color,
        transparent: true,
        opacity: 0.1
    });
    const glow = new THREE.Mesh(glowGeometry, glowMaterial);
    enemyGroup.add(glow);

    // Position enemy far away, will move into screen
    enemyGroup.position.x = (Math.random() - 0.5) * 50;
    enemyGroup.position.y = (Math.random() - 0.5) * 40;
    enemyGroup.position.z = -120 - Math.random() * 20;

    // Movement pattern (0: horizontal sweep, 1: sine wave, 2: circle, 3: stationary)
    const movementPattern = Math.floor(Math.random() * 4);

    // Set up movement parameters
    let moveSpeed, targetZ, moveDirection;
    const waveSpeedBonus = currentWave * 0.006;
    switch(movementPattern) {
        case 0: // Horizontal sweep
            moveSpeed = 0.08 + waveSpeedBonus;
            targetZ = -45;
            moveDirection = Math.random() > 0.5 ? 1 : -1;
            break;
        case 1: // Sine wave
            moveSpeed = 0.06 + waveSpeedBonus;
            targetZ = -45;
            moveDirection = Math.random() > 0.5 ? 1 : -1;
            break;
        case 2: // Circle
            moveSpeed = 0.05 + waveSpeedBonus;
            targetZ = -45;
            moveDirection = Math.random() > 0.5 ? 1 : -1;
            break;
        case 3: // Stationary sniper
            moveSpeed = 0.08 + waveSpeedBonus;
            targetZ = -50;
            moveDirection = 0;
            break;
    }

    enemyGroup.userData = {
        type: type,
        health: health,
        maxHealth: health,
        points: points,
        shootPattern: shootPattern,
        movementPattern: movementPattern,
        moveSpeed: moveSpeed,
        targetZ: targetZ,
        moveDirection: moveDirection,
        hasReachedPosition: false,
        lastShootTime: Date.now() + Math.random() * 2000,
        shootCooldown: Math.max(800, 3000 - currentWave * 120) + Math.random() * Math.max(400, 1500 - currentWave * 80),
        timeAlive: 0,
        circleRadius: 5 + Math.random() * 3,
        circleAngle: Math.random() * Math.PI * 2,
        initialX: (Math.random() - 0.5) * 50,
        initialY: (Math.random() - 0.5) * 40,
        body: body,
        glow: glow,
        engine: engine,
        cockpit: cockpit
    };

    scene.add(enemyGroup);
    enemies.push(enemyGroup);
}

function createEnemyBullet(enemy, pattern) {
    const bulletGeometry = new THREE.SphereGeometry(0.15, 8, 8);
    const bulletMaterial = new THREE.MeshBasicMaterial({ color: 0xff0000 });

    const playerPos = spaceship.position.clone();
    const enemyPos = enemy.position.clone();

    const bulletSpeedMult = 1 + currentWave * 0.05;
    switch(pattern) {
        case 'straight':
            // Single bullet straight down
            const bullet1 = new THREE.Mesh(bulletGeometry, bulletMaterial);
            bullet1.position.copy(enemyPos);
            bullet1.userData.velocity = new THREE.Vector3(0, 0, 0.5 * bulletSpeedMult);
            scene.add(bullet1);
            enemyBullets.push(bullet1);
            break;

        case 'aimed':
            // Aimed at player
            const bullet2 = new THREE.Mesh(bulletGeometry, bulletMaterial);
            bullet2.position.copy(enemyPos);
            const direction = playerPos.sub(enemyPos).normalize();
            bullet2.userData.velocity = direction.multiplyScalar(0.6 * bulletSpeedMult);
            scene.add(bullet2);
            enemyBullets.push(bullet2);
            break;

        case 'spread':
            // 3-way spread
            for (let i = 0; i < 3; i++) {
                const bullet3 = new THREE.Mesh(bulletGeometry, bulletMaterial.clone());
                bullet3.position.copy(enemyPos);
                const angle = (i - 1) * 0.3; // -0.3 to 0.3 radians
                const vel = new THREE.Vector3(
                    Math.sin(angle) * 0.5 * bulletSpeedMult,
                    0,
                    Math.cos(angle) * 0.5 * bulletSpeedMult
                );
                bullet3.userData.velocity = vel;
                scene.add(bullet3);
                enemyBullets.push(bullet3);
            }
            break;
    }
}

function createExplosion(position, color = 0xff6600) {
    const particleCount = 20;

    for (let i = 0; i < particleCount; i++) {
        const geometry = new THREE.SphereGeometry(0.2, 4, 4);
        const material = new THREE.MeshBasicMaterial({ color: color });
        const particle = new THREE.Mesh(geometry, material);

        particle.position.copy(position);

        const velocity = new THREE.Vector3(
            (Math.random() - 0.5) * 3,
            (Math.random() - 0.5) * 3,
            (Math.random() - 0.5) * 3
        );

        particle.userData = {
            velocity: velocity,
            lifetime: 30,
            decay: 0.05
        };

        scene.add(particle);
        explosions.push(particle);
    }
}

function createProjectile(side) {
    const geometry = new THREE.SphereGeometry(0.2, 8, 8);
    const color = side === 'left' ? 0xff00ff : 0x00ffff; // Pink for left, cyan for right
    const material = new THREE.MeshBasicMaterial({ color: color });
    const projectile = new THREE.Mesh(geometry, material);

    // Position based on which gun is firing (in local space)
    const offsetX = side === 'left' ? -1.2 : 1.2;
    const gunPosition = new THREE.Vector3(offsetX, 0, -2);

    // Transform gun position to world space based on spaceship rotation and position
    gunPosition.applyEuler(spaceship.rotation);
    gunPosition.add(spaceship.position);

    projectile.position.copy(gunPosition);

    // Add glow
    const glowGeometry = new THREE.SphereGeometry(0.4, 8, 8);
    const glowMaterial = new THREE.MeshBasicMaterial({
        color: color,
        transparent: true,
        opacity: 0.3
    });
    const glow = new THREE.Mesh(glowGeometry, glowMaterial);
    projectile.add(glow);

    // Calculate velocity direction based on spaceship rotation
    const direction = new THREE.Vector3(0, 0, -1); // Forward direction
    direction.applyEuler(spaceship.rotation);
    direction.normalize();

    projectile.userData.velocity = direction.multiplyScalar(5);

    scene.add(projectile);
    projectiles.push(projectile);
}


async function fetchSensorData() {
    try {
        const response = await fetch('/sensor_data');
        const data = await response.json();

        // Smooth the sensor data
        sensorData.roll = sensorData.roll * (1 - SMOOTHING) + data.roll * SMOOTHING;
        sensorData.pitch = sensorData.pitch * (1 - SMOOTHING) + data.pitch * SMOOTHING;
        sensorData.yaw = sensorData.yaw * (1 - SMOOTHING) + data.yaw * SMOOTHING;
        sensorData.antennas = data.antennas;
        sensorData.score = data.score;
        sensorData.health = data.health;

        // Detect left gun fire trigger (rising edge)
        if (data.fire_left && !lastFireLeftState) {
            createProjectile('left');
            lastFireLeftState = true;
        } else if (!data.fire_left) {
            lastFireLeftState = false;
        }

        // Detect right gun fire trigger (rising edge)
        if (data.fire_right && !lastFireRightState) {
            createProjectile('right');
            lastFireRightState = true;
        } else if (!data.fire_right) {
            lastFireRightState = false;
        }

        // Update HUD
        updateHUD();

    } catch (error) {
        console.error('Error fetching sensor data:', error);
    }

    // Fetch at 50Hz
    setTimeout(fetchSensorData, 20);
}

function updateHUD() {
    document.getElementById('wave').textContent = currentWave;
    document.getElementById('score').textContent = sensorData.score;
    document.getElementById('roll').textContent = sensorData.roll.toFixed(1);
    document.getElementById('pitch').textContent = sensorData.pitch.toFixed(1);
    document.getElementById('yaw').textContent = sensorData.yaw.toFixed(1);
    document.getElementById('antennas').textContent =
        `${sensorData.antennas.right.toFixed(2)}, ${sensorData.antennas.left.toFixed(2)}`;

    const healthPercent = (sensorData.health / 100) * 100;
    const healthColor = healthPercent > 50 ? '#0f0' : healthPercent > 25 ? '#ff0' : '#f00';
    document.getElementById('status').innerHTML = `HP: <span style="color: ${healthColor}">${sensorData.health}</span>`;

    // Check for game over
    if (sensorData.health <= 0 && gameStarted && !gameOver) {
        triggerGameOver();
    }
}

async function addScore(points) {
    try {
        await fetch('/add_score', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ points })
        });
    } catch (e) {
        console.error('Error adding score:', e);
    }
}

async function damagePlayer(damage) {
    try {
        await fetch('/damage_player', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ damage })
        });
    } catch (e) {
        console.error('Error damaging player:', e);
    }
}

function updateSpaceship() {
    if (!spaceship) return;

    // Map sensor data to spaceship rotation
    // Pitch: tilt forward/back controls pitch (up/down aiming)
    // Yaw: turn head left/right controls yaw (left/right aiming)
    // Roll: tilt left/right for visual banking effect
    const targetRotation = {
        x: THREE.MathUtils.degToRad(sensorData.pitch * MOVEMENT_SCALE),
        y: THREE.MathUtils.degToRad(sensorData.yaw * MOVEMENT_SCALE), // Yaw controls yaw for left/right aim
        z: THREE.MathUtils.degToRad(sensorData.roll * MOVEMENT_SCALE) // Roll for visual banking
    };

    // Smooth rotation
    spaceship.rotation.x += (targetRotation.x - spaceship.rotation.x) * 0.1;
    spaceship.rotation.y += (targetRotation.y - spaceship.rotation.y) * 0.1;
    spaceship.rotation.z += (targetRotation.z - spaceship.rotation.z) * 0.1;

    // Use yaw to also move spaceship left/right in space for dynamic feel
    const targetX = sensorData.yaw * YAW_MOVEMENT_SCALE;
    spaceship.position.x += (targetX - spaceship.position.x) * 0.1;

    // Limit spaceship movement range
    spaceship.position.x = Math.max(-30, Math.min(30, spaceship.position.x));

    // Animate engine glow
    if (spaceshipParts.engine) {
        const pulse = Math.sin(Date.now() * 0.01) * 0.1 + 0.9;
        spaceshipParts.engine.material.opacity = pulse;
        spaceshipParts.engineLight.intensity = pulse * 2;
    }
}

function updateAsteroids() {
    for (let i = asteroids.length - 1; i >= 0; i--) {
        const asteroid = asteroids[i];

        // Move asteroid toward camera (simulating forward movement)
        asteroid.position.x += asteroid.userData.velocity.x;
        asteroid.position.y += asteroid.userData.velocity.y;
        asteroid.position.z += FORWARD_SPEED + asteroid.userData.velocity.z;

        // Rotate asteroid
        asteroid.rotation.x += asteroid.userData.rotationSpeed.x;
        asteroid.rotation.y += asteroid.userData.rotationSpeed.y;
        asteroid.rotation.z += asteroid.userData.rotationSpeed.z;

        // Remove if behind camera
        if (asteroid.position.z > 20) {
            scene.remove(asteroid);
            asteroids.splice(i, 1);
        }
    }
}

function updateProjectiles() {
    for (let i = projectiles.length - 1; i >= 0; i--) {
        const projectile = projectiles[i];

        // Move projectile using velocity vector
        projectile.position.add(projectile.userData.velocity);

        let hitSomething = false;

        // Check collision with start button (for both start and restart)
        if (!gameStarted && startButton) {
            const distance = projectile.position.distanceTo(startButton.position);
            if (distance < 5) {
                createExplosion(startButton.position, 0x00ff00);
                scene.remove(projectile);
                projectiles.splice(i, 1);

                removeStartButton();

                if (gameOver) {
                    // Restart the game
                    resetGame();
                } else {
                    // Start the game for first time
                    gameStarted = true;
                    nextWaveTime = Date.now() + 1000; // First wave after 1 second

                    // Start background music
                    startMusic();

                    // Hide start message
                    const startMsg = document.getElementById('start-message');
                    if (startMsg) {
                        startMsg.style.display = 'none';
                    }

                    console.log('Game started!');
                }

                hitSomething = true;
                continue;
            }
        }

        if (hitSomething) continue;

        // Check collision with asteroids
        for (let j = asteroids.length - 1; j >= 0; j--) {
            const asteroid = asteroids[j];
            const distance = projectile.position.distanceTo(asteroid.position);

            if (distance < asteroid.geometry.parameters.radius + 0.5) {
                scene.remove(asteroid);
                asteroids.splice(j, 1);

                scene.remove(projectile);
                projectiles.splice(i, 1);

                createExplosion(projectile.position, 0x888888);
                hitSomething = true;
                break;
            }
        }

        if (hitSomething) continue;

        // Check collision with enemies
        for (let j = enemies.length - 1; j >= 0; j--) {
            const enemy = enemies[j];
            const distance = projectile.position.distanceTo(enemy.position);

            // Larger hitbox based on enemy size
            const hitRadius = 3 + (enemy.userData.type === 2 ? 1 : 0); // Heavy enemies are bigger
            if (distance < hitRadius) {
                enemy.userData.health -= 1;

                // Flash enemy when hit
                enemy.userData.body.material.emissiveIntensity = 1;
                setTimeout(() => {
                    if (enemy.userData.body) {
                        enemy.userData.body.material.emissiveIntensity = 0.3;
                    }
                }, 100);

                scene.remove(projectile);
                projectiles.splice(i, 1);

                if (enemy.userData.health <= 0) {
                    createExplosion(enemy.position, enemy.userData.body.material.color);
                    scene.remove(enemy);
                    enemies.splice(j, 1);
                    addScore(enemy.userData.points);
                }

                hitSomething = true;
                break;
            }
        }

        if (hitSomething) continue;

        // Remove if too far from camera
        if (projectile.position.z < -200 || projectile.position.length() > 300) {
            scene.remove(projectile);
            projectiles.splice(i, 1);
        }
    }
}

function updateEnemies() {
    for (let i = enemies.length - 1; i >= 0; i--) {
        const enemy = enemies[i];

        enemy.userData.timeAlive += 0.016;

        // Move enemy into position first
        if (!enemy.userData.hasReachedPosition) {
            // Move toward target Z position
            if (enemy.position.z < enemy.userData.targetZ) {
                enemy.position.z += enemy.userData.moveSpeed;
                if (enemy.position.z >= enemy.userData.targetZ) {
                    enemy.userData.hasReachedPosition = true;
                    enemy.userData.initialX = enemy.position.x;
                    enemy.userData.initialY = enemy.position.y;
                }
            }
        } else {
            // Once in position, execute movement pattern
            switch(enemy.userData.movementPattern) {
                case 0: // Horizontal sweep
                    enemy.position.x += enemy.userData.moveDirection * 0.06;
                    // Bounce off edges
                    if (Math.abs(enemy.position.x) > 35) {
                        enemy.userData.moveDirection *= -1;
                    }
                    break;

                case 1: // Sine wave
                    enemy.position.x = enemy.userData.initialX + Math.sin(enemy.userData.timeAlive * 0.5) * 8;
                    enemy.position.y = enemy.userData.initialY + Math.sin(enemy.userData.timeAlive * 0.4) * 4;
                    break;

                case 2: // Circle
                    enemy.userData.circleAngle += 0.005 * enemy.userData.moveDirection;
                    enemy.position.x = enemy.userData.initialX + Math.cos(enemy.userData.circleAngle) * enemy.userData.circleRadius;
                    enemy.position.y = enemy.userData.initialY + Math.sin(enemy.userData.circleAngle) * enemy.userData.circleRadius;
                    break;

                case 3: // Stationary
                    // Stay in place
                    break;
            }
        }

        // Rotate enemy slowly
        enemy.rotation.z += 0.01;

        // Animate engine glow
        if (enemy.userData.engine) {
            const pulse = Math.sin(Date.now() * 0.005 + i) * 0.3 + 0.7;
            enemy.userData.engine.material.opacity = pulse;
        }

        // Shoot at player only when in position
        if (enemy.userData.hasReachedPosition) {
            const now = Date.now();
            if (now - enemy.userData.lastShootTime > enemy.userData.shootCooldown) {
                createEnemyBullet(enemy, enemy.userData.shootPattern);
                enemy.userData.lastShootTime = now;
            }
        }

        // Remove if too far away or if player flew past them
        if (enemy.position.z > 30 || enemy.position.length() > 150) {
            scene.remove(enemy);
            enemies.splice(i, 1);
        }
    }
}

function updateEnemyBullets() {
    for (let i = enemyBullets.length - 1; i >= 0; i--) {
        const bullet = enemyBullets[i];

        // Move bullet
        bullet.position.add(bullet.userData.velocity);

        // Check collision with player
        const distance = bullet.position.distanceTo(spaceship.position);
        if (distance < 2.0) {
            createExplosion(bullet.position, 0xff0000);
            scene.remove(bullet);
            enemyBullets.splice(i, 1);
            damagePlayer(10);
            console.log('Player hit! HP should decrease by 10');
            continue;
        }

        // Remove if too far
        if (bullet.position.z > 50 || bullet.position.length() > 200) {
            scene.remove(bullet);
            enemyBullets.splice(i, 1);
        }
    }
}

function updateExplosions() {
    for (let i = explosions.length - 1; i >= 0; i--) {
        const particle = explosions[i];

        particle.position.add(particle.userData.velocity);
        particle.userData.velocity.multiplyScalar(0.95);
        particle.userData.lifetime--;

        particle.material.opacity = particle.userData.lifetime / 30;

        if (particle.userData.lifetime <= 0) {
            scene.remove(particle);
            explosions.splice(i, 1);
        }
    }
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function updateReticle() {
    // Calculate where the spaceship is aiming based on rotation
    // Create a point 50 units in front, rotated by the spaceship's rotation
    const aimDirection = new THREE.Vector3(0, 0, -50);

    // Apply spaceship rotation to get aim direction
    const rotationMatrix = new THREE.Matrix4();
    rotationMatrix.makeRotationFromEuler(spaceship.rotation);
    aimDirection.applyMatrix4(rotationMatrix);

    // Add to spaceship position
    const aimPoint = spaceship.position.clone().add(aimDirection);

    // Project to screen coordinates
    const screenPosition = aimPoint.clone();
    screenPosition.project(camera);

    // Convert to pixel coordinates
    const x = (screenPosition.x * 0.5 + 0.5) * window.innerWidth;
    const y = (screenPosition.y * -0.5 + 0.5) * window.innerHeight;

    // Update crosshair position
    const crosshair = document.querySelector('.crosshair');
    if (crosshair) {
        crosshair.style.left = `${x}px`;
        crosshair.style.top = `${y}px`;
        crosshair.style.transform = 'translate(-50%, -50%)';
    }
}

function animate() {
    requestAnimationFrame(animate);

    updateSpaceship();
    updateProjectiles();
    updateExplosions();
    updateReticle();

    // Only update game elements if game has started
    if (gameStarted && !gameOver) {
        updateAsteroids();
        updateEnemies();
        updateEnemyBullets();

        // Wave management
        const now = Date.now();
        if (!waveInProgress && now >= nextWaveTime) {
            startNewWave();
        }

        // Spawn enemies during wave
        if (waveInProgress && enemiesSpawnedThisWave < enemiesToSpawnThisWave) {
            // Spawn rate: one enemy every 0.5-1.5 seconds depending on wave
            const spawnDelay = Math.max(1000, 4000 - currentWave * 200);
            if (Math.random() < 1000 / spawnDelay / 60) { // Approximately correct for 60fps
                spawnWaveEnemy();
            }
        }

        // Check if wave is complete
        checkWaveComplete();
    } else if (!gameStarted) {
        // Animate start button
        if (startButton) {
            startButton.rotation.z += 0.01;
            const pulse = Math.sin(Date.now() * 0.003) * 0.3 + 0.7;
            startButton.userData.button.material.emissiveIntensity = pulse;
            startButton.userData.ring.material.opacity = pulse * 0.7;
        }
    }

    // Move stars to simulate forward movement through space
    stars.forEach(starField => {
        const positions = starField.geometry.attributes.position.array;
        for (let i = 0; i < positions.length; i += 3) {
            positions[i + 2] += FORWARD_SPEED; // Move stars toward us

            // Wrap stars around when they pass us
            if (positions[i + 2] > 50) {
                positions[i + 2] = -1950;
                positions[i] = (Math.random() - 0.5) * 2000;
                positions[i + 1] = (Math.random() - 0.5) * 2000;
            }
        }
        starField.geometry.attributes.position.needsUpdate = true;
    });

    renderer.render(scene, camera);
}

// ──────────────────── Leaderboard ────────────────────

let nameCountdownInterval = null;

function showNameOverlay(score) {
    const overlay = document.getElementById('name-overlay');
    const scoreEl = document.getElementById('name-overlay-score');
    const input = document.getElementById('name-input');
    const countdown = document.getElementById('name-countdown');
    if (!overlay) return;

    scoreEl.textContent = `SCORE: ${score}`;
    // Restore last name from localStorage
    const savedName = localStorage.getItem('spaceship_player_name') || '';
    input.value = savedName;

    overlay.style.display = 'flex';
    input.focus();
    input.select();

    // Auto-submit countdown
    let secondsLeft = 10;
    if (countdown) countdown.textContent = secondsLeft;
    if (nameCountdownInterval) clearInterval(nameCountdownInterval);
    nameCountdownInterval = setInterval(() => {
        secondsLeft--;
        if (countdown) countdown.textContent = secondsLeft;
        if (secondsLeft <= 0) {
            clearInterval(nameCountdownInterval);
            nameCountdownInterval = null;
            submitScore();
        }
    }, 1000);
}

function hideNameOverlay() {
    const overlay = document.getElementById('name-overlay');
    if (overlay) overlay.style.display = 'none';
    if (nameCountdownInterval) {
        clearInterval(nameCountdownInterval);
        nameCountdownInterval = null;
    }
}

function submitScore() {
    hideNameOverlay();
    const input = document.getElementById('name-input');
    const name = (input ? input.value.trim() : '') || 'Pilot';
    localStorage.setItem('spaceship_player_name', name);

    fetch('/leaderboard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ score: finalScore, name, waves_completed: currentWave }),
    })
        .then(() => {
            fetchLeaderboard();
            fetchGlobalLeaderboard();
            autoPublishToGlobal();
        })
        .catch(err => console.warn('Failed to submit score:', err));

    showGameOverScreen();
    fetchHfStatus();
}

async function fetchLeaderboard() {
    try {
        const resp = await fetch('/leaderboard');
        const data = await resp.json();
        renderLocalLeaderboard(data.entries || []);
        showLeaderboardPanel();
    } catch (e) {
        console.warn('Failed to fetch leaderboard:', e);
    }
}

async function fetchGlobalLeaderboard() {
    try {
        const resp = await fetch('/global_leaderboard');
        const data = await resp.json();
        renderGlobalLeaderboard(data.entries || [], data.is_syncing, data.sync_error);
        showLeaderboardPanel();
    } catch (e) {
        console.warn('Failed to fetch global leaderboard:', e);
    }
}

async function fetchHfStatus() {
    try {
        const resp = await fetch('/hf_status');
        const data = await resp.json();
        const statusEl = document.getElementById('hf-status-msg');
        const publishBtn = document.getElementById('lb-publish-btn');
        if (statusEl) statusEl.textContent = data.message || '';
        if (publishBtn) publishBtn.style.display = data.logged_in ? 'block' : 'none';
    } catch (e) {
        console.warn('Failed to fetch HF status:', e);
    }
}

async function autoPublishToGlobal() {
    try {
        const resp = await fetch('/global_leaderboard/publish', { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            fetchGlobalLeaderboard();
        }
    } catch (e) {
        // Silently ignore - not logged in is normal
    }
}

function renderLocalLeaderboard(entries) {
    const list = document.getElementById('leaderboard-list');
    if (!list) return;
    if (entries.length === 0) {
        list.innerHTML = '<li style="color:#888;">No scores yet</li>';
        return;
    }
    list.innerHTML = entries.map(e => {
        const waves = e.waves_completed != null ? ` <span style="color:#888">(w${e.waves_completed})</span>` : '';
        const name = (e.name || 'Anonymous').replace(/</g, '&lt;');
        return `<li><span style="color:#ff0">${e.score}</span> ${name}${waves}</li>`;
    }).join('');
}

function renderGlobalLeaderboard(entries, isSyncing, syncError) {
    const list = document.getElementById('global-leaderboard-list');
    const status = document.getElementById('global-sync-status');
    if (!list) return;
    if (isSyncing && entries.length === 0) {
        list.innerHTML = '<li style="color:#888;">Loading...</li>';
    } else if (entries.length === 0) {
        list.innerHTML = '<li style="color:#888;">No global scores yet</li>';
    } else {
        list.innerHTML = entries.slice(0, 10).map(e => {
            const name = (e.name || 'Anonymous').replace(/</g, '&lt;');
            return `<li><span style="color:#ff0">${e.score}</span> ${name}</li>`;
        }).join('');
    }
    if (status) {
        if (isSyncing) status.textContent = 'Syncing...';
        else if (syncError) status.textContent = 'Sync failed';
        else status.textContent = '';
    }
}

function showLeaderboardPanel() {
    const panel = document.getElementById('leaderboard-panel');
    if (panel) panel.style.display = 'block';
}

// Name overlay event listeners (set up once)
document.addEventListener('DOMContentLoaded', () => {
    const submitBtn = document.getElementById('name-submit-btn');
    const nameInput = document.getElementById('name-input');
    const helpBtn = document.getElementById('lb-help-btn');
    const publishBtn = document.getElementById('lb-publish-btn');
    const helpModal = document.getElementById('hf-help-modal');
    const helpClose = document.getElementById('hf-help-close');

    if (submitBtn) submitBtn.addEventListener('click', submitScore);
    if (nameInput) {
        nameInput.addEventListener('keydown', e => {
            if (e.key === 'Enter') submitScore();
        });
    }
    if (helpBtn) helpBtn.addEventListener('click', () => {
        if (helpModal) helpModal.style.display = 'flex';
    });
    if (helpClose) helpClose.addEventListener('click', () => {
        if (helpModal) helpModal.style.display = 'none';
    });
    if (publishBtn) publishBtn.addEventListener('click', async () => {
        publishBtn.disabled = true;
        publishBtn.textContent = 'PUBLISHING...';
        await autoPublishToGlobal();
        publishBtn.disabled = false;
        publishBtn.textContent = 'PUBLISH TO GLOBAL';
    });
});

// Start the game
init();
