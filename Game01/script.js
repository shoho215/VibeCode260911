const COLS = 10;
const ROWS = 20;
const BLOCK_SIZE = 30;
const COLORS = [null, '#57d9e8', '#f7d65b', '#ff784f', '#9d87ed', '#57c878', '#ff5d93', '#c8f169'];
const SHAPES = [
  [[1, 1, 1, 1]],
  [[2, 2], [2, 2]],
  [[0, 3, 0], [3, 3, 3]],
  [[4, 0, 0], [4, 4, 4]],
  [[0, 0, 5], [5, 5, 5]],
  [[0, 6, 6], [6, 6, 0]],
  [[7, 7, 0], [0, 7, 7]]
];

const boardCanvas = document.querySelector('#game-board');
const nextCanvas = document.querySelector('#next-board');
const boardContext = boardCanvas.getContext('2d');
const nextContext = nextCanvas.getContext('2d');
const scoreElement = document.querySelector('#score');
const highScoreElement = document.querySelector('#high-score');
const levelElement = document.querySelector('#level');
const linesElement = document.querySelector('#lines');
const overlay = document.querySelector('#game-overlay');
const overlayTitle = document.querySelector('#overlay-title');

let board;
let currentPiece;
let nextPiece;
let score = 0;
let lines = 0;
let level = 1;
let dropTimer = 0;
let lastTime = 0;
let isPaused = false;
let isGameOver = false;
let bag = [];
let highScore = Number(localStorage.getItem('neon-tetris-high-score')) || 0;
highScoreElement.textContent = highScore;

function createBoard() {
  return Array.from({ length: ROWS }, () => Array(COLS).fill(0));
}

function refillBag() {
  bag = [0, 1, 2, 3, 4, 5, 6];
  for (let index = bag.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(Math.random() * (index + 1));
    [bag[index], bag[randomIndex]] = [bag[randomIndex], bag[index]];
  }
}

function createPiece() {
  if (!bag.length) refillBag();
  const shape = SHAPES[bag.pop()].map((row) => [...row]);
  return { shape, x: Math.floor((COLS - shape[0].length) / 2), y: 0 };
}

function drawCell(context, x, y, size, color) {
  context.fillStyle = color;
  context.fillRect(x * size + 1, y * size + 1, size - 2, size - 2);
  context.fillStyle = 'rgba(255,255,255,.23)';
  context.fillRect(x * size + 2, y * size + 2, size - 7, 3);
  context.strokeStyle = 'rgba(16,21,27,.4)';
  context.strokeRect(x * size + 1, y * size + 1, size - 2, size - 2);
}

function drawBoard() {
  boardContext.fillStyle = '#17242a';
  boardContext.fillRect(0, 0, boardCanvas.width, boardCanvas.height);
  boardContext.strokeStyle = 'rgba(231,240,232,.08)';
  for (let x = 0; x <= COLS; x += 1) {
    boardContext.beginPath(); boardContext.moveTo(x * BLOCK_SIZE, 0); boardContext.lineTo(x * BLOCK_SIZE, boardCanvas.height); boardContext.stroke();
  }
  for (let y = 0; y <= ROWS; y += 1) {
    boardContext.beginPath(); boardContext.moveTo(0, y * BLOCK_SIZE); boardContext.lineTo(boardCanvas.width, y * BLOCK_SIZE); boardContext.stroke();
  }
  board.forEach((row, y) => row.forEach((value, x) => value && drawCell(boardContext, x, y, BLOCK_SIZE, COLORS[value])));
  if (currentPiece) currentPiece.shape.forEach((row, y) => row.forEach((value, x) => value && drawCell(boardContext, currentPiece.x + x, currentPiece.y + y, BLOCK_SIZE, COLORS[value])));
}

function drawNext() {
  nextContext.fillStyle = 'rgba(255,255,255,.27)';
  nextContext.fillRect(0, 0, nextCanvas.width, nextCanvas.height);
  const size = 24;
  const offsetX = (5 - nextPiece.shape[0].length) * size / 2;
  const offsetY = (5 - nextPiece.shape.length) * size / 2;
  nextPiece.shape.forEach((row, y) => row.forEach((value, x) => value && drawCell(nextContext, x + offsetX / size, y + offsetY / size, size, COLORS[value])));
}

function collides(piece) {
  return piece.shape.some((row, y) => row.some((value, x) => {
    if (!value) return false;
    const boardX = piece.x + x;
    const boardY = piece.y + y;
    return boardX < 0 || boardX >= COLS || boardY >= ROWS || (boardY >= 0 && board[boardY][boardX]);
  }));
}

