document.addEventListener('DOMContentLoaded', function() {
    console.log('Flask app loaded successfully!');
    // Timer functionality
    const timer = document.getElementById('timer');
    const arriveBtn = document.getElementById('arrive-btn');
    const leaveBtn = document.getElementById('leave-btn');
    const pauseBtn = document.getElementById('pause-btn');

    let isPaused = false;
    let timerInterval;

    // Start timer if we're on a page with an active timer
    if (timer) {
        const startTime = parseInt(timer.dataset.start);
        const totalBreakDuration = parseInt(timer.dataset.breaks || 0);
        isPaused = timer.dataset.paused === 'true';

        // Update the pause button text based on current state
        if (pauseBtn) {
            updatePauseButtonText();
        }

        // Update timer every second
        function updateTimer() {
            if (isPaused) return;

            const now = Math.floor(Date.now() / 1000);
            const diff = now - startTime - totalBreakDuration;

            const hours = Math.floor(diff / 3600);
            const minutes = Math.floor((diff % 3600) / 60);
            const seconds = diff % 60;

            timer.textContent = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        }

        // Initial update
        updateTimer();

        // Set interval for updates
        timerInterval = setInterval(updateTimer, 1000);
    }

    function updatePauseButtonText() {
        if (pauseBtn) {
            if (isPaused) {
                pauseBtn.textContent = 'Resume Work';
                pauseBtn.classList.add('resume-btn');
                pauseBtn.classList.remove('pause-btn');
            } else {
                pauseBtn.textContent = 'Pause';
                pauseBtn.classList.add('pause-btn');
                pauseBtn.classList.remove('resume-btn');
            }
        }
    }

    // Handle arrive button click
    if (arriveBtn) {
        arriveBtn.addEventListener('click', function() {
            fetch('/api/arrive', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                // Reload the page to show the active timer
                window.location.reload();
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Failed to record arrival time. Please try again.');
            });
        });
    }

    // Handle pause/resume button click
    if (pauseBtn) {
        pauseBtn.addEventListener('click', function() {
            const entryId = pauseBtn.dataset.id;

            fetch(`/api/toggle-pause/${entryId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                isPaused = data.is_paused;
                updatePauseButtonText();

                // Show a notification
                const notification = document.createElement('div');
                notification.className = 'notification';
                notification.textContent = data.message;
                document.body.appendChild(notification);

                // Remove notification after 3 seconds
                setTimeout(() => {
                    notification.remove();
                }, 3000);
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Failed to pause/resume. Please try again.');
            });
        });
    }

    // Handle leave button click
    if (leaveBtn) {
        leaveBtn.addEventListener('click', function() {
            const entryId = leaveBtn.dataset.id;

            fetch(`/api/leave/${entryId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                // Reload the page to update the UI
                window.location.reload();
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Failed to record departure time. Please try again.');
            });
        });
    }
});
