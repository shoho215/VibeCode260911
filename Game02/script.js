const canvas = document.querySelector('#game-canvas');
const context = canvas.getContext('2d');
const scoreElement = document.querySelector('#score');
const highScoreElement = document.querySelector('#high-score');
const waveElement = document.querySelector('#wave');
const armorMeter = document.querySelector('#armor-meter');
const powerPips = [...document.querySelectorAll('#power-pips i')];
const missionStatus = document.querySelector('#mission-status');
const overlay = document.querySelector('#game-overlay');
const overlayTitle = document.querySelector('#overlay-title');
const overlayCopy = document.querySelector('#overlay-copy');

const WIDTH = canvas.width;
const HEIGHT = canvas.height;
const keys = new Set();
const bullets = [];
const enemyBullets = [];
const enemies = [];
const powerups = [];
const particles = [];
const stars = Array.from({ length: 95 }, (_, index) => ({ x: (index * 73) % WIDTH, y: (index * 137) % HEIGHT, speed: 18 + (index % 5) * 12, size: 1 + (index % 3) * .5 }));
let player;
let score = 0;
let highScore = Number(localStorage.getItem('starfall-high-score')) || 0;
let wave = 1;
let waveTimer = 0;
let spawnTimer = 0;
let fireTimer = 0;
let elapsed = 0;
let lastTime = 0;
let paused = false;
let gameOver = false;
let waveBanner = 0;
let audioContext;

highScoreElement.textContent = formatNumber(highScore);

function formatNumber(value) { return String(value).padStart(6, '0'); }
function random(min, max) { return Math.random() * (max - min) + min; }
function clamp(value, min, max) { return Math.max(min, Math.min(max, value)); }

function unlockAudio() {
  if (!audioContext) audioContext = new (window.AudioContext || window.webkitAudioContext)();
  if (audioContext.state === 'suspended') audioContext.resume();
}

function playSound(type) {
  unlockAudio();
  const settings = {
    fire: { frequency: 520, endFrequency: 180, duration: .08, volume: .045, wave: 'square' },
    hit: { frequency: 110, endFrequency: 55, duration: .16, volume: .08, wave: 'sawtooth' },
    fruit: { frequency: 260, endFrequency: 620, duration: .12, volume: .06, wave: 'triangle' },
    power: { frequency: 420, endFrequency: 880, duration: .24, volume: .07, wave: 'sine' },
    damage: { frequency: 90, endFrequency: 42, duration: .24, volume: .08, wave: 'sawtooth' }
  }[type];
  if (!settings) return;
  const now = audioContext.currentTime;
  const oscillator = audioContext.createOscillator();
  const gain = audioContext.createGain();
  oscillator.type = settings.wave;
  oscillator.frequency.setValueAtTime(settings.frequency, now);
  oscillator.frequency.exponentialRampToValueAtTime(settings.endFrequency, now + settings.duration);
  gain.gain.setValueAtTime(settings.volume, now);
  gain.gain.exponentialRampToValueAtTime(.001, now + settings.duration);
  oscillator.connect(gain).connect(audioContext.destination);
  oscillator.start(now);
  oscillator.stop(now + settings.duration);
}

function makePlayer() {
  return { x: WIDTH / 2, y: HEIGHT - 82, width: 25, height: 34, armor: 100, power: 1, invulnerable: 0 };
}

function createEnemy(type = 'scout') {
  const isHeavy = type === 'heavy';
  const fruit = isHeavy ? 'watermelon' : ['apple', 'orange', 'strawberry', 'lemon'][Math.floor(random(0, 4))];
  return { x: random(35, WIDTH - 35), y: -35, width: isHeavy ? 38 : 28, height: isHeavy ? 34 : 28, hp: isHeavy ? 3 : 1, maxHp: isHeavy ? 3 : 1, type, fruit, speed: isHeavy ? 40 : 70, phase: random(0, Math.PI * 2), fireTime: random(1.4, 3.5), age: 0 };
}

function spawnWave() {
  const count = Math.min(4 + wave, 11);
  for (let index = 0; index < count; index += 1) {
    enemies.push(createEnemy(index % 5 === 0 && wave > 1 ? 'heavy' : 'scout'));
  }
  waveBanner = 2;
  missionStatus.textContent = `WAVE ${String(wave).padStart(2, '0')} INBOUND`;
  waveElement.textContent = String(wave).padStart(2, '0');
}