function mergePiece() {
  currentPiece.shape.forEach((row, y) => row.forEach((value, x) => {
    if (value && currentPiece.y + y >= 0) board[currentPiece.y + y][currentPiece.x + x] = value;
  }));
}

function clearLines() {
  let cleared = 0;
  board = board.filter((row) => {
    if (row.every(Boolean)) { cleared += 1; return false; }
    return true;
  });
  while (board.length < ROWS) board.unshift(Array(COLS).fill(0));
  if (cleared) {
    const points = [0, 100, 300, 500, 800][cleared] * level;
    score += points;
    lines += cleared;
    level = Math.floor(lines / 10) + 1;
    updateStats();
  }
}

function rotatePiece() {
  const rotated = currentPiece.shape[0].map((_, index) => currentPiece.shape.map((row) => row[index]).reverse());
  const previousShape = currentPiece.shape;
  currentPiece.shape = rotated;
  if (collides(currentPiece)) {
    currentPiece.x += 1;
    if (collides(currentPiece)) currentPiece.x -= 2;
    if (collides(currentPiece)) { currentPiece.x += 1; currentPiece.shape = previousShape; }
  }
  drawBoard();
}

function movePiece(direction) {
  currentPiece.x += direction;
  if (collides(currentPiece)) currentPiece.x -= direction;
  drawBoard();
}

function dropPiece(manual = false) {
  currentPiece.y += 1;
  if (collides(currentPiece)) {
    currentPiece.y -= 1;
    mergePiece();
    clearLines();
    currentPiece = nextPiece;
    nextPiece = createPiece();
    drawNext();
    if (collides(currentPiece)) endGame();
  } else if (manual) {
    score += 1;
    updateStats();
  }
  dropTimer = 0;
  drawBoard();
}

function hardDrop() {
  let distance = 0;
  while (!collides(currentPiece)) { currentPiece.y += 1; distance += 1; }
  currentPiece.y -= 1;
  score += Math.max(0, distance - 1) * 2;
  updateStats();
  dropPiece();
}

function updateStats() {
  scoreElement.textContent = score;
  highScore = Math.max(highScore, score);
  highScoreElement.textContent = highScore;
  levelElement.textContent = level;
  linesElement.textContent = lines;
  localStorage.setItem('neon-tetris-high-score', highScore);
}

function endGame() {
  isGameOver = true;
  overlayTitle.textContent = 'GAME OVER';
  overlay.classList.remove('hidden');
}

function togglePause() {
  if (isGameOver) return;
  isPaused = !isPaused;
  overlayTitle.textContent = 'PAUSED';
  overlay.classList.toggle('hidden', !isPaused);
}

function restart() {
  board = createBoard(); score = 0; lines = 0; level = 1; dropTimer = 0; isPaused = false; isGameOver = false; bag = [];
  currentPiece = createPiece(); nextPiece = createPiece(); overlay.classList.add('hidden'); updateStats(); drawNext(); drawBoard();
}

function gameLoop(time = 0) {
  const delta = time - lastTime; lastTime = time;
  if (!isPaused && !isGameOver) { dropTimer += delta; if (dropTimer > Math.max(110, 750 - (level - 1) * 55)) dropPiece(); }
  requestAnimationFrame(gameLoop);
}

document.addEventListener('keydown', (event) => {
  if (['ArrowLeft', 'ArrowRight', 'ArrowDown', 'ArrowUp', ' '].includes(event.key)) event.preventDefault();
  if (event.key === 'ArrowLeft') movePiece(-1);
  if (event.key === 'ArrowRight') movePiece(1);
  if (event.key === 'ArrowDown') dropPiece(true);
  if (event.key === 'ArrowUp') rotatePiece();
  if (event.key === ' ') hardDrop();
  if (event.key.toLowerCase() === 'p') togglePause();
});

document.querySelectorAll('[data-action]').forEach((button) => button.addEventListener('click', () => {
  const action = button.dataset.action;
  if (action === 'left') movePiece(-1);
  if (action === 'right') movePiece(1);
  if (action === 'rotate') rotatePiece();
  if (action === 'drop') dropPiece(true);
}));
document.querySelector('#pause-button').addEventListener('click', togglePause);
document.querySelector('#restart-overlay').addEventListener('click', restart);
restart();
requestAnimationFrame(gameLoop);
