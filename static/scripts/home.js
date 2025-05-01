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
});