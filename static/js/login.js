/**
 * Big Royal SaaS — Login Page Enhancements
 *
 * Pequeñas mejoras de UX para el formulario de inicio de sesión:
 * - Deshabilita el botón mientras se envía para evitar doble submit.
 * - Muestra un indicador de carga.
 */

document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("loginForm");
    if (!form) return;

    const btn = document.getElementById("btnLogin");

    form.addEventListener("submit", function () {
        if (btn) {
            btn.disabled = true;
            btn.textContent = "Iniciando sesión…";
        }
    });
});
