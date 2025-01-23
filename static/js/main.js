document.addEventListener('DOMContentLoaded', () => {
    const board = document.getElementById('board');
    const cells = Array.from({ length: 9 }, () => document.createElement('div'));
    cells.forEach(cell => board.appendChild(cell));

    board.addEventListener('click', event => {
        if (event.target.tagName === 'DIV' && !event.target.textContent) {
            event.target.textContent = 'X';  // Example move, you can implement your own logic
            // Emit move event to server
            socket.emit('move', { session: sessionId, cell: cells.indexOf(event.target), player: username });
        }
    });

    socket.on('move', data => {
        cells[data.cell].textContent = data.player === username ? 'X' : 'O';
    });
});