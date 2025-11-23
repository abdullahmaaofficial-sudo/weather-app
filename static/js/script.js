/* ============================================
   WEATHER APP - JAVASCRIPT
   ============================================ */

// DOM Elements
const slider = document.getElementById('hourSlider');
const nextBtn = document.getElementById('nextHour');
const prevBtn = document.getElementById('prevHour');
const loading = document.getElementById('loading');
const forms = document.querySelectorAll('form');
const unitSelects = document.querySelectorAll('#unit, #unit-mobile');
const dayLinks = document.querySelectorAll('.day-link');

// ============================
// Loading Spinner
// ============================
function showLoading() {
    if (loading) loading.classList.remove('hidden');
}

function hideLoading() {
    if (loading) loading.classList.add('hidden');
}

// Hide on page load
window.addEventListener('load', hideLoading);
window.addEventListener('pageshow', hideLoading);

// ============================
// Hourly Slider Navigation
// ============================
function getScrollAmount() {
    if (!slider) return 0;
    const card = slider.querySelector('.hourly-card');
    if (!card) return 0;
    
    const style = window.getComputedStyle(card);
    const gap = parseFloat(window.getComputedStyle(slider).gap) || 16;
    const cardWidth = card.offsetWidth + gap;
    
    // Cards to scroll based on screen width
    let cards = 3;
    if (window.innerWidth <= 480) cards = 1;
    else if (window.innerWidth <= 768) cards = 2;
    
    return cardWidth * cards;
}

function scrollSlider(direction) {
    if (!slider) return;
    const amount = getScrollAmount();
    slider.scrollBy({
        left: direction === 'next' ? amount : -amount,
        behavior: 'smooth'
    });
}

if (nextBtn && prevBtn) {
    nextBtn.addEventListener('click', () => scrollSlider('next'));
    prevBtn.addEventListener('click', () => scrollSlider('prev'));
}

// ============================
// Form Submission (All Forms)
// ============================
forms.forEach(form => {
    form.addEventListener('submit', e => {
        const input = form.querySelector('input[name="city_name"]');
        if (input && input.value.trim()) {
            showLoading();
        }
    });
});

// ============================
// Unit Change (Desktop & Mobile)
// ============================
function handleUnitChange(selectElement) {
    showLoading();
    
    fetch('/get_unit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ unit: selectElement.value })
    })
    .then(res => res.json())
    .then(() => {
        setTimeout(() => location.reload(), 100);
    })
    .catch(err => {
        console.error('Unit change error:', err);
        hideLoading();
    });
}

// Add event listener to all unit selectors
unitSelects.forEach(select => {
    select.addEventListener('change', function() {
        // Sync both selects
        unitSelects.forEach(s => {
            if (s !== this) s.value = this.value;
        });
        handleUnitChange(this);
    });
});

// ============================
// Day Link Navigation
// ============================
dayLinks.forEach(link => {
    link.addEventListener('click', () => showLoading());
});

// ============================
// Card Hover Effects (Touch)
// ============================
const dailyCards = document.querySelectorAll('.daily-card');

dailyCards.forEach(card => {
    card.addEventListener('touchstart', function() {
        dailyCards.forEach(c => c.classList.remove('touch-active'));
        this.classList.add('touch-active');
    }, { passive: true });
});

// Remove touch-active on scroll
window.addEventListener('scroll', () => {
    dailyCards.forEach(c => c.classList.remove('touch-active'));
}, { passive: true });

// ============================
// Keyboard Navigation
// ============================
document.addEventListener('keydown', e => {
    // Only if not typing in an input
    if (document.activeElement.tagName === 'INPUT') return;
    
    if (e.key === 'ArrowLeft' && slider) {
        scrollSlider('prev');
    } else if (e.key === 'ArrowRight' && slider) {
        scrollSlider('next');
    }
});

// ============================
// Intersection Observer for Animations
// ============================
const observerOptions = {
    root: null,
    rootMargin: '0px',
    threshold: 0.1
};

const animateOnScroll = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
        }
    });
}, observerOptions);

// Observe daily cards for scroll animation
document.querySelectorAll('.daily-card').forEach(card => {
    animateOnScroll.observe(card);
});

// ============================
// Touch Swipe Support
// ============================
let touchStartX = 0;

if (slider) {
    slider.addEventListener('touchstart', e => {
        touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });
}

// ============================
// FIXED: Geolocation Function with IP Fallback
// ============================
function getLocation() {
    // Show loading spinner
    showLoading();

    // First, try to get user's city via client-side IP geolocation
    fetch('http://ip-api.com/json/')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success' && data.city) {
                // Use IP-based city detection (more accurate for weather)
                window.location.href = `/location?city=${encodeURIComponent(data.city)}`;
                return;
            }
            // If IP geolocation fails, fall back to GPS
            useGPSLocation();
        })
        .catch(error => {
            console.log('IP geolocation failed, trying GPS:', error);
            // If IP API fails, fall back to GPS
            useGPSLocation();
        });
}

function useGPSLocation() {
    // Check if geolocation is supported
    if (!navigator.geolocation) {
        hideLoading();
        alert('Geolocation is not supported by your browser.');
        return;
    }

    // Get current position with proper options
    navigator.geolocation.getCurrentPosition(
        // Success callback
        function(position) {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            
            // Use proper URL encoding and redirect
            window.location.href = `/location?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`;
        },
        // Error callback
        function(error) {
            hideLoading();
            
            let errorMessage = 'Unable to get your location. ';
            
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    errorMessage += 'Please allow location access in your browser settings.';
                    break;
                case error.POSITION_UNAVAILABLE:
                    errorMessage += 'Location information is unavailable.';
                    break;
                case error.TIMEOUT:
                    errorMessage += 'Location request timed out. Please try again.';
                    break;
                default:
                    errorMessage += 'An unknown error occurred.';
            }
            
            alert(errorMessage);
        },
        // Options for better accuracy
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        }
    );
}