function addParticle(x, y, color, amount = 8, force = 1) {
  for (let index = 0; index < amount; index += 1) {
    const angle = random(0, Math.PI * 2);
    const speed = random(25, 115) * force;
    particles.push({ x, y, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed, life: random(.3, .75), maxLife: .75, size: random(1, 3), color });
  }
}

function dropPowerUp(x, y) {
  if (player.power >= 3 || Math.random() > .3) return;
  powerups.push({ x, y, size: 13, spin: 0, speed: 62 });
}

function fire() {
  if (fireTimer > 0 || gameOver || paused) return;
  const spread = player.power >= 3 ? [-10, 0, 10] : player.power === 2 ? [-6, 6] : [0];
  spread.forEach((offset) => bullets.push({ x: player.x + offset, y: player.y - 23, vx: offset * .65, vy: -440, radius: 3 }));
  fireTimer = player.power >= 3 ? .12 : .2;
  playSound('fire');
}

function hitPlayer() {
  if (player.invulnerable > 0) return;
  player.armor -= 25;
  player.invulnerable = 1.2;
  addParticle(player.x, player.y, '#ff4f65', 18, 1.5);
  playSound('damage');
  updateHud();
  if (player.armor <= 0) endGame();
}

function updateHud() {
  scoreElement.textContent = formatNumber(score);
  highScoreElement.textContent = formatNumber(highScore);
  armorMeter.style.width = `${clamp(player.armor, 0, 100)}%`;
  powerPips.forEach((pip, index) => { pip.style.opacity = index < player.power ? '1' : '.22'; });
}

function drawBackground(delta) {
  context.fillStyle = '#050e1a';
  context.fillRect(0, 0, WIDTH, HEIGHT);
  context.strokeStyle = 'rgba(80, 227, 255, .055)';
  context.lineWidth = 1;
  for (let x = 0; x <= WIDTH; x += 40) { context.beginPath(); context.moveTo(x, 0); context.lineTo(x, HEIGHT); context.stroke(); }
  for (let y = 0; y <= HEIGHT; y += 40) { context.beginPath(); context.moveTo(0, y); context.lineTo(WIDTH, y); context.stroke(); }
  stars.forEach((star) => {
    star.y += star.speed * delta;
    if (star.y > HEIGHT + 5) star.y = -5;
    context.globalAlpha = .25 + star.size / 5;
    context.fillStyle = star.size > 1.5 ? '#86f7d1' : '#50e3ff';
    context.fillRect(star.x, star.y, star.size, star.size * 2.3);
  });
  context.globalAlpha = 1;
}

function drawShip() {
  if (player.invulnerable > 0 && Math.floor(elapsed * 12) % 2 === 0) return;
  context.save();
  context.translate(player.x, player.y);
  context.shadowBlur = 20;
  context.shadowColor = '#50e3ff';
  context.fillStyle = '#173f64';
  context.beginPath(); context.moveTo(0, -25); context.lineTo(10, -5); context.lineTo(28, 10); context.lineTo(9, 9); context.lineTo(0, 19); context.lineTo(-9, 9); context.lineTo(-28, 10); context.lineTo(-10, -5); context.closePath(); context.fill();
  context.fillStyle = '#50e3ff';
  context.beginPath(); context.moveTo(0, -26); context.lineTo(8, 8); context.lineTo(0, 18); context.lineTo(-8, 8); context.closePath(); context.fill();
  context.fillStyle = '#d9f4ff';
  context.beginPath(); context.moveTo(0, -19); context.lineTo(5, 1); context.lineTo(0, 7); context.lineTo(-5, 1); context.closePath(); context.fill();
  context.fillStyle = '#ff8c42';
  context.fillRect(-19, 7, 9, 3); context.fillRect(10, 7, 9, 3);
  context.shadowBlur = 0;
  context.fillStyle = '#ff4f65';
  context.fillRect(-5, 16, 3, random(8, 16)); context.fillRect(2, 16, 3, random(8, 16));
  context.fillStyle = '#ffe36e';
  context.fillRect(-2, 16, 4, 6);
  context.restore();
}

