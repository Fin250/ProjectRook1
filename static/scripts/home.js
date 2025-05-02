document.addEventListener("DOMContentLoaded", () => {
    const slides = document.querySelectorAll(".slideshow img");
    let currentIndex = 0;

    // Ensure the first slide is visible on page load
    slides[currentIndex].classList.add("active");

    function showSlide(index) {
        slides.forEach((slide, i) => {
            slide.classList.toggle("active", i === index);
        });
    }

    function nextSlide() {
        currentIndex = (currentIndex + 1) % slides.length;
        showSlide(currentIndex);
    }

    // Automatically change slides every 5 seconds
    setInterval(nextSlide, 5000);

    const countdownElements = document.querySelectorAll(".countdown-text");

    countdownElements.forEach((countdownElement) => {
        const eventDate = new Date(countdownElement.dataset.date);

        const updateCountdown = () => {
            const now = new Date();
            const timeDifference = eventDate - now;

            if (timeDifference <= 0) {
                countdownElement.textContent = "Event is live!";
                return;
            }

            const days = Math.floor(timeDifference / (1000 * 60 * 60 * 24));
            const hours = Math.floor((timeDifference / (1000 * 60 * 60)) % 24);
            const minutes = Math.floor((timeDifference / (1000 * 60)) % 60);
            const seconds = Math.floor((timeDifference / 1000) % 60);

            countdownElement.textContent = `${days}d ${hours}h ${minutes}m ${seconds}s`;
        };

        updateCountdown();
        setInterval(updateCountdown, 1000); // Update every second
    });
});