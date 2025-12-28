/*
 * Minimal CRM interactions for PurpleAdmin layout.
 */

document.addEventListener('DOMContentLoaded', function () {
  const toggles = document.querySelectorAll('[data-crm-toggle="sidebar"]');
  toggles.forEach((toggle) => {
    toggle.addEventListener('click', function () {
      document.body.classList.toggle('sidebar-collapsed');
    });
  });
});