function drawEnemy(enemy) {
  context.save();
  context.translate(enemy.x, enemy.y);
  context.shadowBlur = 14;
  context.shadowColor = enemy.fruit === 'watermelon' ? '#86f7d1' : '#ff8c42';
  if (enemy.fruit === 'apple') {
    context.fillStyle = '#ff4f65'; context.beginPath(); context.arc(-7, 2, 10, 0, Math.PI * 2); context.arc(7, 2, 10, 0, Math.PI * 2); context.fill();
    context.fillStyle = '#ff7180'; context.beginPath(); context.arc(-5, -2, 3, 0, Math.PI * 2); context.fill();
    context.fillStyle = '#86f7d1'; context.fillRect(-2, -14, 3, 7); context.beginPath(); context.ellipse(5, -13, 6, 3, -.4, 0, Math.PI * 2); context.fill();
  } else if (enemy.fruit === 'orange') {
    context.fillStyle = '#ff8c42'; context.beginPath(); context.arc(0, 2, 13, 0, Math.PI * 2); context.fill();
    context.strokeStyle = 'rgba(255,227,110,.65)'; context.lineWidth = 1.5; context.beginPath(); context.arc(0, 2, 8, -.4, 1.1); context.stroke(); context.beginPath(); context.arc(0, 2, 8, 1.7, 3.2); context.stroke();
    context.fillStyle = '#86f7d1'; context.fillRect(-1, -13, 3, 5);
  } else if (enemy.fruit === 'strawberry') {
    context.fillStyle = '#ff4f65'; context.beginPath(); context.moveTo(0, 15); context.bezierCurveTo(-18, 4, -12, -12, 0, -7); context.bezierCurveTo(12, -12, 18, 4, 0, 15); context.fill();
    context.fillStyle = '#ffe36e'; [-7, 0, 7].forEach((x) => { context.fillRect(x, -1 + Math.abs(x) / 8, 2, 3); });
    context.fillStyle = '#86f7d1'; context.beginPath(); context.moveTo(0, -7); context.lineTo(-10, -15); context.lineTo(0, -11); context.lineTo(10, -15); context.closePath(); context.fill();
  } else {
    context.fillStyle = '#86f7d1'; context.beginPath(); context.ellipse(0, 0, enemy.type === 'heavy' ? 22 : 16, enemy.type === 'heavy' ? 16 : 12, 0, 0, Math.PI * 2); context.fill();
    context.strokeStyle = '#173f64'; context.lineWidth = 3; context.beginPath(); context.moveTo(-18, -8); context.quadraticCurveTo(0, 2, 18, -8); context.stroke(); context.beginPath(); context.moveTo(-15, 7); context.quadraticCurveTo(0, -3, 15, 7); context.stroke();
    context.fillStyle = '#ff4f65'; context.beginPath(); context.ellipse(0, -14, 7, 3, 0, 0, Math.PI * 2); context.fill();
  }
  context.shadowBlur = 0;
  context.fillStyle = 'rgba(7,17,31,.8)'; context.beginPath(); context.arc(-5, 2, 2, 0, Math.PI * 2); context.arc(5, 2, 2, 0, Math.PI * 2); context.fill();
  if (enemy.hp < enemy.maxHp) { context.fillStyle = '#ffe36e'; context.fillRect(-enemy.width / 2, -enemy.height - 7, enemy.width * (enemy.hp / enemy.maxHp), 2); }
  context.restore();
}

function drawParticles() {
  particles.forEach((particle) => { context.globalAlpha = clamp(particle.life / particle.maxLife, 0, 1); context.fillStyle = particle.color; context.fillRect(particle.x, particle.y, particle.size, particle.size); });
  context.globalAlpha = 1;
}

function drawPowerUp(powerup) {
  context.save();
  context.translate(powerup.x, powerup.y);
  context.rotate(powerup.spin);
  context.shadowBlur = 18;
  context.shadowColor = '#ffe36e';
  context.fillStyle = '#ffe36e';
  context.beginPath();
  context.moveTo(0, -powerup.size);
  context.lineTo(powerup.size, 0);
  context.lineTo(0, powerup.size);
  context.lineTo(-powerup.size, 0);
  context.closePath();
  context.fill();
  context.shadowBlur = 0;
  context.fillStyle = '#07111f';
  context.font = '700 14px Space Mono';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  context.fillText('+', 0, 1);
  context.restore();
}

