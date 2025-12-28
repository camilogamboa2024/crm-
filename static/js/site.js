/*
 * Custom JavaScript for the Gamboa Rental Cars website.
 *
 * Handles the responsive navigation menu on small screens and provides
 * simple client-side behaviour such as preventing default form submissions
 * in the contact form (demonstration purposes).
 */

document.addEventListener('DOMContentLoaded', function () {
  const hamburger = document.getElementById('hamburger');
  const navMenu = document.getElementById('navMenu');

  if (hamburger) {
    hamburger.addEventListener('click', function () {
      navMenu.classList.toggle('open');
      if (navMenu.style.display === 'flex') {
        navMenu.style.display = 'none';
      } else {
        navMenu.style.display = 'flex';
        navMenu.style.flexDirection = 'column';
      }
    });
  }

  // Prevent actual form submission for the demo contact form
  const contactForm = document.querySelector('.contact-form');
  if (contactForm) {
    contactForm.addEventListener('submit', function (e) {
      e.preventDefault();
      alert('Gracias por tu mensaje. Nos pondremos en contacto contigo pronto.');
      contactForm.reset();
    });
  }
});