function update(delta) {
  elapsed += delta;
  fireTimer = Math.max(0, fireTimer - delta);
  player.invulnerable = Math.max(0, player.invulnerable - delta);
  waveTimer += delta;
  waveBanner = Math.max(0, waveBanner - delta);
  if (waveTimer > 14 && enemies.length === 0) { wave += 1; waveTimer = 0; spawnWave(); }

  const moveSpeed = 245;
  if (keys.has('ArrowLeft') || keys.has('a')) player.x -= moveSpeed * delta;
  if (keys.has('ArrowRight') || keys.has('d')) player.x += moveSpeed * delta;
  player.x = clamp(player.x, 21, WIDTH - 21);
  if (keys.has(' ') || keys.has('fire')) fire();

  spawnTimer -= delta;
  if (spawnTimer <= 0 && enemies.length < 14) { enemies.push(createEnemy(wave > 2 && Math.random() < .2 ? 'heavy' : 'scout')); spawnTimer = Math.max(.35, 1.25 - wave * .05); }

  bullets.forEach((bullet) => { bullet.x += bullet.vx * delta; bullet.y += bullet.vy * delta; });
  enemyBullets.forEach((bullet) => { bullet.x += bullet.vx * delta; bullet.y += bullet.vy * delta; });
  powerups.forEach((powerup) => { powerup.y += powerup.speed * delta; powerup.spin += delta * 3; });
  enemies.forEach((enemy) => {
    enemy.age += delta; enemy.y += enemy.speed * delta; enemy.x += Math.sin(enemy.age * 2 + enemy.phase) * 38 * delta;
    enemy.fireTime -= delta;
    if (enemy.fireTime <= 0 && enemy.y > 20 && enemy.y < HEIGHT - 180) { enemyBullets.push({ x: enemy.x, y: enemy.y + 13, vx: (player.x - enemy.x) * .13, vy: 185 + wave * 8, radius: 4 }); enemy.fireTime = random(2.2, 4.2); }
  });

  bullets.forEach((bullet) => enemies.forEach((enemy) => {
    if (Math.abs(bullet.x - enemy.x) < enemy.width / 2 + bullet.radius && Math.abs(bullet.y - enemy.y) < enemy.height / 2 + bullet.radius) { bullet.y = -100; enemy.hp -= 1; addParticle(bullet.x, bullet.y, '#ffe36e', 4); playSound('hit'); if (enemy.hp <= 0) { const defeatedX = enemy.x; const defeatedY = enemy.y; enemy.y = HEIGHT + 100; score += enemy.type === 'heavy' ? 350 : 100; if (score > highScore) { highScore = score; localStorage.setItem('starfall-high-score', highScore); } addParticle(defeatedX, defeatedY, enemy.fruit === 'watermelon' ? '#86f7d1' : '#ff4f65', 20, 1.4); dropPowerUp(defeatedX, defeatedY); playSound('fruit'); updateHud(); } }
  }));
  enemyBullets.forEach((bullet) => { if (Math.abs(bullet.x - player.x) < 17 && Math.abs(bullet.y - player.y) < 22) { bullet.y = HEIGHT + 100; hitPlayer(); } });
  powerups.forEach((powerup) => { if (Math.abs(powerup.x - player.x) < powerup.size + 15 && Math.abs(powerup.y - player.y) < powerup.size + 20) { powerup.y = HEIGHT + 100; if (player.power < 3) { player.power += 1; missionStatus.textContent = `POWER ${player.power} ACQUIRED`; addParticle(player.x, player.y, '#ffe36e', 18, 1.2); playSound('power'); updateHud(); } } });
  enemies.forEach((enemy) => { if (enemy.y > HEIGHT + 35) enemy.y = -60; if (Math.abs(enemy.x - player.x) < enemy.width / 2 + 14 && Math.abs(enemy.y - player.y) < enemy.height / 2 + 18) { enemy.y = HEIGHT + 100; hitPlayer(); } });
  bullets.splice(0, bullets.length, ...bullets.filter((bullet) => bullet.y > -30 && bullet.y < HEIGHT + 30));
  enemyBullets.splice(0, enemyBullets.length, ...enemyBullets.filter((bullet) => bullet.y < HEIGHT + 30));
  powerups.splice(0, powerups.length, ...powerups.filter((powerup) => powerup.y < HEIGHT + 30));
  enemies.splice(0, enemies.length, ...enemies.filter((enemy) => enemy.y < HEIGHT + 80));
  particles.forEach((particle) => { particle.x += particle.vx * delta; particle.y += particle.vy * delta; particle.vy += 30 * delta; particle.life -= delta; });
  particles.splice(0, particles.length, ...particles.filter((particle) => particle.life > 0));
}

function draw() {
  drawBackground((performance.now() - lastTime) / 1000 || 0);
  bullets.forEach((bullet) => { context.fillStyle = '#ffe36e'; context.shadowBlur = 12; context.shadowColor = '#ffe36e'; context.fillRect(bullet.x - 2, bullet.y - 9, 4, 12); context.shadowBlur = 0; });
  enemyBullets.forEach((bullet) => { context.fillStyle = '#ff8c42'; context.beginPath(); context.arc(bullet.x, bullet.y, bullet.radius, 0, Math.PI * 2); context.fill(); });
  enemies.forEach(drawEnemy); powerups.forEach(drawPowerUp); drawParticles(); drawShip();
  if (waveBanner > 0) { context.globalAlpha = Math.min(1, waveBanner); context.fillStyle = '#50e3ff'; context.font = '700 22px Space Mono'; context.textAlign = 'center'; context.fillText(`WAVE ${String(wave).padStart(2, '0')}`, WIDTH / 2, HEIGHT / 2 - 40); context.globalAlpha = 1; }
}

function endGame() { gameOver = true; overlayTitle.textContent = 'GAME OVER'; overlayCopy.textContent = `최종 점수 ${formatNumber(score)}`; overlay.classList.remove('hidden'); missionStatus.textContent = 'SIGNAL LOST'; }
function togglePause() { if (gameOver) return; paused = !paused; overlayTitle.textContent = 'PAUSED'; overlayCopy.textContent = 'P를 눌러 계속하기'; overlay.classList.toggle('hidden', !paused); }
function restart() { bullets.length = 0; enemyBullets.length = 0; enemies.length = 0; powerups.length = 0; particles.length = 0; player = makePlayer(); score = 0; wave = 1; waveTimer = 0; spawnTimer = 0; fireTimer = 0; paused = false; gameOver = false; overlay.classList.add('hidden'); missionStatus.textContent = 'SECTOR CLEAR'; spawnWave(); updateHud(); }

function loop(time = 0) { const delta = Math.min(.035, (time - lastTime) / 1000 || 0); lastTime = time; if (!paused && !gameOver) update(delta); draw(); requestAnimationFrame(loop); }

document.addEventListener('keydown', (event) => { if (['ArrowLeft', 'ArrowRight', ' ', 'a', 'd', 'p'].includes(event.key) || event.code === 'Space') event.preventDefault(); if (event.key.toLowerCase() === 'p') togglePause(); else { keys.add(event.key); if (event.key === ' ' || event.code === 'Space') { keys.add(' '); fire(); } } });
document.addEventListener('keyup', (event) => keys.delete(event.key));
document.querySelector('#pause-button').addEventListener('click', togglePause);
document.querySelector('#restart-button').addEventListener('click', restart);
document.querySelectorAll('[data-control]').forEach((button) => { const control = button.dataset.control; const controlKey = control === 'left' ? 'ArrowLeft' : control === 'right' ? 'ArrowRight' : 'fire'; const press = (event) => { event.preventDefault(); unlockAudio(); keys.add(controlKey); if (control === 'fire') fire(); }; const release = (event) => { event.preventDefault(); keys.delete(controlKey); }; button.addEventListener('pointerdown', press); button.addEventListener('pointerup', release); button.addEventListener('pointercancel', release); button.addEventListener('pointerleave', release); });

restart();
requestAnimationFrame(loop);
